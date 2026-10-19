/* Island Architect — the Learn tab content.
 *
 * Keeping the prose in a module (instead of inside a component template) means
 * the code samples below are the same thing you can read in the real files.
 */

export const LESSONS = [
  {
    id: "round-trip",
    title: "One click, end to end",
    blurb:
      "Press Save on the Design tab and seven things happen. None of them is magic, and each one lives in a file you can open.",
    steps: [
      {
        label: "A component method calls the API module",
        detail:
          "ui/components/NodeEditor.html collects the form, app.html calls saveDesign() from static/js/api.js. Components never call fetch directly.",
      },
      {
        label: "fetch() posts JSON to Flaxon",
        detail: "POST /api/designs with {name, scenario, seed, graph}. One request, one JSON body.",
      },
      {
        label: "Flaxon matches the route",
        detail: "app.py registers @app.post('/api/designs') before the SPA catch-all, so /api/* is never treated as a page.",
      },
      {
        label: "The schema validates the body",
        detail:
          "DesignSchema (flaxon.validation) checks name length and types. A bad body returns 422 with per-field problems, no handler code runs.",
      },
      {
        label: "Python re-validates the graph",
        detail:
          "graph_problems() checks ids, kinds, regions and cycles. The browser already checked the same rules; the server does not trust it.",
      },
      {
        label: "The ORM writes one row",
        detail: "await Design.create(...) — flaxon.db (Tortoise) writes into island_designs. That is the whole persistence layer.",
      },
      {
        label: "JSON comes back, Teloce updates the DOM",
        detail:
          "201 with the saved record. The component pushes it into its designs list and the list re-renders. No page reload, no manual DOM work.",
      },
    ],
    code: {
      label: "app.py — the write path",
      source: [
        "@app.post('/api/designs')",
        "async def create_design(data: DesignSchema):",
        "    payload = data.to_dict()",
        "    graph = payload.get('graph') or {'nodes': [], 'edges': []}",
        "    problems = graph_problems(graph)",
        "    if problems:",
        "        return JSONResponse({'error': 'Invalid design.', 'problems': problems}, status_code=422)",
        "",
        "    design = await Design.create(",
        "        name=payload['name'],",
        "        scenario=payload.get('scenario') or 'calm-day',",
        "        seed=payload.get('seed') or 7,",
        "        graph=graph,",
        "    )",
        "    return JSONResponse(design_record(design), status_code=201)",
      ].join("\n"),
    },
    pitfalls: [
      "Validating only in the browser. curl does not run your JavaScript.",
      "Letting the SPA catch-all swallow /api/*. Register API routes first.",
      "Returning model objects straight from a handler — always serialise (design_record).",
    ],
  },
  {
    id: "teloce",
    title: "What Teloce actually does",
    blurb:
      "Teloce is a component compiler, not a framework you install in the browser. Flaxon compiles ui/ to JavaScript on first request and serves it.",
    steps: [
      {
        label: "One .html file is one component",
        detail:
          "ui/app.html holds <template>, <script> and <style>. Flaxon's use_teloce() compiles the tree into .flaxon/build/ui/*.js — plain ES modules.",
      },
      {
        label: "The browser loads modules, not a bundle",
        detail:
          "The page is served by request.compile('app.html'), which emits a <script type='module'> pointing at the compiled entry. Your static/js/*.js files are imported by relative path.",
      },
      {
        label: "State lives in data() and signal()",
        detail:
          "data() returns the component's reactive state; signal()/computed()/effect() are the same reactivity used inside the compiled runtime. Change state, the DOM follows.",
      },
      {
        label: "Props down, events up",
        detail:
          "A child receives props and reports with $emit('add-node', payload); the parent owns the source of truth. Never mutate a prop in the child.",
      },
      {
        label: "Python stays on the server",
        detail:
          "Components fetch data; they do not query the database. The API is the contract, which is why the same design renders identically tomorrow.",
      },
    ],
    code: {
      label: "ui/app.html — owning state, passing it down",
      source: [
        "<script>",
        'import TopoMap from "./components/TopoMap.html";',
        'import { createRun, step } from "../static/js/sim.js";',
        "",
        "export default {",
        "  components: { TopoMap },",
        "  data() {",
        "    return { design: cloneDesign(DEFAULT_DESIGN), tick: 0, running: false };",
        "  },",
        "  methods: {",
        "    stepOnce() {",
        "      this.snapshot = step(this.run);",
        "      this.tick = this.run.tick;",
        "    },",
        "  },",
        "};",
        "</script>",
      ].join("\n"),
    },
    pitfalls: [
      "Importing a .js module from a nested folder — the builder copies authored .js next to the component or from static/, so keep relative paths shallow.",
      "Doing work in the template. Compute it in a method and bind the result.",
      "Mutating props in a child: emit instead.",
    ],
  },
  {
    id: "simulate",
    title: "How to write a simulator",
    blurb:
      "The engine in static/js/sim.js is about 200 lines and it is the point of this example. A simulator is five things; build them in this order.",
    steps: [
      {
        label: "1. One state object",
        detail:
          "createRun(design, scenario, seed) returns everything the run needs: order, queues, rng, tick. If you cannot snapshot it, you cannot reset it.",
      },
      {
        label: "2. Deterministic randomness",
        detail:
          "mulberry32(seed) instead of Math.random(). Same seed, same run — otherwise you can never compare two designs or debug a tick.",
      },
      {
        label: "3. A step() that moves one tick",
        detail:
          "step(state) pushes traffic along the topological order, applies capacity, then returns a snapshot. Never loop inside step; the caller decides how fast to tick.",
      },
      {
        label: "4. Measure every tick",
        detail:
          "Each snapshot carries per-node served/dropped/queued/latency plus totals and an event log. A final average hides the overload spike you needed to see.",
      },
      {
        label: "5. A scenario table",
        detail:
          "SCENARIOS says what 'unusual' means: 3x arrivals, a region going dark, a cold cache, a slow queue. Scenarios are data, not branches in your code.",
      },
    ],
    code: {
      label: "static/js/sim.js — the five pieces",
      source: [
        "export function createRun(design, scenarioId, seed) {",
        "  return { design, scenario: scenarioById(scenarioId), rng: mulberry32(seed),",
        "           tick: 0, queues: {}, order: topoOrder(design) };",
        "}",
        "",
        "export function step(state) {",
        "  state.tick += 1;",
        "  // clients produce traffic, then every node in topological order:",
        "  //   accepted = min(arriving + queued, capacity)",
        "  //   dropped  = the rest (or absorbed by a queue)",
        "  //   latency  = base + load^2 * 45 + queue delay, scaled by linkFactor",
        "  return { tick: state.tick, nodes: report, events, totals };",
        "}",
      ].join("\n"),
    },
    pitfalls: [
      "Math.random() in the engine: your run stops being reproducible.",
      "Averaging everything: keep the per-tick series, then summarise at the end.",
      "Mixing rendering into the engine. sim.js returns numbers; the component decides colours.",
      "No tick budget. Cap ticks and nodes — a simulator that hangs is worse than one that is wrong.",
    ],
  },
  {
    id: "server-side",
    title: "When the engine should live in Python",
    blurb:
      "This example simulates in the browser so you can step it. Move it server-side when the run is heavy, must be shared, or must be trusted.",
    steps: [
      {
        label: "Keep it client-side when",
        detail: "You want tick-by-tick exploration, the run is small, and a wrong number is harmless.",
      },
      {
        label: "Move it server-side when",
        detail:
          "Runs take seconds, several people must see the same result, or the outcome drives a decision nobody may tamper with in devtools.",
      },
      {
        label: "The shape of the endpoint",
        detail:
          "POST /api/simulate with {design, scenario, seed, ticks} → 200 with the snapshot array. The client becomes a player, not the engine.",
      },
      {
        label: "Keep the two honest",
        detail:
          "Whichever side owns the engine, keep it a pure function of (design, scenario, seed, ticks) so both sides agree.",
      },
    ],
    code: {
      label: "app.py — the server-side shape (not wired up here)",
      source: [
        "@app.post('/api/simulate')",
        "async def simulate(request: Request):",
        "    body = await request.json() or {}",
        "    problems = graph_problems(body.get('graph') or {})",
        "    if problems:",
        "        return JSONResponse({'error': 'Invalid design.', 'problems': problems}, status_code=422)",
        "    # snapshots = engine.run(body['graph'], body['scenario'], body['seed'], body['ticks'])",
        "    return {'snapshots': snapshots}",
      ].join("\n"),
    },
    pitfalls: [
      "Duplicating the engine in two languages without tests that compare them.",
      "Letting a client ask for an unbounded number of ticks.",
    ],
  },
];
