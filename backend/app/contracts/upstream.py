"""Subconjunto estricto de los contratos verificados en `Proyecto_1811(1).zip`."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CreateSimulation(BaseModel):
    topology: str = "ieee13"
    load_multiplier: float = Field(default=1, gt=0, le=5)


class QSTSInput(BaseModel):
    duration_hours: float = Field(default=24, gt=0)
    step_minutes: float = Field(default=30, gt=0)
    profile_source: Literal["values"] = "values"
    load_multipliers: list[float]

    @model_validator(mode="after")
    def check_steps(self):
        expected = round(self.duration_hours * 60 / self.step_minutes)
        if len(self.load_multipliers) != expected or any(
            not 0 < p <= 5 for p in self.load_multipliers
        ):
            raise ValueError("Número de pasos y multiplicadores incorrectos")
        return self


class SolveQSTS(BaseModel):
    simulation_type: Literal["qsts"] = "qsts"
    qsts: QSTSInput


class QSTSStep(BaseModel):
    step: int = Field(ge=1)
    simulated_minutes: float = Field(ge=0)
    converged: bool
    load_multiplier: float = Field(gt=0)
    total_kw: float | None = None
    total_kvar: float | None = None
    min_voltage_pu: float | None = None
    max_voltage_pu: float | None = None
    solve_ms: float = 0


class QSTSResult(BaseModel):
    session_id: str
    simulation_type: Literal["qsts"]
    steps: list[QSTSStep]
    summary: dict

    @model_validator(mode="after")
    def verify_all_steps(self):
        if not self.steps or any(s.step != i for i, s in enumerate(self.steps, 1)):
            raise ValueError("Pasos incompletos o desordenados")
        if not all(s.converged for s in self.steps):
            raise ValueError("Pasos no convergentes; no confirmar la corrida")
        if self.summary.get("failed_steps", 0) != 0:
            raise ValueError("Resumen de pasos fallidos")
        return self
