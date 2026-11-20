"""Despacho óptimo offline MILP; energía/peak/throughput/curtail y restricciones explícitas."""

from __future__ import annotations

from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from backend.app.services.constraints import validate_dispatch
from backend.app.services.objective_registry import coefficient, evaluate

VARIABLES = (
    "charge",
    "discharge",
    "import",
    "export",
    "curtail",
    "soc",
    "flex",
    "battery_mode",
    "grid_mode",
)


def tariff(scenario: dict, index: int) -> float:
    setting = scenario["tariff"]
    return (
        setting["buy_peak_aud_per_kwh"]
        if setting["peak_start_slot"] <= index < setting["peak_end_slot"]
        else setting["buy_offpeak_aud_per_kwh"]
    )


def optimize(
    profile: dict,
    scenario: dict,
    objective: dict,
    operational_context: list[dict] | None = None,
) -> dict:
    data = profile["records"]
    count = len(data)
    if not data or count != scenario["time_steps"]:
        raise ValueError("La cantidad de muestras no coincide con el escenario")
    if operational_context is not None and len(operational_context) != count:
        raise ValueError("Contexto TKG no coincide con el número de intervalos")
    dt = scenario["step_minutes"] / 60.0
    b, f, limits = scenario["battery"], scenario["flexible_load"], scenario["limits"]
    names = len(VARIABLES)
    nvars = names * count + 1
    peak_id = nvars - 1

    def at(step: int, key: str) -> int:
        return step * names + VARIABLES.index(key)

    lower = [0.0] * nvars
    upper = [float("inf")] * nvars
    integral = [0] * nvars
    costs = [0.0] * nvars
    constraints = []

    def add_constraint(terms: dict[int, float], lb: float, ub: float):
        constraints.append((terms, lb, ub))

    for t, sample in enumerate(data):
        v = {key: at(t, key) for key in VARIABLES}
        context = (
            operational_context[t]
            if operational_context is not None
            else {"availability": "AVAILABLE"}
        )
        if context.get("availability") not in ("AVAILABLE", "UNAVAILABLE"):
            raise ValueError("TKG entregó disponibilidad no válida")
        available = context["availability"] == "AVAILABLE"
        upper[v["charge"]] = b["max_charge_kw"] if available else 0.0
        upper[v["discharge"]] = b["max_discharge_kw"] if available else 0.0
        upper[v["import"]] = limits["grid_import_kw"]
        upper[v["export"]] = limits["grid_export_kw"]
        upper[v["curtail"]] = float(sample["pv_kw"])
        lower[v["soc"]] = b["min_soc_kwh"]
        upper[v["soc"]] = b["max_soc_kwh"]
        for key in ("flex", "battery_mode", "grid_mode"):
            upper[v[key]] = 1
            integral[v[key]] = 1
        if not f["earliest_slot"] <= t <= f["latest_slot"]:
            upper[v["flex"]] = 0
        # Import/export exclusive, battery charge/discharge exclusive.
        add_constraint({v["charge"]: 1, v["battery_mode"]: -b["max_charge_kw"]}, -float("inf"), 0)
        add_constraint(
            {v["discharge"]: 1, v["battery_mode"]: b["max_discharge_kw"]},
            -float("inf"),
            b["max_discharge_kw"],
        )
        add_constraint(
            {v["import"]: 1, v["grid_mode"]: -limits["grid_import_kw"]}, -float("inf"), 0
        )
        add_constraint(
            {v["export"]: 1, v["grid_mode"]: limits["grid_export_kw"]},
            -float("inf"),
            limits["grid_export_kw"],
        )
        # Grid import - grid export = load + flexible + charge - discharge - PV + curtail.
        add_constraint(
            {
                v["import"]: 1,
                v["export"]: -1,
                v["charge"]: -1,
                v["discharge"]: 1,
                v["curtail"]: -1,
                v["flex"]: -f["power_kw"],
            },
            sample["load_kw"] - sample["pv_kw"],
            sample["load_kw"] - sample["pv_kw"],
        )
        # Storage SOC increments, initial measured only as model assumption.
        balance = {
            v["soc"]: 1,
            v["charge"]: -dt * b["eta_charge"],
            v["discharge"]: dt / b["eta_discharge"],
        }
        if t:
            balance[at(t - 1, "soc")] = -1
        initial = 0 if t else b["initial_soc_kwh"]
        add_constraint(balance, initial, initial)
        # Peak bound, shared across intervals.
        add_constraint({peak_id: 1, v["import"]: -1}, 0, float("inf"))
        e = coefficient(objective, "energy")
        costs[v["import"]] = e * tariff(scenario, t) * dt
        costs[v["export"]] = -e * scenario["tariff"]["sell_aud_per_kwh"] * dt
        costs[v["charge"]] += coefficient(objective, "battery") * dt
        costs[v["discharge"]] += coefficient(objective, "battery") * dt
        costs[v["curtail"]] += coefficient(objective, "curtail") * dt
    add_constraint(
        {at(t, "flex"): 1 for t in range(count)}, f["slots_required"], f["slots_required"]
    )
    add_constraint({at(count - 1, "soc"): 1}, b["terminal_min_kwh"], float("inf"))
    upper[peak_id] = limits["grid_import_kw"]
    costs[peak_id] = coefficient(objective, "peak")
    matrix = lil_matrix((len(constraints), nvars), dtype=float)
    c_lo = []
    c_hi = []
    for i, (coeffs, lo, hi) in enumerate(constraints):
        for j, val in coeffs.items():
            matrix[i, j] = val
        c_lo.append(lo)
        c_hi.append(hi)
    result = milp(
        c=costs,
        integrality=integral,
        bounds=Bounds(lower, upper),
        constraints=LinearConstraint(matrix.tocsr(), c_lo, c_hi),
        options={"time_limit": 45, "mip_rel_gap": 0.01},
    )
    if result.x is None or result.status != 0:
        raise ValueError(f"Sin despacho factible: status MILP={result.status}; {result.message}")
    rows = []
    for t, sample in enumerate(data):
        charge, discharge = result.x[at(t, "charge")], result.x[at(t, "discharge")]
        rows.append(
            {
                "step": t + 1,
                "timestamp": sample["timestamp"],
                "load_kw": sample["load_kw"],
                "pv_kw": sample["pv_kw"],
                "battery_kw": float(charge - discharge),
                "soc_kwh": float(result.x[at(t, "soc")]),
                "grid_import_kw": float(result.x[at(t, "import")]),
                "grid_export_kw": float(result.x[at(t, "export")]),
                "pv_curtail_kw": float(result.x[at(t, "curtail")]),
                "flex_kw": f["power_kw"] if result.x[at(t, "flex")] > 0.5 else 0.0,
                "tariff_aud_per_kwh": tariff(scenario, t),
                "source_kind": "DERIVED",
                "electrical_validation": "NOT_VALIDATED",
                "operational_context": operational_context[t] if operational_context else None,
            }
        )
    errors = validate_dispatch(rows, scenario)
    if errors:
        raise ValueError("MILP violates constraints: " + "; ".join(errors[:8]))
    raw = {
        "energy": sum(
            (
                x["grid_import_kw"] * x["tariff_aud_per_kwh"]
                - x["grid_export_kw"] * scenario["tariff"]["sell_aud_per_kwh"]
            )
            * dt
            for x in rows
        ),
        "peak": max(x["grid_import_kw"] for x in rows),
        "battery": sum(abs(x["battery_kw"]) * dt for x in rows),
        "curtail": sum(x["pv_curtail_kw"] * dt for x in rows),
    }
    return {
        "rows": rows,
        "metrics": raw,
        "objective": evaluate(objective, raw),
        "status": "ENERGY_MODEL_OPTIMIZED",
        "electrical_verification": "NOT_VALIDATED",
        "solver": "scipy.optimize.milp",
        "optimality_gap_limit": 0.01,
        "warnings": [
            "La batería y la carga flexible son escenarios modelados; QSTS remoto aún no aplica estas consignas."
        ],
    }
