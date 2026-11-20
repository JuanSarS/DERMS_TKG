/** Snapshot OpenDSS agregado, distinto de un despacho BESS eléctricamente validado. */
import { api } from "../api.js";
import { escapeHtml } from "../state.js";

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function mountSnapshotControl(root) {
  const parent = root.querySelector(".main-workspace > section.card");
  if (!parent) return;
  const section = document.createElement("section");
  section.className = "card";
  section.id = "snapshotCard";
  section.innerHTML = `<h3>Snapshot OpenDSS (referencia eléctrica)</h3>
    <p class="muted small">Resuelve IEEE13 con UN multiplicador global; NO aplica batería/PV del optimizador.
    Si falla /health, conserva el último resultado confirmado.</p>
    <div class="button-row"><label>Multiplicador de carga
      <input type="number" id="snapshotMultiplier" min="0.01" max="5" step="0.05" value="1" /></label>
      <button id="runSnapshot">Ejecutar Snapshot OpenDSS</button></div>
    <div id="snapshotOutput" role="status">Sin ejecutar.</div>`;
  parent.after(section);
  const button = section.querySelector("#runSnapshot");
  const output = section.querySelector("#snapshotOutput");
  button.onclick = async () => {
    button.disabled = true;
    output.textContent = "Verificando OpenDSS y creando snapshot...";
    try {
      const multiplier = Number(section.querySelector("#snapshotMultiplier").value);
      const topology = root.querySelector("#topology")?.value || "ieee13";
      const created = await api.snapshot({ topology, load_multiplier: multiplier });
      let result = null;
      for (let attempt = 0; attempt < 80; attempt++) {
        await wait(1250);
        result = await api.run(created.run_id);
        if (["SNAPSHOT_VERIFIED", "ERROR"].includes(result.status)) break;
      }
      if (result?.status === "SNAPSHOT_VERIFIED") {
        const physical = result.result?.result ?? {};
        output.innerHTML = `<p><strong>Snapshot remoto confirmado · ${escapeHtml(result.run_id.slice(0, 8))}</strong></p>
          <p>Convergencia: ${escapeHtml(physical.converged)} · Potencia: ${escapeHtml(physical.total_power_kw)} kW
          · Q: ${escapeHtml(physical.total_power_kvar)} kvar · duración: ${escapeHtml(physical.elapsed_ms)} ms</p>
          <p class="muted small">Multiplicador global ${escapeHtml(physical.load_multiplier)} ·
          ${escapeHtml(Object.keys(physical.voltages ?? {}).length)} voltajes registrados.</p>
          <p class="muted small">Verificación solo del alimentador de referencia. BESS: NOT_VALIDATED.</p>`;
      } else {
        output.textContent =
          result?.error || "No se confirmó el snapshot. Los resultados previos siguen disponibles.";
      }
    } catch (error) {
      output.textContent = `No se envió o completó el snapshot: ${error.message}`;
    } finally {
      button.disabled = false;
    }
  };
}
