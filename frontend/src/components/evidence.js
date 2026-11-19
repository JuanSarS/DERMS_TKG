/** Etiquetas de procedencia y advertencia contra conclusiones no medidas. */
import { escapeHtml } from "../state.js";

export function evidence(run) {
  return `<section class="card"><h3>Evidencia y procedencia</h3>
  <div class="key-values">
  <span>run_id</span><code>${escapeHtml(run?.run_id || "N/D")}</code>
  <span>Fuente</span><b>${escapeHtml(run?.origin_kind || "N/D")}</b>
  <span>QSTS</span><b>${escapeHtml(run?.remote_verification || "NOT_VALIDATED")}</b>
  <span>Estado</span><b>${escapeHtml(run?.status || "N/D")}</b></div>
  <p class="muted small">Toda mejora económica es atribuible al algoritmo y los supuestos, no al TKG sin comparación controlada.</p></section>`;
}
