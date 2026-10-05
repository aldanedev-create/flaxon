# SiteLedger Teloce SPA

This example uses one central `ui/` tree. Flaxon owns the API and serves the
startup-compiled Teloce application; Teloce owns client-side navigation and UI
state. No separate frontend command or checked-in `dist/` directory is needed.

```bash
pip install -e .
pip install -e C:/Users/aldan/Downloads/teloce-python
cd examples/teloce_siteledger
flaxon run app:app
```

Open `http://127.0.0.1:8000`. Generated files are written to
`examples/teloce_siteledger/.flaxon/build`.
