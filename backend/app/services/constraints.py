"""Verificación independiente SOC, balance, eficiencia y programación flexible."""


def validate_dispatch(rows: list[dict], scenario: dict, *, tolerance: float = 1e-4) -> list[str]:
    b = scenario["battery"]
    limits = scenario["limits"]
    errors = []
    soc = b["initial_soc_kwh"]
    dt = scenario["step_minutes"] / 60
    flex_count = 0
    for index, row in enumerate(rows):
        power = float(row["battery_kw"])
        if not -b["max_discharge_kw"] - tolerance <= power <= b["max_charge_kw"] + tolerance:
            errors.append(f"t={index}: potencia batería")
        expected_soc = (
            soc + b["eta_charge"] * max(power, 0) * dt - max(-power, 0) * dt / b["eta_discharge"]
        )
        if abs(row["soc_kwh"] - expected_soc) > tolerance:
            errors.append(f"t={index}: balance SOC")
        soc = expected_soc
        if not b["min_soc_kwh"] - tolerance <= soc <= b["max_soc_kwh"] + tolerance:
            errors.append(f"t={index}: SOC fuera de límite")
        flexible = float(row["flex_kw"])
        if flexible > tolerance:
            flex_count += 1
            if (
                not scenario["flexible_load"]["earliest_slot"]
                <= index
                <= scenario["flexible_load"]["latest_slot"]
            ):
                errors.append(f"t={index}: carga flexible fuera de ventana")
        balance = row["load_kw"] + flexible - row["pv_kw"] + row["pv_curtail_kw"] + power
        if abs(row["grid_import_kw"] - row["grid_export_kw"] - balance) > tolerance:
            errors.append(f"t={index}: balance energético")
        if not -tolerance <= row["grid_import_kw"] <= limits["grid_import_kw"] + tolerance:
            errors.append(f"t={index}: límite de importación")
        if not -tolerance <= row["grid_export_kw"] <= limits["grid_export_kw"] + tolerance:
            errors.append(f"t={index}: límite de exportación")
    if flex_count != scenario["flexible_load"]["slots_required"]:
        errors.append("Cantidad de intervalos de carga flexible incorrecta")
    if soc < b["terminal_min_kwh"] - tolerance:
        errors.append("SOC terminal inferior al mínimo")
    return errors
