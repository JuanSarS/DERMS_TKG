"""Estado de OpenDSS independiente de último dato confirmado."""

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import services
from backend.app.integrations.ollama_http import Ollama
from backend.app.services.cim_import import cim_catalog
from backend.app.services.electrical_check import capability

router = APIRouter()


@router.get("/status")
async def status(s=Depends(services)):
    remote = await s.monitor.check(authenticate=False)
    ollama = await Ollama().status()
    last_id = s.store.get_meta("last_good_run")
    last = s.store.get_run(last_id) if last_id else None
    return {
        "remote": remote,
        "authenticated": bool(s.remote.auth.token),
        "last_good_run": {
            "run_id": last_id,
            "created_at": last["created_at"],
            "steps": len(last["steps"]),
        }
        if last
        else None,
        "active_run": s.store.get_meta("active_run"),
        "stale": remote["state"] != "HEALTHY",
        "llm_enabled": ollama["status"] == "READY",
        "llm": ollama,
        "electrical_capabilities": capability(),
        "cim": cim_catalog(),
    }
