"""Ciclo salud→auth→REST sesión→WSS→REST solve→GET results→commit atómico."""

from __future__ import annotations

import asyncio
import json

from websockets.exceptions import ConnectionClosed

from backend.app.contracts.upstream import QSTSInput, QSTSResult, SolveQSTS
from backend.app.integrations.opendss_http import RemoteOpenDSS, UpstreamError
from backend.app.integrations.opendss_ws import connect_ws
from backend.app.persistence.file_store import export_run
from backend.app.services.health_monitor import HealthMonitor
from backend.app.services.profile_mapper import to_multipliers
from backend.app.services.qsts_bridge import normalize_event
from backend.app.services.run_manager import RunManager
from backend.app.services.tkg_builder import build_qsts_graph
from backend.app.services.ws_recovery import reconnect


class Orchestrator:
    def __init__(self, remote: RemoteOpenDSS, monitor: HealthMonitor, manager: RunManager):
        self.remote = remote
        self.monitor = monitor
        self.manager = manager

    async def execute(self, run_id: str, scenario: dict, profile: dict) -> None:
        store = self.manager.store
        session_id = None
        try:
            await self.monitor.require_healthy()
            multipliers = to_multipliers(
                profile, scale_multiplier=scenario.get("scale_multiplier", 1)
            )
            payload = SolveQSTS(
                qsts=QSTSInput(
                    duration_hours=len(multipliers) * 0.5,
                    step_minutes=30,
                    load_multipliers=multipliers,
                )
            )
            await self.remote._get_token()
            created = await self.remote.create(scenario["topology"])
            session_id = created["session_id"]
            store.update(run_id, "CONNECTING_WS", session_id=session_id)
            await self.manager.broadcast(
                run_id, {"type": "session_created", "session_id": session_id}
            )
            # Strictly subscribe before sending any solve requests.
            ws = await connect_ws(self.remote, session_id)
            self.monitor.ws_state = "CONNECTED"
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=20)
                first = json.loads(raw)
                if first.get("type") != "snapshot":
                    raise UpstreamError("WS_PROTOCOL", "Primer mensaje WSS no es snapshot")
                await self.manager.broadcast(run_id, normalize_event(run_id, first))
                store.update(run_id, "SOLVING")
                task = asyncio.create_task(self.remote.solve(session_id, payload))
                received = set()
                completed = False
                ws_failure = None
                deadline = asyncio.get_running_loop().time() + 240
                while not completed and asyncio.get_running_loop().time() < deadline:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=30)
                        event = json.loads(raw)
                        normalized = normalize_event(run_id, event)
                        if event.get("type") == "qsts_progress":
                            await self.monitor.require_healthy()  # Si /health cae, congelar datos.
                            step = int(event.get("step", 0))
                            if 1 <= step <= len(multipliers) and step not in received:
                                received.add(step)
                                store.step(run_id, event)
                        await self.manager.broadcast(run_id, normalized)
                        if event.get("type") == "error":
                            raise UpstreamError("WS_SIM_ERROR", "La API envió error de simulación")
                        if event.get("type") == "completed":
                            completed = True
                    except asyncio.TimeoutError:
                        if task.done():
                            ws_failure = "WS_IDLE_AFTER_SOLVE"
                            break
                        continue
                    except (ConnectionClosed, ConnectionError, OSError, RuntimeError) as exc:
                        self.monitor.ws_state = "RECOVERING"
                        try:
                            replacement = await reconnect(self.remote, session_id, attempts=3)
                            await ws.close()
                            ws = replacement
                            self.monitor.ws_state = "CONNECTED"
                            snapshot = json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
                            if snapshot.get("type") != "snapshot":
                                raise UpstreamError("WS_PROTOCOL", "Reconexión sin snapshot")
                            await self.manager.broadcast(run_id, normalize_event(run_id, snapshot))
                        except (UpstreamError, asyncio.TimeoutError):
                            ws_failure = type(exc).__name__
                            break
                solve_result = await task
                if not isinstance(solve_result, dict) or solve_result.get("status") not in (
                    "COMPLETED",
                ):
                    raise UpstreamError("SOLVE_FAILED", "El servidor no confirmó COMPLETED")
                if ws_failure:
                    self.monitor.ws_state = "DEGRADED_WS"
                    await self.manager.broadcast(
                        run_id, {"type": "ws_degraded", "detail": ws_failure}
                    )
            finally:
                await ws.close()
                if self.monitor.ws_state != "DEGRADED_WS":
                    self.monitor.ws_state = "DISCONNECTED"
            # Reconcile complete data from REST; WS progress is provisional only.
            await self.monitor.require_healthy()
            result = await self.remote.results(session_id)
            parsed = QSTSResult.model_validate(result)
            if len(parsed.steps) != len(multipliers):
                raise UpstreamError(
                    "INCOMPLETE_RESULTS", "Longitud REST distinta al perfil solicitado"
                )
            if any(
                abs(step.load_multiplier - multipliers[i]) > 1e-5
                for i, step in enumerate(parsed.steps)
            ):
                raise UpstreamError(
                    "MISMATCH_RESULTS", "Multiplicadores no coinciden con el escenario"
                )
            store.commit_verified(run_id, result)
            build_qsts_graph(store.get_run(run_id), result)
            export_run(store.get_run(run_id))
            await self.manager.broadcast(
                run_id, {"type": "confirmed", "status": "VERIFIED", "steps": len(parsed.steps)}
            )
        except Exception as exc:
            # Never clear last_good_run; provisional rows may be available as historical evidence.
            code = exc.code if isinstance(exc, UpstreamError) else type(exc).__name__
            store.update(run_id, "ERROR", session_id=session_id, error=f"{code}: {exc}")
            await self.manager.broadcast(
                run_id, {"type": "error", "code": code, "message": str(exc)}
            )
