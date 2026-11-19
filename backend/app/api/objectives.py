"""Configurable sin reescribir el optimizador; cambios quedan versionados en corridas."""

import json
import os

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import require_mutation
from backend.app.contracts.objective import Objective
from backend.app.settings import ROOT, read_json

router = APIRouter()
PATH = ROOT / "config/objective.json"


@router.get("/objective")
def get_objective():
    return read_json(PATH)


@router.put("/objective", dependencies=[Depends(require_mutation)])
def put_objective(objective: Objective):
    data = objective.model_dump()
    temp = PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf8")
    os.replace(temp, PATH)
    return data
