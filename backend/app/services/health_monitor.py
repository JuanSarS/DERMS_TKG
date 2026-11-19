"""Máquina de estado de conexión: salud, autenticación y degradación WS."""

from backend.app.integrations.opendss_http import RemoteOpenDSS, UpstreamError


class HealthMonitor:
    def __init__(self, remote: RemoteOpenDSS):
        self.remote = remote
        self.state = "UNKNOWN"
        self.ws_state = "DISCONNECTED"
        self.message = "Sin consultar"

    async def check(self, authenticate: bool = False) -> dict:
        result = await self.remote.health()
        self.state = result["state"]
        self.message = result["message"]
        if self.state == "HEALTHY" and authenticate:
            try:
                await self.remote._get_token()
            except UpstreamError as exc:
                self.state = "AUTH_ERROR"
                self.message = str(exc)
        return {"state": self.state, "ws_state": self.ws_state, "message": self.message}

    async def require_healthy(self) -> None:
        status = await self.check()
        if status["state"] != "HEALTHY":
            raise UpstreamError("OFFLINE", status["message"])
