"""El LLM solo explica datos; no puede iniciar simulación ni acciones de control."""

from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.dependencies import services
from backend.app.contracts.llm import ExplainRequest
from backend.app.services.llm_service import explain

router = APIRouter()


@router.post("/llm/explain")
async def llm_explain(request: ExplainRequest, s=Depends(services)):
    run = s.store.get_run(request.run_id)
    if not run:
        raise HTTPException(404, "Corrida no encontrada")
    return await explain(run, request.question, request.step)


@router.post("/llm/propose")
async def llm_propose(request: ExplainRequest, s=Depends(services)):
    from backend.app.integrations.ollama_http import Ollama
    from backend.app.services.explanation import evidence_packet
    from backend.app.settings import ROOT, read_json

    run = s.store.get_run(request.run_id)
    if not run:
        raise HTTPException(404, "Corrida no encontrada")
    objective = read_json(ROOT / "config/objective.json")
    return await Ollama().suggest_weights(
        evidence_packet(run, request.step), request.question, objective
    )
