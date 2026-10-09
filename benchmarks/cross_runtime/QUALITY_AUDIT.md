# Security and code quality audit

The mypy `target_platform` key was invalid; it is now `platform`. Development/CI tooling is constrained to mypy <2 after intermittent internal crashes with 2.4.0; targeted checks passed on mypy 1.20.2.

- Critical Ruff syntax/undefined-name checks pass across src/flaxon.
- Full Ruff inventory at audit time: 3,864 issues, dominated by missing method/class docstrings (1,777/479), long lines (478), and intentional or legacy local imports (234). There are 62 C901 complexity findings. This is remaining debt, not a clean full Ruff run.
- Full strict mypy now runs and reports 896 errors in 177 files, including missing optional dependency stubs and legacy untyped code. New endpoint-plan and JWT modules pass targeted strict checks with imports skipped. This is not equivalent to full-repository type safety.
- All 12 previously silent direct `except Exception: pass` handlers were reviewed. Optional plugin/listener failures now warn with the exception type, queue errors propagate, platform/finalizer handlers catch expected exceptions. No direct catch-all `pass` handlers remain in src/flaxon.
- There are 94 total broad Exception handlers (including named exceptions and application boundaries). They are inventoried in exception-audit.json. Retaining a top-level error-to-response boundary or cleanup-and-rethrow is deliberate; not every broad catch is a swallowed failure. Further review remains appropriate.

Security changes cover both JWT and JWTBackend, legacy password verification and Admin upgrade-on-login, inferred query validation, lazy session creation and secure helper defaults. JWTBackend revocation is instance-local; a distributed deployment needs a shared revocation design.

Fixes discovered while checking critical lint include missing MySQL cursor, retry asyncio, template Callable and audit Request imports. Compression now invokes the ASGI app with receive/send, emits exactly one response-start event, preserves chunked finite bodies, and uses gzip's correct compresslevel argument. Unknown-length streams pass through without buffering.

Verification before publishing: the final complete framework suite passed **873 tests**, with **29 skipped** (benchmark timing disabled for this correctness run). Both Admin/CMS and ORM Admin real-browser tests passed. Final targeted security/state/authentication checks passed **216 tests**, with **2 skipped**. Critical Ruff checks pass; new execution-plan and JWT modules pass targeted strict mypy checks.

No independent penetration test or human developer productivity study was conducted. Percentages reported in UPGRADE_RESULTS.md concern HTTP throughput only.
