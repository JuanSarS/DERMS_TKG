"""Traduce eventos WS remoto al canal local sin confundirlos con resultados finales."""


def normalize_event(run_id: str, event: dict) -> dict:
    kind = event.get("type")
    valid = {
        "snapshot",
        "simulation_started",
        "model_loaded",
        "solving",
        "qsts_progress",
        "result",
        "completed",
        "error",
    }
    if kind not in valid:
        return {"type": "upstream_unknown", "run_id": run_id, "original_type": str(kind)}
    kept = {k: v for k, v in event.items() if k not in ("access_token", "token", "cookie")}
    return {"run_id": run_id, **kept}
