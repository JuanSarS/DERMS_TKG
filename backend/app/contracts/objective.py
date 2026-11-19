"""Pesos y escalas normalizadas editables sin reescribir el optimizador."""

from pydantic import BaseModel, Field, model_validator


class Term(BaseModel):
    enabled: bool = True
    weight: float = Field(ge=0, le=100)
    scale: float = Field(gt=0)
    unit: str


class Objective(BaseModel):
    version: str
    terms: dict[str, Term]
    description: str = ""

    @model_validator(mode="after")
    def check_terms(self):
        if set(self.terms) != {"energy", "peak", "battery", "curtail"}:
            raise ValueError("Los 4 términos definidos son obligatorios")
        return self
