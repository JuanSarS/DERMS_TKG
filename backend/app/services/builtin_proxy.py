"""Escenarios QSTS con IEEE13 integrado, usando SOLO LoadMult.

No crea Storage/PVSystem y nunca declara verificación física de BESS.
La inyección neta modelada se representa como cambio equivalente de carga.
"""

from __future__ import annotations

import math

from backend.app.services.profile_mapper import to_multipliers

MIN_LOAD_MULT = 0.001
MAX_LOAD_MULT = 5.0


def proxy_multipliers(
    profile: dict,
    scenario: dict,
    reference_qsts: dict,
    dispatch_rows: list[dict],
    *,
    resource_scale: float,
    reference_multipliers: list[float] | None = None,
) -> tuple[list[float], dict]:
    """Translate net-power *assumptions* into feeder-wide load multipliers.

    The feeder's per-step apparent active-power sensitivity is approximated by
    |P_ref| / LoadMult_ref; voltage-dependent losses are not corrected. No
    individual resource, inverter or battery constraints are checked.
    """
    records = profile["records"]
    steps = reference_qsts.get("steps", [])
    if len(records) != 48 or len(steps) != 48 or len(dispatch_rows) != 48:
        raise ValueError("Proxy IEEE13 exige 48 registros, decisiones y resultados QSTS")
    if not math.isfinite(resource_scale) or not 0 < resource_scale <= 1000:
        raise ValueError("Escala experimental inválida")
    original = reference_multipliers or to_multipliers(
        profile, scale_multiplier=float(scenario.get("scale_multiplier", 1))
    )
    if len(original) != 48:
        raise ValueError("Multiplicadores de referencia incompletos")
    new_values: list[float] = []
    audit: list[dict] = []
    for index, (qsts, rec, decision, mult) in enumerate(
        zip(steps, records, dispatch_rows, original, strict=True), start=1
    ):
        if (
            int(qsts["step"]) != index
            or int(decision["step"]) != index
            or decision["timestamp"] != rec["timestamp"]
            or not qsts.get("converged", False)
        ):
            raise ValueError(f"Referencia QSTS inválida o desalineada en paso {index}")
        observed_mult = float(qsts.get("load_multiplier", mult))
        if abs(observed_mult - mult) > 1e-5:
            raise ValueError(f"Multiplicador QSTS distinto de referencia en paso {index}")
        p_ref = abs(float(qsts["total_kw"]))
        if not math.isfinite(p_ref) or p_ref < 1:
            raise ValueError(f"Potencia base no calibrable en paso {index}")
        # MILP: positivo = carga de batería. FV disponible = producción menos recorte.
        change_kw = resource_scale * (
            float(decision["battery_kw"])
            + float(decision["flex_kw"])
            - (float(decision["pv_kw"]) - float(decision["pv_curtail_kw"]))
        )
        # Observed QSTS P is used only as an approximate local sensitivity.
        factor = 1 + change_kw / p_ref
        candidate = float(mult) * factor
        if not math.isfinite(candidate) or not MIN_LOAD_MULT <= candidate <= MAX_LOAD_MULT:
            raise ValueError(
                f"Intervalo {index}: LoadMult equivalente {candidate:.5g} fuera de "
                f"[{MIN_LOAD_MULT}, {MAX_LOAD_MULT}]. Reducir escala o usar otro caso. "
                "No se recorta silenciosamente el valor."
            )
        new_values.append(round(candidate, 6))
        audit.append(
            {
                "step": index,
                "reference_multiplier": float(mult),
                "proxy_multiplier": round(candidate, 6),
                "reference_abs_feeder_kw": p_ref,
                "assumed_delta_net_kw": change_kw,
                "assumed_bess_kw": float(decision["battery_kw"]),
                "assumed_pv_kw": float(decision["pv_kw"]) - float(decision["pv_curtail_kw"]),
                "assumed_flex_kw": float(decision["flex_kw"]),
            }
        )
    return new_values, {
        "mapping": "FEEDER_WIDE_LOAD_MULTIPLIER_PROXY",
        "resource_scale": resource_scale,
        "steps": audit,
        "device_telemetry_verified": False,
        "pv_storage_elements_in_feeder": False,
        "limits": [MIN_LOAD_MULT, MAX_LOAD_MULT],
        "warning": (
            "Sustitución aproximada de inyecciones por LoadMult global: cambia todas las "
            "cargas y su potencia reactiva. NO hay Storage/PVSystem en IEEE13 integrado. "
            "Las respuestas de tensión solo corresponden al equivalente agregado, no a "
            "consignas individuales de batería ni a una factibilidad DERMS validada."
        ),
    }


def fixed_policy_rows(profile: dict, scenario: dict) -> list[dict]:
    """Same PV and fixed flexible demand as the non-optimized cost baseline."""
    f = scenario["flexible_load"]
    return [
        {
            "step": i,
            "timestamp": rec["timestamp"],
            "battery_kw": 0.0,
            "flex_kw": float(f["power_kw"])
            if f["earliest_slot"] <= i - 1 < f["earliest_slot"] + f["slots_required"]
            else 0.0,
            "pv_kw": float(rec["pv_kw"]),
            "pv_curtail_kw": 0.0,
        }
        for i, rec in enumerate(profile["records"], 1)
    ]
