/** Explora RDF semántico y afirma estados temporalmente, sin inferir topología faltante. */
import { api } from "../api.js";
import { renderGraph } from "../components/graph_view.js";
import { appState } from "../state.js";

export async function graphPage(root) {
  root.innerHTML = `<div class="page-heading"><div><p class="eyebrow">LABORATORIO 02 / TKG</p>
    <h1>Explorador RDF y CIM</h1><p class="muted">Relaciones versionadas, nodos y aserciones bitemporales</p></div></div>
    <section class="card"><div id="cimInfo">Cargando inventario CIM100...</div></section>
    <section class="card"><div class="button-row"><label>Corrida<input id="graphRun" placeholder="run_id" /></label>
      <button id="loadGraph" class="primary">Cargar grafo</button></div>
      <div id="graphCanvas" class="graph-canvas"></div><div id="graphSummary" class="muted small"></div></section>
    <section class="card"><h3>Consulta temporal (as-of)</h3><div class="button-row">
      <label>Instante UTC<input type="text" id="asofTime" value="2011-06-30T14:00:00Z" /></label>
      <button id="asofSubmit">Consultar vigencia</button></div><pre id="asofResult">Seleccione una corrida.</pre></section>
    <section class="card"><h3>SPARQL SELECT (solo lectura, máximo 100 filas)</h3>
      <textarea id="sparql" rows="5" spellcheck="false">PREFIX tkg: &lt;https://example.org/derms/tkg#&gt;
SELECT ?assertion ?object WHERE { ?assertion a tkg:StateAssertion ; tkg:object ?object . } LIMIT 10</textarea>
      <div class="button-row"><button id="runQuery">Ejecutar SPARQL</button></div><pre id="sparqlResult"></pre></section>`;
  root.querySelector("#graphRun").value =
    appState.currentRun?.run_id || appState.status?.last_good_run?.run_id || "";
  try {
    const cat = (await api.requestCim?.()) ?? (await (await fetch("/api/graph/cim")).json());
    root.querySelector("#cimInfo").innerHTML =
      `<b>Modelo CIM100 original</b> · ${cat.triples} tripletas, ${cat.ac_line_segments} líneas, ${cat.terminals} terminales, ${cat.connectivity_nodes} nodos de conectividad.`;
  } catch {
    root.querySelector("#cimInfo").textContent = "Modelo CIM aún no comprobado.";
  }
  function getId() {
    return root.querySelector("#graphRun").value.trim();
  }
  root.querySelector("#loadGraph").onclick = async () => {
    try {
      const result = await api.graph(getId());
      renderGraph(root.querySelector("#graphCanvas"), result);
      root.querySelector("#graphSummary").textContent =
        `${result.count_triples} tripletas RDF. Vista limitada a 120 entidades.`;
    } catch (error) {
      root.querySelector("#graphSummary").textContent = error.message;
    }
  };
  root.querySelector("#asofSubmit").onclick = async () => {
    const target = root.querySelector("#asofResult");
    try {
      target.textContent = JSON.stringify(
        await api.asof(getId(), root.querySelector("#asofTime").value),
        null,
        2,
      );
    } catch (error) {
      target.textContent = error.message;
    }
  };
  root.querySelector("#runQuery").onclick = async () => {
    const target = root.querySelector("#sparqlResult");
    try {
      target.textContent = JSON.stringify(
        await api.graphQuery({ run_id: getId(), query: root.querySelector("#sparql").value }),
        null,
        2,
      );
    } catch (error) {
      target.textContent = error.message;
    }
  };
}
