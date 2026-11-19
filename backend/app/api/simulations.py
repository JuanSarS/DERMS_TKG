"""Ejecución QSTS remota, historial y verificación eléctrica honestamente diferenciada."""

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.dependencies import require_mutation, services
from backend.app.contracts.scenario import RunRequest
from backend.app.persistence.file_store import export_run
from backend.app.services.ausgrid import parse_profile
from backend.app.services.comparisons import compare_dispatch
from backend.app.services.dispatcher import optimize
from backend.app.services.electrical_check import verify_dispatch
from backend.app.services.tkg_builder import build_graph
from backend.app.settings import ROOT, read_json

router = APIRouter()


def get_or_404(store, run_id):
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(404, "Corrida no encontrada")
    return run


@router.get("/runs")
async def list_runs(s=Depends(services)):
    return s.store.list_runs()


@router.post("/runs", status_code=202, dependencies=[Depends(require_mutation)])
async def create_run(payload: RunRequest, s=Depends(services)):
    if payload.mode != "remote":
        raise HTTPException(422, "Use /api/experiments/offline para un escenario sin red")
    remote_health = await s.monitor.check()
    if remote_health["state"] != "HEALTHY":
        raise HTTPException(503, "/health remoto no responde; último resultado conservado")
    if "/" in payload.profile_file or "\\" in payload.profile_file:
        raise HTTPException(422, "Nombre de perfil inválido")
    scenario = read_json(ROOT / "config/scenario_ieee13.json")
    profile = parse_profile(ROOT / "data/processed" / payload.profile_file)
    scenario.update(
        {
            "topology": payload.topology,
            "scale_multiplier": payload.scale_multiplier,
            "input_sha256": profile["source_sha256"],
            "profile_file": payload.profile_file,
        }
    )
    objective = read_json(ROOT / "config/objective.json")
    run_id = s.store.create(scenario, objective)
    s.manager.launch(run_id, s.orchestrator.execute(run_id, scenario, profile))
    return {"run_id": run_id, "status": "PENDING", "note": "WSS suscrito ANTES de POST /solve"}


@router.get("/runs/{run_id}")
async def run_detail(run_id: str, s=Depends(services)):
    return get_or_404(s.store, run_id)


@router.get("/runs/{run_id}/steps")
async def run_steps(run_id: str, s=Depends(services)):
    return get_or_404(s.store, run_id)["steps"]


@router.post("/runs/{run_id}/dispatch", dependencies=[Depends(require_mutation)])
async def dispatch(run_id: str, s=Depends(services)):
    parent = get_or_404(s.store, run_id)
    if parent["status"] not in ("VERIFIED", "ENERGY_MODEL_ONLY"):
        raise HTTPException(409, "Primero debe terminar la corrida o usar el experimento offline")
    scenario = parent["scenario"]
    objective = read_json(ROOT / "config/objective.json")
    profile = parse_profile(
        ROOT / "data/processed" / scenario.get("profile_file", "ausgrid_c12_2011-07-01.csv")
    )
    scenario = {**scenario, "derived_from_run_id": run_id}
    child = s.store.create(scenario, objective, origin_kind="DERIVED")
    s.store.update(child, "ENERGY_MODEL_ONLY")
    computed = optimize(profile, scenario, objective)
    computed["comparison"] = compare_dispatch(profile, scenario, objective, computed)
    s.store.save_dispatch(child, computed)
    graph = build_graph(s.store.get_run(child), profile, computed)
    export_run(s.store.get_run(child))
    return {
        "run_id": child,
        "parent_run_id": run_id,
        "dispatch": computed,
        "graph_path": str(graph.relative_to(ROOT)),
        "electrical_verification": "NOT_VALIDATED",
    }


@router.post("/runs/{run_id}/verify", dependencies=[Depends(require_mutation)])
async def verify(run_id: str, s=Depends(services)):
    run = get_or_404(s.store, run_id)
    result = verify_dispatch(run)
    return {**result, "run_id": run_id}
