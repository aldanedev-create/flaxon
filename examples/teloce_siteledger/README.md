# SiteLedger Teloce SPA

This example uses one central `ui/` tree. Flaxon owns the API and serves the
startup-compiled Teloce application; Teloce owns client-side navigation and UI
state. No separate frontend command or checked-in `dist/` directory is needed.

```bash
pip install -e .
pip install --upgrade teloce-py
cd examples/teloce_siteledger
flaxon run app:app
```

Open `http://127.0.0.1:8000`. Generated files are written to
`examples/teloce_siteledger/.flaxon/build`.

See [the integration API and five lessons](../../docs/api/teloce.md). Use a Teloce release containing the MinifyJS production integration; for unreleased changes, install from your local Teloce checkout. Sample data is in memory and is not a production database.
