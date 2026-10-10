// Development adapter. The server never injects this client in production.
export function installTeloceDebugger(config) {
  globalThis.__FLAXON_TELOCE_DEBUG_CLEANUP__?.();
  const nativeFetch = window.fetch.bind(window);
  const originalFetch = window.fetch;
  const seen = new Map(); let activeReports = 0; let closed = false; let overlay;
  const show = (report, result = {}) => {
    overlay?.remove(); overlay = document.createElement('dialog');
    overlay.setAttribute('data-flaxon-error', '');
    Object.assign(overlay.style, { color: '#e2e8f0', background: '#0f172a', maxWidth: 'min(900px,90vw)', width: '90vw', border: '1px solid #475569', padding: '24px' });
    const heading = document.createElement('h2'); heading.textContent = `Flaxon / Teloce ${report.category || 'browser'} error`;
    const details = document.createElement('pre'); details.style.whiteSpace = 'pre-wrap';
    details.textContent = [result.location || report.component || report.filename, report.message, result.source_excerpt, report.stack].filter(Boolean).join('\n\n');
    const close = document.createElement('button'); close.textContent = 'Dismiss'; close.onclick = () => overlay.close();
    const dashboard = document.createElement('a'); dashboard.href = '/__debug__#error-' + encodeURIComponent(result.related_error_id || result.error_id || ''); dashboard.textContent = 'Open Flaxon debugger'; dashboard.style.marginLeft = '16px';
    overlay.append(heading, details, close, dashboard); document.body.append(overlay); overlay.showModal();
  };
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
      if (response.ok && !closed) show(item, await response.json());
    } catch (_) { /* Diagnostic transport failures stay local. */ }
    finally { activeReports -= 1; }
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
  const cleanup = () => { closed = true; if (window.fetch === tracedFetch) window.fetch = originalFetch; overlay?.remove(); window.removeEventListener('teloce:error', runtime); window.removeEventListener('error', error); window.removeEventListener('unhandledrejection', rejection); };
  globalThis.__FLAXON_TELOCE_DEBUG_CLEANUP__ = cleanup;
  globalThis.__FLAXON_TELOCE_REPORT__ = report;
  return cleanup;
}
