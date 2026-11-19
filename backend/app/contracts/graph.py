"""Consultas RDF con limites explícitos y fechas UTC."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class AsOfQuery(BaseModel):
    run_id: str
    at: datetime

    @model_validator(mode="after")
    def utc_only(self):
        if not self.at.tzinfo:
            raise ValueError("Se requiere zona horaria")
        return self


class SPARQLQuery(BaseModel):
    run_id: str
    query: str = Field(min_length=4, max_length=3000)
