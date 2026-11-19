"""Compone explicación determinista y LLM opcional bajo el mismo paquete de evidencia."""

from backend.app.integrations.ollama_http import Ollama
from backend.app.services.explanation import deterministic_explanation, evidence_packet


async def explain(run: dict, question: str, step: int | None = None) -> dict:
    packet = evidence_packet(run, step)
    deterministic = deterministic_explanation(packet)
    llm = await Ollama().explain(packet, question)
    return {
        "status": llm["status"],
        "answer": llm["answer"] if llm["status"] == "GENERATED_NOT_VALIDATED" else deterministic,
        "fallback": deterministic,
        "model": llm.get("model"),
        "evidence": packet,
    }
