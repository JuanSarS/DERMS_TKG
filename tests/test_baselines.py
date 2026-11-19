"""El TKG no obtiene una mejora ficticia sobre tablas temporales competentes."""

from backend.app.services.baselines import compare_baselines


def test_temporal_relational_matches_tkg():
    result = compare_baselines()
    assert len(result["answers"]) == 3
    assert all(row["B0_equals_B2"] for row in result["answers"].values())
    assert next(iter(result["answers"].values()))["B1"] != "AVAILABLE"
