"""Paquetes DSS independientes: aplica el despacho al circuito IEEE13 real.

No modifica IEEE13 original ni el servidor remoto. La semántica de Storage FOLLOW
invierte el signo respecto al MILP: en DSS + = descarga, - = carga.
"""

from __future__ import annotations

import hashlib
import json
import math
import zipfile
from pathlib import Path

from backend.app.services.profile_mapper import to_multipliers
from backend.app.settings import ROOT

REFERENCE = ROOT / "data/reference/DSS_model"
BASE_FILES = ("IEEE13Nodeckt.dss", "IEEELineCodes.DSS", "IEEE13Node_BusXY.csv")
MASTER = "master.dss"


def _number(value: float) -> str:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Valor no finito en el perfil DSS")
    return f"{number:.10g}"


def _shape(name: str, multipliers: list[float], minutes: int) -> str:
    if not (multipliers and 0 < minutes <= 60):
        raise ValueError("Perfil temporal vacío o paso inválido")
    return (
        f"New LoadShape.{name} npts={len(multipliers)} "
        f"minterval={minutes} mult=({' '.join(_number(v) for v in multipliers)})"
    )


def _baseline_rows(profile: dict, scenario: dict) -> list[dict]:
    flex = scenario["flexible_load"]
    positions = range(flex["earliest_slot"], flex["earliest_slot"] + flex["slots_required"])
    return [
        {
            "step": index + 1,
            "timestamp": rec["timestamp"],
            "battery_kw": 0.0,
            "pv_kw": rec["pv_kw"],
            "pv_curtail_kw": 0.0,
            "flex_kw": flex["power_kw"] if index in positions else 0.0,
        }
        for index, rec in enumerate(profile["records"])
    ]


def build_dispatch_zip(
    profile: dict,
    scenario: dict,
    dispatch: dict | None,
    destination: Path,
    *,
    resource_scale: float = 100.0,
    variant: str = "optimized",
) -> dict:
    """Construye un ZIP ejecutable con circuitos DSS, LoadShape, Storage, PV y Load.

    :param resource_scale: Mapeo HIPOTÉTICO hogares->feeder, se registra siempre.
    """
    if variant not in {"baseline", "optimized"}:
        raise ValueError("Variante debe ser baseline u optimized")
    if not (math.isfinite(resource_scale) and 0.1 <= resource_scale <= 1000):
        raise ValueError("Escala eléctrica no permitida")
    records = profile["records"]
    count = len(records)
    if count != scenario["time_steps"] or count != 48 or scenario["step_minutes"] != 30:
        raise ValueError("El adaptador actual exige 48 intervalos de 30 minutos")
    if variant == "optimized":
        if not dispatch or len(dispatch.get("rows", [])) != count:
            raise ValueError("El despacho debe contener exactamente 48 consignas")
        rows = dispatch["rows"]
    else:
        rows = _baseline_rows(profile, scenario)
    if any(
        row["step"] != i or row["timestamp"] != records[i - 1]["timestamp"]
        for i, row in enumerate(rows, 1)
    ):
        raise ValueError("Despacho desordenado o no alineado al perfil")

    battery = scenario["battery"]
    charge_limit = float(
        battery.get(
            "nameplate_kw", max(float(battery["max_charge_kw"]), float(battery["max_discharge_kw"]))
        )
    )
    if charge_limit <= 0:
        raise ValueError("BESS sin capacidad de potencia")
    bess_scale_kw = charge_limit * resource_scale
    pv_peak_kw = (
        max(max(float(row["pv_kw"]) - float(row["pv_curtail_kw"]), 0.0) for row in rows)
        * resource_scale
    )
    pv_rating_kw = max(0.001, pv_peak_kw)
    flex_scale_kw = float(scenario["flexible_load"]["power_kw"]) * resource_scale
    storage_curve = [-float(row["battery_kw"]) / charge_limit for row in rows]
    if any(abs(v) > 1.000001 for v in storage_curve):
        raise ValueError("Consigna BESS excede potencia nominal")
    solar_curve = [
        max(
            0.0, (float(row["pv_kw"]) - float(row["pv_curtail_kw"])) * resource_scale / pv_rating_kw
        )
        for row in rows
    ]
    # LoadMult remoto multiplica TODAS las Load, también nuestra carga flexible.
    # Compensarlo por paso mantiene el kW programado en el dispositivo añadido.
    global_load_multipliers = to_multipliers(
        profile, scale_multiplier=scenario.get("scale_multiplier", 1)
    )
    flex_curve = [
        float(row["flex_kw"]) / float(scenario["flexible_load"]["power_kw"]) / factor
        for row, factor in zip(rows, global_load_multipliers, strict=True)
    ]
    if any(not 0 <= x <= 1.000001 for x in solar_curve):
        raise ValueError("Consigna solar fuera de rango")
    if any(x < 0 or not math.isfinite(x) for x in flex_curve):
        raise ValueError("Consigna de carga flexible fuera de rango")

    initial_pct = float(battery["initial_soc_kwh"]) / float(battery["capacity_kwh"]) * 100
    reserve_pct = float(battery["min_soc_kwh"]) / float(battery["capacity_kwh"]) * 100
    commands = [
        "! TKG_POWER_LAB: modelo experimental, no red residencial Ausgrid",
        "Redirect IEEE13Nodeckt.dss",
        "! Recurso BESS/FV asignado por HIPOTESIS a la barra 671, no ubicacion medida",
        _shape("TKG_BESS", storage_curve, 30),
        _shape("TKG_PV", solar_curve, 30),
        _shape("TKG_FLEX", flex_curve, 30),
        (
            "New Storage.TKG_BESS phases=3 bus1=671.1.2.3 conn=delta kv=4.16 "
            f"kWrated={_number(bess_scale_kw)} kWhrated={_number(float(battery['capacity_kwh']) * resource_scale)} "
            f"%stored={_number(initial_pct)} %reserve={_number(reserve_pct)} "
            f"%EffCharge={_number(float(battery['eta_charge']) * 100)} "
            f"%EffDischarge={_number(float(battery['eta_discharge']) * 100)} "
            "%idlingkW=0 dispmode=follow daily=TKG_BESS"
        ),
        (
            "New PVSystem.TKG_PV phases=3 bus1=671.1.2.3 kv=4.16 "
            f"pmpp={_number(pv_rating_kw)} kva={_number(pv_rating_kw * 1.2)} "
            "irradiance=1 %cutin=0 %cutout=0 daily=TKG_PV"
        ),
        (
            "New Load.TKG_FLEX phases=3 bus1=671.1.2.3 conn=delta kv=4.16 "
            f"kW={_number(flex_scale_kw)} kvar=0 daily=TKG_FLEX"
        ),
    ]
    manifest = {
        "variant": variant,
        "n_steps": count,
        "step_minutes": 30,
        "resource_scale": resource_scale,
        "assignment": "SIMULATED_NOT_PHYSICAL",
        "bus": "671",
        "global_load_multiplier_compensated_in_flex": True,
        "battery_nameplate_kw": charge_limit,
        "battery_sign_milp": "positive=charging",
        "storage_follow_sign_dss": "positive=discharging",
        "source_kind": "SIMULATED",
        "data_provenance": profile.get("source_sha256"),
        "limitations": [
            "Las consignas dependen de la sincronizacion de LoadShape con reloj QSTS; "
            "comprobar alineamiento en OpenDSS en ejecucion real.",
            "La respuesta agregada QSTS no incluye telemetria directa SOC de Storage.",
        ],
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name in BASE_FILES:
            path = REFERENCE / name
            if not path.is_file():
                raise FileNotFoundError(f"Falta modelo de referencia: {name}")
            out.write(path, arcname=name)
        out.writestr(MASTER, "\n".join(commands) + "\n")
        out.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    manifest["package_sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
    return manifest


def build_reference_zip(destination: Path) -> Path:
    """Compatibilidad con la función anterior: circuito sin recursos añadidos."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name in BASE_FILES:
            out.write(REFERENCE / name, arcname=name)
    return destination
