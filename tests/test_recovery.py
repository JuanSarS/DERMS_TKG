from backend.app.persistence.sqlite_store import Store


def test_last_good_persists_across_restart(tmp_path):
    db_path = tmp_path / "lab.db"
    store = Store(db_path)
    good = store.create({"topology": "ieee13"}, {})
    store.update(good, "SOLVING")
    row = {"step": 1, "simulated_minutes": 0, "converged": True, "load_multiplier": 1.0}
    store.commit_verified(
        good,
        {
            "session_id": "s",
            "simulation_type": "qsts",
            "steps": [row],
            "summary": {"failed_steps": 0},
        },
    )
    broken = store.create({"topology": "ieee13"}, {})
    store.update(broken, "ERROR", error="remote offline")
    reopened = Store(db_path)
    assert reopened.get_meta("last_good_run") == good
    assert reopened.get_run(good)["steps"][0]["step"] == 1
    assert reopened.get_run(broken)["status"] == "ERROR"
