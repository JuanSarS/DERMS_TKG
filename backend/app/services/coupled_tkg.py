"""Prueba semántica: enlaza evidencia de restricciones, decisiones y QSTS verificado."""

from __future__ import annotations

from datetime import datetime, timezone

from rdflib import RDF, XSD, Graph, Literal

from backend.app.services.rdf_store import load_turtle, save_turtle
from backend.app.services.tkg_builder import RESOURCE, TKG
from backend.app.settings import ROOT


def build_coupled_graph(run: dict, operational: Graph, report: dict):
    folder = ROOT / "results/runs" / run["run_id"]
    graph = load_turtle(folder / "derms_graph.ttl")
    graph += operational
    run_uri = RESOURCE[f"run/{run['run_id']}"]
    graph.add((run_uri, TKG.evaluatedByOpenDSS, RESOURCE[f"run/{report['optimized_run_id']}"]))
    graph.add((run_uri, TKG.comparedTo, RESOURCE[f"run/{report['baseline_run_id']}"]))
    graph.add((run_uri, TKG.verificationScope, Literal(report["validation_scope"])))
    graph.add((run_uri, TKG.electricalStatus, Literal(report["status"])))
    recorded = Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime)
    dispatch = run.get("dispatch") or {}
    for row in dispatch.get("rows", []):
        index = int(row["step"])
        decision = RESOURCE[f"assertion/{run['run_id']}/{index}"]
        context = row.get("operational_context") or {}
        if context.get("evidence_uri"):
            graph.add((decision, TKG.usedKnowledge, RESOURCE[f"operational/availability/{index}"]))
        electric = RESOURCE[f"qsts/{report['optimized_run_id']}/{index}"]
        graph.add((electric, RDF.type, TKG.QSTSStep))
        graph.add((electric, TKG.recordedAt, recorded))
        graph.add((decision, TKG.checkedBy, electric))
        matching = next((x for x in report["electrical"]["steps"] if x["step"] == index), None)
        if matching:
            for key, predicate in [
                ("optimized_vmin_pu", TKG.minVoltagePu),
                ("optimized_vmax_pu", TKG.maxVoltagePu),
                ("optimized_total_kw", TKG.totalKw),
            ]:
                if matching.get(key) is not None:
                    graph.add(
                        (electric, predicate, Literal(float(matching[key]), datatype=XSD.double))
                    )
    return save_turtle(graph, folder / "coupled_graph.ttl")
