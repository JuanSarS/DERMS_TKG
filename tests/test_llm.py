import pytest

from backend.app.integrations.ollama_http import Ollama
from backend.app.services.explanation import deterministic_explanation


@pytest.mark.asyncio
async def test_ollama_disabled():
    out = await Ollama({"enabled": False}).explain({"run_id": "x"}, "why")
    assert out["status"] == "DISABLED"


def test_deterministic_explanation_states_limits():
    evidence = {
        "run_id": "x",
        "status": "ENERGY_MODEL_ONLY",
        "electrical_verification": "NOT_VALIDATED",
    }
    assert "NOT_VALIDATED" in deterministic_explanation(evidence)
