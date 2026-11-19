import pytest
from pydantic import ValidationError

from backend.app.contracts.objective import Objective
from backend.app.services.objective_registry import evaluate
from backend.app.settings import ROOT, read_json


def test_normalized_weights_and_total():
    obj = read_json(ROOT / "config/objective.json")
    result = evaluate(obj, {"energy": 4, "peak": 2, "battery": 5, "curtail": 0})
    assert abs(result["total"] - (4 + 0.45 * 2 + 0.05 * 5)) < 1e-8


def test_bad_scale_rejected():
    obj = read_json(ROOT / "config/objective.json")
    obj["terms"]["energy"]["scale"] = 0
    with pytest.raises(ValidationError):
        Objective.model_validate(obj)
