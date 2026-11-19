from backend.app.persistence.sqlite_store import Store


def test_duplicate_step_upsert_is_idempotent(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    run = store.create({}, {})
    store.step(run, {"step": 1, "value": 10})
    store.step(run, {"step": 1, "value": 11})
    steps = store.get_run(run)["steps"]
    assert len(steps) == 1 and steps[0]["value"] == 11
