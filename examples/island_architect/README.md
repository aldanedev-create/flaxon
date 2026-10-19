# Island Architect — Teloce interface over the Flaxon ORM

A small teaching example that shows how the three parts of a Flaxon app pull
apart cleanly:

| Layer | Where | Role |
| --- | --- | --- |
| Data | `models.py`, `app.py` | `flaxon.db` (Tortoise) table `island_designs` holds saved system designs |
| API | `app.py` | JSON endpoints (`/api/designs`, `/api/scenarios`) validate and serve designs |
| Interface | `ui/` | A Teloce single-page interface compiled to browser JavaScript on first request |
| Simulation | `static/js/sim.js` | Plain JavaScript that steps the design tick by tick, no round trip |

The browser **never** touches the database and Python **never** renders HTML —
the JSON API is the whole contract between the two, which is the point of the
example.

You design a system for an island: clients, edge gateways, services, caches,
queues, and databases, wired together by links. The simulator runs the topology
under five scenarios (calm day, peak season, storm, cache cold, queue backup)
and reports dropped requests, error rate, latency, and per-node load — all
deterministically from a seed, so the same design always produces the same
numbers.

## Run it

```bash
cd examples/island_architect
python management.py makemigrations   # create the ORM table
python management.py migrate
python management.py runserver         # http://127.0.0.1:8000
```

Open http://127.0.0.1:8000. There is no staff Admin in this example — flip
`ADMIN_ENABLED` to `True` in `settings.py` and read
`docs/guides/orm-admin-custom-pages.md` if you want one.

## The three tabs

- **Design** — add nodes and links; the form is validated client-side
  (`validateDesign` in `static/js/island.js`) and server-side (`graph_problems`
  in `app.py`, the same checks) before a design can be saved.
- **Simulate** — pick a scenario and seed, then step or play the run.
  `static/js/sim.js` runs entirely in the browser, so there is no latency from
  the server and the run is fully reproducible.
- **Learn** — short lessons that explain the model (arrivals, queueing,
  back-pressure, region failures) in `static/js/lessons.js`.

## What to look at

- `models.py` — one `Design` row; `graph` is a schemaless JSON blob by design.
- `app.py` — `use_teloce()` is set up **before** the management guard so
  `build`/`typecheck` work without a database. The `/api/*` routes are
  registered before the SPA catch-all, so they never fall through to the shell.
- `static/js/sim.js` — the whole engine as plain JS: `createRun`, `step`,
  `summarize`, and the scenario table. It rejects cyclic graphs rather than
  simulating them.
- `ui/app.html` — the shell, the three tab buttons, and the child components
  (`NodeEditor`, `TopoMap`, `SimPanel`, `LessonPane`) registered by their
  kebab-case tags.
- `smoke_test.py` — boots its own server on a throwaway database and checks the
  SPA, every served asset, and the full API round-trip (create / list / get /
  update / delete), plus the 422-on-bad-graph and 404-on-missing-id paths.

## Tests

```bash
python smoke_test.py
```

All checks must pass before opening a pull request touching this example.
