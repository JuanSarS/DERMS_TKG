/** Tabla verificable de acciones calculadas con signo explícito. */
import { escapeHtml } from "../state.js";

export function dispatchTable(rows) {
  if (!rows?.length) return `<p class="muted">Sin despacho calculado.</p>`;
  return `<div class="scroll-table"><table><thead><tr>
    <th>Paso</th><th>Hora UTC</th><th>Consumo kW</th><th>FV kW</th>
    <th>BESS kW</th><th>SOC kWh</th><th>Red kW</th><th>Validación</th>
  </tr></thead><tbody>${rows
    .map(
      (r) => `<tr><td>${r.step}</td><td>${escapeHtml(r.timestamp)}</td>
    <td>${r.load_kw.toFixed(3)}</td><td>${r.pv_kw.toFixed(3)}</td>
    <td>${r.battery_kw.toFixed(3)}</td><td>${r.soc_kwh.toFixed(3)}</td>
    <td>${r.grid_import_kw.toFixed(3)}</td><td>${escapeHtml(r.electrical_validation)}</td></tr>`,
    )
    .join("")}</tbody></table></div>`;
}
