from backend.app.services.ausgrid import default_profile
from backend.app.services.profile_mapper import to_multipliers


def test_source_and_48_samples():
    p = default_profile()
    assert len(p["records"]) == 48
    assert p["processed_kind"] == "DERIVED"
    assert len(p["source_sha256"]) == 64
    assert p["records"][0]["timestamp"].endswith("Z")


def test_positive_48_qsts_multipliers():
    x = to_multipliers(default_profile())
    assert len(x) == 48
    assert 0 < min(x) and max(x) <= 5
