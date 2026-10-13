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

## Automatic development checks

With `DEBUG = True`, `python management.py runserver` starts a background checker during application startup. It checks once, then checks saved UI, TypeScript, and JSON configuration changes about once per second, even with no browser connected. Checks run serially outside the event loop. Findings appear in the terminal and the development debugger; errors do not stop the server. The latest result and operational error are available as `app.teloce.development_typecheck.result` and `.error`. Debugger reports are historical; use the latest result to inspect the current check.

Disable automatic checking while retaining the manual command:

```python
app.use_teloce(typecheck=False)
```

Production (`DEBUG = False`) never starts the watcher. Shutdown stops polling and waits for an active compiler call to finish. Automatic checking is advisory; keep the explicit `typecheck` command as a deployment gate. The development checks require the Teloce release providing project-context support.

## Checker dependency

PyTSCheck is already a core Flaxon dependency because automatic development checks use it. A normal `pip install flaxon` installs the bundled checker; `flaxon[typecheck]` remains a supported explicit extra. Standalone Teloce keeps checking optional through `teloce-py[typecheck]`. This installs the compiler without requiring Node.js; it does not install npm package declarations used by your application.
