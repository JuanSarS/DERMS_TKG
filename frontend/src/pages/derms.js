/** Pantalla principal: configuración, QSTS remoto, curvas y acciones calculadas. */
import { api } from "../api.js";
import { clearSeries, drawSeries } from "../components/charts.js";
import { dispatchTable } from "../components/dispatch_table.js";
import { evidence } from "../components/evidence.js";
import { feederDiagram } from "../components/feeder.js";
import { llmPanel } from "../components/llm_panel.js";
import { scenarioForm } from "../components/scenario_form.js";
import { mountSnapshotControl } from "../components/snapshot_control.js";
import { timeSlider } from "../components/timeline.js";
import { connectLive } from "../live.js";
import { appState, escapeHtml, update } from "../state.js";

export async function dermsPage(root) {
  root.innerHTML = `<div class="page-heading"><div><p class="eyebrow">LABORATORIO 01 / DERMS</p>
    <h1>Simulación y despacho energético</h1><p class="muted">IEEE13 · QSTS remoto · Ausgrid · batería/carga flexible modeladas</p></div>
    <span class="tag">No hay control físico</span></div>
    <div class="workspace-grid"><div class="main-workspace">
      <section class="card"><h3>Configuración de escenario</h3>${scenarioForm()}
        <div class="button-row"><button class="primary" id="runRemote">Ejecutar QSTS remoto</button>
        <button id="runOffline">Laboratorio offline explícito</button><button id="loadGood">Último confirmado</button>
        <button id="runDispatch" disabled>Optimizar batería</button></div>
        <div class="message" id="runMessage">Sin acción. Las 48 muestras históricas son independientes de IEEE13.</div>
      </section>
      <section class="card"><h3>Parámetros de la función objetivo</h3>
        <p class="muted small">Cada peso se aplica a su término normalizado. Guardar no modifica corridas anteriores.</p>
        <div id="objectiveControls" class="objective-grid"></div><button id="saveObjective">Guardar nueva función</button></section>
      ${feederDiagram()}
      <section class="card"><h3>Curvas de simulación y energía</h3>
        <p class="muted small">Curvas QSTS remoto y despacho local están etiquetadas por separado.</p>
        <div class="chart-zone"><canvas id="powerChart"></canvas></div>
        <div class="chart-zone"><canvas id="batteryChart"></canvas></div>
        <div id="timelineHost"></div></section>
      <section class="card"><h3>Decisiones por intervalo</h3><div id="dispatchTable"></div></section>
    </div><aside class="side-workspace"><div id="currentSummary" class="card"><h3>Corrida</h3><p class="muted">Seleccione o ejecute un escenario.</p></div>
      <section class="card" id="llmCard"><h3>Asistente contextual</h3><p class="muted">Seleccione una corrida.</p></section>
    </aside></div>`;
  mountSnapshotControl(root);
  const message = root.querySelector("#runMessage");
  const remoteButton = root.querySelector("#runRemote");
  const dispatchButton = root.querySelector("#runDispatch");
  let objective = await api.objective();
  const objectiveHost = root.querySelector("#objectiveControls");
  objectiveHost.innerHTML = Object.entries(objective.terms)
    .map(
      ([key, term]) => `
    <label>${escapeHtml(key)} <span class="muted small">(${escapeHtml(term.unit)})</span>
      <input type="number" data-term="${key}" min="0" max="100" step="0.01" value="${term.weight}" />
    </label>`,
    )
    .join("");
  root.querySelector("#saveObjective").onclick = async () => {
    for (const input of objectiveHost.querySelectorAll("input"))
      objective.terms[input.dataset.term].weight = Number(input.value);
    try {
      objective = await api.saveObjective(objective);
      message.textContent =
        "Función objetivo actualizada. Ejecute un nuevo despacho para medir el efecto.";
    } catch (error) {
      message.textContent = error.message;
    }
  };

  async function showRun(run) {
    if (!root.isConnected) return;
    update({ currentRun: run });
    const dispatch = run.dispatch;
    const series = dispatch?.rows ?? run.steps ?? [];
    const remote = run.steps ?? [];
    const snapshot = run.result?.simulation_type === "snapshot" ? run.result.result : null;
    root.querySelector("#currentSummary").outerHTML =
      `<section class="card" id="currentSummary">${evidence(run).replace('<section class="card">', "").replace("</section>", "")}
      <p class="muted small">${escapeHtml(run?.scenario?.derived_from_run_id ? "Despacho derivado: verificación BESS NO VALIDADA." : "Simulación eléctrica basada en multiplicador global de carga.")}</p>
      ${snapshot ? `<p class="muted small">Snapshot: converged=${escapeHtml(snapshot.converged)}, P=${escapeHtml(snapshot.total_power_kw)} kW, Q=${escapeHtml(snapshot.total_power_kvar)} kvar. BESS NOT_VALIDATED.</p>` : ""}</section>`;
    dispatchButton.disabled = !["VERIFIED", "ENERGY_MODEL_ONLY"].includes(run.status);
    root.querySelector("#dispatchTable").innerHTML = dispatchTable(dispatch?.rows);
    if (remote.length)
      drawSeries(
        root.querySelector("#powerChart"),
        remote,
        "OpenDSS QSTS remoto · kW / tensiones p.u.",
        [
          { key: "total_kw", label: "Potencia kW" },
          { key: "min_voltage_pu", label: "V mín p.u." },
          { key: "max_voltage_pu", label: "V máx p.u." },
        ],
      );
    else if (dispatch?.rows)
      drawSeries(
        root.querySelector("#powerChart"),
        series,
        "Energía modelada · sin verificación eléctrica de BESS",
        [
          { key: "load_kw", label: "Carga kW" },
          { key: "pv_kw", label: "FV kW" },
          { key: "grid_import_kw", label: "Importación kW" },
        ],
      );
    if (!remote.length && !dispatch?.rows) clearSeries(root.querySelector("#powerChart"));
    if (!dispatch?.rows) clearSeries(root.querySelector("#batteryChart"));
    if (dispatch?.rows)
      drawSeries(
        root.querySelector("#batteryChart"),
        series,
        "Despacho local de BESS · kW y SOC kWh",
        [
          { key: "battery_kw", label: "BESS kW (+ carga)" },
          { key: "soc_kwh", label: "SOC kWh" },
        ],
      );
    const timeHost = root.querySelector("#timelineHost");
    timeHost.replaceChildren();
    if (series.length)
      timeHost.append(
        timeSlider(series, (row) => {
          const stepInput = root.querySelector("#llmStep");
          if (stepInput) stepInput.value = row.step;
        }),
      );
    llmPanel(run.run_id, root.querySelector("#llmCard"));
  }

  async function refresh(runId) {
    const record = await api.run(runId);
    await showRun(record);
  }

  remoteButton.onclick = async () => {
    remoteButton.disabled = true;
    message.textContent = "Verificando salud y autenticación de OpenDSS...";
    try {
      const result = await api.createRun({
        topology: root.querySelector("#topology").value,
        profile_file: root.querySelector("#profile").value,
        scale_multiplier: Number(root.querySelector("#scale").value),
        mode: "remote",
      });
      message.textContent = `Corrida ${result.run_id.slice(0, 8)} iniciada: esperando snapshot WSS...`;
      connectLive(result.run_id, async (event) => {
        if (!root.isConnected) return;
        if (event.type === "qsts_progress")
          message.textContent = `QSTS ${event.step}/${event.total_steps} · ${event.progress_pct?.toFixed(1) ?? "?"}%`;
        if (["confirmed", "error"].includes(event.type)) {
          await refresh(result.run_id);
          message.textContent =
            event.type === "confirmed"
              ? "Corrida REMOTA validada y persistida."
              : `Error remoto: ${event.message}`;
          remoteButton.disabled = false;
        }
      });
      await refresh(result.run_id);
    } catch (error) {
      message.textContent = error.message;
      remoteButton.disabled = false;
    }
  };
  root.querySelector("#runOffline").onclick = async () => {
    message.textContent = "Ejecutando MILP y construyendo RDF local...";
    try {
      const result = await api.offline();
      await refresh(result.run_id);
      message.textContent =
        "Laboratorio energético OFFLINE ejecutado. No ha actualizado la última corrida QSTS confirmada.";
    } catch (error) {
      message.textContent = error.message;
    }
  };
  root.querySelector("#loadGood").onclick = async () => {
    const status = await api.status();
    if (status.last_good_run) await refresh(status.last_good_run.run_id);
    else message.textContent = "Todavía no existe una corrida remota confirmada.";
  };
  dispatchButton.onclick = async () => {
    if (!appState.currentRun?.run_id) return;
    try {
      const r = await api.dispatch(appState.currentRun.run_id);
      await refresh(r.run_id);
      message.textContent =
        "Nuevo despacho creado. Cambió el objetivo/modelo local, NO las consignas remotas OpenDSS.";
    } catch (error) {
      message.textContent = error.message;
    }
  };
  if (appState.currentRun?.run_id) await refresh(appState.currentRun.run_id);
  else if (appState.status?.last_good_run?.run_id)
    await refresh(appState.status.last_good_run.run_id);
}
