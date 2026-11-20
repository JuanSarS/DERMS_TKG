"""Consultas locales LLM; el contexto lo decide el servidor, no el navegador."""

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.dependencies import services
from backend.app.contracts.llm import ExplainRequest
from backend.app.integrations.ollama_http import Ollama
from backend.app.services.evidence_context import build_context
from backend.app.services.llm_service import explain
from backend.app.settings import ROOT, read_json

router = APIRouter()


@router.get("/llm/status")
async def llm_status():
    """Distingue servicio disponible de modelo efectivamente instalado."""
    return await Ollama().status()


@router.post("/llm/explain")
async def llm_explain(request: ExplainRequest, s=Depends(services)):
    run = s.store.get_run(request.run_id)
    if not run:
        raise HTTPException(404, "Corrida no encontrada")
    return await explain(run, request.question, request.step, store=s.store)


@router.post("/llm/propose")
async def llm_propose(request: ExplainRequest, s=Depends(services)):
    run = s.store.get_run(request.run_id)
    if not run:
        raise HTTPException(404, "Corrida no encontrada")
    objective = read_json(ROOT / "config/objective.json")
    return await Ollama().suggest_weights(
        build_context(run, request.step, store=s.store), request.question, objective
    )
