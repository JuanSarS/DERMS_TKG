/** Asistente contextual: diagnósticos reales de Ollama y evidencias RDF/SQL. */
import { api } from "../api.js";
import { escapeHtml } from "../state.js";

export function llmPanel(runId, container) {
  container.innerHTML = `<h3>Asistente contextual</h3>
    <p class="muted small">El modelo explica evidencias RDF/SQL; no ejecuta consignas.</p>
    <p id="ollamaDiagnostic" class="muted small" role="status">Comprobando Ollama...</p>
    <textarea id="llmQuestion" rows="3" placeholder="¿Qué decidió la batería y qué evidencia TKG lo respalda?"></textarea>
    <label>Paso<input id="llmStep" type="number" min="1" max="48" value="1" /></label>
    <button id="llmAsk" class="primary">Explicar con evidencias</button>
    <button id="llmPropose">Sugerir pesos (sin aplicar)</button>
    <div id="llmAnswer" role="status"></div>`;

  const statusHost = container.querySelector("#ollamaDiagnostic");
  api
    .llmStatus()
    .then((status) => {
      if (!statusHost.isConnected) return;
      statusHost.textContent =
        status.status === "READY"
          ? `Ollama READY · modelo ${status.model} · respuesta generada no validada`
          : `Ollama ${status.status}: ${status.hint ?? "Revise la configuración"}`;
    })
    .catch((error) => {
      statusHost.textContent = `Diagnóstico Ollama falló: ${error.message}`;
    });

  const params = () => ({
    run_id: runId,
    question: container.querySelector("#llmQuestion").value || "Explica la evidencia de este paso",
    step: Number(container.querySelector("#llmStep").value),
  });
  container.querySelector("#llmAsk").onclick = async () => {
    const out = container.querySelector("#llmAnswer");
    out.textContent = "Consultando RDF, historial y Ollama...";
    try {
      const result = await api.explain(params());
      const graph = result.evidence?.tkg;
      const references = (graph?.asof ?? [])
        .slice(0, 3)
        .map((x) => x.assertion)
        .join(" · ");
      out.innerHTML = `<p>${escapeHtml(result.answer)}</p>
        <p class="muted small">Estado: ${escapeHtml(result.status)} · modelo: ${escapeHtml(result.model || "no disponible")}</p>
        <p class="muted small">TKG: ${escapeHtml(graph?.status || graph?.triples || "N/D")} · Aserciones: ${escapeHtml(references || "ninguna para este paso")}</p>
        ${result.diagnostic ? `<p class="muted small">${escapeHtml(result.diagnostic)}</p>` : ""}`;
    } catch (error) {
      out.textContent = error.message;
    }
  };
  container.querySelector("#llmPropose").onclick = async () => {
    const out = container.querySelector("#llmAnswer");
    out.textContent = "Solicitando propuesta no ejecutable...";
    try {
      const response = await api.propose(params());
      out.textContent = response.proposal
        ? `Propuesta NO aplicada: ${JSON.stringify(response.proposal)}. Valide antes de cambiar pesos.`
        : `LLM ${response.status}: ${response.hint || "No se efectuaron cambios."}`;
    } catch (error) {
      out.textContent = error.message;
    }
  };
}
