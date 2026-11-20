"""Verify adapted built-in API flow WITHOUT claiming physical BESS checks."""

from __future__ import annotations

import asyncio

import pytest

from backend.app.persistence.sqlite_store import Store
from backend.app.services.ausgrid import default_profile
from backend.app.services.builtin_proxy import fixed_policy_rows, proxy_multipliers
from backend.app.services.coupled_runner import CoupledRunner
from backend.app.services.dispatcher import optimize
from backend.app.services.operational_tkg import resolve_constraints
from backend.app.services.profile_mapper import to_multipliers
from backend.app.settings import ROOT, read_json


def _reference(profile, scenario):
    vals = to_multipliers(profile)
    return {
        "steps": [
            {
                "step": i,
                "load_multiplier": m,
                "converged": True,
                "total_kw": -max(1.0, 2000 * m),
                "min_voltage_pu": 0.98,
                "max_voltage_pu": 1.02,
            }
            for i, m in enumerate(vals, 1)
        ]
    }


def test_proxy_does_not_hide_physical_limitations():
    profile = default_profile()
    scenario = read_json(ROOT / "config/scenario_ieee13.json")
    objective = read_json(ROOT / "config/objective.json")
    context, _ = resolve_constraints(profile, scenario, [])
    result = optimize(profile, scenario, objective, context)
    fixed, a = proxy_multipliers(
        profile,
        scenario,
        _reference(profile, scenario),
        fixed_policy_rows(profile, scenario),
        resource_scale=20,
    )
    candidate, b = proxy_multipliers(
        profile,
        scenario,
        _reference(profile, scenario),
        result["rows"],
        resource_scale=20,
    )
    assert len(fixed) == len(candidate) == 48
    assert a["pv_storage_elements_in_feeder"] is False
    assert b["device_telemetry_verified"] is False
    assert any(abs(x - y) > 1e-5 for x, y in zip(fixed, candidate, strict=True))


def test_proxy_rejects_unrepresentable_exports():
    profile = default_profile()
    scenario = read_json(ROOT / "config/scenario_ieee13.json")
    rows = fixed_policy_rows(profile, scenario)
    rows[0]["battery_kw"] = -900
    with pytest.raises(ValueError, match="fuera de"):
        proxy_multipliers(
            profile, scenario, _reference(profile, scenario), rows, resource_scale=100
        )


class GuardedRemote:
    async def checked(self, *args, **kwargs):
        raise AssertionError("No debe subir ni validar DSS custom en modo builtin_proxy")


class HealthyMonitor:
    async def require_healthy(self):
        return None


class DummyManager:
    def __init__(self, store):
        self.store = store
        self.notifications = []

    async def broadcast(self, run_id, event):
        self.notifications.append(event)


class FakeQSTS:
    def __init__(self, store):
        self.store = store
        self.calls = []

    async def execute(self, run_id, scenario, profile):
        assert scenario["topology"] == "ieee13"
        assert len(scenario["qsts_load_multipliers"]) == 48
        self.calls.append(scenario["model_label"])
        steps = [
            {
                "step": i,
                "load_multiplier": m,
                "converged": True,
                "total_kw": -2000 * m,
                "min_voltage_pu": 0.98,
                "max_voltage_pu": 1.02,
            }
            for i, m in enumerate(scenario["qsts_load_multipliers"], 1)
        ]
        self.store.commit_verified(run_id, {"steps": steps, "summary": {"failed_steps": 0}})


def test_runner_uses_only_builtin_ieee13(monkeypatch, tmp_path):
    from backend.app.services import coupled_runner, coupled_tkg, tkg_builder

    profile = default_profile()
    scenario = read_json(ROOT / "config/scenario_ieee13.json")
    objective = read_json(ROOT / "config/objective.json")
    store = Store(tmp_path / "test.sqlite")
    monkeypatch.setattr(coupled_runner, "ROOT", tmp_path)
    monkeypatch.setattr(coupled_tkg, "ROOT", tmp_path)
    monkeypatch.setattr(tkg_builder, "ROOT", tmp_path)
    manager = DummyManager(store)
    qsts = FakeQSTS(store)
    runner = CoupledRunner(
        remote=GuardedRemote(), monitor=HealthyMonitor(), manager=manager, orchestrator=qsts
    )
    job = store.create(scenario, objective, origin_kind="DERIVED")
    asyncio.run(
        runner.execute(
            job, profile, scenario, objective, resource_scale=20, mode="builtin_proxy", events=[]
        )
    )
    run = store.get_run(job)
    assert run["status"] == "COUPLED_COMPLETED", run.get("error")
    assert qsts.calls == ["ieee13_reference", "fixed_policy_proxy", "optimized_netload_proxy"]
    assert run["result"]["validation_scope"] == "BUILTIN_IEEE13_NETLOAD_PROXY_NOT_BESS_VALIDATION"
    assert run["result"]["model_has_storage_pv"] is False
    assert run["result"]["device_telemetry_verified"] is False
    assert run["result"]["electrical"]["network_response_different"]
