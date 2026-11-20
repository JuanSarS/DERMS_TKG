"""Contrato del SolveResponse snapshot real del repositorio OpenDSS adjunto."""

from pydantic import BaseModel, Field


class SnapshotRequest(BaseModel):
    topology: str = Field(default="ieee13", min_length=1, max_length=200)
    load_multiplier: float = Field(default=1.0, gt=0, le=5)


class SnapshotElectrical(BaseModel):
    session_id: str
    topology: str
    converged: bool
    elapsed_ms: float = Field(ge=0)
    load_multiplier: float = Field(gt=0, le=5)
    total_power_kw: float
    total_power_kvar: float
    voltages: dict = Field(default_factory=dict)
    currents: dict = Field(default_factory=dict)


class SnapshotResults(BaseModel):
    session_id: str
    simulation_type: str
    result: SnapshotElectrical
