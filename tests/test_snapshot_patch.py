"""Snapshot REST/WSS simulado: commit solo si el resultado está confirmado."""

import asyncio
import json

import pytest

from backend.app.persistence.sqlite_store import Store
from backend.app.services.health_monitor import HealthMonitor
from backend.app.services.run_manager import RunManager
from backend.app.services.snapshot_runner import SnapshotRunner


class FakeSnapshotRemote:
    def __init__(self, online=True, converged=True):
        self.online = online
        self.converged = converged
        self.calls = []

    async def health(self):
        return {"state": "HEALTHY" if self.online else "OFFLINE", "message": "mock"}

    async def _get_token(self):
        return "fake-token"

    async def results(self, session_id):
        return await self.checked("GET", f"/simulations/{session_id}/results")

    async def checked(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        if path == "/simulations":
            return {"session_id": "s1"}
        if path.endswith("/solve"):
            return {"session_id": "s1", "converged": self.converged}
        if path.endswith("/results"):
            return {
                "session_id": "s1",
                "simulation_type": "snapshot",
                "result": {
                    "session_id": "s1",
                    "topology": "ieee13",
                    "converged": self.converged,
                    "elapsed_ms": 4,
                    "load_multiplier": 1.0,
                    "total_power_kw": 210,
                    "total_power_kvar": 30,
                    "voltages": {},
                    "currents": {},
                },
            }
        raise AssertionError(path)


class FakeWS:
    def __init__(self):
        self.events = iter([{"type": "snapshot"}, {"type": "completed"}])

    async def recv(self):
        return json.dumps(next(self.events))

    async def close(self):
        pass


@pytest.mark.asyncio
async def test_snapshot_remote_commit(monkeypatch, tmp_path):
    from backend.app.services import snapshot_runner as module

    monkeypatch.setattr(
        module, "connect_ws", lambda remote, session: asyncio.sleep(0, result=FakeWS())
    )
    monkeypatch.setattr(module, "build_snapshot_graph", lambda run, data: tmp_path / "snap.ttl")
    monkeypatch.setattr(module, "export_run", lambda run: tmp_path)
    store = Store(tmp_path / "test.sqlite")
    remote = FakeSnapshotRemote()
    manager = RunManager(store)
    run_id = store.create({"topology": "ieee13"}, {})
    await SnapshotRunner(remote, HealthMonitor(remote), manager).execute(run_id, "ieee13", 1.0)
    record = store.get_run(run_id)
    assert record["status"] == "SNAPSHOT_VERIFIED", record.get("error")
    assert record["result"]["result"]["total_power_kw"] == 210
    assert store.get_meta("last_good_run") == run_id
    assert any(x[1] == "/simulations/s1/solve" for x in remote.calls)
    assert not any("battery_kw" in str(x) for x in remote.calls)


@pytest.mark.asyncio
async def test_snapshot_offline_does_not_replace_last_good(monkeypatch, tmp_path):
    store = Store(tmp_path / "test.sqlite")
    former = store.create({}, {})
    store.commit_snapshot(former, {"simulation_type": "snapshot", "result": {}})
    current = store.create({"topology": "ieee13"}, {})
    remote = FakeSnapshotRemote(online=False)
    await SnapshotRunner(remote, HealthMonitor(remote), RunManager(store)).execute(
        current, "ieee13", 1.0
    )
    assert store.get_meta("last_good_run") == former
    assert store.get_run(current)["status"] == "ERROR"
    assert remote.calls == []


@pytest.mark.asyncio
async def test_nonconvergent_snapshot_not_verified(monkeypatch, tmp_path):
    from backend.app.services import snapshot_runner as module

    monkeypatch.setattr(
        module, "connect_ws", lambda remote, session: asyncio.sleep(0, result=FakeWS())
    )
    store = Store(tmp_path / "test.sqlite")
    remote = FakeSnapshotRemote(converged=False)
    run_id = store.create({}, {})
    await SnapshotRunner(remote, HealthMonitor(remote), RunManager(store)).execute(
        run_id, "ieee13", 1
    )
    assert store.get_run(run_id)["status"] == "ERROR"
    assert store.get_meta("last_good_run") is None
