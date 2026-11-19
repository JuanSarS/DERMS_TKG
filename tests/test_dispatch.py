from backend.app.services.ausgrid import default_profile
from backend.app.services.constraints import validate_dispatch
from backend.app.services.dispatcher import optimize
from backend.app.settings import ROOT, read_json


def config():
    return read_json(ROOT / "config/scenario_ieee13.json"), read_json(
        ROOT / "config/objective.json"
    )


def test_milp_and_constraints():
    s, o = config()
    result = optimize(default_profile(), s, o)
    assert len(result["rows"]) == 48
    assert not validate_dispatch(result["rows"], s)
    assert result["electrical_verification"] == "NOT_VALIDATED"
    assert result["metrics"]["energy"] >= 0


def test_modified_weights_change_dispatch():
    s, o = config()
    base = optimize(default_profile(), s, o)
    o["terms"]["peak"]["weight"] = 12
    changed = optimize(default_profile(), s, o)
    assert (
        abs(changed["metrics"]["peak"] - base["metrics"]["peak"]) > 1e-5
        or abs(changed["metrics"]["energy"] - base["metrics"]["energy"]) > 1e-5
    )
