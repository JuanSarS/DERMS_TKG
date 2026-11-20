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
  const isProxy = r.validation_scope === "BUILTIN_IEEE13_NETLOAD_PROXY_NOT_BESS_VALIDATION";
  return `<div class="key-values">
    <span>Modo de evaluación</span><b>${isProxy ? "IEEE13 integrado · equivalente agregado" : "DSS personalizado"}</b>
    <span>Estado IEEE13</span><b>${r.status}</b>
    <span>J modelo fijo</span><b>${fmt(baseline)}</b>
    <span>J optimizado</span><b>${fmt(optimized)}</b>
    <span>Costo energía</span><b>${fmt(r.energy_metrics?.energy)} AUD</b>
    <span>Pico optimizado</span><b>${fmt(r.energy_metrics?.peak)} kW</b>
    <span>Pasos QSTS</span><b>${electrical.steps?.length ?? 0}</b>
    <span>Desviación máxima de potencia</span><b>${fmt(electrical.max_abs_delta_kw)} kW</b>
    <span>Violaciones de tensión</span><b>${check.violations?.length ?? "N/D"}</b>
    <span>Telemetría individual BESS</span><b>NO DISPONIBLE</b>
    </div><p class="muted small">${
      isProxy
        ? "Se ejecutó OpenDSS IEEE13 integrado con LoadMult equivalente para reproducir el efecto agregado aproximado de batería/FV. NO se añadió Storage/PVSystem y NO se validaron consignas individuales."
        : "Se evaluó una red IEEE13 personalizada; QSTS no entrega SOC ni potencia terminal de cada Storage."
    }</p>`;
}

export function mountCoupledControl(root, onFinish) {
  const host = root.querySelector("#coupledControl");
  if (!host) return;
  host.innerHTML = `<h3>Simular, optimizar y volver a simular en IEEE13</h3>
    <p class="muted small">Por defecto usa solo IEEE13 integrado: QSTS de referencia, MILP con
    restricciones temporales TKG y QSTS del efecto agregado equivalente.
    No modifica ni sube modelos al servidor OpenDSS.</p>
    <div class="objective-grid">
    <label>Modo de evaluación<select id="coupledMode">
      <option value="builtin_proxy">IEEE13 integrado (sin modificar API)</option>
      <option value="custom_dss">DSS personalizado (experimental, puede fallar)</option>
    </select></label>
    <label>Escala experimental de recursos<input type="number" id="resourceScale" value="100" min="0.1" max="1000" step="10"></label>
    <label>Máximo de evaluaciones DSS custom (no usado en IEEE13 integrado)
    <input type="number" id="coupledPasses" value="2" min="1" max="3" disabled></label>
    </div><button class="primary" id="executeCoupled">Optimizar y comprobar con OpenDSS</button>
    <div id="coupledResults" class="message" role="status">Sin ejecutar</div>`;
  const modeControl = host.querySelector("#coupledMode");
  const passesControl = host.querySelector("#coupledPasses");
  modeControl.onchange = () => {
    passesControl.disabled = modeControl.value !== "custom_dss";
  };
  const button = host.querySelector("#executeCoupled");
  const resultBox = host.querySelector("#coupledResults");
  button.onclick = async () => {
    button.disabled = true;
    try {
      const mode = host.querySelector("#coupledMode").value;
      const scale = Number(host.querySelector("#resourceScale").value);
      const passes = Number(host.querySelector("#coupledPasses").value);
      const input = {
        mode,
        resource_scale: scale,
        max_passes: passes,
        profile_file: root.querySelector("#profile")?.value || "ausgrid_c12_2011-07-01.csv",
        load_scale: Number(root.querySelector("#scale")?.value || 1),
      };
      const submitted = await api.coupled(input);
      resultBox.textContent = `Corrida ${submitted.run_id.slice(0, 8)}: ${
        mode === "builtin_proxy"
          ? "ejecutando IEEE13 integrado sin subir modelos..."
          : "validando DSS personalizado..."
      }`;
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
