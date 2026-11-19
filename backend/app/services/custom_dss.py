"""Plantilla de paquete DSS aislado; no se ejecuta como si estuviese validado."""

import zipfile
from pathlib import Path

from backend.app.settings import ROOT


def build_reference_zip(destination: Path) -> Path:
    """Empaqueta solo modelo de referencia, sin insertar BESS/PV no validado."""
    files = [
        ROOT / "data/reference/DSS_model/IEEE13Nodeckt.dss",
        ROOT / "data/reference/DSS_model/IEEELineCodes.DSS",
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for item in files:
            out.write(item, arcname=item.name)
    return destination
