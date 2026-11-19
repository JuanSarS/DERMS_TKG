"""Contrato CSV normalizado con potencia media, zona horaria y SHA256."""

from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from backend.app.settings import ROOT


def parse_profile(path: Path) -> dict:
    path = path.resolve()
    if not path.is_relative_to((ROOT / "data/processed").resolve()):
        raise ValueError("El perfil debe residir en data/processed")
    with path.open(encoding="utf8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or len(rows) != 48:
        raise ValueError("Se requieren 48 registros de 30 minutos")
    times, series = [], []
    for row in rows:
        t = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        if t.tzinfo is None or t.utcoffset() != timedelta(0):
            raise ValueError("Fechas UTC con zona explícita obligatorias")
        load, pv = float(row["load_kw"]), float(row["pv_kw"])
        if not 0 <= load <= 10000 or not 0 <= pv <= 10000:
            raise ValueError("Potencias fuera de rango")
        times.append(t)
        series.append(
            {"timestamp": t.isoformat().replace("+00:00", "Z"), "load_kw": load, "pv_kw": pv}
        )
    if any((b - a) != timedelta(minutes=30) for a, b in zip(times, times[1:])):
        raise ValueError("Intervalos no consecutivos")
    return {
        "records": series,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_kind": "REAL",
        "processed_kind": "DERIVED",
        "input_name": path.name,
        "timezone": "UTC",
        "unit": "kW average per interval",
    }


def default_profile() -> dict:
    return parse_profile(ROOT / "data/processed/ausgrid_c12_2011-07-01.csv")
