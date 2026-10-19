/* Island Architect — the shape of a design.
 *
 * Plain JavaScript, no build step. The Teloce components in ui/ import this
 * file, and app.py validates the same rules before storing a design.
 *
 * Coordinates are in the SVG viewBox used by components/TopoMap.html
 * (1000 x 560), so a node's position is just its region plus a small offset.
 */

export const REGIONS = [
  { id: "negril", label: "Negril", note: "West end · one small edge node", x: 110, y: 330 },
  { id: "montego-bay", label: "Montego Bay", note: "North-west · tourist traffic", x: 250, y: 170 },
  { id: "ocho-rios", label: "Ocho Rios", note: "North coast · cruise days", x: 560, y: 120 },
  { id: "kingston", label: "Kingston", note: "Capital · main data centre", x: 780, y: 330 },
  { id: "portmore", label: "Portmore", note: "South · backup site", x: 680, y: 450 },
];

/* capacity is requests/second per replica; baseLatency is ms of work per
 * request before any queueing. */
export const NODE_KINDS = {
  client: { label: "Client", capacity: 0, baseLatency: 2, note: "Visitor app or kiosk" },
  edge: { label: "Gateway", capacity: 900, baseLatency: 6, note: "TLS, routing, rate limits" },
  service: { label: "Service", capacity: 380, baseLatency: 25, note: "Your Python handlers" },
  cache: { label: "Cache", capacity: 1600, baseLatency: 3, note: "Read-through cache" },
  queue: { label: "Queue", capacity: 600, baseLatency: 8, note: "Absorbs bursts" },
  db: { label: "Database", capacity: 220, baseLatency: 40, note: "The slowest tier" },
};

export const KIND_IDS = Object.keys(NODE_KINDS);

/* A small but real starting point: two clients on the north coast, one
 * gateway in Kingston, a couple of services, a cache, a queue and a database. */
export const DEFAULT_DESIGN = {
  nodes: [
    { id: "guest-app", name: "Guest app", kind: "client", region: "montego-bay", replicas: 1 },
    { id: "kiosk", name: "Hotel kiosk", kind: "client", region: "ocho-rios", replicas: 1 },
    { id: "gateway", name: "Island gateway", kind: "edge", region: "kingston", replicas: 2 },
    { id: "booking", name: "Booking service", kind: "service", region: "kingston", replicas: 3 },
    { id: "search", name: "Search service", kind: "service", region: "kingston", replicas: 2 },
    { id: "cache", name: "Read cache", kind: "cache", region: "kingston", replicas: 1 },
    { id: "jobs", name: "Job queue", kind: "queue", region: "kingston", replicas: 1 },
    { id: "ledger", name: "Booking ledger", kind: "db", region: "kingston", replicas: 1 },
    { id: "west-edge", name: "West end edge", kind: "service", region: "negril", replicas: 1 },
  ],
  edges: [
    { from: "guest-app", to: "gateway" },
    { from: "kiosk", to: "gateway" },
    { from: "gateway", to: "booking" },
    { from: "gateway", to: "search" },
    { from: "gateway", to: "west-edge" },
    { from: "search", to: "cache" },
    { from: "cache", to: "ledger" },
    { from: "booking", to: "ledger" },
    { from: "booking", to: "jobs" },
    { from: "west-edge", to: "cache" },
  ],
};

export function cloneDesign(design) {
  return JSON.parse(JSON.stringify(design || { nodes: [], edges: [] }));
}

export function regionOf(node) {
  return REGIONS.find((region) => region.id === node.region) || REGIONS[0];
}

/* Fan the nodes of one region out around its anchor so they do not overlap. */
export function nodePosition(node, indexInRegion, countInRegion) {
  const region = regionOf(node);
  const spread = 46;
  const offset = countInRegion <= 1 ? 0 : (indexInRegion - (countInRegion - 1) / 2) * spread;
  return { x: region.x, y: region.y + offset, region };
}

export function nodePositions(design) {
  const counts = {};
  const seen = {};
  const result = {};
  (design.nodes || []).forEach((node) => {
    counts[node.region] = (counts[node.region] || 0) + 1;
  });
  (design.nodes || []).forEach((node) => {
    const index = seen[node.region] || 0;
    seen[node.region] = index + 1;
    result[node.id] = nodePosition(node, index, counts[node.region]);
  });
  return result;
}

export function nodeById(design, id) {
  return (design.nodes || []).find((node) => node.id === id) || null;
}

/* Kahn's algorithm. Returns null when the graph has a cycle, which is the one
 * structural problem the simulator cannot run at all. */
export function topoOrder(design) {
  const incoming = {};
  const outgoing = {};
  (design.nodes || []).forEach((node) => {
    incoming[node.id] = 0;
    outgoing[node.id] = [];
  });
  (design.edges || []).forEach((edge) => {
    if (!outgoing[edge.from] || !incoming.hasOwnProperty(edge.to)) return;
    outgoing[edge.from].push(edge.to);
    incoming[edge.to] += 1;
  });

  const queue = Object.keys(incoming).filter((id) => incoming[id] === 0);
  const order = [];
  while (queue.length) {
    const id = queue.shift();
    order.push(id);
    outgoing[id].forEach((next) => {
      incoming[next] -= 1;
      if (incoming[next] === 0) queue.push(next);
    });
  }
  return order.length === Object.keys(incoming).length ? order : null;
}

/* Mirrors app.py `graph_problems`: the browser runs it first so Save is only
 * enabled for a design the server will accept. */
export function validateDesign(design) {
  const problems = [];
  const nodes = design.nodes || [];
  const edges = design.edges || [];

  if (nodes.length === 0) problems.push("Add at least one node.");
  if (nodes.length > 24) problems.push("At most 24 nodes.");
  if (edges.length > 48) problems.push("At most 48 edges.");

  const ids = new Set();
  nodes.forEach((node) => {
    if (!node.id) problems.push("Every node needs an id.");
    else if (ids.has(node.id)) problems.push(`Duplicate node id "${node.id}".`);
    ids.add(node.id);
    if (!NODE_KINDS[node.kind]) problems.push(`Node "${node.id}" has an unknown kind.`);
    if (!REGIONS.some((region) => region.id === node.region)) {
      problems.push(`Node "${node.id}" is in an unknown region.`);
    }
  });

  edges.forEach((edge) => {
    if (!ids.has(edge.from) || !ids.has(edge.to)) {
      problems.push(`Edge ${edge.from || "?"} → ${edge.to || "?"} points at a missing node.`);
    }
  });

  if (topoOrder(design) === null) problems.push("The graph has a cycle; the simulator needs a DAG.");
  return problems;
}

export function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 24);
}
