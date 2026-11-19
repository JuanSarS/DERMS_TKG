"""TKG RDF reificado: intervalo, procedencia, tiempo de conocimiento y decisiones."""

from datetime import datetime, timedelta
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal, Namespace

from backend.app.persistence.sqlite_store import utc_now
from backend.app.services.cim_import import CIM, load_cim
from backend.app.services.rdf_store import save_turtle
from backend.app.settings import ROOT

TKG = Namespace("https://example.org/derms/tkg#")
RESOURCE = Namespace("https://example.org/derms/resource/")


def build_graph(run: dict, profile: dict, dispatch: dict) -> Path:
    graph = Graph()
    graph += load_cim()  # RDF/CIM100 de referencia aportado por el usuario.
    graph.bind("cim", CIM)
    graph.bind("tkg", TKG)
    graph.bind("res", RESOURCE)
    run_uri = RESOURCE["run/" + run["run_id"]]
    battery = RESOURCE["Battery/BESS_MODELED_01"]
    source = RESOURCE["Source/ausgrid_customer12"]
    graph.add((run_uri, RDF.type, TKG.SimulationRun))
    graph.add((run_uri, TKG.sourceId, Literal("ausgrid_customer12")))
    graph.add((run_uri, TKG.sourceKind, Literal("DERIVED")))
    graph.add(
        (
            run_uri,
            TKG.remoteElectricalValidation,
            Literal(run.get("remote_verification", "NOT_VALIDATED")),
        )
    )
    graph.add((source, RDF.type, TKG.Source))
    graph.add((source, TKG.sourceKind, Literal("REAL")))
    graph.add((source, TKG.rawUri, Literal("data/processed/ausgrid_c12_2011-07-01.csv")))
    graph.add((source, TKG.rawSha256, Literal(profile.get("source_sha256", ""))))
    graph.add((battery, RDF.type, TKG.Battery))
    # La relación experimental con la barra 671 apunta al recurso CIM existente.
    bus671 = next((s for s in graph.subjects(CIM["IdentifiedObject.name"], Literal("671"))), None)
    if bus671 is not None:
        graph.add((battery, TKG.connectedTo, bus671))
    else:
        graph.add((battery, TKG.connectedTo, RESOURCE["Bus/671"]))
    graph.add((battery, TKG.assignmentKind, Literal("SIMULATED_NOT_PHYSICAL")))
    graph.add((battery, TKG.hasSource, source))
    recorded = Literal(utc_now(), datatype=XSD.dateTime)
    for row in dispatch["rows"]:
        i = int(row["step"])
        node = RESOURCE[f"assertion/{run['run_id']}/{i}"]
        start = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        stop = start + timedelta(minutes=30)
        state = (
            "CHARGING"
            if row["battery_kw"] > 1e-6
            else "DISCHARGING"
            if row["battery_kw"] < -1e-6
            else "IDLE"
        )
        graph.add((node, RDF.type, TKG.StateAssertion))
        graph.add((node, TKG.forRun, run_uri))
        graph.add((node, TKG.subject, battery))
        graph.add((node, TKG.predicate, TKG.hasState))
        graph.add((node, TKG.object, RESOURCE["BatteryState/" + state]))
        graph.add((node, TKG.validFrom, Literal(start.isoformat(), datatype=XSD.dateTime)))
        graph.add((node, TKG.validTo, Literal(stop.isoformat(), datatype=XSD.dateTime)))
        graph.add((node, TKG.recordedAt, recorded))
        graph.add((node, TKG.sourceId, Literal("ausgrid_customer12")))
        graph.add((node, TKG.sourceKind, Literal("DERIVED")))
        graph.add((node, TKG.usesEvidence, source))
        graph.add((node, TKG.batteryKw, Literal(float(row["battery_kw"]), datatype=XSD.double)))
        graph.add((node, TKG.socKwh, Literal(float(row["soc_kwh"]), datatype=XSD.double)))
        graph.add((node, TKG.loadKw, Literal(float(row["load_kw"]), datatype=XSD.double)))
        graph.add((node, TKG.pvKw, Literal(float(row["pv_kw"]), datatype=XSD.double)))
        graph.add((run_uri, TKG.hasDecision, node))
    path = ROOT / "results/runs" / run["run_id"] / "derms_graph.ttl"
    return save_turtle(graph, path)


def build_qsts_graph(run: dict, result: dict) -> Path:
    """TKG de resultados QSTS remotos, sin inferir tiempo de Ausgrid del reloj OpenDSS."""
    graph = Graph()
    graph += load_cim()
    graph.bind("cim", CIM)
    graph.bind("tkg", TKG)
    uri = RESOURCE["run/" + run["run_id"]]
    graph.add((uri, RDF.type, TKG.SimulationRun))
    graph.add((uri, TKG.sourceKind, Literal("SIMULATED")))
    graph.add((uri, TKG.remoteElectricalValidation, Literal("remote_qsts_baseline_verified")))
    graph.add((uri, TKG.upstreamSessionId, Literal(result["session_id"])))
    now = Literal(utc_now(), datatype=XSD.dateTime)
    for row in result["steps"]:
        i = int(row["step"])
        node = RESOURCE[f"qsts/{run['run_id']}/{i}"]
        graph.add((node, RDF.type, TKG.QSTSStep))
        graph.add((node, TKG.forRun, uri))
        graph.add((node, TKG.recordedAt, now))
        graph.add(
            (
                node,
                TKG.simulatedMinutes,
                Literal(float(row["simulated_minutes"]), datatype=XSD.double),
            )
        )
        graph.add(
            (node, TKG.loadMultiplier, Literal(float(row["load_multiplier"]), datatype=XSD.double))
        )
        graph.add((node, TKG.converged, Literal(bool(row["converged"]), datatype=XSD.boolean)))
        for name, key in [
            ("totalKw", "total_kw"),
            ("minVoltagePu", "min_voltage_pu"),
            ("maxVoltagePu", "max_voltage_pu"),
        ]:
            if row.get(key) is not None:
                graph.add((node, TKG[name], Literal(float(row[key]), datatype=XSD.double)))
        graph.add((uri, TKG.hasSimulationStep, node))
    path = ROOT / "results/runs" / run["run_id"] / "qsts_graph.ttl"
    return save_turtle(graph, path)
