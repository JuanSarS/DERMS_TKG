/** Comparaciones energéticas separadas de latencias TKG no medidas. */
import { api } from "../api.js";
import { escapeHtml } from "../state.js";

export async function experimentsPage(root) {
  root.innerHTML = `<div class="page-heading"><div><p class="eyebrow">LABORATORIO 03 / EXPERIMENTOS</p>
    <h1>Resultados y reproducibilidad</h1><p class="muted">Diferenciar política fija, optimizador y valor del TKG</p></div></div>
    <section class="card"><h3>Historial local</h3><div id="runHistory">Cargando...</div></section>
    <section class="card"><h3>Comparación</h3><p class="muted small">Costo/peak pertenecen al modelo energético; no son una mejora causal del grafo.</p>
      <div id="experimentComparison">Seleccione una corrida con despacho.</div></section>
    <section class="card"><h3>Microbenchmark B0 / B1 / B2</h3><button id="runBaselines">Ejecutar consulta temporal comparativa</button><pre id="baselineResult">Aún no ejecutado.</pre></section>
    <section class="card"><h3>Evaluación futura B0/B1/B2</h3>
      <p>B0 = tablas temporales; B1 = RDF estático; B2 = TKG RDF con vigencia y tiempo de conocimiento.
      Para evaluar ventaja se requieren corridas repetidas de corrección, latencia y trazabilidad con mismo algoritmo.
      Los valores no medidos figuran como <b>NOT_RUN</b>.</p></section>`;
  const items = await api.runs();
  const list = root.querySelector("#runHistory");
  list.innerHTML = items.length
    ? `<div class="scroll-table"><table><thead><tr><th>Corrida</th><th>Fecha</th><th>Estado</th><th>Origen</th><th></th></tr></thead><tbody>
    ${items
      .map(
        (
          r,
        ) => `<tr><td class="mono">${escapeHtml(r.run_id.slice(0, 8))}</td><td>${escapeHtml(r.created_at)}</td>
      <td>${escapeHtml(r.status)}</td><td>${escapeHtml(r.origin_kind)}</td>
      <td><button data-run="${escapeHtml(r.run_id)}">Comparar</button></td></tr>`,
      )
      .join("")}</tbody></table></div>`
    : "No hay corridas registradas";
  list.querySelectorAll("button[data-run]").forEach((b) => {
    b.onclick = async () => {
      try {
        const response = await api.compare(b.dataset.run);
        const target = root.querySelector("#experimentComparison");
        const compare = response.comparison;
        if (!compare) {
          target.textContent = "Esta corrida todavía no tiene despacho local.";
          return;
        }
        const b0 = compare.baseline?.metrics,
          opt = compare.optimized?.metrics;
        if (!b0 || !opt) {
          target.textContent = "Baseline no factible o datos incompletos";
          return;
        }
        target.innerHTML = `<div class="metric-grid">
        <div class="metric"><span>Costo modelo fijo</span><b>${b0.energy.toFixed(3)} AUD</b></div>
        <div class="metric"><span>Costo optimizado</span><b>${opt.energy.toFixed(3)} AUD</b></div>
        <div class="metric"><span>Pico fijo</span><b>${b0.peak.toFixed(3)} kW</b></div>
        <div class="metric"><span>Pico optimizado</span><b>${opt.peak.toFixed(3)} kW</b></div></div>
        <p class="warning">NO VALIDADO eléctricamente para la batería. Costos basados en escenarios de tarifa, no en facturación real.</p>`;
      } catch (error) {
        root.querySelector("#experimentComparison").textContent = error.message;
      }
    };
  });
  root.querySelector("#runBaselines").onclick = async () => {
    const target = root.querySelector("#baselineResult");
    try {
      const response = await fetch("/api/experiments/baselines");
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      target.textContent = JSON.stringify(result, null, 2);
    } catch (error) {
      target.textContent = error.message;
    }
  };
}
