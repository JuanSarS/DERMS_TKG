"""Nueva ruta local para snapshots OpenDSS, sin tocar el servicio remoto."""

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.dependencies import require_mutation, services
from backend.app.contracts.snapshot import SnapshotRequest
from backend.app.settings import ROOT, read_json

router = APIRouter()


@router.post("/snapshots", status_code=202, dependencies=[Depends(require_mutation)])
async def execute_snapshot(request: SnapshotRequest, s=Depends(services)):
    health = await s.monitor.check(authenticate=True)
    if health["state"] != "HEALTHY":
        raise HTTPException(503, "OpenDSS no disponible/autenticado: conservar último confirmado")
    scenario = read_json(ROOT / "config/scenario_ieee13.json")
    scenario.update(
        {
            "topology": request.topology,
            "simulation_type": "snapshot",
            "snapshot_load_multiplier": request.load_multiplier,
            "note": "No valida BESS individual, solo una condición global de carga",
        }
    )
    objective = read_json(ROOT / "config/objective.json")
    run_id = s.store.create(scenario, objective, origin_kind="SIMULATED")
    s.manager.launch(
        run_id, s.snapshot_runner.execute(run_id, request.topology, request.load_multiplier)
    )
    return {
        "run_id": run_id,
        "status": "PENDING",
        "mode": "snapshot",
        "warning": "Snapshot de carga global, no verificación de despacho BESS",
    }
