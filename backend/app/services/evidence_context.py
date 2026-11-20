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
        "coupled_graph.ttl"
        if (base / "coupled_graph.ttl").exists()
        else "derms_graph.ttl"
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
        if (
            selected
            and selected.get("timestamp")
            and rdf_file.name in {"derms_graph.ttl", "coupled_graph.ttl"}
        ):
            try:
                at = datetime.fromisoformat(selected["timestamp"].replace("Z", "+00:00"))
                packet["tkg"]["asof"] = query_asof(run["run_id"], at)[:8]
            except (ValueError, OSError):
                packet["tkg"]["query_error"] = "No se logró consultar este instante."
        if rdf_file.name == "coupled_graph.ttl":
            from backend.app.services.tkg_builder import RESOURCE

            selected_step = selected.get("step") if selected else None
            if selected_step:
                decision = RESOURCE[f"assertion/{run['run_id']}/{selected_step}"]
                packet["tkg"]["used_knowledge_uris"] = [
                    str(node) for node in graph.objects(decision, TKG.usedKnowledge)
                ]
                packet["tkg"]["checked_by_uris"] = [
                    str(node) for node in graph.objects(decision, TKG.checkedBy)
                ]
                packet["tkg"]["aggregate_proxy_uris"] = [
                    str(node) for node in graph.objects(decision, TKG.assessedByAggregateProxy)
                ]
            packet["tkg"]["evaluation_status"] = list(
                str(node)
                for node in graph.objects(RESOURCE[f"run/{run['run_id']}"], TKG.electricalStatus)
            )[:1]
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
    coupled = run.get("result") or {}
    if run.get("status") == "COUPLED_COMPLETED" and "electrical" in coupled:
        packet["coupled_validation"] = {
            "status": coupled.get("status"),
            "baseline_run_id": coupled.get("baseline_run_id"),
            "optimized_run_id": coupled.get("optimized_run_id"),
            "scope": coupled.get("validation_scope"),
            "voltage_check": coupled["electrical"].get("optimized_check"),
            "power_difference_kw": coupled["electrical"].get("max_abs_delta_kw"),
            "individual_storage_telemetry": coupled.get("device_telemetry_verified", False),
            "model_has_storage_pv": coupled.get("model_has_storage_pv", False),
            "reference_run_id": coupled.get("reference_run_id"),
            "warnings": coupled.get("warnings", []),
        }
    packet["knowledge_limits"] = [
        "Las fuentes Ausgrid son históricas; la batería, cargas flexibles y tarifas son modeladas.",
        "El TKG operativo aporta estados de disponibilidad consultados antes del MILP.",
        "El modo IEEE13 integrado usa multiplicadores globales como proxy agregado; NO incorpora BESS/PV físico ni verifica consignas individuales.",
        "Solo el modo DSS personalizado intentaría aplicar Storage; necesita validación exitosa en el worker.",
        "No atribuir ahorro energético al TKG sin comparación controlada B0/B2.",
    ]
    return packet
