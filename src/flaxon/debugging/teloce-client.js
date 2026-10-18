// Development adapter. The server never injects this client in production.

/**
 * Values the server embeds in the page (see `TeloceIntegration._debug_client_script`).
 * @typedef {Object} TeloceDebugConfig
 * @property {string} token    Per-process debugger token. It changes on every Python restart.
 * @property {string} revision Fingerprint of the UI sources this page was rendered from.
 */

/**
 * JSON body returned by `POST /__debug__/teloce/reload`.
 * @typedef {Object} ReloadResult
 * @property {string}  revision Fingerprint of the UI sources on the server right now.
 * @property {boolean} failed   True when the last rebuild failed.
 */

/**
 * A diagnostic sent to `/__debug__/teloce/errors` and shown in the overlay.
 * @typedef {Object} DebugReport
 * @property {string}  [category]  compile | ssr | runtime | hydration | browser | api | typecheck
 * @property {string}  [message]
 * @property {string}  [stack]
 * @property {string}  [component]
 * @property {string}  [filename]
 * @property {number}  [line]
 * @property {number}  [column]
 * @property {string}  [request_id]
 */

/**
 * A button shown inside the status banner.
 * @typedef {Object} NoticeAction
 * @property {string}     label
 * @property {() => void} onClick
 */

const RELOAD_ENDPOINT = '/__debug__/teloce/reload';
const POLL_INTERVAL_MS = 2000;
const MAX_BACKOFF_MS = 30000;

/**
 * Error code the server sends when it rejects the page's origin (see `ORIGIN_REJECTED` in
 * `debugging/teloce.py`). Reloading can never fix it, unlike a stale token after a restart.
 */
const ORIGIN_REJECTED = 'FX-DEBUG-ORIGIN';

/** sessionStorage key: set after the one allowed reload for a 403 (see `claimOnce`). */
const FORBIDDEN_KEY = 'flaxon:teloce-403';
/** sessionStorage key: timestamps of recent automatic reloads (see `mayAutoReload`). */
const RELOADS_KEY = 'flaxon:teloce-reloads';
/** More than this many automatic reloads inside the window is treated as a loop. */
const MAX_AUTO_RELOADS = 6;
const AUTO_RELOAD_WINDOW_MS = 20000;

/**
 * Mark `key` as used in this tab. Returns true only the first time.
 * If sessionStorage is unavailable it returns false, so callers never loop.
 * @param {string} key
 * @returns {boolean}
 */
function claimOnce(key) {
  try {
    if (sessionStorage.getItem(key) === '1') return false;
    sessionStorage.setItem(key, '1');
    return true;
  } catch (_) { return false; }
}

/**
 * Forget a sessionStorage key. Storage errors are ignored.
 * @param {string} key
 * @returns {void}
 */
function forget(key) {
  try { sessionStorage.removeItem(key); } catch (_) { /* storage unavailable */ }
}

/**
 * Loop breaker for automatic reloads. Call it right before `location.reload()`.
 * Records the reload and returns false when this tab already reloaded
 * `MAX_AUTO_RELOADS` times within `AUTO_RELOAD_WINDOW_MS`, whatever the cause was.
 * If sessionStorage is unavailable the loop cannot be detected, so it returns true
 * (plain live reload keeps working; only the 403 path is strict, see `claimOnce`).
 * @returns {boolean} true when another automatic reload is safe.
 */
function mayAutoReload() {
  try {
    const now = Date.now();
    const parsed = JSON.parse(sessionStorage.getItem(RELOADS_KEY) || '[]');
    const recent = (Array.isArray(parsed) ? parsed : []).filter(t => now - t < AUTO_RELOAD_WINDOW_MS);
    if (recent.length >= MAX_AUTO_RELOADS) return false;
    recent.push(now);
    sessionStorage.setItem(RELOADS_KEY, JSON.stringify(recent));
    return true;
  } catch (_) { return true; }
}

/**
 * Read why the server answered 403. Older servers send no code, so both fields may be empty.
 * @param {Response} response
 * @returns {Promise<{code: string, message: string}>}
 */
async function rejectionOf(response) {
  try {
    const { error } = await response.json();
    return { code: String(error?.code || ''), message: String(error?.message || '').slice(0, 600) };
  } catch (_) { return { code: '', message: '' }; }
}

/**
 * Say why a report was rejected, so "no mapped location" is never mistaken for a broken mapping.
 * @param {Response} response
 * @returns {Promise<string>}
 */
async function transportNote(response) {
  const status = Number(response.status) || 0;
  const rejection = await rejectionOf(response);
  if (rejection.code === ORIGIN_REJECTED) {
    return `Source mapping unavailable: the debug endpoint rejected this origin (${status}).`;
  }
  return `Source mapping unavailable: the debug endpoint answered ${status}.`;
}

/** Selector scope for the error dialog and the status banner, so app CSS cannot restyle them. */
const OVERLAY = 'dialog[data-flaxon-error]';
const NOTICE = '[data-flaxon-notice]';

/**
 * Error overlay and status banner styles. Applied through a constructed stylesheet, which a
 * Content-Security-Policy without 'unsafe-inline' does not block (a <style> element is the fallback).
 * Palette: canvas #0d1117, surface #161b22, text #e6edf0, muted #8b949e, border #30363d.
 */
const OVERLAY_CSS = `
${OVERLAY},${NOTICE}{--bg:#0d1117;--surface:#161b22;--raised:#1c2128;--text:#e6edf0;--muted:#8b949e;--faint:#6e7681;--line:#30363d;--line-strong:#484f58;--danger:#f85149;--warn:#d29922;--accent:#58a6ff;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif;--mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace}
${OVERLAY}{box-sizing:border-box;width:min(760px,calc(100vw - 32px));max-height:min(86vh,720px);margin:auto;padding:0;overflow:hidden;color:var(--text);background:var(--bg);border:1px solid var(--line);border-radius:12px;font:14px/1.5 var(--sans);text-align:left;color-scheme:dark;box-shadow:0 0 0 1px rgba(1,4,9,.5),0 24px 56px rgba(1,4,9,.6)}
${OVERLAY}[open]{display:flex;flex-direction:column;animation:fx-in .16s ease-out}
${OVERLAY}::backdrop{background:rgba(1,4,9,.74);backdrop-filter:blur(3px)}
${OVERLAY}:focus{outline:none}
${OVERLAY} *{box-sizing:border-box}
${OVERLAY} [hidden]{display:none !important}
@keyframes fx-in{from{opacity:0;transform:translateY(6px)}}

${OVERLAY} .fx-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 10px 10px 20px;background:var(--surface);border-bottom:1px solid var(--line)}
${OVERLAY} .fx-kind{display:inline-flex;align-items:center;gap:10px;font-size:13px;font-weight:600}
${OVERLAY} .fx-kind::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--danger);box-shadow:0 0 0 3px rgba(248,81,73,.2)}
${OVERLAY} .fx-close{display:grid;place-items:center;width:28px;height:28px;padding:0;border:0;border-radius:6px;background:transparent;color:var(--muted);cursor:pointer;transition:background .12s,color .12s}
${OVERLAY} .fx-close:hover{background:var(--raised);color:var(--text)}

${OVERLAY} .fx-body{display:grid;grid-auto-rows:max-content;gap:16px;align-content:start;min-height:0;padding:20px 20px 12px;overflow:auto}
${OVERLAY} .fx-title{margin:0;color:var(--text);font:600 18px/1.4 var(--sans);overflow-wrap:anywhere}
${OVERLAY} .fx-where{justify-self:start;display:inline-flex;align-items:baseline;gap:10px;max-width:100%;margin:-8px 0 0;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--muted);font:12.5px/1.5 var(--mono);text-align:left;cursor:pointer;transition:border-color .12s,color .12s}
${OVERLAY} .fx-where:hover{border-color:var(--line-strong);color:var(--text)}
${OVERLAY} .fx-path{overflow-wrap:anywhere}
${OVERLAY} .fx-hint{flex:none;color:var(--muted);font:12px/1.5 var(--sans)}
${OVERLAY} .fx-tip{margin:-8px 0 0;color:var(--muted);font:13px/1.5 var(--sans);overflow-wrap:anywhere}
${OVERLAY} .fx-note{margin:0;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--muted);font:12.5px/1.5 var(--sans);overflow-wrap:anywhere}

${OVERLAY} .fx-src{display:grid;overflow:auto;padding:6px 0;border:1px solid var(--line);border-radius:8px;background:var(--surface);font:12.5px/1.7 var(--mono)}
${OVERLAY} .fx-ln{display:grid;grid-template-columns:52px minmax(max-content,1fr);white-space:pre}
${OVERLAY} .fx-num{padding-right:14px;text-align:right;color:var(--faint);user-select:none}
${OVERLAY} .fx-hit{background:rgba(248,81,73,.12);box-shadow:inset 2px 0 var(--danger)}
${OVERLAY} .fx-hit .fx-num{color:var(--text)}

${OVERLAY} .fx-sum{display:flex;align-items:center;gap:8px;padding:2px 0;color:var(--text);font-size:13px;font-weight:600;list-style:none;cursor:pointer}
${OVERLAY} .fx-sum::-webkit-details-marker{display:none}
${OVERLAY} .fx-sum::before{content:"";flex:none;border:solid transparent;border-width:4px 0 4px 6px;border-left-color:var(--muted);transition:transform .15s}
${OVERLAY} details[open]>.fx-sum::before{transform:rotate(90deg)}
${OVERLAY} .fx-count{color:var(--muted);font-weight:400}
${OVERLAY} .fx-frames{margin:8px 0 0;padding:0;overflow:hidden;list-style:none;border:1px solid var(--line);border-radius:8px;background:var(--surface);font:12.5px/1.55 var(--mono)}
${OVERLAY} .fx-frame{padding:8px 12px;border-top:1px solid var(--line);color:var(--muted)}
${OVERLAY} .fx-frame:first-child{border-top:0;box-shadow:inset 2px 0 var(--danger)}
${OVERLAY} .fx-frame:first-child .fx-fn{color:var(--text)}
${OVERLAY} .fx-fn{display:block;font-weight:600}
${OVERLAY} .fx-frame:first-child.fx-bare .fx-at{color:var(--text)}
${OVERLAY} .fx-at{display:block;overflow-wrap:anywhere}
${OVERLAY} .fx-last{padding:0}
${OVERLAY} .fx-more{display:block;width:100%;padding:8px 12px;border:0;background:transparent;color:var(--accent);font:13px/1.4 var(--sans);text-align:left;cursor:pointer}
${OVERLAY} .fx-more:hover{background:var(--raised)}
${OVERLAY} .fx-raw .fx-sum{color:var(--muted);font-weight:500}
${OVERLAY} .fx-pre{max-height:220px;margin:8px 0 0;padding:12px;overflow:auto;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--muted);font:12px/1.6 var(--mono);white-space:pre-wrap;overflow-wrap:anywhere}

${OVERLAY} .fx-foot{display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding:12px 20px 16px;border-top:1px solid var(--line)}
${OVERLAY} .fx-spacer{flex:1}
${OVERLAY} .fx-btn,${NOTICE} .fx-btn{display:inline-flex;align-items:center;justify-content:center;padding:8px 12px;border:1px solid var(--line);border-radius:6px;background:var(--surface);color:var(--text);font:500 13px/1.2 var(--sans);text-decoration:none;cursor:pointer;transition:background .12s,border-color .12s}
${OVERLAY} .fx-btn:hover,${NOTICE} .fx-btn:hover{border-color:var(--line-strong);background:var(--raised)}
${OVERLAY} .fx-btn:active,${NOTICE} .fx-btn:active{transform:translateY(.5px)}
${OVERLAY} .fx-primary{border-color:var(--accent);background:var(--accent);color:#0d1117;font-weight:600}
${OVERLAY} .fx-primary:hover{border-color:#79b8ff;background:#79b8ff}
${OVERLAY} button:focus-visible,${OVERLAY} a:focus-visible,${OVERLAY} summary:focus-visible,${NOTICE} button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

${NOTICE}{position:fixed;left:16px;right:16px;bottom:16px;z-index:2147483647;display:flex;align-items:center;gap:12px;max-width:680px;margin:0 auto;padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--text);font:13px/1.5 var(--sans);box-shadow:0 12px 32px rgba(1,4,9,.55)}
${NOTICE}::before{content:"";flex:none;width:8px;height:8px;border-radius:50%;background:var(--warn)}
${NOTICE} .fx-text{flex:1}

@media (max-width:520px){
  ${OVERLAY}{width:calc(100vw - 16px);max-height:92vh}
  ${OVERLAY} .fx-body{padding:16px 16px 8px}
  ${OVERLAY} .fx-foot{padding:12px 16px 16px}
  ${OVERLAY} .fx-foot .fx-btn{flex:1 1 auto}
  ${OVERLAY} .fx-spacer{display:none}
}
@media (prefers-reduced-motion:reduce){
  ${OVERLAY}[open]{animation:none}
  ${OVERLAY} *{transition:none !important}
}
`;

/** Human label for each report category shown in the overlay header. */
const CATEGORY_LABELS = {
  compile: 'Compile error', ssr: 'Server render error', runtime: 'Runtime error',
  hydration: 'Hydration error', browser: 'Browser error', api: 'API error', typecheck: 'Type error',
};

/** Frames shown before the "Show more" control appears. */
const VISIBLE_FRAMES = 5;

/**
 * Drop the page origin from URLs so long dev-server hosts (Codespaces, tunnels) do not bury the path.
 * @param {string} text
 * @returns {string}
 */
function shorten(text) {
  const origin = globalThis.location?.origin;
  return origin ? String(text).split(origin).join('') : String(text);
}

/**
 * Split a browser stack into frames and drop the leading "Name: message" line.
 * Understands Chrome ("at fn (url:1:2)", "at url:1:2") and Firefox/Safari ("fn@url:1:2").
 * @param {string | undefined} stack
 * @returns {{fn: string, at: string}[]} `fn` is empty for frames without a function name.
 */
function parseStack(stack) {
  /** @type {{fn: string, at: string}[]} */
  const frames = [];
  for (const raw of String(stack || '').split('\n')) {
    const line = raw.trim();
    const chrome = line.match(/^at\s+(?:(.+?)\s+\((.+)\)|(.+))$/);
    if (chrome) { frames.push({ fn: chrome[1] || '', at: chrome[2] || chrome[3] }); continue; }
    const gecko = line.match(/^([^@\s]*)@(.+)$/);
    if (gecko) frames.push({ fn: gecko[1] || '', at: gecko[2] });
  }
  return frames;
}

/**
 * Parse the server's source excerpt, whose lines look like "12: <markup>".
 * @param {string | undefined} excerpt
 * @param {number} errorLine 1-based line to highlight, or 0 when unknown.
 * @returns {{num: number, code: string, hit: boolean}[]}
 */
function parseExcerpt(excerpt, errorLine) {
  /** @type {{num: number, code: string, hit: boolean}[]} */
  const rows = [];
  for (const line of String(excerpt || '').split('\n')) {
    const match = line.match(/^(\d+): ?(.*)$/);
    if (match) rows.push({ num: Number(match[1]), code: match[2], hit: Number(match[1]) === errorLine });
  }
  return rows;
}

/**
 * Schemes a browser must never be asked to follow from a link we render.
 * The server refuses them too; this is the second half of that check.
 */
const FORBIDDEN_EDITOR_SCHEMES = new Set(['javascript', 'data', 'vbscript', 'file']);

/**
 * Keep only editor links a browser may follow: http(s) and custom schemes such as
 * `vscode://`. Anything else, and anything that is not a URL at all, becomes ''.
 * @param {unknown} url
 * @returns {string} The accepted URL, or '' when it must not be used.
 */
export function safeEditorUrl(url) {
  const text = String(url || '').trim();
  if (!text) return '';
  try {
    const parsed = new URL(text, globalThis.location?.href || 'http://localhost/');
    if (FORBIDDEN_EDITOR_SCHEMES.has(parsed.protocol.slice(0, -1).toLowerCase())) return '';
  } catch (_) { return ''; }
  return text;
}

/** How V8 prints a name: letters, digits, `_` and `$`, never starting with a digit. */
const IDENTIFIER = '([A-Za-z_$][\\w$]*)';
/** Start of a name: never in the middle of `a-b`, `a.b` or a longer word. */
const NAME_START = '(?:^|[\\s(])';

/**
 * Hints for the runtime messages developers hit most. V8 (Chromium, Edge, Node)
 * wording only: another engine simply gets no hint rather than a wrong one.
 * Order matters, the first matching rule wins.
 * @type {{pattern: RegExp, hint: (match: RegExpMatchArray) => string}[]}
 */
const HINT_RULES = [
  {
    pattern: new RegExp(`${NAME_START}${IDENTIFIER} is not defined`),
    hint: m => `${m[1]} is not defined. Declare it in the component <script> block, ` +
      `import it, or fix the spelling.`,
  },
  {
    pattern: new RegExp(`${NAME_START}${IDENTIFIER} is not a function`),
    hint: m => `${m[1]} is not a function. A Teloce signal is read by calling it (${m[1]}()), ` +
      `so check what ${m[1]} holds.`,
  },
  {
    pattern: new RegExp(`${NAME_START}${IDENTIFIER} is not iterable`),
    hint: m => `${m[1]} is not iterable. Give the signal a list as its default, or wrap the value.`,
  },
  {
    pattern: /Cannot read properties of (undefined|null) \(reading '([^']*)'\)/,
    hint: m => `The value is ${m[1]} when .${m[2]} is read. Give the signal a default, or guard the read.`,
  },
  {
    pattern: /Cannot set properties of (undefined|null) \(setting '([^']*)'\)/,
    hint: m => `The value is ${m[1]} when .${m[2]} is set. Create it first, usually as a signal.`,
  },
  {
    pattern: /Cannot read property '([^']*)' of (undefined|null)/,
    hint: m => `The value is ${m[2]} when .${m[1]} is read. Give the signal a default, or guard the read.`,
  },
  {
    pattern: /Maximum call stack size exceeded/,
    hint: () => 'A function keeps calling itself. Check an effect or computed that writes a signal it also reads.',
  },
  {
    pattern: /Assignment to constant variable/,
    hint: () => 'Assigning to a const. Make it a signal: const count = signal(0), then count(count() + 1).',
  },
  {
    pattern: /Unexpected token '<'/,
    hint: () => 'JavaScript arrived as HTML: a script URL is missing, so the dev server returned its page.',
  },
];

/**
 * Short, actionable hint for a runtime message. Pure: no DOM, no state, and the same
 * input always gives the same answer. Returns '' for messages it does not recognise.
 * @param {string} [message]
 * @returns {string}
 */
export function hintFor(message) {
  const text = String(message || '');
  for (const rule of HINT_RULES) {
    const match = text.match(rule.pattern);
    if (match) return rule.hint(match);
  }
  return '';
}

/**
 * Copy text to the clipboard. Falls back to a hidden textarea on insecure origins.
 * @param {string} text
 * @param {HTMLElement} host Element to attach the fallback textarea to (must be inside a modal dialog).
 * @returns {Promise<boolean>} Whether the copy worked.
 */
async function copyText(text, host) {
  try { await navigator.clipboard.writeText(text); return true; } catch (_) { /* try the fallback */ }
  try {
    const area = document.createElement('textarea');
    area.value = text; area.style.cssText = 'position:fixed;opacity:0;pointer-events:none';
    host.append(area); area.select();
    const copied = document.execCommand('copy'); area.remove();
    return copied;
  } catch (_) { return false; }
}

/**
 * Install the development error overlay, fetch tracing and live reload.
 * Calling it again first removes the previous installation.
 * @param {TeloceDebugConfig} config
 * @returns {() => void} Cleanup function that removes every listener, timer and overlay.
 */
export function installTeloceDebugger(config) {
  globalThis.__FLAXON_TELOCE_DEBUG_CLEANUP__?.();
  const nativeFetch = window.fetch.bind(window);
  const originalFetch = window.fetch;
  /** `document` is absent in non-browser test environments. */
  const doc = globalThis.document;
  const seen = new Map(); let activeReports = 0; let closed = false;
  /** @type {HTMLElement | undefined} */
  let banner;
  /** @type {CSSStyleSheet | undefined} */
  let sheet;
  /** @type {HTMLStyleElement | undefined} */
  let styleEl;
  /**
   * The open error dialog: its elements, the report it shows and the text "Copy error" copies.
   * @type {{item: DebugReport, dialog: HTMLDialogElement, kind: HTMLElement, body: HTMLElement,
   *   link: HTMLAnchorElement, editor: HTMLAnchorElement, note: string, text: string} | undefined}
   */
  let ui;
  /** True once the person dismissed the dialog for the current report. */
  let dismissed = false;

  /**
   * Create an element, optionally with a class and text. Text is always set as text, never as HTML.
   * @param {string} tag
   * @param {string} [className]
   * @param {string} [text]
   * @returns {HTMLElement}
   */
  const el = (tag, className, text) => {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };

  /** Install the overlay stylesheet once. @returns {void} */
  const ensureStyles = () => {
    if (!doc || sheet || styleEl) return;
    try {
      if (typeof CSSStyleSheet !== 'undefined' && 'adoptedStyleSheets' in doc) {
        sheet = new CSSStyleSheet(); sheet.replaceSync(OVERLAY_CSS);
        doc.adoptedStyleSheets = [...doc.adoptedStyleSheets, sheet];
        return;
      }
    } catch (_) { sheet = undefined; }
    styleEl = el('style', undefined, OVERLAY_CSS); doc.head?.append(styleEl);
  };

  /**
   * Run a copy and show the result on a label for a moment.
   * @param {HTMLElement} label Element whose text shows "Copied" or "Copy failed".
   * @param {string} idle Text to restore afterwards.
   * @param {string} text What to copy.
   * @returns {Promise<void>}
   */
  const copyWithFeedback = async (label, idle, text) => {
    label.textContent = (await copyText(text, ui.dialog)) ? 'Copied' : 'Copy failed';
    setTimeout(() => { label.textContent = idle; }, 1400);
  };

  /**
   * Build the dialog shell once per report: header, empty body and footer.
   * @param {DebugReport} report
   * @returns {void}
   */
  const build = report => {
    const dialog = /** @type {HTMLDialogElement} */ (el('dialog'));
    dialog.setAttribute('data-flaxon-error', ''); dialog.setAttribute('role', 'alertdialog');
    dialog.setAttribute('aria-labelledby', 'fx-title'); dialog.tabIndex = -1;

    const kind = el('span', 'fx-kind');
    const close = el('button', 'fx-close'); close.type = 'button'; close.title = 'Close (Esc)';
    close.setAttribute('aria-label', 'Close');
    close.innerHTML = '<svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="M3 3l8 8M11 3l-8 8"/></svg>';
    close.onclick = () => dialog.close();
    const head = el('div', 'fx-head'); head.append(kind, close);

    const body = el('div', 'fx-body');

    const link = /** @type {HTMLAnchorElement} */ (el('a', 'fx-btn fx-primary', 'Open Flaxon debugger'));
    // Only revealed when the server sends a usable editor URL for the mapped location.
    const editor = /** @type {HTMLAnchorElement} */ (el('a', 'fx-btn', 'Open in editor'));
    editor.target = '_blank'; editor.rel = 'noreferrer noopener'; editor.hidden = true;
    const copy = el('button', 'fx-btn', 'Copy error'); copy.type = 'button';
    copy.onclick = () => copyWithFeedback(copy, 'Copy error', ui.text);
    const dismiss = el('button', 'fx-btn', 'Dismiss'); dismiss.type = 'button';
    dismiss.onclick = () => dialog.close();
    const foot = el('div', 'fx-foot'); foot.append(link, editor, copy, el('span', 'fx-spacer'), dismiss);

    dialog.append(head, body, foot);
    // Close on a click outside the panel, but not when a text selection merely ends there.
    let pressedOutside = false;
    dialog.addEventListener('mousedown', event => { pressedOutside = event.target === dialog; });
    dialog.addEventListener('click', event => { if (pressedOutside && event.target === dialog) dialog.close(); });
    dialog.addEventListener('close', () => { dismissed = true; });
    ui = { item: report, dialog, kind, body, link, editor, note: '', text: '' };
  };

  /**
   * Fill the dialog for a report. Called again with the server's extra context, which adds the
   * mapped source location and excerpt without re-opening or re-animating the dialog.
   * @param {DebugReport} report
   * @param {{location?: string, source_excerpt?: string, related_error_id?: string, error_id?: string,
   *   editor_url?: string}} result
   * @returns {void}
   */
  const fill = (report, result) => {
    ui.editor.hidden = true; ui.editor.removeAttribute('href');
    const href = safeEditorUrl(result.editor_url);
    if (href) { ui.editor.href = href; ui.editor.hidden = false; }
    const place = result.location || report.component || report.filename || '';
    const where = result.location || (place && report.line ? `${place}:${report.line}${report.column ? ':' + report.column : ''}` : place);
    ui.text = [place, report.message, result.source_excerpt, report.stack].filter(Boolean).join('\n\n');
    ui.kind.textContent = CATEGORY_LABELS[report.category || 'browser'] || `${report.category} error`;
    ui.link.href = '/__debug__#error-' + encodeURIComponent(result.related_error_id || result.error_id || '');

    const parts = [];
    const title = el('h2', 'fx-title', String(report.message || 'Unknown error').split('\n')[0].replace(/^Uncaught\s+/, ''));
    title.id = 'fx-title'; parts.push(title);

    const tip = hintFor(report.message);
    if (tip) parts.push(el('p', 'fx-tip', tip));

    if (where) {
      const chip = el('button', 'fx-where'); chip.type = 'button'; chip.title = 'Copy path';
      const hint = el('span', 'fx-hint', 'Copy');
      chip.append(el('span', 'fx-path', shorten(where)), hint);
      chip.onclick = () => copyWithFeedback(hint, 'Copy', where);
      parts.push(chip);
    }

    if (ui.note) parts.push(el('p', 'fx-note', ui.note));

    const errorLine = Number((result.location || '').split(':')[1]) || Number(report.line) || 0;
    const rows = parseExcerpt(result.source_excerpt, errorLine);
    if (rows.length) {
      const src = el('div', 'fx-src'); src.setAttribute('role', 'region'); src.setAttribute('aria-label', 'Source excerpt');
      for (const row of rows) {
        const line = el('div', row.hit ? 'fx-ln fx-hit' : 'fx-ln');
        line.append(el('span', 'fx-num', String(row.num)), el('span', 'fx-code', row.code));
        src.append(line);
      }
      parts.push(src);
    }

    const frames = parseStack(report.stack);
    if (frames.length) {
      const stack = el('details', 'fx-stack'); stack.open = true;
      const summary = el('summary', 'fx-sum', 'Stack trace ');
      summary.append(el('span', 'fx-count', `${frames.length} ${frames.length === 1 ? 'frame' : 'frames'}`));
      const list = el('ol', 'fx-frames');
      frames.forEach((frame, index) => {
        const item = el('li', 'fx-frame');
        if (frame.fn) item.append(el('span', 'fx-fn', frame.fn)); else item.classList.add('fx-bare');
        item.append(el('span', 'fx-at', shorten(frame.at)));
        if (index >= VISIBLE_FRAMES) item.hidden = true;
        list.append(item);
      });
      if (frames.length > VISIBLE_FRAMES) {
        const row = el('li', 'fx-frame fx-last');
        const more = el('button', 'fx-more', `Show ${frames.length - VISIBLE_FRAMES} more`); more.type = 'button';
        more.onclick = () => { list.querySelectorAll('[hidden]').forEach(item => { item.hidden = false; }); row.remove(); };
        row.append(more); list.append(row);
      }
      stack.append(summary, list);
      parts.push(stack);
    }

    const raw = el('details', 'fx-raw'); raw.append(el('summary', 'fx-sum', 'Plain text'), el('pre', 'fx-pre', ui.text));
    parts.push(raw);
    ui.body.replaceChildren(...parts);
  };

  /**
   * Show the error dialog. The same report shown again (with server context) updates in place.
   * @param {DebugReport} report
   * @param {{location?: string, source_excerpt?: string, related_error_id?: string, error_id?: string}} [result]
   *   Extra context returned by the server after it recorded the report.
   * @returns {void}
   */
  const show = (report, result = {}) => {
    if (!doc) return;
    if (ui && ui.item === report) { if (!dismissed) fill(report, result); return; }
    ui?.dialog.remove(); dismissed = false;
    ensureStyles(); build(report); fill(report, result);
    doc.body.append(ui.dialog); ui.dialog.showModal(); ui.dialog.focus({ preventScroll: true });
  };
  /**
   * Record a diagnostic: show it, then send it to the server (max 3 in flight, deduplicated for 2s).
   * @param {DebugReport} value
   * @returns {Promise<void>}
   */
  const report = async value => {
    if (closed || activeReports >= 3) return;
    const item = { category: 'browser', ...value, path: location.pathname };
    item.message = String(item.message || 'Unknown browser error').slice(0, 4000);
    item.stack = String(item.stack || '').slice(0, 12000);
    const key = `${item.component || item.filename}:${item.line}:${item.message}`;
    if (Date.now() - (seen.get(key) || 0) < 2000) return;
    if (seen.size >= 100) seen.clear(); seen.set(key, Date.now());
    show(item); activeReports += 1;
    try {
      const response = await nativeFetch('/__debug__/teloce/errors', { method: 'POST', credentials: 'same-origin',
        headers: { 'content-type': 'application/json', 'x-flaxon-debug-token': config.token }, body: JSON.stringify(item) });
      if (closed) return;
      if (response.ok) { show(item, await response.json()); return; }
      // A rejected report used to be swallowed whole, which looked like a mapping bug.
      if (ui) { ui.note = await transportNote(response); show(item, {}); }
    } catch (_) {
      if (ui && !closed) {
        ui.note = 'Source mapping unavailable: the debug endpoint could not be reached.';
        show(item, {});
      }
    } finally { activeReports -= 1; }
  };
  const runtime = event => report(event.detail || {});
  const error = event => report({message: event.message, stack: event.error?.stack, filename: event.filename, line: event.lineno, column: event.colno});
  const rejection = event => report({message: event.reason?.message || String(event.reason), stack: event.reason?.stack});
  window.addEventListener('teloce:error', runtime); window.addEventListener('error', error); window.addEventListener('unhandledrejection', rejection);
  const tracedFetch = async (input, init) => {
    const url = new URL(input instanceof Request ? input.url : String(input), location.href);
    const relevant = url.origin === location.origin && !url.pathname.startsWith('/__debug__/');
    try {
      const response = await nativeFetch(input, init);
      if (relevant && response.status >= 500) report({ category: 'api',
        message: `${init?.method || (input instanceof Request ? input.method : 'GET')} ${url.pathname} returned ${response.status}`,
        request_id: response.headers.get('x-request-id') || '' });
      return response;
    } catch (error) {
      if (relevant && error?.name !== 'AbortError') report({ category: 'api', message: error.message, stack: error.stack });
      throw error;
    }
  };
  window.fetch = tracedFetch;
  /**
   * Non-blocking status banner (unlike `show`, it never takes over the page).
   * @param {string} message
   * @param {NoticeAction} [action]
   * @returns {void}
   */
  const notice = (message, action) => {
    if (!doc) return;
    ensureStyles();
    banner?.remove(); banner = el('div');
    banner.setAttribute('data-flaxon-notice', ''); banner.setAttribute('role', 'status');
    banner.append(el('span', 'fx-text', message));
    if (action) {
      const button = el('button', 'fx-btn', action.label); button.type = 'button';
      button.onclick = action.onClick; banner.append(button);
    }
    doc.body.append(banner);
  };

  // Serial polling avoids overlapping builds and works through ordinary HTTP proxies.
  let revision = config.revision;
  /** @type {ReturnType<typeof setTimeout> | undefined} */
  let reloadTimer;
  let polling = false;   // a poll request is in flight
  let stopped = false;   // live reload is off for this page load
  let failures = 0;      // consecutive failed polls, drives the backoff

  /**
   * Schedule the next poll. Does nothing while closed, stopped or the tab is hidden,
   * so background tabs do not use up the shared diagnostics rate limit.
   * @param {number} delay Milliseconds to wait.
   * @returns {void}
   */
  const schedule = delay => {
    clearTimeout(reloadTimer);
    if (closed || stopped || doc?.hidden) return;
    reloadTimer = setTimeout(pollReload, delay);
  };

  /**
   * Turn live reload off for this page load and tell the developer why.
   * @param {string} [message] Omit for a silent stop.
   * @param {NoticeAction} [action]
   * @returns {void}
   */
  const stopPolling = (message, action) => {
    stopped = true; clearTimeout(reloadTimer);
    if (message) notice(message, action);
  };

  /**
   * Ask the server whether the UI sources changed, and reload when they did.
   * Reload only ever happens on a changed revision, one 403 after a Python restart,
   * and never more than `MAX_AUTO_RELOADS` times per `AUTO_RELOAD_WINDOW_MS`.
   * @returns {Promise<void>}
   */
  const pollReload = async () => {
    if (closed || stopped || polling) return;
    polling = true;
    let delay = POLL_INTERVAL_MS;
    let leaving = false;
    try {
      const response = await nativeFetch(RELOAD_ENDPOINT, {
        method: 'POST', credentials: 'same-origin', cache: 'no-store',
        headers: { 'x-flaxon-debug-token': config.token },
      });
      if (closed) return;
      if (response.status === 403) {
        const rejection = await rejectionOf(response);
        if (closed) return;
        // Origin/host/scheme mismatch (proxy, tunnel): reloading can never help, so stop now.
        if (rejection.code === ORIGIN_REJECTED) {
          stopPolling(`Teloce live reload is off. ${rejection.message || 'The debug endpoint rejected this origin (403).'}`);
          return;
        }
        // Otherwise the token is stale because Python restarted: reload once to obtain a new one.
        // Servers that send no code get the same single reload, then polling stops.
        if (claimOnce(FORBIDDEN_KEY)) { leaving = true; location.reload(); return; }
        stopPolling('Teloce live reload is off: the debug endpoint keeps answering 403. ' +
          'Open the app on the same host and scheme the server sees, e.g. http://127.0.0.1:8000.');
        return;
      }
      if (response.status === 404) { stopPolling(); return; } // debug endpoints are not mounted
      if (!response.ok) { delay = Math.min(MAX_BACKOFF_MS, POLL_INTERVAL_MS * 2 ** failures++); return; } // 429, 5xx
      failures = 0; forget(FORBIDDEN_KEY);
      /** @type {ReloadResult} */
      const result = await response.json();
      if (closed || result.revision === revision) return;
      revision = result.revision;
      if (result.failed) {
        show({ category: 'compile', message: 'Teloce rebuild failed. Open the Flaxon debugger for diagnostics.' });
        return;
      }
      if (mayAutoReload()) { leaving = true; location.reload(); return; }
      stopPolling(`Teloce live reload paused: the page reloaded ${MAX_AUTO_RELOADS} times in ` +
        `${AUTO_RELOAD_WINDOW_MS / 1000}s, which looks like a reload loop.`,
        { label: 'Reload now', onClick: () => { forget(RELOADS_KEY); location.reload(); } });
    } catch (_) {
      // The Python server is probably restarting: retry with backoff.
      delay = Math.min(MAX_BACKOFF_MS, POLL_INTERVAL_MS * 2 ** failures++);
    } finally {
      polling = false;
      if (!leaving) schedule(delay);
    }
  };

  /** Resume polling right away when the tab becomes visible again. */
  const visibility = () => { if (!doc?.hidden) schedule(0); };
  doc?.addEventListener('visibilitychange', visibility);
  schedule(POLL_INTERVAL_MS);
  /** @returns {void} */
  const cleanup = () => { closed = true; clearTimeout(reloadTimer); doc?.removeEventListener('visibilitychange', visibility); banner?.remove(); if (window.fetch === tracedFetch) window.fetch = originalFetch; ui?.dialog.remove(); if (sheet) doc.adoptedStyleSheets = doc.adoptedStyleSheets.filter(item => item !== sheet); styleEl?.remove(); window.removeEventListener('teloce:error', runtime); window.removeEventListener('error', error); window.removeEventListener('unhandledrejection', rejection); };
  globalThis.__FLAXON_TELOCE_DEBUG_CLEANUP__ = cleanup;
  globalThis.__FLAXON_TELOCE_REPORT__ = report;
  return cleanup;
}