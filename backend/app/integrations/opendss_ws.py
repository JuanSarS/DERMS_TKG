"""Suscripción WSS con el subprotocolo JWT implementado por la API original."""

from urllib.parse import urlparse, urlunparse

import websockets

from backend.app.integrations.opendss_http import RemoteOpenDSS


def websocket_url(base_url: str, session_id: str) -> str:
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, f"/ws/simulations/{session_id}", "", "", ""))


async def connect_ws(remote: RemoteOpenDSS, session_id: str):
    token = await remote._get_token()
    return await websockets.connect(
        websocket_url(remote.base_url, session_id),
        subprotocols=["opendss.jwt", token],
        open_timeout=12,
        ping_interval=20,
        max_size=16 * 1024 * 1024,
    )
