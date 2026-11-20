/** Indicadores de disponibilidad y política de último resultado válido. */
import { escapeHtml } from "../state.js";

export function statusBar(status) {
  const remote = status?.remote ?? { state: "UNKNOWN", message: "Sin comprobar" };
  const stale = remote.state !== "HEALTHY";
  const llmStatus =
    status?.llm?.status ?? (status?.llm_enabled ? "CONFIGURED_UNTESTED" : "DISABLED");
  return `<div class="status-row">
    <span class="state-pill ${stale ? "danger" : "success"}">● OpenDSS: ${escapeHtml(remote.state)}</span>
    <span class="state-pill">WSS: ${escapeHtml(remote.ws_state || "N/D")}</span>
    <span class="state-pill ${llmStatus === "READY" ? "success" : ""}">LLM: ${escapeHtml(llmStatus)}</span>
    <span class="state-pill ${stale ? "danger" : ""}">${stale ? "Datos históricos conservados · SIN nuevas actualizaciones" : "En línea"}</span>
    <span class="muted small">Última corrida confirmada: ${escapeHtml(status?.last_good_run?.run_id?.slice(0, 8) || "ninguna")}</span>
  </div>`;
}
