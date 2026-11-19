import asyncio
import json

import pytest

from backend.app.persistence.sqlite_store import Store
from backend.app.services.ausgrid import default_profile
from backend.app.services.health_monitor import HealthMonitor
from backend.app.services.orchestrator import Orchestrator
from backend.app.services.profile_mapper import to_multipliers
from backend.app.services.run_manager import RunManager


class FakeWS:
    def __init__(self, events):
        self.events = iter(events)
        self.closed = False

    async def recv(self):
        await asyncio.sleep(0)
        return json.dumps(next(self.events))

    async def close(self):
        self.closed = True


class FakeRemote:
    def __init__(self, profile):
        self.multipliers = to_multipliers(profile)
        self.created = False
        self.solved = False

    async def health(self):
        return {"state": "HEALTHY", "message": "mock"}

    async def _get_token(self):
        return "mock-non-production"

    async def create(self, _):
        self.created = True
        return {"session_id": "fake-session"}

    async def solve(self, session, payload):
        assert self.created
        assert len(payload.qsts.load_multipliers) == 48
        self.solved = True
        return {"status": "COMPLETED"}

    async def results(self, session):
        assert self.solved
        return {
            "session_id": session,
            "simulation_type": "qsts",
            "steps": [
                {
                    "step": i + 1,
                    "simulated_minutes": i * 30,
                    "converged": True,
                    "load_multiplier": v,
                    "total_kw": 100 * v,
                    "min_voltage_pu": 0.98,
                    "max_voltage_pu": 1.02,
                }
                for i, v in enumerate(self.multipliers)
            ],
            "summary": {"failed_steps": 0, "converged_steps": 48},
        }


@pytest.mark.asyncio
async def test_rest_ws_rest_commit(monkeypatch, tmp_path):
    from backend.app.services import orchestrator as module

    profile = default_profile()
    mock = FakeRemote(profile)
    events = [
        {"type": "snapshot"},
        {"type": "qsts_progress", "step": 1, "total_steps": 48, "progress_pct": 2.08},
        {"type": "result"},
        {"type": "completed", "status": "COMPLETED"},
    ]
    monkeypatch.setattr(module, "connect_ws", lambda r, s: asyncio.sleep(0, result=FakeWS(events)))
    store = Store(tmp_path / "db.sqlite")
    manager = RunManager(store)
    scenario = {"topology": "ieee13", "scale_multiplier": 1}
    id = store.create(scenario, {})
    await Orchestrator(mock, HealthMonitor(mock), manager).execute(id, scenario, profile)
    run = store.get_run(id)
    assert run["status"] == "VERIFIED", run.get("error")
    assert len(run["steps"]) == 48
    assert store.get_meta("last_good_run") == id
