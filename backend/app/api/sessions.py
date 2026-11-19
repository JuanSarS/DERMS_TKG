"""Consulta remota y creación de sesiones, sin eliminar sesiones ajenas."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.api.dependencies import require_mutation, services

router = APIRouter()


class CreateSession(BaseModel):
    topology: str = "ieee13"


@router.get("/models")
async def models(s=Depends(services)):
    return await s.remote.models()


@router.get("/sessions")
async def list_sessions(s=Depends(services)):
    return await s.remote.sessions()


@router.post("/sessions", dependencies=[Depends(require_mutation)])
async def new_session(payload: CreateSession, s=Depends(services)):
    data = await s.remote.create(payload.topology)
    s.created_sessions.add(data["session_id"])
    return data
