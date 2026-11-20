"""El endpoint Snapshot NO debe crear sesiones remotas si /health falla."""

from fastapi.testclient import TestClient

from backend.app.integrations.opendss_http import RemoteOpenDSS
from backend.app.persistence.sqlite_store import Store


def test_snapshot_endpoint_health_blocks_remote_calls(monkeypatch, tmp_path):
    from backend.app import main as module

    called = {"remote_posts": 0}

    async def offline(_self):
        return {"state": "OFFLINE", "message": "mock offline"}

    async def checked(_self, *_args, **_kwargs):
        called["remote_posts"] += 1
        raise AssertionError("No se permite un POST upstream")

    monkeypatch.setattr(RemoteOpenDSS, "health", offline)
    monkeypatch.setattr(RemoteOpenDSS, "checked", checked)
    monkeypatch.setattr(module, "Store", lambda: Store(tmp_path / "db.sqlite"))
    with TestClient(module.app) as client:
        response = client.post(
            "/api/snapshots",
            json={
                "topology": "ieee13",
                "load_multiplier": 1.0,
            },
        )
        assert response.status_code == 503
        assert called["remote_posts"] == 0
        assert client.get("/api/runs").json() == []
