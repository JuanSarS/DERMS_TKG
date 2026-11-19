"""Reintento WSS sin reejecutar `/solve` y sin alterar last_good_run."""

from __future__ import annotations

import asyncio
import random

from backend.app.integrations.opendss_http import UpstreamError
from backend.app.integrations.opendss_ws import connect_ws


async def reconnect(remote, session_id: str, attempts: int = 3):
    """Restituye solo la suscripción a eventos; la simulación sigue en REST remoto."""
    last_exception = None
    for number in range(attempts):
        if number:
            await asyncio.sleep(min(2**number, 8) + random.uniform(0, 0.3))
        try:
            health = await remote.health()
            if health["state"] != "HEALTHY":
                raise UpstreamError("OFFLINE", "Sin salud remota durante recuperación WSS")
            ws = await connect_ws(remote, session_id)
            return ws
        except (OSError, RuntimeError, TimeoutError, UpstreamError) as exc:
            last_exception = exc
    raise UpstreamError("DEGRADED_WS", f"WSS no recuperado: {type(last_exception).__name__}")
