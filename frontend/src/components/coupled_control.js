/** Ciclo completo REST: modelo custom IEEE13, despacho y nueva QSTS. */
import { api } from "../api.js";

const DONE = new Set(["COUPLED_COMPLETED", "ERROR"]);
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const fmt = (n, digits = 3) =>
  typeof n === "number" && Number.isFinite(n) ? n.toFixed(digits) : "N/D";

function reportHTML(run) {
  const r = run.result;
  if (!r) return `<span>${run.status || "PENDING"}</span>`;
  const electrical = r.electrical ?? {};
  const check = electrical.optimized_check ?? {};
  const compare = run.dispatch?.comparison;
  const baseline = compare?.baseline?.objective?.total;
  const optimized = r.objective?.total;
  return `<div class="key-values">
    <span>Estado IEEE13</span><b>${r.status}</b>
    <span>J modelo fijo</span><b>${fmt(baseline)}</b>
    <span>J optimizado</span><b>${fmt(optimized)}</b>
    <span>Costo energía</span><b>${fmt(r.energy_metrics?.energy)} AUD</b>
    <span>Pico optimizado</span><b>${fmt(r.energy_metrics?.peak)} kW</b>
    <span>Pasos QSTS</span><b>${electrical.steps?.length ?? 0}</b>
    <span>Desviación máxima de potencia</span><b>${fmt(electrical.max_abs_delta_kw)} kW</b>
    <span>Violaciones de tensión</span><b>${check.violations?.length ?? "N/D"}</b>
    <span>Telemetría individual BESS</span><b>NO DISPONIBLE</b>
    </div><p class="muted small">Se evaluó una red IEEE13 con Storage/PVSystem modelados;
    la API QSTS no entrega SOC ni potencia terminal de cada Storage.</p>`;
}

export function mountCoupledControl(root, onFinish) {
  const host = root.querySelector("#coupledControl");
  if (!host) return;
  host.innerHTML = `<h3>Simular, optimizar y volver a simular en IEEE13</h3>
    <p class="muted small">Sube modelos DSS personalizados y ejecuta dos QSTS remotos.
    El modelo añade BESS, FV y carga flexible a la barra 671 por hipótesis.</p>
    <div class="objective-grid">
    <label>Escala experimental de recursos<input type="number" id="resourceScale" value="100" min="0.1" max="1000" step="10"></label>
    <label>Máximo de evaluaciones<input type="number" id="coupledPasses" value="2" min="1" max="3"></label>
    </div><button class="primary" id="executeCoupled">Optimizar y comprobar con OpenDSS</button>
    <div id="coupledResults" class="message" role="status">Sin ejecutar</div>`;
  const button = host.querySelector("#executeCoupled");
  const resultBox = host.querySelector("#coupledResults");
  button.onclick = async () => {
    button.disabled = true;
    try {
      const scale = Number(host.querySelector("#resourceScale").value);
      const passes = Number(host.querySelector("#coupledPasses").value);
      const input = {
        resource_scale: scale,
        max_passes: passes,
        profile_file: root.querySelector("#profile")?.value || "ausgrid_c12_2011-07-01.csv",
        load_scale: Number(root.querySelector("#scale")?.value || 1),
      };
      const submitted = await api.coupled(input);
      resultBox.textContent = `Corrida ${submitted.run_id.slice(0, 8)}: iniciando modelos custom...`;
      for (let poll = 0; poll < 160 && root.isConnected; poll += 1) {
        const run = await api.run(submitted.run_id);
        if (DONE.has(run.status)) {
          if (run.status === "ERROR") {
            resultBox.textContent = `Error: ${run.error || "Revisar resultados y permisos del servidor"}`;
          } else {
            resultBox.innerHTML = reportHTML(run);
            await onFinish(run);
          }
          return;
        }
        resultBox.textContent = `Corrida ${submitted.run_id.slice(0, 8)}: ${run.status}`;
        await wait(3000);
      }
      resultBox.textContent = "La ejecución sigue pendiente; revise la corrida desde Historial.";
    } catch (error) {
      resultBox.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  };
}
