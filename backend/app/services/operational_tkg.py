"""Contexto operativo bitemporal de BESS: RDF consultado ANTES del MILP.

La configuración fija aserciones SIMULATED (no estados medidos de Ausgrid).
Los índices son de base 1 y los intervalos son [inicio, fin).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal, Namespace

from backend.app.services.tkg_builder import RESOURCE, TKG
from backend.app.settings import ROOT

OPS = Namespace("https://example.org/derms/ops#")


def _instant(raw: str) -> datetime:
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("Los tiempos del perfil necesitan zona horaria")
    return value.astimezone(timezone.utc)


def build_operational_graph(profile: dict, scenario: dict, events: list[dict]) -> Graph:
    """Incorpora estados con procedencia y tiempos de vigencia explícitos."""
    records = profile["records"]
    count = len(records)
    dt = timedelta(minutes=int(scenario["step_minutes"]))
    graph = Graph()
    graph.bind("tkg", TKG)
    graph.bind("ops", OPS)
    battery = RESOURCE["Battery/BESS_MODELED_01"]
    graph.add((battery, RDF.type, TKG.Battery))
    states = ["AVAILABLE"] * count
    for event in events:
        start = event.get("start_step")
        end = event.get("end_step")
        state = event.get("state")
        if not (type(start) is int and type(end) is int and 1 <= start <= end <= count):
            raise ValueError("Intervalo operacional inválido")
        if state not in {"AVAILABLE", "UNAVAILABLE"}:
            raise ValueError("Estado operacional inválido")
        for i in range(start - 1, end):
            states[i] = state
    recorded = datetime.now(timezone.utc).isoformat()
    for i, (row, state) in enumerate(zip(records, states, strict=True), 1):
        start = _instant(row["timestamp"])
        assertion = RESOURCE[f"operational/availability/{i}"]
        graph.add((assertion, RDF.type, TKG.StateAssertion))
        graph.add((assertion, TKG.subject, battery))
        graph.add((assertion, TKG.predicate, TKG.hasAvailability))
        graph.add((assertion, TKG.object, RESOURCE[f"Availability/{state}"]))
        graph.add((assertion, TKG.validFrom, Literal(start.isoformat(), datatype=XSD.dateTime)))
        graph.add(
            (assertion, TKG.validTo, Literal((start + dt).isoformat(), datatype=XSD.dateTime))
        )
        graph.add((assertion, TKG.recordedAt, Literal(recorded, datatype=XSD.dateTime)))
        graph.add((assertion, TKG.sourceKind, Literal("SIMULATED")))
        graph.add((assertion, TKG.sourceId, Literal("operational_events_v1")))
    return graph


def operational_asof(graph: Graph, at: str, *, known_at: str | None = None) -> dict:
    """SPARQL: recupera la única aserción vigente, de forma conservadora."""
    now = datetime.now(timezone.utc).isoformat()
    when = _instant(at).isoformat()
    knowledge = _instant(known_at).isoformat() if known_at else now
    query = """PREFIX tkg: <https://example.org/derms/tkg#>
    SELECT ?assertion ?state WHERE {
      ?assertion a tkg:StateAssertion ; tkg:predicate tkg:hasAvailability ;
        tkg:object ?state ; tkg:validFrom ?start ; tkg:validTo ?end ;
        tkg:recordedAt ?recorded .
      FILTER (?start <= ?at && ?end > ?at && ?recorded <= ?known)
    }"""
    bindings = {
        "at": Literal(when, datatype=XSD.dateTime),
        "known": Literal(knowledge, datatype=XSD.dateTime),
    }
    matches = list(graph.query(query, initBindings=bindings))
    if len(matches) != 1:
        raise ValueError(f"Aserciones de disponibilidad esperadas=1, encontradas={len(matches)}")
    name = str(matches[0].state).rsplit("/", 1)[-1]
    if name not in {"AVAILABLE", "UNAVAILABLE"}:
        raise ValueError("Estado RDF desconocido")
    return {"availability": name, "evidence_uri": str(matches[0].assertion)}


def resolve_constraints(
    profile: dict, scenario: dict, events: list[dict]
) -> tuple[list[dict], Graph]:
    graph = build_operational_graph(profile, scenario, events)
    return [operational_asof(graph, row["timestamp"]) for row in profile["records"]], graph


def load_events(file: Path | None = None) -> list[dict]:
    path = file or ROOT / "config/operational_events.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"events": []}
    if set(data) != {"events"} or not isinstance(data["events"], list):
        raise ValueError("Formato config/operational_events.json inválido")
    return data["events"]


def save_operational_graph(graph: Graph, folder: Path) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "operational_tkg.ttl"
    graph.serialize(destination=path, format="turtle")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"file": path.name, "sha256": digest, "triples": len(graph)}
