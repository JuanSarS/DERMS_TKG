PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS runs (
 run_id TEXT PRIMARY KEY,
 session_id TEXT,
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 status TEXT NOT NULL,
 scenario_json TEXT NOT NULL,
 scenario_sha256 TEXT NOT NULL,
 objective_json TEXT,
 origin_kind TEXT NOT NULL,
 result_json TEXT,
 dispatch_json TEXT,
 error TEXT,
 remote_verification TEXT NOT NULL DEFAULT 'NOT_VALIDATED'
);
CREATE TABLE IF NOT EXISTS steps (
 run_id TEXT NOT NULL REFERENCES runs(run_id),
 step INTEGER NOT NULL,
 data_json TEXT NOT NULL,
 PRIMARY KEY (run_id, step)
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (
 event_id INTEGER PRIMARY KEY AUTOINCREMENT,
 run_id TEXT NOT NULL REFERENCES runs(run_id),
 recorded_at TEXT NOT NULL,
 event_type TEXT NOT NULL,
 data_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_run ON events(run_id, recorded_at);
