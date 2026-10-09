# Release readiness audit — 2026-10-09

Status: the local release gates passed after the fixes below. Merge the audit PR
and require its GitHub Actions checks before cutting a new release. No version,
release tag or PyPI package was published during this audit.

## Fixed

- Environment `FLAXON_SECRET_KEY` retains its exact string value. Numeric,
  boolean-looking and comma-containing secrets are not converted into other types.
- Release tooling reads and updates `src/flaxon/version.py`, the authoritative
  version source, rather than the now-reexporting `__init__.py`.
- Version information supports `a`, `b`, `rc`, and development version suffixes.
- Release changelog generation accepts both existing Unreleased heading formats,
  preserves older releases, creates a new Unreleased heading, and fails clearly
  when the section is missing.
- Twine receives actual wheel/sdist paths. Artifact checks no longer use a shell
  with a subprocess argument list, and uploads do not receive a literal wildcard.
- Dry-run performs no build, cleanup, Git mutation or upload. Reusing the current
  version is rejected. Tagged releases require a clean working tree and commit
  the version/changelog before tagging, so the tag points at the release content.
- The browser head-injection test uses the real pinned Bootstrap 5.3.3 JavaScript
  fixture with its MIT license. CDN availability is no longer a condition for
  verifying the converter API, TypeScript runtime, and collapse interaction.
- Package metadata links point at the current repository. Source distributions
  include release scripts and the browser fixture.
- CI now checks ORM/Admin on Python 3.11, 3.12 and 3.13, runs release-tooling
  regression tests, and builds/checks distributions plus an isolated-wheel smoke.

## Evidence

- Full suite with optional browser tests enabled: **913 passed, 24 skipped**.
  Includes Admin/CMS, ORM Admin, generated welcome, converter and taskboard browser
  workflows. Skips remain environment/optional-integration checks; this is not a
  claim that every supported external service was exercised locally.
- Release tooling: 17 regression cases covering secrets, version updates,
  prerelease imports, changelog history, artifact commands, commits, and dry-run.
- Wheel and sdist builds passed; `twine check` passed for both.
- All Admin templates/static files and CLI starter files were present in the
  built wheel (419 entries checked).
- A fresh isolated environment installed the built wheel with standard/Admin
  dependencies. `python -m flaxon new`, management checks, Python migration
  creation/application, welcome API, compiled UI assets, Admin login and protected
  Admin requests passed outside the source checkout. Distribution and runtime
  versions matched.
- Critical Ruff checks and targeted mypy passed. All framework source parses as
  Python 3.11 syntax. Runtime compatibility across the CI matrix remains a CI gate.
- No broken relative Markdown links found in README, SECURITY and documentation.
- `pip-audit` found no known vulnerabilities in the clean standard/Admin/Pydantic
  test environment after updating its installer. Initial findings concerned that
  environment's old pip, not Flaxon runtime dependencies. This is an advisory scan
  at one point in time, not an independent security certification.
- Existing GitHub Actions ORM gates were green for SQLite, PostgreSQL and Admin
  browser behavior after the missing Pydantic mypy-plugin dependency fix.

## Release decision

Use a **new version**, not another 0.2.7 upload. The recent default JSON wire
contract and JWT changes merit an explicit migration release; 0.3.0 is a reasonable
candidate. Review the JSON and authentication migration guides, prepare the
version/changelog, and pass all CI gates before tagging or publishing.

The audit does not certify every deployment or third-party integration. Existing
repository-wide style/type debt remains outside the targeted passing checks.
Production applications must configure persistent secrets/storage, shared session
and WebSocket infrastructure for multiple workers, trusted hosts, TLS, backups and
migration rollout. Starting the server must not silently alter database schema.
Known deterministic Admin route-overlap warnings remain; verified static-route
precedence handles those overlaps. They are not failed migrations.
