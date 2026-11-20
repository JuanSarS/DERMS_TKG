"""Ejecuta Snapshot IEEE13 remoto; nunca considera validada una consigna BESS local."""

from __future__ import annotations

import asyncio
import json

from websockets.exceptions import ConnectionClosed

from backend.app.contracts.snapshot import SnapshotResults
from backend.app.integrations.opendss_http import RemoteOpenDSS, UpstreamError
from backend.app.integrations.opendss_ws import connect_ws
from backend.app.persistence.file_store import export_run
from backend.app.services.health_monitor import HealthMonitor
from backend.app.services.qsts_bridge import normalize_event
from backend.app.services.run_manager import RunManager
from backend.app.services.tkg_builder import build_snapshot_graph


class SnapshotRunner:
    def __init__(self, remote: RemoteOpenDSS, monitor: HealthMonitor, manager: RunManager):
        self.remote = remote
        self.monitor = monitor
        self.manager = manager

    async def _watch_ws(self, ws, run_id: str) -> None:
        """Solo telemetría, nunca comandos. REST es la fuente final de verdad."""
        for _ in range(40):
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
            except asyncio.TimeoutError:
                return
            event = json.loads(raw)
            await self.manager.broadcast(run_id, normalize_event(run_id, event))
            if event.get("type") in {"completed", "error"}:
                return

    async def execute(self, run_id: str, topology: str, multiplier: float) -> None:
        store = self.manager.store
        session_id = None
        ws = None
        listener = None
        try:
            await self.monitor.require_healthy()
            await self.remote._get_token()
            created = await self.remote.checked(
                "POST",
                "/simulations",
                json={
                    "topology": topology,
                    "load_multiplier": multiplier,
                },
            )
            session_id = created["session_id"]
            store.update(run_id, "CONNECTING_WS", session_id=session_id)
            await self.manager.broadcast(
                run_id, {"type": "session_created", "session_id": session_id}
            )
            try:
                ws = await connect_ws(self.remote, session_id)
                first = json.loads(await asyncio.wait_for(ws.recv(), timeout=12))
                if first.get("type") != "snapshot":
                    raise UpstreamError("WS_PROTOCOL", "WS no envió snapshot inicial de estado")
                self.monitor.ws_state = "CONNECTED"
                await self.manager.broadcast(run_id, normalize_event(run_id, first))
                listener = asyncio.create_task(self._watch_ws(ws, run_id))
            except (OSError, TimeoutError, ValueError, UpstreamError, ConnectionClosed):
                self.monitor.ws_state = "DEGRADED_WS"
                # REST puede confirmar el cálculo aunque falle el transporte de eventos.
            store.update(run_id, "SOLVING")
            solve = await self.remote.checked(
                "POST",
                f"/simulations/{session_id}/solve",
                json={
                    "simulation_type": "snapshot",
                    "load_multiplier": multiplier,
                },
            )
            if not isinstance(solve, dict) or not solve.get("converged", False):
                raise UpstreamError("SNAPSHOT_FAILED", "El resultado del solve no es convergente")
            await self.monitor.require_healthy()
            remote_result = await self.remote.results(session_id)
            parsed = SnapshotResults.model_validate(remote_result)
            if parsed.simulation_type != "snapshot" or parsed.session_id != session_id:
                raise UpstreamError(
                    "RESULT_MISMATCH", "Respuesta REST no es el snapshot solicitado"
                )
            result = parsed.result
            if (
                not result.converged
                or result.session_id != session_id
                or abs(result.load_multiplier - multiplier) > 1e-6
            ):
                raise UpstreamError(
                    "RESULT_MISMATCH", "La potencia/consigna no corresponde al escenario"
                )
            store.commit_snapshot(run_id, remote_result)
            build_snapshot_graph(store.get_run(run_id), remote_result)
            export_run(store.get_run(run_id))
            await self.manager.broadcast(
                run_id,
                {
                    "type": "confirmed",
                    "status": "SNAPSHOT_VERIFIED",
                    "source": "OpenDSS snapshot real, carga global",
                },
            )
        except Exception as exc:
            code = exc.code if isinstance(exc, UpstreamError) else type(exc).__name__
            store.update(run_id, "ERROR", session_id=session_id, error=f"{code}: {exc}")
            await self.manager.broadcast(
                run_id, {"type": "error", "code": code, "message": str(exc)}
            )
        finally:
            if listener:
                if not listener.done():
                    listener.cancel()
                await asyncio.gather(listener, return_exceptions=True)
            if ws is not None:
                await ws.close()
            if self.monitor.ws_state == "CONNECTED":
                self.monitor.ws_state = "DISCONNECTED"
