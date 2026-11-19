"""WS local para el navegador; no expone JWT remoto ni reenvía credenciales."""

import json

from fastapi import WebSocket, WebSocketDisconnect


async def local_ws(websocket: WebSocket):
    run_id = websocket.path_params["run_id"]
    origin = websocket.headers.get("origin", "")
    if origin and not (
        origin.startswith("http://127.0.0.1:") or origin.startswith("http://localhost:")
    ):
        await websocket.close(code=1008)
        return
    if websocket.app.state.services.store.get_run(run_id) is None:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    manager = websocket.app.state.services.manager
    queue = manager.subscribe(run_id)
    try:
        await websocket.send_json(
            {"type": "snapshot_local", "run": websocket.app.state.services.store.get_run(run_id)}
        )
        while True:
            event = await queue.get()
            await websocket.send_text(json.dumps(event))
    except WebSocketDisconnect:
        pass
    finally:
        manager.unsubscribe(run_id, queue)
