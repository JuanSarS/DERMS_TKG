"""Servicios compartidos y seguridad local basada en loopback."""

from fastapi import HTTPException, Request

from backend.app.settings import settings


def services(request: Request):
    return request.app.state.services


def require_mutation(request: Request):
    origin = request.headers.get("origin", "")
    if origin and not (
        origin.startswith("http://127.0.0.1:") or origin.startswith("http://localhost:")
    ):
        raise HTTPException(403, "No se admiten mutaciones desde otros orígenes")
    if settings.app_token and request.headers.get("x-derms-app-token") != settings.app_token:
        raise HTTPException(401, "Se requiere token de acceso local")
    return True
