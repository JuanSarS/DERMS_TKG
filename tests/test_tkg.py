from datetime import datetime, timedelta, timezone

import pytest
from rdflib import RDF

from backend.app.persistence.sqlite_store import Store
from backend.app.services.ausgrid import default_profile
from backend.app.services.cim_import import CIM, cim_catalog, load_cim
from backend.app.services.dispatcher import optimize
from backend.app.services.rdf_store import load_turtle
from backend.app.services.sparql_queries import query_asof, safe_select
from backend.app.services.tkg_builder import build_graph
from backend.app.settings import ROOT, read_json


def test_original_cim_is_semantic():
    cat = cim_catalog()
    assert cat["triples"] > 3000
    assert cat["ac_line_segments"] == 11
    assert len(list(load_cim().subjects(RDF.type, CIM.ConnectivityNode))) == 16


def test_rdf_temporal_queries(tmp_path):
    db = Store(tmp_path / "test.db")
    p = default_profile()
    sc = read_json(ROOT / "config/scenario_ieee13.json")
    obj = read_json(ROOT / "config/objective.json")
    id = db.create(sc, obj)
    db.update(id, "ENERGY_MODEL_ONLY")
    result = optimize(p, sc, obj)
    db.save_dispatch(id, result)
    path = build_graph(db.get_run(id), p, result)
    graph = load_turtle(path)
    assert len(graph) > 4000
    at = datetime.fromisoformat(p["records"][0]["timestamp"].replace("Z", "+00:00"))
    assert len(query_asof(id, at)) == 1
    before = at - timedelta(seconds=1)
    assert query_asof(id, before) == []
    future = datetime.now(timezone.utc) + timedelta(days=1)
    assert len(query_asof(id, at, future)) == 1
    early = datetime(2020, 1, 1, tzinfo=timezone.utc)
    assert query_asof(id, at, early) == []  # knowledge-at: time of registration matters
    out = safe_select(
        id,
        "PREFIX tkg: <https://example.org/derms/tkg#> SELECT ?a WHERE { ?a a tkg:StateAssertion } LIMIT 2",
    )
    assert len(out["rows"]) == 2
    with pytest.raises(ValueError):
        safe_select(id, "DROP ALL")
