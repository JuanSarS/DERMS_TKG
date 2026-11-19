"""Consulta temporal RDF con SPARQL SELECT y controles de tiempo de conocimiento."""

from datetime import datetime, timezone

from rdflib import XSD, Literal, Namespace

from backend.app.services.rdf_store import load_turtle
from backend.app.settings import ROOT

TKG = Namespace("https://example.org/derms/tkg#")


def query_asof(run_id: str, at: datetime, known_at: datetime | None = None) -> list[dict]:
    if at.tzinfo is None:
        raise ValueError("Se requiere timezone para as-of")
    path = ROOT / "results/runs" / run_id / "derms_graph.ttl"
    graph = load_turtle(path)
    at = at.astimezone(timezone.utc)
    known_at = (known_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    query = """
    PREFIX tkg: <https://example.org/derms/tkg#>
    SELECT ?assertion ?object ?batteryKw ?socKwh ?sourceKind ?recordedAt WHERE {
      ?assertion a tkg:StateAssertion ; tkg:validFrom ?start ; tkg:validTo ?end ;
          tkg:recordedAt ?recordedAt ; tkg:object ?object ;
          tkg:batteryKw ?batteryKw ; tkg:socKwh ?socKwh ; tkg:sourceKind ?sourceKind .
      FILTER (?start <= ?target && ?end > ?target && ?recordedAt <= ?known)
    } ORDER BY ?assertion LIMIT 100
    """
    return [
        {
            "assertion": str(r.assertion),
            "state": str(r.object).rsplit("/", 1)[-1],
            "battery_kw": float(r.batteryKw),
            "soc_kwh": float(r.socKwh),
            "source_kind": str(r.sourceKind),
            "recorded_at": str(r.recordedAt),
        }
        for r in graph.query(
            query,
            initBindings={
                "target": Literal(at.isoformat(), datatype=XSD.dateTime),
                "known": Literal(known_at.isoformat(), datatype=XSD.dateTime),
            },
        )
    ]


def safe_select(run_id: str, query: str) -> dict:
    upper = " ".join(query.upper().split())
    if not upper.startswith(("SELECT ", "PREFIX ")) or any(
        word in upper
        for word in ("INSERT", "DELETE", "LOAD ", "SERVICE ", "CLEAR", "DROP ", "CREATE ", "UPDATE")
    ):
        raise ValueError("Solo consultas SPARQL SELECT locales; no SERVICE ni escritura")
    if "SELECT " not in upper or "CONSTRUCT " in upper or "DESCRIBE " in upper or "ASK " in upper:
        raise ValueError("Se exige SELECT")
    path = (ROOT / "results/runs" / run_id / "derms_graph.ttl").resolve()
    if not path.is_relative_to((ROOT / "results/runs").resolve()):
        raise ValueError("run_id fuera de la carpeta permitida")
    graph = load_turtle(path)
    result = graph.query(query)
    rows = [
        [str(value) if value is not None else None for value in row]
        for _, row in zip(range(100), result)
    ]
    return {"columns": [str(v) for v in result.vars], "rows": rows, "row_limit": 100}
