"""Comparación B0 temporal relacional vs B1 RDF estático vs B2 TKG RDF."""

from __future__ import annotations

import sqlite3
import time

from rdflib import RDF, XSD, Graph, Literal, Namespace

NS = Namespace("https://example.org/experiment/")
T = Namespace("https://example.org/derms/tkg#")


def compare_baselines() -> dict:
    states = [
        ("2026-11-20T00:00:00+00:00", "2026-11-20T17:00:00+00:00", "AVAILABLE"),
        ("2026-11-20T17:00:00+00:00", None, "UNAVAILABLE"),
    ]
    query_times = [
        "2026-11-20T16:30:00+00:00",
        "2026-11-20T17:00:00+00:00",
        "2026-11-20T17:30:00+00:00",
    ]
    sqlite = sqlite3.connect(":memory:")
    sqlite.execute("CREATE TABLE relation(valid_from TEXT, valid_to TEXT, state TEXT)")
    sqlite.executemany("INSERT INTO relation VALUES (?,?,?)", states)
    static = Graph()
    static.add((NS.Battery, NS.state, NS.UNAVAILABLE))
    temporal = Graph()
    for i, (start, stop, state) in enumerate(states):
        uri = NS[f"relation{i}"]
        temporal.add((uri, RDF.type, T.StateAssertion))
        temporal.add((uri, T.object, NS[state]))
        temporal.add((uri, T.validFrom, Literal(start, datatype=XSD.dateTime)))
        if stop:
            temporal.add((uri, T.validTo, Literal(stop, datatype=XSD.dateTime)))
    latencies = {"B0": [], "B1": [], "B2": []}
    answers = {}
    for at in query_times:
        t0 = time.perf_counter_ns()
        b0 = sqlite.execute(
            "SELECT state FROM relation WHERE valid_from <= ? AND (valid_to IS NULL OR valid_to > ?)",
            (at, at),
        ).fetchone()[0]
        latencies["B0"].append((time.perf_counter_ns() - t0) / 1000)
        t1 = time.perf_counter_ns()
        b1 = str(static.value(NS.Battery, NS.state)).split("/")[-1]
        latencies["B1"].append((time.perf_counter_ns() - t1) / 1000)
        t2 = time.perf_counter_ns()
        states_asof = []
        for node in temporal.subjects(RDF.type, T.StateAssertion):
            start = str(temporal.value(node, T.validFrom))
            end = temporal.value(node, T.validTo)
            if start <= at and (end is None or str(end) > at):
                states_asof.append(str(temporal.value(node, T.object)).split("/")[-1])
        b2 = states_asof[0] if len(states_asof) == 1 else "AMBIGUOUS"
        latencies["B2"].append((time.perf_counter_ns() - t2) / 1000)
        answers[at] = {"B0": b0, "B1": b1, "B2": b2, "B0_equals_B2": b0 == b2}
    return {
        "scenario": "SIMULATED_BESS_AVAILABILITY",
        "query_times": query_times,
        "answers": answers,
        "latency_microseconds_single_run": latencies,
        "caution": "Microbenchmark ilustrativo sin estadísticas; B0 y B2 temporalmente correctos en esta prueba. B1 carece de historial.",
    }
