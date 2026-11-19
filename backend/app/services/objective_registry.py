"""Función objetivo modular con pesos/escala; términos fijos pero editables."""

from backend.app.contracts.objective import Objective

TERMS = ("energy", "peak", "battery", "curtail")


def coefficient(obj: dict, term: str) -> float:
    config = Objective.model_validate(obj).terms[term]
    return (config.weight / config.scale) if config.enabled else 0.0


def evaluate(obj: dict, values: dict) -> dict:
    contributions = {term: coefficient(obj, term) * float(values.get(term, 0)) for term in TERMS}
    return {
        "raw": {term: float(values.get(term, 0)) for term in TERMS},
        "weighted_contributions": contributions,
        "total": sum(contributions.values()),
    }
