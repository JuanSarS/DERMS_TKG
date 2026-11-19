"""Contratos de explicaciones sin autoridad de control."""

from pydantic import BaseModel, Field


class ExplainRequest(BaseModel):
    run_id: str
    question: str = Field(min_length=3, max_length=500)
    step: int | None = Field(default=None, ge=1)


class ExplainResponse(BaseModel):
    status: str
    answer: str
    evidence: dict
    model: str | None = None
