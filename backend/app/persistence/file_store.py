"""Exportación de evidencias con archivos atómicos y SHA256."""

import hashlib
import json
import os
from pathlib import Path

from backend.app.settings import ROOT


def dump_json(path: Path, obj: dict | list) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf8")
    os.replace(temp, path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_run(run: dict) -> Path:
    out = ROOT / "results/runs" / run["run_id"]
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    files["run.json"] = dump_json(out / "run.json", run)
    files["steps.json"] = dump_json(out / "steps.json", run["steps"])
    if "dispatch" in run:
        files["dispatch.json"] = dump_json(out / "dispatch.json", run["dispatch"])
    manifest = {
        "run_id": run["run_id"],
        "checksums_sha256": files,
        "source_kind": run.get("origin_kind"),
        "verification": run.get("remote_verification"),
    }
    dump_json(out / "manifest.json", manifest)
    return out
