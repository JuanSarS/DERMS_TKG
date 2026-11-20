"""Ciclo IEEE13 -> despacho TKG/MILP -> nuevo IEEE13 -> validación agregada.

Aprovecha exclusivamente los endpoints existentes de modelos personalizados y QSTS.
No usa comandos inventados en WSS ni altera el servidor remoto.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path

from backend.app.integrations.opendss_http import UpstreamError
from backend.app.persistence.file_store import export_run
from backend.app.services.comparisons import compare_dispatch
from backend.app.services.custom_dss import build_dispatch_zip
from backend.app.services.dispatcher import optimize
from backend.app.services.operational_tkg import (
    load_events,
    resolve_constraints,
    save_operational_graph,
)
from backend.app.services.tkg_builder import build_graph
from backend.app.settings import ROOT


def check_electrical(results: dict, scenario: dict) -> dict:
    """Comprueba convergencia y límites en los valores agregados retornados por OpenDSS."""
    low, high = scenario["limits"]["voltage_min_pu"], scenario["limits"]["voltage_max_pu"]
    violations = []
    for step in results.get("steps", []):
        mn, mx = step.get("min_voltage_pu"), step.get("max_voltage_pu")
        if not step.get("converged") or mn is None or mx is None:
            violations.append({"step": step.get("step"), "reason": "SIN_CONVERGENCIA_O_TENSION"})
            continue
        if not (math.isfinite(float(mn)) and math.isfinite(float(mx))):
            violations.append({"step": step.get("step"), "reason": "TENSION_NO_FINITA"})
        elif float(mn) < low or float(mx) > high:
            violations.append(
                {"step": step.get("step"), "reason": "TENSION_FUERA_RANGO", "vmin": mn, "vmax": mx}
            )
    return {
        "voltage_limits_pu": [low, high],
        "all_steps_converged": len(results.get("steps", [])) > 0
        and all(s.get("converged") for s in results["steps"]),
        "voltage_compliant": len(violations) == 0,
        "violations": violations,
    }


def compare_remote(baseline: dict, optimized: dict, scenario: dict) -> dict:
    a, b = baseline["steps"], optimized["steps"]
    if (
        len(a) != 48
        or len(b) != 48
        or any(
            x.get("step") != i or y.get("step") != i
            for i, (x, y) in enumerate(zip(a, b, strict=True), 1)
        )
    ):
        raise ValueError("QSTS comparados deben contener los mismos 48 pasos")
    rows = []
    for x, y in zip(a, b, strict=True):
        rows.append(
            {
                "step": int(x["step"]),
                "baseline_total_kw": x.get("total_kw"),
                "optimized_total_kw": y.get("total_kw"),
                "delta_total_kw": (float(y["total_kw"]) - float(x["total_kw"]))
                if x.get("total_kw") is not None and y.get("total_kw") is not None
                else None,
                "baseline_vmin_pu": x.get("min_voltage_pu"),
                "optimized_vmin_pu": y.get("min_voltage_pu"),
                "optimized_vmax_pu": y.get("max_voltage_pu"),
            }
        )
    power_deltas = [abs(r["delta_total_kw"]) for r in rows if r["delta_total_kw"] is not None]
    return {
        "steps": rows,
        "baseline_check": check_electrical(baseline, scenario),
        "optimized_check": check_electrical(optimized, scenario),
        "network_response_different": bool(power_deltas) and max(power_deltas) > 1e-4,
        "max_abs_delta_kw": max(power_deltas, default=None),
        "scope": "CUSTOM_DSS_QSTS_AGGREGATED_NETWORK_RESPONSE",
        "device_telemetry_verified": False,
        "warning": (
            "El servicio OpenDSS devuelve respuesta agregada; no expone telemetria "
            "independiente de Storage ni confirma el alineamiento temporal exacto de LoadShape. "
            "La factibilidad electrica se refiere al alimentador modelado, no a una bateria real."
        ),
    }


class CoupledRunner:
    def __init__(self, *, remote, monitor, manager, orchestrator):
        self.remote = remote
        self.monitor = monitor
        self.manager = manager
        self.orchestrator = orchestrator

    async def _upload_model(self, package: Path) -> str:
        """Sube ZIP + valida master en worker; no modificar el OpenDSS original."""
        await self.monitor.require_healthy()
        response = await self.remote.checked(
            "POST",
            "/models/upload",
            files={"file": (package.name, package.read_bytes(), "application/zip")},
        )
        model_id = response.get("model_id") if isinstance(response, dict) else None
        if not model_id or not isinstance(model_id, str) or not model_id.replace("-", "").isalnum():
            raise UpstreamError("CUSTOM_MODEL_UPLOAD", "El servidor no devolvio model_id válido")
        checked = await self.remote.checked(
            "POST",
            f"/models/custom/{model_id}/validate",
            params={"master": "master.dss"},
        )
        if not isinstance(checked, dict) or checked.get("valid") is not True:
            raise UpstreamError("CUSTOM_MODEL_INVALID", "El worker no validó master.dss")
        return f"custom:{model_id}:master.dss"

    async def _remote_qsts(
        self, job_id: str, profile: dict, scenario: dict, objective: dict, package: Path, label: str
    ) -> dict:
        topology = await self._upload_model(package)
        remote_scenario = {
            **scenario,
            "topology": topology,
            "derived_from_run_id": job_id,
            "model_label": label,
        }
        child_id = self.manager.store.create(remote_scenario, objective, origin_kind="SIMULATED")
        await self.orchestrator.execute(child_id, remote_scenario, profile)
        child = self.manager.store.get_run(child_id)
        if not child or child["status"] != "VERIFIED" or not child.get("result"):
            raise UpstreamError(
                "CUSTOM_QSTS_FAILED", f"Fallo escenario {label}; registro {child_id}"
            )
        return {"run_id": child_id, "result": child["result"], "topology": topology}

    async def execute(
        self,
        job_id: str,
        profile: dict,
        scenario: dict,
        objective: dict,
        *,
        resource_scale: float = 100.0,
        max_passes: int = 2,
        events: list[dict] | None = None,
    ) -> None:
        """Controlador secuencial con limitación de BESS y reevaluación de seguridad."""
        store = self.manager.store
        run_dir = ROOT / "results/runs" / job_id
        run_dir.mkdir(parents=True, exist_ok=True)
        try:
            await self.monitor.require_healthy()
            context, operational_graph = resolve_constraints(
                profile, scenario, load_events() if events is None else events
            )
            graph_manifest = save_operational_graph(operational_graph, run_dir)
            store.event(job_id, "OPERATIONAL_TKG_USED", graph_manifest)
            working = copy.deepcopy(scenario)
            working["battery"]["nameplate_kw"] = max(
                float(scenario["battery"]["max_charge_kw"]),
                float(scenario["battery"]["max_discharge_kw"]),
            )
            # FASE 1: resolver IEEE13 con PV y carga flexible fijas, BESS en reposo.
            baseline_zip = run_dir / "model_baseline.zip"
            baseline_manifest = build_dispatch_zip(
                profile,
                working,
                None,
                baseline_zip,
                variant="baseline",
                resource_scale=resource_scale,
            )
            store.update(job_id, "COUPLED_BASELINE_QSTS")
            base = await self._remote_qsts(
                job_id, profile, working, objective, baseline_zip, "baseline"
            )
            # FASE 2: consultar estados operativos RDF y optimizar (NO usar cifras futuras QSTS
            # como si fueran mediciones de Ausgrid; solo se usa el contexto estructurado).
            store.update(job_id, "COUPLED_OPTIMIZING")
            solution = optimize(profile, working, objective, context)
            solution["comparison"] = compare_dispatch(profile, working, objective, solution)
            store.save_dispatch(job_id, solution)
            build_graph(store.get_run(job_id), profile, solution)
            passed = None
            attempts = []
            for attempt in range(1, max_passes + 1):
                await self.monitor.require_healthy()
                store.update(job_id, "COUPLED_DISPATCH_QSTS")
                candidate_zip = run_dir / f"model_dispatch_pass_{attempt}.zip"
                candidate_manifest = build_dispatch_zip(
                    profile,
                    working,
                    solution,
                    candidate_zip,
                    variant="optimized",
                    resource_scale=resource_scale,
                )
                dispatched = await self._remote_qsts(
                    job_id, profile, working, objective, candidate_zip, f"optimized_{attempt}"
                )
                electrical = compare_remote(base["result"], dispatched["result"], working)
                attempts.append(
                    {
                        "attempt": attempt,
                        "candidate_run_id": dispatched["run_id"],
                        "candidate_manifest": candidate_manifest,
                        "voltage_violations": len(electrical["optimized_check"]["violations"]),
                        "objective_total": solution["objective"]["total"],
                    }
                )
                passed = (solution, dispatched, electrical, candidate_manifest)
                if electrical["optimized_check"]["voltage_compliant"]:
                    break
                if attempt < max_passes:
                    # Conservador: reoptimizar con menor capacidad BESS, sin fingir gradientes.
                    working = copy.deepcopy(working)
                    working["battery"]["max_charge_kw"] *= 0.5
                    working["battery"]["max_discharge_kw"] *= 0.5
                    solution = optimize(profile, working, objective, context)
                    solution["comparison"] = compare_dispatch(profile, working, objective, solution)
                    store.save_dispatch(job_id, solution)
                    build_graph(store.get_run(job_id), profile, solution)
            assert passed is not None
            solution, dispatched, electrical, candidate_manifest = passed
            report = {
                "baseline_run_id": base["run_id"],
                "optimized_run_id": dispatched["run_id"],
                "source_kind": "SIMULATED",
                "status": "VOLTAGE_COMPLIANT_AGGREGATED_QSTS"
                if electrical["optimized_check"]["voltage_compliant"]
                else "VOLTAGE_VIOLATIONS_AGGREGATED_QSTS",
                "model_has_storage_pv": True,
                "validation_scope": "AGGREGATED_FEEDER_QSTS_ONLY",
                "device_telemetry_verified": False,
                "resource_scale": resource_scale,
                "baseline_package": baseline_manifest,
                "optimized_package": candidate_manifest,
                "operational_tkg": graph_manifest,
                "electrical": electrical,
                "attempts": attempts,
                "objective": solution["objective"],
                "energy_metrics": solution["metrics"],
            }
            from backend.app.services.coupled_tkg import build_coupled_graph

            build_coupled_graph(store.get_run(job_id), operational_graph, report)
            store.save_coupled_result(job_id, report)
            export_run(store.get_run(job_id))
            await self.manager.broadcast(
                job_id, {"type": "coupled_completed", "status": report["status"]}
            )
        except Exception as exc:
            code = exc.code if isinstance(exc, UpstreamError) else type(exc).__name__
            store.update(job_id, "ERROR", error=f"{code}: {exc}")
            store.event(job_id, "COUPLED_ERROR", {"code": code, "message": str(exc)})
            await self.manager.broadcast(
                job_id, {"type": "error", "code": code, "message": str(exc)}
            )
