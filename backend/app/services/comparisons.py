"""Diferencia optimización vs control y comparación temporal RDF/SQL sin atribuciones falsas."""

from backend.app.services.objective_registry import evaluate


def baseline(profile: dict, scenario: dict, objective: dict) -> dict:
    rows = []
    dt = scenario["step_minutes"] / 60
    f = scenario["flexible_load"]
    energy = peak = curtail = 0.0
    for t, sample in enumerate(profile["records"]):
        flex = (
            f["power_kw"]
            if f["earliest_slot"] <= t < f["earliest_slot"] + f["slots_required"]
            else 0.0
        )
        net = sample["load_kw"] + flex - sample["pv_kw"]
        im, ex = max(net, 0), max(-net, 0)
        if im > scenario["limits"]["grid_import_kw"] or ex > scenario["limits"]["grid_export_kw"]:
            return {"status": "NOT_FEASIBLE_BASELINE", "reason": "Límite de red superado"}
        tariff = (
            scenario["tariff"]["buy_peak_aud_per_kwh"]
            if scenario["tariff"]["peak_start_slot"] <= t < scenario["tariff"]["peak_end_slot"]
            else scenario["tariff"]["buy_offpeak_aud_per_kwh"]
        )
        energy += (im * tariff - ex * scenario["tariff"]["sell_aud_per_kwh"]) * dt
        peak = max(peak, im)
        rows.append({"step": t + 1, "grid_import_kw": im, "grid_export_kw": ex})
    metrics = {"energy": energy, "peak": peak, "battery": 0.0, "curtail": curtail}
    return {
        "status": "ENERGY_MODEL_BASELINE",
        "metrics": metrics,
        "objective": evaluate(objective, metrics),
        "rows": rows,
        "electrical_verification": "NOT_VALIDATED",
    }


def compare_dispatch(profile: dict, scenario: dict, objective: dict, dispatch: dict) -> dict:
    base = baseline(profile, scenario, objective)
    return {
        "baseline": base,
        "optimized": {
            k: dispatch[k] for k in ("status", "metrics", "objective", "electrical_verification")
        },
        "causal_warning": "La diferencia de costo es del optimizador, NO del TKG.",
    }
