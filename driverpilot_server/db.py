"""SQLite-Zugriff. Eine Verbindung, serialisiert ueber ein Lock.

Der Pilot laeuft auf einem Raspberry Pi 4 mit wenigen Anfragen; SQLite im
WAL-Modus mit secure_delete reicht. Loeschungen ueberschreiben freigegebene
Seiten (secure_delete) und die Bereinigung erzwingt einen WAL-Checkpoint, damit
geloeschte Berichte nicht in der WAL-Datei liegen bleiben.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Einladungen: Default einmalig (max_uses=1). Mehrfachnutzung ist eine serverinterne
-- Option fuer die Weitergabe an mehrere Freunde; jede Einloesung erzeugt einen eigenen Client.
CREATE TABLE IF NOT EXISTS invitations (
    id TEXT PRIMARY KEY,
    code_hash TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    max_uses INTEGER NOT NULL DEFAULT 1,
    uses INTEGER NOT NULL DEFAULT 0,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    invitation_id TEXT,
    label TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id),
    scan_id TEXT NOT NULL,
    report_sha256 TEXT NOT NULL,
    report_bytes BLOB NOT NULL,
    received_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL,
    status_reason TEXT,
    external_ai_allowed INTEGER NOT NULL,
    previous_case_id TEXT,
    symptom_category TEXT NOT NULL,
    app_version TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    current_revision INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS cases_client ON cases(client_id);
CREATE INDEX IF NOT EXISTS cases_status ON cases(status);

-- Nur Zeitpunkte, kein Inhalt: fuer Tageslimits auch nach Loeschung eines Falls.
CREATE TABLE IF NOT EXISTS case_ledger (
    case_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    received_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS idempotency (
    client_id TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    key TEXT NOT NULL,
    body_sha256 TEXT NOT NULL,
    case_id TEXT,
    feedback_id TEXT,
    retired INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    PRIMARY KEY (client_id, endpoint, key)
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    status TEXT NOT NULL,            -- queued | leased | done | cancelled | failed
    created_at TEXT NOT NULL,
    lease_until TEXT,
    worker_id TEXT,
    case_version INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status);

CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    origin TEXT NOT NULL,            -- ai | human
    author TEXT NOT NULL,            -- Adaptername oder Adminbenutzer
    body_json TEXT NOT NULL,
    model TEXT,
    prompt_version TEXT,
    run_id TEXT,
    superseded INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS drafts_case ON drafts(case_id);

CREATE TABLE IF NOT EXISTS results (
    case_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    released_at TEXT NOT NULL,
    released_by TEXT NOT NULL,
    body_json TEXT NOT NULL,
    PRIMARY KEY (case_id, revision)
);

CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    result_revision INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    note TEXT,
    received_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS feedback_case ON feedback(case_id);

CREATE TABLE IF NOT EXISTS ai_runs (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    adapter TEXT NOT NULL,
    model TEXT,
    prompt_version TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    outcome TEXT,                    -- draft | transient_error | rejected | timeout | unknown | cancelled
    usage_json TEXT
);

CREATE TABLE IF NOT EXISTS ai_budget (
    day TEXT PRIMARY KEY,
    reserved INTEGER NOT NULL DEFAULT 0
);

-- Metadaten-Audit: Akteur, Operation, Fall, Ergebnis. Kein Berichtinhalt.
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    operation TEXT NOT NULL,
    case_id TEXT,
    outcome TEXT NOT NULL,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS audit_at ON audit(at);
"""


class Database:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.lock = threading.RLock()
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(self.path.parent, 0o700)
            except OSError:
                pass
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        if str(self.path) != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA secure_delete = ON")
        self.conn.execute("PRAGMA synchronous = FULL")
        self.conn.execute("PRAGMA busy_timeout = 5000")
        self.conn.executescript(SCHEMA)
        if str(self.path) != ":memory:":
            try:
                os.chmod(self.path, 0o600)
            except OSError:
                pass

    @contextmanager
    def transaction(self):
        """IMMEDIATE-Transaktion; Rollback bei jeder Ausnahme."""
        with self.lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield self.conn
            except BaseException:
                self.conn.execute("ROLLBACK")
                raise
            else:
                self.conn.execute("COMMIT")

    def query(self, sql: str, params=()) -> list[sqlite3.Row]:
        with self.lock:
            return self.conn.execute(sql, params).fetchall()

    def one(self, sql: str, params=()) -> sqlite3.Row | None:
        with self.lock:
            return self.conn.execute(sql, params).fetchone()

    def checkpoint(self) -> None:
        with self.lock:
            try:
                self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.OperationalError:
                pass

    def healthy(self) -> bool:
        try:
            with self.lock:
                self.conn.execute("SELECT 1 FROM meta LIMIT 1").fetchall()
                self.conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES ('readiness_probe', datetime('now'))")
            return True
        except sqlite3.Error:
            return False

    def close(self) -> None:
        with self.lock:
            self.conn.close()
