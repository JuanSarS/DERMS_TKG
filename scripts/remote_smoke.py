"""Prueba MUTANTE, requiere confirmación explícita desde smoke_qsts.ps1."""

import asyncio
import json

from backend.app.contracts.upstream import QSTSInput, QSTSResult, SolveQSTS
from backend.app.integrations.opendss_http import RemoteOpenDSS
from backend.app.integrations.opendss_ws import connect_ws


async def main():
    remote = RemoteOpenDSS()
    session = None
    try:
        health = await remote.health()
        if health["state"] != "HEALTHY":
            print("NOT_RUN: /health no disponible")
            return
        created = await remote.create("ieee13")
        session = created["session_id"]
        ws = await connect_ws(remote, session)
        try:
            assert json.loads(await asyncio.wait_for(ws.recv(), 15))["type"] == "snapshot"
            payload = SolveQSTS(
                qsts=QSTSInput(
                    duration_hours=0.25, step_minutes=5, load_multipliers=[0.8, 1.0, 1.2]
                )
            )
            solve_task = asyncio.create_task(remote.solve(session, payload))
            while True:
                event = json.loads(await asyncio.wait_for(ws.recv(), 60))
                print("WSS", event.get("type"), event.get("step", ""))
                if event.get("type") == "completed":
                    break
                if event.get("type") == "error":
                    raise RuntimeError("Error WS remoto")
            await solve_task
        finally:
            await ws.close()
        result = QSTSResult.model_validate(await remote.results(session))
        assert len(result.steps) == 3
        print("PASS: 3 pasos QSTS + WSS + REST /results")
    finally:
        if session:
            print("Sesión creada por smoke:", session)
            print("Se deja remota para inspección; no elimina sesiones automáticamente.")
        await remote.aclose()


if __name__ == "__main__":
    asyncio.run(main())
