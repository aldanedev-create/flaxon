# Teloce SSR and the Flaxon debugger

Flaxon loads application data and returns HTTP responses. Teloce owns template compilation, server rendering and browser hydration. Its independent renderer does not import Flaxon. Use matching package versions containing the AST renderer; if your published packages do not yet include the integration, install both matching updated checkouts with `pip install -e /path/to/teloce-py -e /path/to/flaxon`.

## Enable SSR deliberately

In `app.py`, keep your existing factory, settings and mounted modules. Configure the UI integration after creating the application:

```python
from flaxon import Flaxon, Request

app = Flaxon('Projects', debug=True)
app.use_teloce(options={
    'ssr': 'opt-in',
    'ssr_entries': ['app.html'],
    'ssr_fallback': 'error',
})


@app.get('/')
async def home(request: Request):
    # Construct the public snapshot deliberately; do not serialize a whole user.
    public_props = {
        'title': 'Projects',
        'count': {'value': 2},
        'projects': [{'id': 1, 'name': 'Learn Flaxon'}],
    }
    return await request.compile(
        'app.html',
        public_props,
        ssr=True,
        meta={
            'title': 'Projects',
            'description': 'Manage your projects',
            'canonical': 'https://example.com/',
        },
    )
```

Create `ui/app.html`:

```html
<template>
  <main>
    <h1>{{ title }}</h1>
    <ul>
      <li v-for="project in projects" :key="project.id">{{ project.name }}</li>
    </ul>
    <p>{{ count.value }}</p>
    <button @click="count.value++">Increase</button>
  </main>
</template>

<script>
export default {
  data() {
    return { title: '', projects: [], count: signal(0) };
  },
};
</script>

<style scoped>
main { max-width: 48rem; margin: 2rem auto; padding: 1rem; }
</style>
```

Run the normal generated-project command, `python management.py runserver`. Flaxon builds the browser assets and SSR programs, renders into a marked `#app`, adds escaped public props, metadata, styles and module preloads, then calls Teloce's `hydrate`. Teloce preserves matching nodes and seeds `count.value` without replacing the signal. You do not manually import signal helpers in this component workflow.

`ssr: 'opt-in'` keeps routes client-rendered unless they pass `ssr=True`. `ssr_entries` names entries relative to registered UI sources; imported child components are included automatically. It defaults to the configured app entry. This allows browser-only forms/components elsewhere in the project. `ssr: True` renders by default and, without selected entries, validates all components for SSR. You can still pass `ssr=False` for a client-only page.

## Public state and supported syntax

Public props must be a plain JSON dictionary, with plain nested dictionaries/lists. Convert models, dates, decimals and unsafe integers explicitly. Nonfinite/unsafe numbers and arbitrary objects are rejected. The complete public snapshot reaches the browser; keep secrets, internal records and permission decisions on the server.

The first SSR subset supports interpolation, conditionals, indexed/keyed loops, safe attributes, text/show/hide bindings, imported children, and default/named slots. It implements explicit JavaScript truthiness/equality/coercion helpers with Node parity tests. Raw HTML, `v-model`, virtual lists, arbitrary calls, spreads, template literals and dynamic components are outside this subset. Unsupported syntax is a build diagnostic, not silently empty output. Browser lifecycle hooks remain client-only. Missing public values are request-time render errors.

Use the [Teloce SSR guide](https://github.com/aldanedev-create/teloce-py/blob/main/docs/ssr-and-hydration.md) for the exact supported expressions, limits and hydration contract. Client-only pages continue to support the broader browser API.

## Errors in the browser and dashboard

With `debug=True`, Flaxon injects a development error client into compiled pages. It captures:

- Teloce runtime/event failures and hydration mismatch diagnostics.
- Unhandled browser errors and promise rejections.
- Same-origin failed API requests with status 500 or greater, and network failures.

An overlay shows the message, available original component location, source excerpt and stack. Its dashboard link opens `/__debug__`. The dashboard also records compiler and server-rendering errors. Failed builds leave the development dashboard available so you can inspect diagnostics and restart/rebuild after fixing the source.

Request IDs connect API reports to the corresponding Python failure. Incoming request IDs are bounded and validated; each stored server error has its own unique ID. The reporter does not collect response bodies, request bodies, cookies, headers or the entire component state. Reports are marked as client-reported, and all displayed values are escaped.

Runtime hooks supply original expression positions. For generated stacks, Flaxon reads only known build source maps and registered UI inputs, using the nearest available mapping. Some transformations lack token-level mappings; diagnostics may point to the handler expression rather than an exact inner statement. Unsupported/malformed locations cannot read arbitrary server files.

The development endpoint requires a same-origin request and a per-app token, limits bodies to 32 KB during receipt, limits field lengths, rate-limits reports and redacts recognized sensitive data. Redaction is best effort: keep real secrets out of error messages and development source. Run the debugger only in a trusted local development environment.

Teloce remains usable without this adapter: hosts can subscribe to `onTeloceError` or `teloce:error` browser events from its shared runtime.

## Error and production policies

The default `ssr_fallback: 'error'` exposes rendering failures through Flaxon's normal error response. Development records the SSR location. An explicitly configured `ssr_fallback: 'client'` logs an SSR rendering failure and serves the client shell for that page. This fallback handles render errors only; invalid public data, missing manifests, configuration failures and route/authentication errors keep their normal failure behavior. Apply authentication and authorization before calling `request.compile()`.

`debug=False` removes the injected client and disables the reporting endpoint/dashboard. A production build uses MinifyJS defaults for browser optimization; source maps are disabled unless explicitly requested. Optional production monitoring is a separate integration, not this development transport.

The default render cache is disabled. `ssr_cache_size: 32` enables Teloce's bounded cache keyed by entry and the complete public snapshot. This cache never bypasses route authentication or application data loading. A new build replaces the renderer/cache. Teloce also offers `teloce prerender` for public static pages.

SPA navigation with `data-teloce-link` continues to use the existing router. SSR applies to the requested entry; later client page navigation mounts normal browser components. The initial router outlet is not automatically server-rendered as a second independently loaded page. Keep server data loading for that shell explicit, and use API loaders for later navigation.

A runnable example is in [examples/teloce_ssr](../../examples/teloce_ssr/).
