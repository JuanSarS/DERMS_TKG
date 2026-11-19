"""Corridas demostrativas offline separadas de la conexión confirmada."""

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.dependencies import require_mutation, services
from backend.app.services.experiments import offline_experiment

router = APIRouter()


@router.post("/experiments/offline", dependencies=[Depends(require_mutation)])
async def offline(s=Depends(services)):
    return offline_experiment(s.store)


@router.get("/experiments/compare")
async def compare(run_id: str, s=Depends(services)):
    run = s.store.get_run(run_id)
    if not run:
        raise HTTPException(404, "Corrida no encontrada")
    dispatch = run.get("dispatch")
    return {
        "run_id": run_id,
        "comparison": dispatch.get("comparison") if dispatch else None,
        "note": "B0/B1/B2 requiere contrastar consultas RDF/SQL con idénticas entradas; no se atribuye ahorro energético al TKG.",
    }


@router.get("/experiments/baselines")
def baselines():
    from backend.app.services.baselines import compare_baselines

    return compare_baselines()
