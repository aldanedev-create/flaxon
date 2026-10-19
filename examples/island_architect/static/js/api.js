/* Island Architect — the only place that talks to Flaxon.
 *
 * Every request in the app goes through here, so there is one place to look
 * when something returns 422: log the body, check app.py's DesignSchema, done.
 */
const BASE = "/api";

async function request(path, options) {
  const response = await fetch(BASE + path, options);
  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch (error) {
      payload = null;
    }
  }
  if (!response.ok) {
    const detail = payload && payload.problems ? payload.problems.join(" ") : payload && payload.error;
    throw new Error(detail || `Request failed (HTTP ${response.status}).`);
  }
  return payload;
}

function json(method, body) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export function listDesigns() {
  return request("/designs").then((payload) => (payload && payload.items) || []);
}

export function getDesign(id) {
  return request(`/designs/${id}`);
}

export function createDesign(design) {
  return request("/designs", json("POST", design));
}

export function updateDesign(id, design) {
  return request(`/designs/${id}`, json("PUT", design));
}

export function deleteDesign(id) {
  return request(`/designs/${id}`, { method: "DELETE" });
}

export function listScenarios() {
  return request("/scenarios").then((payload) => (payload && payload.items) || []);
}
