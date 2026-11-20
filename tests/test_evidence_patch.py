"""Prueba de recuperación de evidencias RDF y ausencia de inferencias falsas."""

from rdflib import RDF, XSD, Graph, Literal

from backend.app.services import evidence_context, sparql_queries
from backend.app.services.tkg_builder import RESOURCE, TKG


def test_rdf_assertion_visible_asof(monkeypatch, tmp_path):
    run_id = "demo-rdf"
    path = tmp_path / "results/runs" / run_id / "derms_graph.ttl"
    path.parent.mkdir(parents=True)
    graph = Graph()
    node = RESOURCE["assertion/demo-rdf/1"]
    graph.add((node, RDF.type, TKG.StateAssertion))
    for pred, value in (
        (TKG.validFrom, Literal("2011-07-01T00:00:00+00:00", datatype=XSD.dateTime)),
        (TKG.validTo, Literal("2011-07-01T00:30:00+00:00", datatype=XSD.dateTime)),
        (TKG.recordedAt, Literal("2011-07-01T00:00:00+00:00", datatype=XSD.dateTime)),
        (TKG.object, RESOURCE["BatteryState/CHARGING"]),
        (TKG.batteryKw, Literal(1.0, datatype=XSD.double)),
        (TKG.socKwh, Literal(4.1, datatype=XSD.double)),
        (TKG.sourceKind, Literal("DERIVED")),
    ):
        graph.add((node, pred, value))
    graph.serialize(path, format="turtle")
    monkeypatch.setattr(evidence_context, "ROOT", tmp_path)
    monkeypatch.setattr(sparql_queries, "ROOT", tmp_path)
    run = {
        "run_id": run_id,
        "status": "ENERGY_MODEL_ONLY",
        "origin_kind": "DERIVED",
        "dispatch": {
            "rows": [
                {"step": 1, "timestamp": "2011-07-01T00:00:00Z", "battery_kw": 1.0, "soc_kwh": 4.1}
            ]
        },
    }
    packet = evidence_context.build_context(run, 1)
    assert packet["tkg"]["state_assertions"] == 1
    assert len(packet["tkg"]["asof"]) == 1
    assert "CHARGING" in packet["tkg"]["asof"][0]["state"]
