/** Vista interactiva de nodos/relaciones RDF; se limita para no bloquear el navegador. */
import cytoscape from "cytoscape";

export function renderGraph(container, data) {
  const ids = new Set();
  const nodes = [];
  for (const n of data.nodes || []) {
    if (!ids.has(n.id)) {
      ids.add(n.id);
      nodes.push({ data: { id: n.id, label: n.label } });
    }
  }
  for (const e of data.edges || []) {
    for (const id of [e.source, e.target]) {
      if (!ids.has(id)) {
        ids.add(id);
        nodes.push({ data: { id, label: id.split("/").at(-1) } });
      }
    }
  }
  const edges = (data.edges || []).map((e, index) => ({
    data: { id: `e${index}`, source: e.source, target: e.target, label: e.label },
  }));
  return cytoscape({
    container,
    elements: [...nodes, ...edges],
    style: [
      {
        selector: "node",
        style: {
          "background-color": "#3bb6e7",
          label: "data(label)",
          color: "#eaf2fa",
          "font-size": 10,
          "text-valign": "bottom",
          "text-margin-y": 7,
        },
      },
      {
        selector: "edge",
        style: {
          width: 1.3,
          "line-color": "#7089a6",
          "target-arrow-color": "#7089a6",
          "target-arrow-shape": "triangle",
          label: "data(label)",
          color: "#aec6dc",
          "font-size": 7,
        },
      },
    ],
    layout: { name: "cose", animate: false, randomize: false },
    minZoom: 0.25,
    maxZoom: 3,
  });
}
