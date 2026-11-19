"""Escenario experimental sin atribuir los perfiles a IEEE13 físicamente."""

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    topology: str = "ieee13"
    profile_file: str = "ausgrid_c12_2011-07-01.csv"
    scale_multiplier: float = Field(default=1.0, gt=0, le=3)
    mode: str = "remote"


class RunIdentifier(BaseModel):
    run_id: str
    status: str
