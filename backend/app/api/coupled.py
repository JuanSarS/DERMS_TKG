"""API local: ejecutar flujo TKG/MILP + modelos custom IEEE13 QSTS."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.dependencies import require_mutation, services
from backend.app.services.ausgrid import parse_profile
from backend.app.services.coupled_runner import CoupledRunner
from backend.app.settings import ROOT, read_json

router = APIRouter()


class CoupledRequest(BaseModel):
    profile_file: str = Field(default="ausgrid_c12_2011-07-01.csv", max_length=100)
    resource_scale: float = Field(default=100.0, ge=0.1, le=1000)
    max_passes: int = Field(default=2, ge=1, le=3)
    load_scale: float = Field(default=1.0, gt=0, le=5)
    mode: Literal["builtin_proxy", "custom_dss"] = "builtin_proxy"


@router.post("/coupled-runs", status_code=202, dependencies=[Depends(require_mutation)])
async def coupled_run(payload: CoupledRequest, s=Depends(services)):
    if any(char in payload.profile_file for char in ("/", "\\", "..")):
        raise HTTPException(422, "Nombre de perfil inválido")
    remote = await s.monitor.check(authenticate=True)
    if remote["state"] != "HEALTHY":
        raise HTTPException(503, "OpenDSS /health o autenticación fallaron; historial conservado")
    scenario = read_json(ROOT / "config/scenario_ieee13.json")
    scenario["profile_file"] = payload.profile_file
    scenario["scale_multiplier"] = payload.load_scale
    scenario["custom_resource_scale"] = payload.resource_scale
    scenario["coupled_max_passes"] = payload.max_passes
    scenario["coupled_mode"] = payload.mode
    objective = read_json(ROOT / "config/objective.json")
    try:
        profile = parse_profile(ROOT / "data/processed" / payload.profile_file)
    except (ValueError, FileNotFoundError, KeyError, OSError) as exc:
        raise HTTPException(422, f"Perfil inválido: {exc}") from exc
    run_id = s.store.create(scenario, objective, origin_kind="DERIVED")
    runner = CoupledRunner(
        remote=s.remote,
        monitor=s.monitor,
        manager=s.manager,
        orchestrator=s.orchestrator,
    )
    s.manager.launch(
        run_id,
        runner.execute(
            run_id,
            profile,
            scenario,
            objective,
            resource_scale=payload.resource_scale,
            max_passes=payload.max_passes,
            mode=payload.mode,
        ),
    )
    return {
        "run_id": run_id,
        "status": "PENDING",
        "message": (
            "IEEE13 integrado: referencia, política fija y proxy agregado de despacho. "
            "NO se validan consignas individuales BESS."
            if payload.mode == "builtin_proxy"
            else "Se intentará ejecutar IEEE13 DSS personalizado con Storage/PVSystem."
        ),
        "validation_scope": (
            "BUILTIN_IEEE13_NETLOAD_PROXY_NOT_BESS_VALIDATION"
            if payload.mode == "builtin_proxy"
            else "AGGREGATED_FEEDER_QSTS_ONLY"
        ),
    }
