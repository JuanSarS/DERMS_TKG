"""Autenticación REST del OpenDSS original; el JWT nunca sale hacia el navegador."""

from __future__ import annotations

import time

import httpx


class AuthError(Exception):
    pass


class RemoteAuth:
    def __init__(self, config: dict):
        self.config = config
        self.token: str | None = None
        self.expires_at = 0.0

    async def token_for(self, client: httpx.AsyncClient) -> str:
        if self.token and time.monotonic() < self.expires_at - 60:
            return self.token
        username = self.config.get("username")
        password = self.config.get("password")
        if not username or not password:
            raise AuthError("Configure secrets/opendss.local.json; credenciales no disponibles")
        response = await client.post(
            "/auth/token", data={"username": username, "password": password}
        )
        if response.status_code in (401, 403, 429):
            raise AuthError(f"Autenticación remota rechazada, HTTP {response.status_code}")
        response.raise_for_status()
        payload = response.json()
        self.token = payload["access_token"]
        self.expires_at = time.monotonic() + float(payload.get("expires_in", 600))
        return self.token

    def expire(self) -> None:
        self.token = None
        self.expires_at = 0.0
