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

This is an initial framework adapter. It checks an isolated generated project and does not automatically inherit the application's `tsconfig.json`, aliases, or `node_modules`. Component props currently use permissive types, and template positions use heuristic expression mapping. A passing check does not establish complete framework or dependency type safety. Use the Teloce adapter documentation for supported expressions and mapping limits.
