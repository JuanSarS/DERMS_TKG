"""Contexto RAG verificable: SQL y RDF de la corrida, nunca memoria inventada del modelo."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rdflib import RDF

from backend.app.services.explanation import evidence_packet
from backend.app.services.rdf_store import load_turtle
from backend.app.services.sparql_queries import query_asof
from backend.app.services.tkg_builder import TKG
from backend.app.settings import ROOT


def _safe_run_path(run_id: str) -> Path:
    root = (ROOT / "results/runs").resolve()
    path = (root / run_id).resolve()
    if not path.is_relative_to(root):
        raise ValueError("run_id no válido")
    return path


def build_context(run: dict, step: int | None = None, store=None) -> dict:
    """Evidencia acotada con referencias; no afirma que el TKG haya optimizado."""
    packet = evidence_packet(run, step)
    base = _safe_run_path(run["run_id"])
    selected = packet.get("step")
    rdf_file = base / (
        "derms_graph.ttl"
        if (base / "derms_graph.ttl").exists()
        else "qsts_graph.ttl"
        if (base / "qsts_graph.ttl").exists()
        else "snapshot_graph.ttl"
    )
    if rdf_file.exists():
        graph = load_turtle(rdf_file)
        packet["tkg"] = {
            "file": str(rdf_file.relative_to(ROOT)),
            "triples": len(graph),
            "graph_type": "RDF_CIM_WITH_TEMPORAL_ASSERTIONS",
            "state_assertions": len(set(graph.subjects(RDF.type, TKG.StateAssertion))),
            "qsts_steps": len(set(graph.subjects(RDF.type, TKG.QSTSStep))),
            "snapshot_results": len(set(graph.subjects(RDF.type, TKG.SnapshotResult))),
            "asof": [],
        }
        if selected and selected.get("timestamp") and rdf_file.name == "derms_graph.ttl":
            try:
                at = datetime.fromisoformat(selected["timestamp"].replace("Z", "+00:00"))
                packet["tkg"]["asof"] = query_asof(run["run_id"], at)[:8]
            except (ValueError, OSError):
                packet["tkg"]["query_error"] = "No se logró consultar este instante."
        if rdf_file.name == "qsts_graph.ttl":
            packet["tkg"]["step_links"] = [
                str(node) for node in list(graph.objects(None, TKG.hasSimulationStep))[:4]
            ]
        if rdf_file.name == "snapshot_graph.ttl":
            packet["tkg"]["snapshot_links"] = [
                str(node) for node in list(graph.objects(None, TKG.hasSnapshot))[:4]
            ]
    else:
        packet["tkg"] = {"status": "NO_GRAPH_FOR_RUN", "asof": []}

    if store is not None:
        parent_id = run.get("scenario", {}).get("derived_from_run_id")
        if parent_id:
            parent = store.get_run(parent_id)
            if parent:
                packet["parent_run"] = {
                    "run_id": parent_id,
                    "status": parent["status"],
                    "remote_verification": parent.get("remote_verification"),
                }
        packet["recent_runs"] = [
            {
                "run_id": row["run_id"],
                "status": row["status"],
                "origin_kind": row.get("origin_kind"),
                "remote_verification": row.get("remote_verification"),
            }
            for row in store.list_runs(limit=5)
        ]
    packet["knowledge_limits"] = [
        "No hay control BESS en la API QSTS original; su simulación global no verifica despachos.",
        "El TKG actual registra estados y permite consultarlos; el MILP no incorpora aún restricciones RDF.",
        "Las fuentes Ausgrid son mediciones históricas; la batería, cargas flexibles y tarifas son modeladas.",
    ]
    return packet
