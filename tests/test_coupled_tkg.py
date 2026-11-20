"""Contrato de seguridad, DSS y TKG; no supone acceso real al cloud."""

from __future__ import annotations

import asyncio
import io
import zipfile

import pytest

from backend.app.persistence.sqlite_store import Store
from backend.app.services.ausgrid import default_profile
from backend.app.services.coupled_runner import CoupledRunner, compare_remote
from backend.app.services.custom_dss import build_dispatch_zip
from backend.app.services.dispatcher import optimize
from backend.app.services.operational_tkg import operational_asof, resolve_constraints
from backend.app.settings import ROOT, read_json


@pytest.fixture
def case():
    return (
        default_profile(),
        read_json(ROOT / "config/scenario_ieee13.json"),
        read_json(ROOT / "config/objective.json"),
    )


def test_unavailable_bess_becomes_milp_constraint(case):
    profile, scenario, objective = case
    contexts, graph = resolve_constraints(
        profile,
        scenario,
        [{"start_step": 30, "end_step": 35, "state": "UNAVAILABLE"}],
    )
    assert contexts[28]["availability"] == "AVAILABLE"
    assert contexts[29]["availability"] == "UNAVAILABLE"
    assert contexts[34]["availability"] == "UNAVAILABLE"
    assert contexts[35]["availability"] == "AVAILABLE"
    assert (
        operational_asof(graph, profile["records"][29]["timestamp"])["availability"]
        == "UNAVAILABLE"
    )
    result = optimize(profile, scenario, objective, contexts)
    assert all(abs(row["battery_kw"]) < 1e-8 for row in result["rows"][29:35])
    assert result["rows"][29]["operational_context"]["evidence_uri"].endswith("/30")


def test_invalid_event_fails_closed(case):
    profile, scenario, _ = case
    with pytest.raises(ValueError):
        resolve_constraints(
            profile, scenario, [{"start_step": 0, "end_step": 2, "state": "UNAVAILABLE"}]
        )


def test_dss_custom_contains_follow_shapes_and_real_reference(tmp_path, case):
    profile, scenario, objective = case
    solution = optimize(profile, scenario, objective)
    original = (ROOT / "data/reference/DSS_model/IEEE13Nodeckt.dss").read_bytes()
    output = tmp_path / "custom.zip"
    manifest = build_dispatch_zip(profile, scenario, solution, output, resource_scale=100)
    with zipfile.ZipFile(output) as archive:
        assert archive.read("IEEE13Nodeckt.dss") == original
        assert set(archive.namelist()) == {
            "IEEE13Nodeckt.dss",
            "IEEELineCodes.DSS",
            "IEEE13Node_BusXY.csv",
            "master.dss",
            "manifest.json",
        }
        master = archive.read("master.dss").decode("utf-8")
        for fragment in (
            "Redirect IEEE13Nodeckt.dss",
            "New Storage.TKG_BESS",
            "dispmode=follow",
            "New PVSystem.TKG_PV",
            "New Load.TKG_FLEX",
            "npts=48",
            "bus1=671.1.2.3",
        ):
            assert fragment in master
        assert "Storage.TKG_BESS" in master
        assert "daily=TKG_BESS" in master
        assert manifest["assignment"] == "SIMULATED_NOT_PHYSICAL"


def test_remote_check_reports_network_without_bess_telemetry():
    def result(offset):
        return {
            "steps": [
                {
                    "step": index,
                    "converged": True,
                    "total_kw": 500 + index + offset,
                    "min_voltage_pu": 0.97,
                    "max_voltage_pu": 1.02,
                }
                for index in range(1, 49)
            ]
        }

    scenario = read_json(ROOT / "config/scenario_ieee13.json")
    comparison = compare_remote(result(0), result(-5), scenario)
    assert comparison["network_response_different"] is True
    assert comparison["device_telemetry_verified"] is False
    assert comparison["optimized_check"]["voltage_compliant"] is True


class FakeRemote:
    def __init__(self):
        self.calls = []
        self.uploads = 0

    async def checked(self, method, path, **kwargs):
        self.calls.append((method, path))
        if path == "/models/upload":
            self.uploads += 1
            with zipfile.ZipFile(io.BytesIO(kwargs["files"]["file"][1])) as z:
                assert "New Storage.TKG_BESS" in z.read("master.dss").decode()
            return {"model_id": f"candidate{self.uploads}"}
        if path.endswith("/validate"):
            assert kwargs["params"]["master"] == "master.dss"
            return {"valid": True}
        raise AssertionError(path)


class FakeMonitor:
    def __init__(self, fail=False):
        self.fail = fail

    async def require_healthy(self):
        if self.fail:
            raise RuntimeError("OFFLINE")


class FakeManager:
    def __init__(self, store):
        self.store = store
        self.events = []

    async def broadcast(self, run_id, event):
        self.events.append(event)


class FakeOrchestrator:
    def __init__(self, store):
        self.store = store

    async def execute(self, run_id, scenario, profile):
        top = scenario["topology"]
        is_optimized = "candidate2" in top
        steps = [
            {
                "step": n,
                "simulated_minutes": n * 30,
                "load_multiplier": 1,
                "converged": True,
                "total_kw": 1000 + n - (50 if is_optimized else 0),
                "min_voltage_pu": 0.97,
                "max_voltage_pu": 1.02,
            }
            for n in range(1, 49)
        ]
        self.store.commit_verified(
            run_id,
            {
                "session_id": "fake-session",
                "simulation_type": "qsts",
                "steps": steps,
                "summary": {"failed_steps": 0},
            },
        )


def test_full_coupled_orchestration_mocked(monkeypatch, tmp_path, case):
    """Prueba de integración sin fingir que la nube respondió."""
    profile, scenario, objective = case
    from backend.app import settings as settings_module
    from backend.app.services import coupled_runner, coupled_tkg, tkg_builder

    store = Store(tmp_path / "database.sqlite")
    old_root = settings_module.ROOT
    monkeypatch.setattr(coupled_runner, "ROOT", tmp_path)
    monkeypatch.setattr(coupled_tkg, "ROOT", tmp_path)
    monkeypatch.setattr(tkg_builder, "ROOT", tmp_path)
    monkeypatch.setattr(settings_module, "ROOT", old_root)  # fixture lee referencia real
    # El grafo de las corridas usa ROOT temporal; los ficheros CIM de la aplicación permanecen intactos.
    fake_remote = FakeRemote()
    manager = FakeManager(store)
    runner = CoupledRunner(
        remote=fake_remote,
        monitor=FakeMonitor(),
        manager=manager,
        orchestrator=FakeOrchestrator(store),
    )
    job = store.create(scenario, objective)
    asyncio.run(runner.execute(job, profile, scenario, objective, max_passes=1, events=[]))
    run = store.get_run(job)
    assert run["status"] == "COUPLED_COMPLETED", run.get("error")
    assert run["result"]["electrical"]["network_response_different"] is True
    assert run["result"]["device_telemetry_verified"] is False
    assert store.get_meta("last_good_run") == job
    assert (tmp_path / "results/runs" / job / "coupled_graph.ttl").exists()


def test_fail_health_does_not_change_last_good(tmp_path, case):
    profile, scenario, objective = case
    store = Store(tmp_path / "database.sqlite")
    good = store.create(scenario, objective)
    store.commit_verified(good, {"steps": [{"step": 1}]})
    last = store.get_meta("last_good_run")
    bad = store.create(scenario, objective)
    remote = FakeRemote()
    runner = CoupledRunner(
        remote=remote,
        monitor=FakeMonitor(fail=True),
        manager=FakeManager(store),
        orchestrator=FakeOrchestrator(store),
    )
    asyncio.run(runner.execute(bad, profile, scenario, objective, events=[]))
    assert store.get_run(bad)["status"] == "ERROR"
    assert store.get_meta("last_good_run") == last
    assert remote.calls == []
