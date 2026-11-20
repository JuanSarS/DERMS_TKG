"""Construcción de contexto RDF/SQL y explicación Ollama con alternativa determinista."""

from backend.app.integrations.ollama_http import Ollama
from backend.app.services.evidence_context import build_context
from backend.app.services.explanation import deterministic_explanation


async def explain(run: dict, question: str, step: int | None = None, store=None) -> dict:
    packet = build_context(run, step, store=store)
    deterministic = deterministic_explanation(packet)
    generated = await Ollama().explain(packet, question)
    return {
        "status": generated["status"],
        "answer": generated["answer"]
        if generated["status"] == "GENERATED_NOT_VALIDATED"
        else deterministic,
        "fallback": deterministic,
        "diagnostic": generated.get(
            "hint",
            generated.get("answer") if generated["status"] != "GENERATED_NOT_VALIDATED" else None,
        ),
        "model": generated.get("model"),
        "evidence": packet,
    }
