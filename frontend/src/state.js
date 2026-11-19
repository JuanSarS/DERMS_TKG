/** Estado local; el último resultado confirmado nunca se borra por caída de red. */
export const appState = {
  page: "derms",
  status: null,
  currentRun: null,
  lastGood: null,
  progress: null,
  profile: null,
  objective: null,
  error: "",
};
const listeners = new Set();
export function subscribe(callback) {
  listeners.add(callback);
  return () => listeners.delete(callback);
}
export function update(patch) {
  Object.assign(appState, patch);
  for (const callback of listeners) callback(appState);
}
export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
