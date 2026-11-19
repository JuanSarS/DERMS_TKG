"""Servicio para crear escenarios offline, sin alterar último resultado remoto verificado."""

from backend.app.persistence.file_store import export_run
from backend.app.services.ausgrid import default_profile
from backend.app.services.comparisons import compare_dispatch
from backend.app.services.dispatcher import optimize
from backend.app.services.tkg_builder import build_graph
from backend.app.settings import ROOT, read_json


def offline_experiment(store, objective: dict | None = None) -> dict:
    profile = default_profile()
    scenario = read_json(ROOT / "config/scenario_ieee13.json")
    obj = objective or read_json(ROOT / "config/objective.json")
    run_id = store.create(scenario, obj, origin_kind="DERIVED")
    store.update(run_id, "ENERGY_MODEL_ONLY")
    result = optimize(profile, scenario, obj)
    result["comparison"] = compare_dispatch(profile, scenario, obj, result)
    store.save_dispatch(run_id, result)
    stored = store.get_run(run_id)
    path = build_graph(stored, profile, result)
    export_run(store.get_run(run_id))
    return {
        "run_id": run_id,
        "status": "ENERGY_MODEL_ONLY",
        "graph_path": str(path.relative_to(ROOT)),
        "dispatch": result,
        "note": "NO se ejecutó OpenDSS remoto; la corrida NO actualiza last_good_run",
    }
