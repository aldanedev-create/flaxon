# Type-check Teloce interfaces

Install `flaxon[typecheck]` and a Teloce release that provides `teloce typecheck`:

```sh
python -m pip install --upgrade "flaxon[typecheck]" "teloce-py[typecheck]"
python management.py typecheck
python management.py typecheck --json
python management.py typecheck --no-templates
```

Until the Teloce integration is released, install its integration branch or commit instead of the published Teloce package. Installing PyTSCheck alone does not add Teloce's framework adapter.

Register your UI with `app.use_teloce()` before the `app.is_management` guard. The command checks every registered application and module UI source without running server startup hooks. An absent UI or an empty source list is an error; it never falls back to checking an unrelated working directory.

The default checks TypeScript `<script lang="ts">` blocks, `.ts` and `.d.ts` files, and supported template expressions. `--no-templates` checks scripts only. JSON output includes `ok`, `compiler`, and `findings`; each finding contains its original filename, one-based line and UTF-16 column, TypeScript diagnostic code, and message.

Exit codes are `0` for a clean check, `1` for type errors or management configuration errors, and `2` for checker input, dependency, or compiler failures. Use the exit code in CI before building assets:

```sh
python management.py typecheck && python management.py build
```

Teloce uses the Flaxon project root, inherits `tsconfig.json` (including extended compiler settings), and resolves real TypeScript files and installed package declarations. Without a config, it uses strict ES2022/bundler defaults. Generated files are checked in a temporary workspace without replacing your component sources. Install npm package declarations when importing npm packages; installing the checker through Python does not install those dependencies.

Object-style props using supported constructors get types inside the component, including required/default handling. Array-style props remain permissive, and props passed to statically imported TypeScript children are checked for wrong types, required inputs, and unknown names. Dynamic or untyped children and certain import forms remain outside these checks. Template positions still use heuristic expression mapping. See the Teloce adapter documentation for supported expressions and mapping limits.

## Development server and explicit checks

Starting `python management.py runserver` builds and serves Teloce components but does not start type checking by default. Run `python management.py typecheck` separately when you want diagnostics. A successful JavaScript build does not prove type correctness: the compiler can strip TypeScript annotations without validating them, and the adapter does not yet model every runtime feature.

For existing Flaxon 0.3.0 installations, disable the automatic checker explicitly while preserving all other integration options:

```python
app.use_teloce(project_root=ROOT, ui_dir="ui", typecheck=False)
```

The optional development watcher remains available only when explicitly requested with `typecheck=True`. It checks on startup and saved input changes, reports findings without stopping the server, and never starts in production (`DEBUG = False`). The manual management command works regardless of this option. Register `app.use_teloce()` before the `app.is_management` guard so the command can discover your UI.

## Checker dependency

PyTSCheck is already a core Flaxon dependency for the explicit management command and optional development watcher. A normal `pip install flaxon` installs the bundled checker; `flaxon[typecheck]` remains a supported explicit extra. Standalone Teloce keeps checking optional through `teloce-py[typecheck]`. This installs the compiler without requiring Node.js; it does not install npm package declarations used by your application.
