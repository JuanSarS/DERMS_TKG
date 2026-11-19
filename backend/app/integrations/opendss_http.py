"""Adaptador de contratos REST QSTS; solo opera tras /health y autenticación."""

from __future__ import annotations

import httpx

from backend.app.contracts.upstream import CreateSimulation, SolveQSTS
from backend.app.integrations.opendss_auth import AuthError, RemoteAuth
from backend.app.settings import settings


class UpstreamError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class RemoteOpenDSS:
    def __init__(self, config: dict | None = None, client: httpx.AsyncClient | None = None):
        self.config = config or settings.remote()
        self.base_url = self.config["base_url"].rstrip("/")
        self.client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=float(self.config.get("timeout_seconds", 20)),
            follow_redirects=False,
        )
        self.auth = RemoteAuth(self.config)

    async def health(self) -> dict:
        try:
            response = await self.client.get("/health", timeout=6)
            if response.status_code != 200 or response.json().get("status") != "ok":
                return {
                    "state": "OFFLINE",
                    "message": f"Respuesta /health inválida: HTTP {response.status_code}",
                }
            return {"state": "HEALTHY", "message": "OpenDSS disponible"}
        except (httpx.HTTPError, ValueError) as exc:
            return {"state": "OFFLINE", "message": type(exc).__name__}

    async def _get_token(self) -> str:
        try:
            return await self.auth.token_for(self.client)
        except AuthError as exc:
            raise UpstreamError("AUTH_ERROR", str(exc)) from exc
        except httpx.HTTPError as exc:
            raise UpstreamError("AUTH_ERROR", type(exc).__name__) from exc

    async def request(self, method: str, path: str, **kwargs) -> dict | list:
        token = await self._get_token()
        try:
            response = await self.client.request(
                method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs
            )
            if response.status_code == 401:
                self.auth.expire()
                raise UpstreamError("AUTH_ERROR", "Token caducado o usuario no autorizado")
            if response.status_code in (403, 404, 409, 422, 429):
                raise UpstreamError(
                    f"HTTP_{response.status_code}",
                    f"OpenDSS rechazó la solicitud: {response.status_code}",
                )
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.HTTPError as exc:
            raise UpstreamError("NETWORK_ERROR", type(exc).__name__) from exc

    async def checked(self, method: str, path: str, **kwargs) -> dict | list:
        status = await self.health()
        if status["state"] != "HEALTHY":
            raise UpstreamError("OFFLINE", "No se envían órdenes: /health no responde")
        return await self.request(method, path, **kwargs)

    async def models(self) -> dict | list:
        return await self.checked("GET", "/models")

    async def sessions(self) -> dict | list:
        return await self.checked("GET", "/simulations")

    async def create(self, topology: str = "ieee13") -> dict:
        return await self.checked(
            "POST", "/simulations", json=CreateSimulation(topology=topology).model_dump()
        )

    async def solve(self, session_id: str, payload: SolveQSTS) -> dict:
        return await self.checked(
            "POST", f"/simulations/{session_id}/solve", json=payload.model_dump()
        )

    async def results(self, session_id: str) -> dict:
        return await self.checked("GET", f"/simulations/{session_id}/results")

    async def detail(self, session_id: str) -> dict:
        return await self.checked("GET", f"/simulations/{session_id}")

    async def aclose(self):
        await self.client.aclose()
