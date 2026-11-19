"""Prueba HTTP local con proveedor remoto falso y sin mutaciones cloud."""

import pytest
from fastapi.testclient import TestClient

from backend.app.integrations.opendss_http import RemoteOpenDSS
from backend.app.persistence.sqlite_store import Store


@pytest.mark.asyncio
async def test_health_failure_blocks_http_mutation_and_offline_is_separate(monkeypatch, tmp_path):
    from backend.app import main as module

    async def fake_health(_self):
        return {"state": "OFFLINE", "message": "mock only"}

    monkeypatch.setattr(RemoteOpenDSS, "health", fake_health)
    monkeypatch.setattr(module, "Store", lambda: Store(tmp_path / "api.db"))
    with TestClient(module.app) as client:
        assert client.get("/api/status").json()["remote"]["state"] == "OFFLINE"
        assert client.post("/api/runs", json={"topology": "ieee13"}).status_code == 503
        offline = client.post("/api/experiments/offline")
        assert offline.status_code == 200
        assert len(offline.json()["dispatch"]["rows"]) == 48
        status = client.get("/api/status").json()
        assert status["last_good_run"] is None
