"""Persistencia transaccional, con last_good estable e independiente de active_run."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.app.settings import ROOT


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def digest(data: object) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path or ROOT / "data/runtime/derms.sqlite"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(
                (ROOT / "backend/app/persistence/schema.sql").read_text(encoding="utf8")
            )

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def create(self, scenario: dict, objective: dict, *, origin_kind: str = "SIMULATED") -> str:
        run_id = str(uuid4())
        now = utc_now()
        with self.connect() as db:
            db.execute(
                "INSERT INTO runs(run_id,created_at,updated_at,status,scenario_json,scenario_sha256,objective_json,origin_kind) VALUES (?,?,?,?,?,?,?,?)",
                (
                    run_id,
                    now,
                    now,
                    "PENDING",
                    json.dumps(scenario),
                    digest(scenario),
                    json.dumps(objective),
                    origin_kind,
                ),
            )
            db.execute("INSERT OR REPLACE INTO meta VALUES ('active_run',?)", (run_id,))
        return run_id

    def update(
        self, run_id: str, status: str, *, session_id: str | None = None, error: str | None = None
    ) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET status=?,updated_at=?,session_id=COALESCE(?,session_id),error=? WHERE run_id=?",
                (status, utc_now(), session_id, error, run_id),
            )

    def event(self, run_id: str, kind: str, data: dict) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(run_id,recorded_at,event_type,data_json) VALUES(?,?,?,?)",
                (run_id, utc_now(), kind, json.dumps(data)),
            )

    def step(self, run_id: str, row: dict) -> None:
        index = int(row["step"])
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO steps(run_id,step,data_json) VALUES(?,?,?)",
                (run_id, index, json.dumps(row)),
            )

    def commit_verified(self, run_id: str, result: dict) -> None:
        """Realizar commit de resultados validados y puntero confirmado en UNA transacción."""
        with self.connect() as db:
            record = db.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if not record or record["status"] == "ERROR":
                raise ValueError("La corrida no puede confirmarse")
            for step in result["steps"]:
                db.execute(
                    "INSERT OR REPLACE INTO steps(run_id,step,data_json) VALUES(?,?,?)",
                    (run_id, int(step["step"]), json.dumps(step)),
                )
            db.execute(
                "UPDATE runs SET status='VERIFIED',remote_verification='remote_qsts_baseline_verified',updated_at=?,result_json=? WHERE run_id=?",
                (utc_now(), json.dumps(result), run_id),
            )
            db.execute("INSERT OR REPLACE INTO meta VALUES ('last_good_run',?)", (run_id,))
            db.execute("INSERT OR REPLACE INTO meta VALUES ('active_run',?)", (run_id,))

    def commit_snapshot(self, run_id: str, result: dict) -> None:
        """Confirma resultado eléctrico snapshot solo tras validar REST/convergencia."""
        with self.connect() as db:
            current = db.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if not current or current["status"] == "ERROR":
                raise ValueError("La corrida snapshot no puede confirmarse")
            db.execute(
                "UPDATE runs SET status='SNAPSHOT_VERIFIED', "
                "remote_verification='remote_snapshot_reference_verified', "
                "updated_at=?,result_json=? WHERE run_id=?",
                (utc_now(), json.dumps(result), run_id),
            )
            db.execute("INSERT OR REPLACE INTO meta VALUES ('last_good_run',?)", (run_id,))
            db.execute("INSERT OR REPLACE INTO meta VALUES ('active_run',?)", (run_id,))

    def save_coupled_result(self, run_id: str, report: dict) -> None:
        """Confirma el ciclo conjunto; el resultado reporta explícitamente violaciones."""
        with self.connect() as db:
            row = db.execute("SELECT status FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if row is None or row["status"] == "ERROR":
                raise ValueError("Corrida conjunta no confirmable")
            db.execute(
                "UPDATE runs SET status='COUPLED_COMPLETED', updated_at=?, "
                "remote_verification='custom_dss_aggregated_qsts', result_json=? WHERE run_id=?",
                (utc_now(), json.dumps(report), run_id),
            )
            db.execute("INSERT OR REPLACE INTO meta VALUES ('last_good_run',?)", (run_id,))
            db.execute("INSERT OR REPLACE INTO meta VALUES ('active_run',?)", (run_id,))

    def save_dispatch(self, run_id: str, dispatch: dict) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE runs SET dispatch_json=?,updated_at=? WHERE run_id=?",
                (json.dumps(dispatch), utc_now(), run_id),
            )

    def get_meta(self, name: str) -> str | None:
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key=?", (name,)).fetchone()
        return row["value"] if row else None

    def get_run(self, run_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
            if row is None:
                return None
            data = dict(row)
            steps = db.execute(
                "SELECT data_json FROM steps WHERE run_id=? ORDER BY step", (run_id,)
            ).fetchall()
        for key in ("scenario_json", "objective_json", "result_json", "dispatch_json"):
            if data[key]:
                data[key[:-5] if key.endswith("_json") else key] = json.loads(data.pop(key))
            else:
                data.pop(key)
        data["steps"] = [json.loads(s[0]) for s in steps]
        return data

    def list_runs(self, limit: int = 30) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT run_id,session_id,created_at,status,origin_kind,remote_verification FROM runs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(x) for x in rows]

    def events(self, run_id: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT recorded_at,event_type,data_json FROM events WHERE run_id=? ORDER BY event_id",
                (run_id,),
            ).fetchall()
        return [{"recorded_at": x[0], "type": x[1], "data": json.loads(x[2])} for x in rows]
