"""Exploración RDF/CIM, as-of bitemporal y SELECT acotado."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from rdflib import RDF

from backend.app.contracts.graph import SPARQLQuery
from backend.app.services.cim_import import cim_catalog
from backend.app.services.rdf_store import load_turtle
from backend.app.services.sparql_queries import query_asof, safe_select
from backend.app.services.tkg_builder import TKG
from backend.app.settings import ROOT

router = APIRouter()


@router.get("/graph/cim")
def cim():
    return cim_catalog()


@router.get("/graph/asof")
def asof(run_id: str, at: datetime, known_at: datetime | None = None):
    if (
        not (ROOT / "results/runs" / run_id / "derms_graph.ttl")
        .resolve()
        .is_relative_to((ROOT / "results/runs").resolve())
    ):
        raise HTTPException(400, "run_id inválido")
    try:
        return {
            "run_id": run_id,
            "at": at.isoformat(),
            "known_at": known_at.isoformat() if known_at else None,
            "assertions": query_asof(run_id, at, known_at),
        }
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/graph/query")
def sparql(request: SPARQLQuery):
    try:
        return safe_select(request.run_id, request.query)
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/graph/nodes")
def graph_nodes(run_id: str, limit: int = 120):
    path = ROOT / "results/runs" / run_id / "derms_graph.ttl"
    if not path.exists():
        path = ROOT / "results/runs" / run_id / "qsts_graph.ttl"
    if not path.resolve().is_relative_to((ROOT / "results/runs").resolve()):
        raise HTTPException(400, "run_id inválido")
    graph = load_turtle(path)
    semantic = [
        (node, kind)
        for node, kind in graph.subject_objects(RDF.type)
        if "example.org/derms/" in str(node)
    ]
    selected = semantic[:limit] or list(graph.subject_objects(RDF.type))[:limit]
    nodes = [
        {
            "id": str(node),
            "label": str(node).rsplit("/", 1)[-1],
            "type": str(kind).rsplit("#", 1)[-1],
        }
        for node, kind in selected
    ]
    edges = [
        {"source": str(s), "target": str(o), "label": str(p).rsplit("#", 1)[-1]}
        for s, p, o in (
            list(graph.triples((None, TKG.hasDecision, None)))[:limit]
            or list(graph.triples((None, TKG.hasSimulationStep, None)))[:limit]
        )
    ]
    return {"nodes": nodes, "edges": edges, "count_triples": len(graph)}
