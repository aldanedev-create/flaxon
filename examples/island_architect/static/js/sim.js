/* Island Architect — the simulation engine.
 *
 * This file is the lesson. A simulator is only five things:
 *
 *   1. a state object you can snapshot and reset
 *   2. a deterministic random source (same seed → same run, every time)
 *   3. a step function that moves the state forward one tick
 *   4. per-tick measurements, not just a final number
 *   5. a scenario table that says what "unusual" means
 *
 * Everything below is plain JavaScript with no dependencies, so the browser can
 * step it tick by tick and you can run it in Node to check the maths.
 */
import { NODE_KINDS, nodeById, topoOrder } from "./island.js";

export const SCENARIOS = [
  {
    id: "calm-day",
    label: "Calm day",
    note: "Baseline traffic. Everything should stay green.",
    arrivalsPerClient: 180,
    jitter: 0.12,
    cacheHitRate: 0.82,
    linkFactor: 1,
    queueDrain: 0.9,
    offlineRegions: [],
  },
  {
    id: "peak-season",
    label: "Peak season",
    note: "3x arrivals: cruise ships and a festival weekend.",
    arrivalsPerClient: 480,
    jitter: 0.2,
    cacheHitRate: 0.82,
    linkFactor: 1.1,
    queueDrain: 0.9,
    offlineRegions: [],
  },
  {
    id: "storm",
    label: "Storm over the north coast",
    note: "Ocho Rios loses power; cross-island links slow down.",
    arrivalsPerClient: 220,
    jitter: 0.18,
    cacheHitRate: 0.78,
    linkFactor: 2.4,
    queueDrain: 0.7,
    offlineRegions: ["ocho-rios"],
  },
  {
    id: "cache-cold",
    label: "Cache cold start",
    note: "The cache forgets everything; every read reaches the database.",
    arrivalsPerClient: 200,
    jitter: 0.15,
    cacheHitRate: 0.05,
    linkFactor: 1,
    queueDrain: 0.9,
    offlineRegions: [],
  },
  {
    id: "queue-backup",
    label: "Queue backlog",
    note: "Consumers slow to 40%; the queue absorbs it until it cannot.",
    arrivalsPerClient: 800,
    jitter: 0.15,
    cacheHitRate: 0.8,
    linkFactor: 1,
    queueDrain: 0.4,
    offlineRegions: [],
  },
];

export function scenarioById(id) {
  return SCENARIOS.find((scenario) => scenario.id === id) || SCENARIOS[0];
}

/* mulberry32: a 32-bit PRNG. Deterministic, tiny, and good enough for traffic
 * jitter. Never use Math.random() in a simulator you want to reproduce. */
export function mulberry32(seed) {
  let state = (seed | 0) || 1;
  return function next() {
    state = (state + 0x6d2b79f5) | 0;
    let t = Math.imul(state ^ (state >>> 15), 1 | state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* 1. state */
export function createRun(design, scenarioId, seed) {
  const order = topoOrder(design);
  return {
    design,
    scenario: scenarioById(scenarioId),
    seed: seed || 7,
    order: order || [],
    valid: order !== null,
    rng: mulberry32(seed || 7),
    tick: 0,
    queues: {},          // node id → requests waiting
    snapshots: [],
  };
}

function pathLatency(design, nodeId, latencyById, memo) {
  if (memo[nodeId] !== undefined) return memo[nodeId];
  const outgoing = (design.edges || []).filter((edge) => edge.from === nodeId);
  let worst = 0;
  outgoing.forEach((edge) => {
    const next = pathLatency(design, edge.to, latencyById, memo);
    worst = Math.max(worst, next);
  });
  memo[nodeId] = (latencyById[nodeId] || 0) + worst;
  return memo[nodeId];
}

/* 3. one tick. Mutates `state` and returns the snapshot for this tick. */
export function step(state) {
  const { design, scenario, rng } = state;
  const nodes = design.nodes || [];
  const edges = design.edges || [];
  if (!state.valid) {
    return { tick: state.tick, valid: false, nodes: {}, events: [], totals: emptyTotals() };
  }

  state.tick += 1;
  const incoming = {};
  const latencyById = {};
  const events = [];
  nodes.forEach((node) => {
    incoming[node.id] = 0;
  });

  // Clients are the only sources of traffic.
  nodes.filter((node) => node.kind === "client").forEach((node) => {
    const jitter = 1 + (rng() * 2 - 1) * scenario.jitter;
    const offline = scenario.offlineRegions.indexOf(node.region) !== -1;
    incoming[node.id] += offline ? 0 : Math.max(0, Math.round(scenario.arrivalsPerClient * jitter));
  });

  /* Traffic leaves a node split evenly across its outgoing links. */
  const forward = (nodeId, amount) => {
    const targets = edges.filter((edge) => edge.from === nodeId);
    if (!targets.length || amount <= 0) return;
    const share = amount / targets.length;
    targets.forEach((edge) => {
      incoming[edge.to] = (incoming[edge.to] || 0) + share;
    });
  };

  const report = {};
  state.order.forEach((nodeId) => {
    const node = nodeById(design, nodeId);
    if (!node) return;
    const kind = NODE_KINDS[node.kind] || NODE_KINDS.service;
    const offline = scenario.offlineRegions.indexOf(node.region) !== -1;
    const arrive = incoming[nodeId] + (state.queues[nodeId] || 0);

    // A client is a source, not a worker: it passes everything downstream.
    if (node.kind === "client") {
      const served = incoming[nodeId];
      report[nodeId] = {
        incoming: served,
        served,
        dropped: 0,
        queued: 0,
        latencyMs: Math.round(kind.baseLatency * scenario.linkFactor),
        healthy: !offline,
        load: 0,
      };
      latencyById[nodeId] = report[nodeId].latencyMs;
      if (offline) {
        events.push({ tick: state.tick, nodeId, level: "error", message: `${node.name} is offline (${node.region}).` });
        return;
      }
      forward(nodeId, served);
      return;
    }

    if (offline) {
      state.queues[nodeId] = 0;
      report[nodeId] = {
        incoming: arrive,
        served: 0,
        dropped: arrive,
        queued: 0,
        latencyMs: 0,
        healthy: false,
        load: 0,
      };
      latencyById[nodeId] = 0;
      events.push({ tick: state.tick, nodeId, level: "error", message: `${node.name} is unreachable — region ${node.region} is down.` });
      return;
    }

    const replicas = Math.max(1, Number(node.replicas) || 1);
    let capacity = kind.capacity * replicas;
    if (node.kind === "queue") capacity = capacity * scenario.queueDrain;

    const accepted = Math.min(arrive, capacity);
    const overflow = arrive - accepted;
    let dropped = 0;
    let queued = 0;

    if (node.kind === "queue") {
      // A queue absorbs the burst instead of failing it, until it fills up.
      queued = Math.min(overflow, capacity * 6);
      dropped = overflow - queued;
    } else {
      dropped = overflow;
      queued = 0;
    }
    state.queues[nodeId] = queued;

    const load = capacity > 0 ? accepted / capacity : 0;
    const queueDelay = capacity > 0 ? (queued / capacity) * 20 : 0;
    const latency = Math.round((kind.baseLatency + load * load * 45 + queueDelay) * scenario.linkFactor);
    latencyById[nodeId] = latency;

    report[nodeId] = {
      incoming: arrive,
      served: accepted,
      dropped,
      queued,
      latencyMs: latency,
      healthy: true,
      load,
    };

    if (dropped > 0) {
      events.push({
        tick: state.tick,
        nodeId,
        level: "error",
        message: `${node.name} dropped ${dropped} req/s — over ${Math.round(capacity)} req/s capacity.`,
      });
    } else if (load > 0.85) {
      events.push({
        tick: state.tick,
        nodeId,
        level: "warn",
        message: `${node.name} at ${Math.round(load * 100)}% capacity.`,
      });
    }
    if (node.kind === "queue" && queued > capacity * 2) {
      events.push({
        tick: state.tick,
        nodeId,
        level: "warn",
        message: `${node.name} backlog: ${queued} requests waiting.`,
      });
    }

    // 4. pass traffic downstream. A cache only forwards its misses.
    if (node.kind === "cache") {
      forward(nodeId, Math.round(accepted * (1 - scenario.cacheHitRate)));
    } else {
      forward(nodeId, accepted);
    }
  });

  // Client-visible latency: the slowest path from a client to a sink.
  const memo = {};
  Object.keys(latencyById).forEach((nodeId) => pathLatency(design, nodeId, latencyById, memo));
  let clientLatency = 0;
  nodes.filter((node) => node.kind === "client").forEach((node) => {
    clientLatency = Math.max(clientLatency, memo[node.id] || 0);
  });

  const totals = emptyTotals();
  nodes.forEach((node) => {
    const row = report[node.id];
    if (!row) return;
    totals.requests += row.incoming;
    totals.served += row.served;
    totals.dropped += row.dropped;
  });
  totals.errorRate = totals.requests > 0 ? totals.dropped / totals.requests : 0;
  totals.clientLatencyMs = clientLatency;

  const snapshot = { tick: state.tick, valid: true, nodes: report, events, totals };
  state.snapshots.push(snapshot);
  return snapshot;
}

function emptyTotals() {
  return { requests: 0, served: 0, dropped: 0, errorRate: 0, clientLatencyMs: 0 };
}

/* Run many ticks and return the snapshots. Used by the "Run" button. */
export function runFor(design, scenarioId, seed, ticks) {
  const state = createRun(design, scenarioId, seed);
  const out = [];
  for (let index = 0; index < ticks; index += 1) out.push(step(state));
  return { state, snapshots: out };
}

/* Averages across a run, for the summary strip. */
export function summarize(snapshots) {
  if (!snapshots.length) return { ticks: 0, errorRate: 0, latencyMs: 0, dropped: 0 };
  let dropped = 0;
  let latency = 0;
  snapshots.forEach((snapshot) => {
    dropped += snapshot.totals.dropped;
    latency += snapshot.totals.clientLatencyMs;
  });
  return {
    ticks: snapshots.length,
    dropped,
    errorRate: snapshots[snapshots.length - 1].totals.errorRate,
    latencyMs: Math.round(latency / snapshots.length),
  };
}
