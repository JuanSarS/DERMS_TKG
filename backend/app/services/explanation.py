"""Explicación determinista que distingue simulación remota de despacho local."""

from __future__ import annotations


def evidence_packet(run: dict, step: int | None = None) -> dict:
    dispatch = run.get("dispatch") or {}
    rows = dispatch.get("rows", [])
    selected = next((row for row in rows if row.get("step") == step), None) if step else None
    qsts_steps = run.get("steps", [])
    qsts_selected = next((row for row in qsts_steps if row.get("step") == step), None)
    result = run.get("result") or {}
    snapshot = result.get("result") if result.get("simulation_type") == "snapshot" else None
    return {
        "run_id": run["run_id"],
        "status": run["status"],
        "source": run.get("origin_kind"),
        "electrical_verification": run.get("remote_verification", "NOT_VALIDATED"),
        "step_requested": step,
        "step": selected,
        "qsts_step": qsts_selected,
        "snapshot_result": {
            key: snapshot.get(key)
            for key in (
                "converged",
                "load_multiplier",
                "total_power_kw",
                "total_power_kvar",
                "elapsed_ms",
            )
        }
        if snapshot
        else None,
        "objective": dispatch.get("objective"),
        "metrics": dispatch.get("metrics"),
        "caveat": (
            "El QSTS remoto normal aplica solo multiplicadores globales. "
            "En una corrida acoplada se evalúa un modelo DSS con Storage/PV "
            "pero falta telemetría individual y sincronización de consignas verificada."
        ),
    }


def deterministic_explanation(evidence: dict) -> str:
    step = evidence.get("step")
    if step:
        return (
            f"En {step['timestamp']}, consigna BESS={step['battery_kw']:.3f} kW "
            f"(positivo=carga), SOC={step['soc_kwh']:.3f} kWh. "
            "Decisión calculada por MILP. La validación requiere revisar coupled_validation. "
            f"Aserciones RDF consultadas: {len(evidence.get('tkg', {}).get('asof', []))}."
        )
    qsts = evidence.get("qsts_step")
    if qsts:
        return (
            f"Paso remoto QSTS {qsts['step']}: converged={qsts.get('converged')}, "
            f"multiplicador global={qsts.get('load_multiplier')}. "
            "No se calculó despacho BESS en esta corrida."
        )
    snap = evidence.get("snapshot_result")
    if snap:
        return (
            f"Snapshot OpenDSS: converged={snap.get('converged')}, "
            f"potencia total={snap.get('total_power_kw')} kW, "
            f"multiplicador global={snap.get('load_multiplier')}. "
            "No valida una consigna BESS individual."
        )
    return (
        f"Corrida {evidence['run_id']}. Estado {evidence['status']}; "
        f"verificación eléctrica: {evidence.get('electrical_verification', 'NOT_VALIDATED')}. "
        "No hay decisión de BESS para el paso seleccionado. Los costos modelados no "
        "constituyen una mejora atribuible al TKG."
    )
