# Petal & Stem Modules + Teloce SPA

Each `FlaxonModule` owns its API or WebSocket endpoints and its Teloce pages
and components. Flaxon compiles every module UI into one application build and
generates one collision-checked client router.

```bash
pip install -e .
pip install --upgrade teloce-py
cd examples/teloce_modules_shop
flaxon run app:app
```

Open `http://127.0.0.1:8000`. Edit any module's `.html` files and let
`flaxon run app:app --reload` restart and rebuild the hidden `.flaxon/build` output.

See [the integration API and five lessons](../../docs/api/teloce.md). Use a Teloce release containing the MinifyJS production integration; for unreleased changes, install from your local Teloce checkout. Sample data is in memory and is not a production database.
