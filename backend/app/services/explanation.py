"""Explicación determinista con evidencia incluso si Ollama está apagado."""


def evidence_packet(run: dict, step: int | None = None) -> dict:
    dispatch = run.get("dispatch", {})
    rows = dispatch.get("rows", [])
    selected = next((x for x in rows if x["step"] == step), None) if step else None
    return {
        "run_id": run["run_id"],
        "status": run["status"],
        "source": run.get("origin_kind"),
        "electrical_verification": run.get("remote_verification"),
        "step": selected,
        "objective": dispatch.get("objective"),
        "metrics": dispatch.get("metrics"),
        "caveat": "QSTS remoto valida únicamente multiplicadores globales; no consignas de BESS.",
    }


def deterministic_explanation(evidence: dict) -> str:
    step = evidence.get("step")
    if step:
        return (
            f"En {step['timestamp']}, la batería tiene una consigna energética "
            f"de {step['battery_kw']:.3f} kW (positivo=carga), SOC={step['soc_kwh']:.3f} kWh. "
            "Es una decisión optimizada localmente, todavía sin validación eléctrica de BESS en OpenDSS."
        )
    return (
        f"Corrida {evidence['run_id']}. Estado {evidence['status']}; "
        f"verificación eléctrica: {evidence['electrical_verification']}. "
        "Los costos modelados no son mejora atribuible al TKG."
    )
