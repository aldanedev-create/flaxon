# Flaxon + Teloce SSR

Use matching Flaxon/Teloce checkouts containing the new AST SSR integration.
From this directory:

```bash
pip install "flaxon[standard]" teloce-py
flaxon run app:app --reload
```

Until the coordinated release is published, install both packages from their updated local checkouts with `pip install -e /path/to/teloce-py -e /path/to/flaxon`. The published versions may not contain `teloce.server` yet.

Visit `/`: project HTML is present before JavaScript starts, and the counter hydrates to the supplied value. Teloce automatically supplies signal imports. Both error buttons deliberately demonstrate development failures; the overlay links to `/__debug__` and API errors carry a related request ID.

For production, set `FLAXON_DEBUG=0` and run `flaxon run app:app` without reload. The build uses MinifyJS production defaults, and neither the debugger reporting route nor the error client is enabled. Remove the demonstration error route/buttons from a real application.

See [SSR and browser debugging](../../docs/guides/teloce-ssr-debugging.md).
