/** Panel LLM: explicación y trazas, sin permisos de ejecutar control. */
import { api } from "../api.js";
import { escapeHtml } from "../state.js";

export function llmPanel(runId, container) {
  container.innerHTML = `<h3>Asistente contextual</h3><p class="muted small">Ollama opcional. Fallback determinista si no está disponible.</p>
    <textarea id="llmQuestion" rows="2" placeholder="¿Por qué se cargó la batería en este paso?"></textarea>
    <label>Paso<input id="llmStep" type="number" min="1" max="48" value="1" /></label>
    <button id="llmAsk" class="primary">Explicar con evidencias</button>
    <button id="llmPropose">Sugerir pesos (sin aplicar)</button><div id="llmAnswer"></div>`;
  container.querySelector("#llmPropose").onclick = async () => {
    const out = container.querySelector("#llmAnswer");
    out.textContent = "Solicitando pesos, sin ejecutar ninguna acción...";
    try {
      const response = await api.propose({
        run_id: runId,
        question: container.querySelector("#llmQuestion").value || "Reducir el pico de demanda",
        step: Number(container.querySelector("#llmStep").value),
      });
      out.textContent = response.proposal
        ? `Propuesta NO aplicada: ${JSON.stringify(response.proposal)}. Ajuste los pesos manualmente y valide.`
        : `LLM: ${response.status}. No se efectuaron cambios.`;
    } catch (error) {
      out.textContent = error.message;
    }
  };
  container.querySelector("#llmAsk").onclick = async () => {
    const question =
      container.querySelector("#llmQuestion").value || "Explica la decisión de este paso";
    const step = Number(container.querySelector("#llmStep").value);
    const out = container.querySelector("#llmAnswer");
    out.textContent = "Consultando evidencia...";
    try {
      const r = await api.explain({ run_id: runId, question, step });
      out.innerHTML = `<p>${escapeHtml(r.answer)}</p><p class="muted small">Estado: ${escapeHtml(r.status)} · modelo: ${escapeHtml(r.model || "no disponible")}</p>`;
    } catch (error) {
      out.textContent = error.message;
    }
  };
}
