/** Cliente REST local; NUNCA construye cabeceras JWT de OpenDSS. */
export async function request(path, method = "GET", payload) {
  const response = await fetch(`/api${path}`, {
    method,
    headers: { "Content-Type": "application/json", "X-DERMS-Client": "ui" },
    credentials: "same-origin",
    ...(payload === undefined ? {} : { body: JSON.stringify(payload) }),
  });
  let data;
  try {
    data = await response.json();
  } catch {
    data = {};
  }
  if (!response.ok) throw new Error(data.detail ?? data.message ?? `HTTP ${response.status}`);
  return data;
}
export const api = {
  status: () => request("/status"),
  models: () => request("/models"),
  runs: () => request("/runs"),
  run: (id) => request(`/runs/${encodeURIComponent(id)}`),
  createRun: (body) => request("/runs", "POST", body),
  snapshot: (body) => request("/snapshots", "POST", body),
  coupled: (body) => request("/coupled-runs", "POST", body),
  offline: () => request("/experiments/offline", "POST"),
  dispatch: (id) => request(`/runs/${encodeURIComponent(id)}/dispatch`, "POST"),
  objective: () => request("/objective"),
  saveObjective: (data) => request("/objective", "PUT", data),
  llmStatus: () => request("/llm/status"),
  explain: (data) => request("/llm/explain", "POST", data),
  propose: (data) => request("/llm/propose", "POST", data),
  graph: (id) => request(`/graph/nodes?run_id=${encodeURIComponent(id)}`),
  asof: (id, at) =>
    request(`/graph/asof?run_id=${encodeURIComponent(id)}&at=${encodeURIComponent(at)}`),
  graphQuery: (data) => request("/graph/query", "POST", data),
  compare: (id) => request(`/experiments/compare?run_id=${encodeURIComponent(id)}`),
};
