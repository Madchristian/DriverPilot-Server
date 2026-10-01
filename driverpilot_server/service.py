"""Fachlogik: Zugang, Faelle, Idempotenz, Zustandsautomat, Freigabe, Worker, Bereinigung.

Alles hier ist unabhaengig vom HTTP-Rahmen, damit API, Adminansicht, Worker
und Tests dieselben Regeln benutzen. Zeit kommt immer aus `Clock`, damit
Ablauf und Bereinigung mit einer steuerbaren Testuhr geprueft werden koennen.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .config import RESULT_SCHEMA_VERSION, Settings
from .contract import (
    FEEDBACK_SCHEMA,
    Contract,
    ContractError,
    TimeLimits,
    format_time,
    is_uuid,
    parse_strict_json,
    parse_time,
)
from .db import Database

POLL_SECONDS = {"queued": 10, "analyzing": 10, "awaiting_review": 30, "released": None, "analysis_failed": None}
OPEN_STATES = ("queued", "analyzing", "awaiting_review", "analysis_failed")
RESULT_CONTENT_KEYS = ("summary", "facts", "hypotheses", "next_steps", "open_questions", "warnings", "sources")


class Clock:
    def __init__(self):
        self.fixed: datetime | None = None
        self.offset = timedelta(0)

    def now(self) -> datetime:
        if self.fixed is not None:
            return self.fixed
        return datetime.now(timezone.utc).replace(microsecond=0) + self.offset


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class AdminError(Exception):
    """Abgelehnte Adminaktion mit verstaendlicher Begruendung."""

    message: str

    def __str__(self) -> str:
        return self.message


class Service:
    def __init__(self, settings: Settings, contract: Contract, db: Database, clock: Clock | None = None):
        self.settings = settings
        self.contract = contract
        self.db = db
        self.clock = clock or Clock()
        self.secret = settings.load_or_create_secret() if str(db.path) != ":memory:" else b"test-secret"
        self.privacy_notice_text = settings.load_privacy_notice()
        self.limits = TimeLimits(
            settings.max_scan_age_seconds, settings.max_future_skew_seconds, settings.max_observation_window_seconds
        )
        # Wird von main.build auf adapter.available gesetzt (z.B. Codex nur mit Login).
        self.ai_available = lambda: settings.ai_configured
        self.codex_auth = None  # CodexAuth, wenn Adapter codex aktiv ist (fuer die Adminseite)

    def external_ai_offered(self) -> bool:
        return bool(self.settings.ai_configured and self.ai_available())

    # ------------------------------------------------------------------ Hilfen

    def now(self) -> datetime:
        return self.clock.now()

    def now_text(self) -> str:
        return format_time(self.now())

    def audit(self, actor: str, operation: str, case_id: str | None, outcome: str, detail: str | None = None) -> None:
        with self.db.lock:
            self.db.conn.execute(
                "INSERT INTO audit(at, actor, operation, case_id, outcome, detail) VALUES (?,?,?,?,?,?)",
                (self.now_text(), actor, operation, case_id, outcome, detail),
            )

    def capabilities(self) -> dict:
        return {
            "protocol_version": "1.0",
            "report_schema_versions": ["1.0"],
            "result_schema_version": RESULT_SCHEMA_VERSION,
            "max_upload_bytes": self.settings.max_upload_bytes,
            "max_scan_age_seconds": self.settings.max_scan_age_seconds,
            "max_future_skew_seconds": self.settings.max_future_skew_seconds,
            "case_retention_days": self.settings.case_retention_days,
            "privacy_notice": {"version": self.settings.privacy_notice_version, "text": self.privacy_notice_text},
            "external_ai_offered": self.external_ai_offered(),
        }

    # ------------------------------------------------------------------ Zugang

    def create_invitation(self, label: str, created_by: str, ttl_seconds: int | None = None, max_uses: int = 1) -> tuple[str, str]:
        """Legt eine Einladung an und gibt (id, Klartextcode) zurueck. Der Code wird nur hier ausgegeben."""
        if max_uses < 1 or max_uses > 500:
            raise AdminError("max_uses muss zwischen 1 und 500 liegen")
        ttl = ttl_seconds or self.settings.invitation_ttl_seconds
        if ttl < 60 or ttl > 365 * 86400:
            raise AdminError("Gueltigkeit muss zwischen einer Minute und einem Jahr liegen")
        code = secrets.token_urlsafe(24)  # 32 Zeichen base64url, 192 Bit
        invitation_id = new_id()
        now = self.now()
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO invitations(id, code_hash, label, created_by, created_at, expires_at, max_uses, uses) "
                "VALUES (?,?,?,?,?,?,?,0)",
                (invitation_id, sha256_hex(code), label[:80], created_by, format_time(now), format_time(now + timedelta(seconds=ttl)), max_uses),
            )
        self.audit(created_by, "invitation.create", None, "ok", f"invitation={invitation_id} max_uses={max_uses}")
        return invitation_id, code

    def redeem_invitation(self, body: bytes) -> dict:
        """POST /pairings/redeem: verbraucht die Einladung atomar, gibt Clientzugang zurueck."""
        instance = parse_strict_json(body)
        if self.contract.violations("pairing-redeem-request", instance):
            raise ContractError("schema_violation")
        code_hash = sha256_hex(instance["invitation_code"])
        now = self.now()
        token = secrets.token_urlsafe(32)  # 43 Zeichen, 256 Bit
        client_id = new_id()
        expires_at = now + timedelta(days=self.settings.access_token_ttl_days)
        with self.db.transaction() as conn:
            updated = conn.execute(
                "UPDATE invitations SET uses = uses + 1 WHERE code_hash = ? AND revoked_at IS NULL "
                "AND uses < max_uses AND expires_at > ?",
                (code_hash, format_time(now)),
            ).rowcount
            if updated != 1:
                raise ContractError("invitation_invalid")
            invitation = conn.execute("SELECT id, label FROM invitations WHERE code_hash = ?", (code_hash,)).fetchone()
            conn.execute(
                "INSERT INTO clients(id, token_hash, invitation_id, label, created_at, expires_at) VALUES (?,?,?,?,?,?)",
                (client_id, sha256_hex(token), invitation["id"], invitation["label"], format_time(now), format_time(expires_at)),
            )
        self.audit(f"client:{client_id}", "pairing.redeem", None, "ok", f"invitation={invitation['id']}")
        return {"client_id": client_id, "access_token": token, "expires_at": format_time(expires_at)}

    def authenticate(self, token: str | None) -> sqlite3.Row:
        """Bearer-Token -> Client. Fehlend, unbekannt, abgelaufen und widerrufen sind nicht unterscheidbar."""
        if not token or len(token) > 256:
            raise ContractError("token_invalid")
        row = self.db.one("SELECT * FROM clients WHERE token_hash = ?", (sha256_hex(token),))
        if row is None or row["revoked_at"] is not None or parse_time(row["expires_at"]) <= self.now():
            raise ContractError("token_invalid")
        return row

    # ------------------------------------------------------------------ Faelle: Sicht des Clients

    def visible_case(self, client_id: str, case_id: str, conn: sqlite3.Connection | None = None) -> sqlite3.Row | None:
        """Eigener, nicht abgelaufener Fall oder None. Fremd, unbekannt, geloescht, abgelaufen: identisch None."""
        if not is_uuid(case_id):
            return None
        conn = conn or self.db.conn
        with self.db.lock:
            row = conn.execute("SELECT * FROM cases WHERE id = ? AND client_id = ?", (case_id, client_id)).fetchone()
        if row is None or parse_time(row["expires_at"]) <= self.now():
            return None
        return row

    def accepted_response(self, case: sqlite3.Row) -> dict:
        return {
            "case_id": case["id"],
            "status": case["status"],
            "received_at": case["received_at"],
            "expires_at": case["expires_at"],
            "report_sha256": case["report_sha256"],
            "poll_after_seconds": POLL_SECONDS[case["status"]],
        }

    def case_response(self, case: sqlite3.Row) -> dict:
        result = None
        if case["status"] == "released":
            row = self.db.one(
                "SELECT body_json FROM results WHERE case_id = ? AND revision = ?", (case["id"], case["current_revision"])
            )
            result = json.loads(row["body_json"]) if row else None
        return {
            "case_id": case["id"],
            "status": case["status"],
            "status_reason": case["status_reason"] if case["status"] == "analysis_failed" else None,
            "scan_id": case["scan_id"],
            "report_sha256": case["report_sha256"],
            "received_at": case["received_at"],
            "expires_at": case["expires_at"],
            "poll_after_seconds": POLL_SECONDS[case["status"]],
            "result": result,
        }

    def etag(self, case: sqlite3.Row) -> str:
        material = f"{case['id']}|{case['status']}|{case['status_reason']}|{case['current_revision']}|{case['version']}|{case['updated_at']}"
        digest = hmac.new(self.secret, material.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
        return f'"{digest}"'

    def _today_prefix(self) -> str:
        return self.now().strftime("%Y-%m-%d")

    def _idempotency_lookup(self, conn, client_id: str, endpoint: str, key: str) -> sqlite3.Row | None:
        return conn.execute(
            "SELECT * FROM idempotency WHERE client_id = ? AND endpoint = ? AND key = ?", (client_id, endpoint, key)
        ).fetchone()

    def create_case(self, client: sqlite3.Row, idempotency_key: str, body: bytes) -> dict:
        """POST /cases, Schritte 4 bis 14 des Vertrags. Schritte 1 bis 3 prueft die HTTP-Schicht."""
        client_id = client["id"]
        body_hash = sha256_hex(body)

        # Schritt 4: Idempotenz ueber die Body-Bytes.
        with self.db.transaction() as conn:
            replay = self._replay(conn, client_id, "cases", idempotency_key, body_hash)
            if replay is not None:
                return replay

        # Schritte 5 bis 12 (reine Pruefungen ohne Datenbank, ausser previous_case_id).
        report = parse_strict_json(body)
        self.contract.check_report_schema(report)
        self.contract.check_report_rules(report, self.now(), self.limits, self.settings.privacy_notice_version)
        previous = report["previous_case_id"]
        if previous is not None and self.visible_case(client_id, previous) is None:
            raise ContractError("previous_case_not_found")
        self.contract.check_text("case-create-request", report)

        # Schritte 13 und 14 in einer Transaktion.
        now = self.now()
        case_id = new_id()
        ai_allowed = bool(report["consent"]["external_ai_allowed"])
        initial_status = "queued" if ai_allowed and self.external_ai_offered() else "awaiting_review"
        try:
            with self.db.transaction() as conn:
                replay = self._replay(conn, client_id, "cases", idempotency_key, body_hash)
                if replay is not None:
                    return replay
                if previous is not None and self.visible_case(client_id, previous, conn) is None:
                    raise ContractError("previous_case_not_found")
                day = self._today_prefix()
                own_today = conn.execute(
                    "SELECT COUNT(*) FROM case_ledger WHERE client_id = ? AND substr(received_at, 1, 10) = ?", (client_id, day)
                ).fetchone()[0]
                if own_today >= self.settings.max_new_cases_per_client_per_day:
                    raise ContractError("daily_case_limit_reached", retry_after=self._seconds_until_midnight())
                global_today = conn.execute(
                    "SELECT COUNT(*) FROM case_ledger WHERE substr(received_at, 1, 10) = ?", (day,)
                ).fetchone()[0]
                open_cases = conn.execute(
                    "SELECT COUNT(*) FROM cases WHERE status != 'released' AND expires_at > ?", (format_time(now),)
                ).fetchone()[0]
                if global_today >= self.settings.max_new_cases_global_per_day or open_cases >= self.settings.max_open_cases_global:
                    raise ContractError("capacity_exhausted", retry_after=3600)

                expires_at = now + timedelta(days=self.settings.case_retention_days)
                conn.execute(
                    "INSERT INTO cases(id, client_id, scan_id, report_sha256, report_bytes, received_at, expires_at, status, "
                    "status_reason, external_ai_allowed, previous_case_id, symptom_category, app_version, attempts, version, "
                    "current_revision, updated_at) VALUES (?,?,?,?,?,?,?,?,NULL,?,?,?,?,0,1,0,?)",
                    (
                        case_id, client_id, report["scan_id"], body_hash, body, format_time(now), format_time(expires_at),
                        initial_status, int(ai_allowed), previous, report["symptom"]["category"], report["app_version"],
                        format_time(now),
                    ),
                )
                conn.execute(
                    "INSERT INTO case_ledger(case_id, client_id, received_at) VALUES (?,?,?)", (case_id, client_id, format_time(now))
                )
                if initial_status == "queued":
                    self._enqueue(conn, case_id, 1)
                conn.execute(
                    "INSERT INTO idempotency(client_id, endpoint, key, body_sha256, case_id, retired, created_at) VALUES (?,?,?,?,?,0,?)",
                    (client_id, "cases", idempotency_key, body_hash, case_id, format_time(now)),
                )
        except sqlite3.IntegrityError:
            # Paralleler Request mit demselben Key hat gewonnen: dessen Ergebnis liefern.
            with self.db.transaction() as conn:
                replay = self._replay(conn, client_id, "cases", idempotency_key, body_hash)
            if replay is None:
                raise ContractError("service_unavailable", retry_after=30)
            return replay
        except sqlite3.Error:
            raise ContractError("service_unavailable", retry_after=120) from None

        self.audit(f"client:{client_id}", "case.create", case_id, "accepted", f"status={initial_status}")
        return self.accepted_response(self._case(case_id))

    def _replay(self, conn, client_id: str, endpoint: str, key: str, body_hash: str) -> dict | None:
        row = self._idempotency_lookup(conn, client_id, endpoint, key)
        if row is None:
            return None
        if row["retired"]:
            raise ContractError("request_retired")
        if row["body_sha256"] != body_hash:
            raise ContractError("idempotency_key_conflict")
        if endpoint == "cases":
            case = self.visible_case(client_id, row["case_id"], conn)
            if case is None:
                raise ContractError("request_retired")
            return self.accepted_response(case)
        feedback = conn.execute("SELECT * FROM feedback WHERE id = ?", (row["feedback_id"],)).fetchone()
        if feedback is None:
            raise ContractError("request_retired")
        return self._feedback_response(feedback)

    def _seconds_until_midnight(self) -> int:
        now = self.now()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return max(1, int((midnight - now).total_seconds()))

    def _case(self, case_id: str) -> sqlite3.Row:
        return self.db.one("SELECT * FROM cases WHERE id = ?", (case_id,))

    def get_case(self, client: sqlite3.Row, case_id: str) -> tuple[dict, str] | None:
        case = self.visible_case(client["id"], case_id)
        if case is None:
            return None
        return self.case_response(case), self.etag(case)

    def delete_case(self, client: sqlite3.Row, case_id: str) -> None:
        """DELETE /cases/{id}: 204 auch fuer nicht sichtbare IDs. Entwertet laufende Arbeit sofort."""
        with self.db.transaction() as conn:
            case = self.visible_case(client["id"], case_id, conn)
            if case is None:
                return
            self._purge_case(conn, case_id, retire=True)
        self.audit(f"client:{client['id']}", "case.delete", case_id, "ok")

    def _purge_case(self, conn, case_id: str, retire: bool) -> None:
        for table in ("drafts", "results", "feedback", "ai_runs"):
            conn.execute(f"DELETE FROM {table} WHERE case_id = ?", (case_id,))
        conn.execute("UPDATE jobs SET status = 'cancelled', updated_at = ? WHERE case_id = ? AND status IN ('queued','leased')", (self.now_text(), case_id))
        conn.execute("DELETE FROM jobs WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        if retire:
            conn.execute("UPDATE idempotency SET retired = 1 WHERE case_id = ?", (case_id,))
            conn.execute("UPDATE idempotency SET retired = 1 WHERE feedback_id IN (SELECT id FROM feedback WHERE case_id = ?)", (case_id,))
        else:
            conn.execute("DELETE FROM idempotency WHERE case_id = ?", (case_id,))

    def create_feedback(self, client: sqlite3.Row, case_id: str, idempotency_key: str, body: bytes) -> dict:
        client_id = client["id"]
        body_hash = sha256_hex(body)
        with self.db.transaction() as conn:
            if self.visible_case(client_id, case_id, conn) is None:
                raise ContractError("not_found")
            replay = self._replay(conn, client_id, "feedback", idempotency_key, body_hash)
            if replay is not None:
                return replay
        instance = parse_strict_json(body)
        if self.contract.violations(FEEDBACK_SCHEMA, instance):
            raise ContractError("schema_violation")
        self.contract.check_text(FEEDBACK_SCHEMA, instance)
        feedback_id = new_id()
        now_text = self.now_text()
        try:
            with self.db.transaction() as conn:
                case = self.visible_case(client_id, case_id, conn)
                if case is None:
                    raise ContractError("not_found")
                replay = self._replay(conn, client_id, "feedback", idempotency_key, body_hash)
                if replay is not None:
                    return replay
                if case["status"] != "released" or case["current_revision"] != instance["result_revision"]:
                    raise ContractError("result_revision_conflict")
                count = conn.execute("SELECT COUNT(*) FROM feedback WHERE case_id = ?", (case_id,)).fetchone()[0]
                if count >= self.settings.max_feedback_per_case:
                    raise ContractError("feedback_limit_reached")
                conn.execute(
                    "INSERT INTO feedback(id, case_id, result_revision, outcome, note, received_at) VALUES (?,?,?,?,?,?)",
                    (feedback_id, case_id, instance["result_revision"], instance["outcome"], instance["note"], now_text),
                )
                conn.execute(
                    "INSERT INTO idempotency(client_id, endpoint, key, body_sha256, case_id, feedback_id, retired, created_at) "
                    "VALUES (?,?,?,?,?,?,0,?)",
                    (client_id, "feedback", idempotency_key, body_hash, case_id, feedback_id, now_text),
                )
        except sqlite3.IntegrityError:
            with self.db.transaction() as conn:
                replay = self._replay(conn, client_id, "feedback", idempotency_key, body_hash)
            if replay is None:
                raise ContractError("service_unavailable", retry_after=30)
            return replay
        except sqlite3.Error:
            raise ContractError("service_unavailable", retry_after=120) from None
        self.audit(f"client:{client_id}", "feedback.create", case_id, "ok", f"revision={instance['result_revision']} outcome={instance['outcome']}")
        return self._feedback_response(self.db.one("SELECT * FROM feedback WHERE id = ?", (feedback_id,)))

    @staticmethod
    def _feedback_response(feedback: sqlite3.Row) -> dict:
        return {
            "feedback_id": feedback["id"],
            "case_id": feedback["case_id"],
            "result_revision": feedback["result_revision"],
            "received_at": feedback["received_at"],
        }

    # ------------------------------------------------------------------ Arbeitsauftraege

    def _enqueue(self, conn, case_id: str, case_version: int) -> str:
        job_id = new_id()
        conn.execute(
            "INSERT INTO jobs(id, case_id, status, created_at, lease_until, worker_id, case_version, updated_at) "
            "VALUES (?,?,'queued',?,NULL,NULL,?,?)",
            (job_id, case_id, self.now_text(), case_version, self.now_text()),
        )
        return job_id

    def _bump(self, conn, case_id: str, **fields) -> None:
        sets = ", ".join(f"{key} = ?" for key in fields)
        conn.execute(
            f"UPDATE cases SET {sets}, version = version + 1, updated_at = ? WHERE id = ?",
            (*fields.values(), self.now_text(), case_id),
        )

    def reserve_ai_budget(self) -> bool:
        """Reserviert atomar einen Aufruf des Tagesbudgets."""
        day = self._today_prefix()
        with self.db.transaction() as conn:
            conn.execute("INSERT OR IGNORE INTO ai_budget(day, reserved) VALUES (?, 0)", (day,))
            updated = conn.execute(
                "UPDATE ai_budget SET reserved = reserved + 1 WHERE day = ? AND reserved < ?", (day, self.settings.ai_daily_calls)
            ).rowcount
        return updated == 1

    def ai_budget_used(self) -> int:
        row = self.db.one("SELECT reserved FROM ai_budget WHERE day = ?", (self._today_prefix(),))
        return row["reserved"] if row else 0

    def lease_job(self, worker_id: str) -> tuple[sqlite3.Row, bytes] | None:
        """Nimmt den aeltesten offenen Auftrag mit dauerhaftem Lease; Fall -> analyzing."""
        now = self.now()
        with self.db.transaction() as conn:
            job = conn.execute(
                "SELECT j.* FROM jobs j JOIN cases c ON c.id = j.case_id WHERE j.status = 'queued' AND c.status = 'queued' "
                "AND c.expires_at > ? ORDER BY j.created_at LIMIT 1",
                (format_time(now),),
            ).fetchone()
            if job is None:
                return None
            lease_until = format_time(now + timedelta(seconds=self.settings.worker_lease_seconds))
            conn.execute(
                "UPDATE jobs SET status = 'leased', lease_until = ?, worker_id = ?, updated_at = ? WHERE id = ?",
                (lease_until, worker_id, format_time(now), job["id"]),
            )
            conn.execute("UPDATE cases SET attempts = attempts + 1 WHERE id = ?", (job["case_id"],))
            self._bump(conn, job["case_id"], status="analyzing", status_reason=None)
            case = conn.execute("SELECT * FROM cases WHERE id = ?", (job["case_id"],)).fetchone()
            job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job["id"],)).fetchone()
        self.audit(f"worker:{worker_id}", "job.lease", case["id"], "ok", f"attempt={case['attempts']}")
        return job, case["report_bytes"]

    def record_ai_run(self, job: sqlite3.Row, adapter: str, model: str | None, prompt_version: str | None) -> str:
        run_id = new_id()
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO ai_runs(id, case_id, job_id, adapter, model, prompt_version, started_at) VALUES (?,?,?,?,?,?,?)",
                (run_id, job["case_id"], job["id"], adapter, model, prompt_version, self.now_text()),
            )
        return run_id

    def _job_still_mine(self, conn, job: sqlite3.Row) -> bool:
        current = conn.execute("SELECT status, worker_id FROM jobs WHERE id = ?", (job["id"],)).fetchone()
        case = conn.execute("SELECT status FROM cases WHERE id = ?", (job["case_id"],)).fetchone()
        return (
            current is not None
            and current["status"] == "leased"
            and current["worker_id"] == job["worker_id"]
            and case is not None
            and case["status"] == "analyzing"
        )

    def complete_job(self, job: sqlite3.Row, run_id: str, draft: dict, adapter: str, model: str | None, prompt_version: str | None, usage: dict | None) -> bool:
        """Schemagueltiger Entwurf liegt vor -> awaiting_review. False, wenn der Fall inzwischen weg ist."""
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE ai_runs SET finished_at = ?, outcome = 'draft', usage_json = ? WHERE id = ?",
                (self.now_text(), json.dumps(usage or {}), run_id),
            )
            if not self._job_still_mine(conn, job):
                conn.execute("UPDATE ai_runs SET outcome = 'cancelled' WHERE id = ?", (run_id,))
                return False
            conn.execute("UPDATE drafts SET superseded = 1 WHERE case_id = ?", (job["case_id"],))
            conn.execute(
                "INSERT INTO drafts(id, case_id, created_at, origin, author, body_json, model, prompt_version, run_id, superseded) "
                "VALUES (?,?,?,'ai',?,?,?,?,?,0)",
                (new_id(), job["case_id"], self.now_text(), adapter, json.dumps(draft, ensure_ascii=False), model, prompt_version, run_id),
            )
            conn.execute("UPDATE jobs SET status = 'done', updated_at = ? WHERE id = ?", (self.now_text(), job["id"]))
            self._bump(conn, job["case_id"], status="awaiting_review", status_reason=None)
        self.audit(f"worker:{job['worker_id']}", "job.complete", job["case_id"], "draft", f"run={run_id}")
        return True

    def fail_job(self, job: sqlite3.Row, run_id: str | None, reason: str, transient: bool) -> str:
        """Fehler im Lauf. Transient und Versuche uebrig -> zurueck in die Warteschlange, sonst analysis_failed."""
        with self.db.transaction() as conn:
            if run_id:
                conn.execute("UPDATE ai_runs SET finished_at = ?, outcome = ? WHERE id = ?", (self.now_text(), reason, run_id))
            if not self._job_still_mine(conn, job):
                return "cancelled"
            case = conn.execute("SELECT attempts FROM cases WHERE id = ?", (job["case_id"],)).fetchone()
            if transient and case["attempts"] < self.settings.ai_max_attempts:
                conn.execute("UPDATE jobs SET status = 'queued', lease_until = NULL, worker_id = NULL, updated_at = ? WHERE id = ?", (self.now_text(), job["id"]))
                self._bump(conn, job["case_id"], status="queued", status_reason=None)
                outcome = "requeued"
            else:
                conn.execute("UPDATE jobs SET status = 'failed', updated_at = ? WHERE id = ?", (self.now_text(), job["id"]))
                self._bump(conn, job["case_id"], status="analysis_failed", status_reason=reason)
                outcome = "analysis_failed"
        self.audit(f"worker:{job['worker_id']}", "job.fail", job["case_id"], outcome, reason)
        return outcome

    def expire_stale_leases(self) -> int:
        """Leases ohne Antwort (z.B. Neustart mitten im Aufruf): Ausgang unbekannt -> analysis_failed."""
        now_text = self.now_text()
        count = 0
        with self.db.transaction() as conn:
            stale = conn.execute("SELECT * FROM jobs WHERE status = 'leased' AND lease_until < ?", (now_text,)).fetchall()
            for job in stale:
                conn.execute("UPDATE jobs SET status = 'failed', updated_at = ? WHERE id = ?", (now_text, job["id"]))
                case = conn.execute("SELECT status FROM cases WHERE id = ?", (job["case_id"],)).fetchone()
                if case is not None and case["status"] == "analyzing":
                    self._bump(conn, job["case_id"], status="analysis_failed", status_reason="outcome_unknown")
                    count += 1
        if count:
            self.audit("worker", "job.lease_expired", None, "analysis_failed", f"count={count}")
        return count

    # ------------------------------------------------------------------ Adminansicht

    def stats(self) -> dict:
        rows = self.db.query("SELECT status, COUNT(*) AS n FROM cases WHERE expires_at > ? GROUP BY status", (self.now_text(),))
        by_status = {row["status"]: row["n"] for row in rows}
        today = self._today_prefix()
        return {
            "by_status": by_status,
            "open": sum(n for status, n in by_status.items() if status != "released"),
            "today": self.db.one("SELECT COUNT(*) FROM case_ledger WHERE substr(received_at,1,10) = ?", (today,))[0],
            "clients_active": self.db.one("SELECT COUNT(*) FROM clients WHERE revoked_at IS NULL AND expires_at > ?", (self.now_text(),))[0],
            "jobs_queued": self.db.one("SELECT COUNT(*) FROM jobs WHERE status = 'queued'")[0],
            "jobs_leased": self.db.one("SELECT COUNT(*) FROM jobs WHERE status = 'leased'")[0],
            "ai_budget_used": self.ai_budget_used(),
            "ai_budget_total": self.settings.ai_daily_calls,
            "ai_provider": self.settings.ai_provider,
        }

    def list_cases(self) -> list[sqlite3.Row]:
        return self.db.query(
            "SELECT c.id, c.status, c.status_reason, c.received_at, c.expires_at, c.symptom_category, c.app_version, "
            "c.external_ai_allowed, c.attempts, c.current_revision, c.client_id, cl.label AS client_label, "
            "(SELECT COUNT(*) FROM feedback f WHERE f.case_id = c.id) AS feedback_count "
            "FROM cases c JOIN clients cl ON cl.id = c.client_id WHERE c.expires_at > ? ORDER BY c.received_at DESC",
            (self.now_text(),),
        )

    def case_detail(self, case_id: str) -> dict | None:
        if not is_uuid(case_id):
            return None
        case = self._case(case_id)
        if case is None or parse_time(case["expires_at"]) <= self.now():
            return None
        report = json.loads(case["report_bytes"].decode("utf-8"))
        drafts = self.db.query("SELECT * FROM drafts WHERE case_id = ? ORDER BY created_at DESC", (case_id,))
        results = self.db.query("SELECT * FROM results WHERE case_id = ? ORDER BY revision DESC", (case_id,))
        feedback = self.db.query("SELECT * FROM feedback WHERE case_id = ? ORDER BY received_at", (case_id,))
        runs = self.db.query("SELECT * FROM ai_runs WHERE case_id = ? ORDER BY started_at DESC", (case_id,))
        jobs = self.db.query("SELECT * FROM jobs WHERE case_id = ? ORDER BY created_at DESC", (case_id,))
        client = self.db.one("SELECT id, label, created_at, expires_at, revoked_at FROM clients WHERE id = ?", (case["client_id"],))
        return {
            "case": case, "report": report, "drafts": drafts, "results": results, "feedback": feedback,
            "runs": runs, "jobs": jobs, "client": client,
            "current_draft": next((d for d in drafts if not d["superseded"]), None),
        }

    def draft_skeleton(self, report: dict) -> dict:
        """Leerer Entwurf als Vorlage fuer die manuelle Analyse."""
        return {
            "summary": "",
            "facts": [{"id": "fact-1", "text": "", "references": [{"kind": "report_field", "pointer": "/symptom/category"}]}],
            "hypotheses": [],
            "next_steps": [
                {
                    "title": "", "rationale": "", "instructions": "", "risk_class": "read_only",
                    "required_privileges": "none", "expected_outcome": "", "rollback": None, "abort_condition": None,
                }
            ],
            "open_questions": [],
            "warnings": [],
            "sources": [],
        }

    def preview_result(self, case: sqlite3.Row, content: dict, revision: int, ai_assisted: bool) -> dict:
        """Vollstaendiges Ergebnisobjekt, wie es der Client bekaeme."""
        body = {
            "result_schema_version": RESULT_SCHEMA_VERSION,
            "case_id": case["id"],
            "scan_id": case["scan_id"],
            "report_sha256": case["report_sha256"],
            "revision": revision,
            "released_at": self.now_text(),
            "origin": "ai_assisted_human_reviewed" if ai_assisted else "human",
        }
        for key in RESULT_CONTENT_KEYS:
            body[key] = content.get(key)
        return body

    def validate_draft(self, case_id: str, content: dict) -> list[str]:
        case = self._case(case_id)
        if case is None:
            return ["Fall nicht vorhanden"]
        unknown = set(content) - set(RESULT_CONTENT_KEYS)
        if unknown:
            return [f"Unbekannte Felder im Entwurf: {sorted(unknown)}"]
        report = json.loads(case["report_bytes"].decode("utf-8"))
        preview = self.preview_result(case, content, max(1, case["current_revision"] + 1), ai_assisted=False)
        problems = self.contract.result_problems(preview, report, self.settings.max_result_bytes)
        for pointer, value in _iter_strings(content):
            hits = self.contract.text_hits(value)
            if hits:
                problems.append(f"{pointer}: enthaelt Marker {', '.join(hits)} (Hinweis, keine Sperre)")
        return problems

    def save_draft(self, case_id: str, content: dict, author: str, ai_assisted: bool) -> str:
        problems = [p for p in self.validate_draft(case_id, content) if "(Hinweis" not in p]
        if problems:
            raise AdminError("Entwurf nicht gespeichert: " + "; ".join(problems[:5]))
        draft_id = new_id()
        with self.db.transaction() as conn:
            conn.execute("UPDATE drafts SET superseded = 1 WHERE case_id = ?", (case_id,))
            conn.execute(
                "INSERT INTO drafts(id, case_id, created_at, origin, author, body_json, model, prompt_version, run_id, superseded) "
                "VALUES (?,?,?,?,?,?,NULL,NULL,NULL,0)",
                (draft_id, case_id, self.now_text(), "ai" if ai_assisted else "human", author, json.dumps(content, ensure_ascii=False)),
            )
        self.audit(author, "draft.save", case_id, "ok", f"draft={draft_id} ai_assisted={int(ai_assisted)}")
        return draft_id

    def release(self, case_id: str, draft_id: str, expected_version: int, actor: str) -> int:
        """Freigabe einer Revision mit optimistischer Versionspruefung."""
        with self.db.transaction() as conn:
            case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
            if case is None or parse_time(case["expires_at"]) <= self.now():
                raise AdminError("Fall ist nicht (mehr) vorhanden")
            if case["version"] != expected_version:
                raise AdminError("Der Fall wurde zwischenzeitlich geaendert. Bitte Seite neu laden und erneut pruefen.")
            if not self.contract.transition_allowed(case["status"], "released", "admin"):
                raise AdminError(f"Freigabe aus Zustand {case['status']} ist nicht erlaubt; erst uebernehmen.")
            draft = conn.execute("SELECT * FROM drafts WHERE id = ? AND case_id = ? AND superseded = 0", (draft_id, case_id)).fetchone()
            if draft is None:
                raise AdminError("Der Entwurf ist nicht mehr aktuell.")
            content = json.loads(draft["body_json"])
            report = json.loads(case["report_bytes"].decode("utf-8"))
            revision = case["current_revision"] + 1
            body = self.preview_result(case, content, revision, ai_assisted=(draft["origin"] == "ai"))
            problems = self.contract.result_problems(body, report, self.settings.max_result_bytes)
            if problems:
                raise AdminError("Ergebnis verletzt das Schema: " + "; ".join(problems[:5]))
            conn.execute(
                "INSERT INTO results(case_id, revision, released_at, released_by, body_json) VALUES (?,?,?,?,?)",
                (case_id, revision, body["released_at"], actor, json.dumps(body, ensure_ascii=False)),
            )
            conn.execute("UPDATE drafts SET superseded = 1 WHERE case_id = ?", (case_id,))
            conn.execute("UPDATE jobs SET status = 'cancelled', updated_at = ? WHERE case_id = ? AND status IN ('queued','leased')", (self.now_text(), case_id))
            self._bump(conn, case_id, status="released", status_reason=None, current_revision=revision)
        self.audit(actor, "case.release", case_id, "ok", f"revision={revision}")
        return revision

    def take_over(self, case_id: str, expected_version: int, actor: str) -> None:
        """queued/analysis_failed -> awaiting_review; ein offener Auftrag wird entwertet."""
        with self.db.transaction() as conn:
            case = self._admin_case(conn, case_id, expected_version)
            if not self.contract.transition_allowed(case["status"], "awaiting_review", "admin"):
                raise AdminError(f"Uebernahme aus Zustand {case['status']} ist nicht vorgesehen.")
            conn.execute("UPDATE jobs SET status = 'cancelled', updated_at = ? WHERE case_id = ? AND status IN ('queued','leased')", (self.now_text(), case_id))
            self._bump(conn, case_id, status="awaiting_review", status_reason=None)
        self.audit(actor, "case.take_over", case_id, "ok")

    def retry(self, case_id: str, expected_version: int, actor: str) -> None:
        """Ausdruecklicher, budgetierter Neuversuch der Analyse."""
        if not self.external_ai_offered():
            raise AdminError("Kein Modellanbieter verfuegbar (nicht konfiguriert oder nicht angemeldet).")
        with self.db.transaction() as conn:
            case = self._admin_case(conn, case_id, expected_version)
            if not case["external_ai_allowed"]:
                raise AdminError("Der Nutzer hat externer KI nicht zugestimmt.")
            if not self.contract.transition_allowed(case["status"], "queued", "admin"):
                raise AdminError(f"Neuversuch aus Zustand {case['status']} ist nicht erlaubt.")
            conn.execute("UPDATE jobs SET status = 'cancelled', updated_at = ? WHERE case_id = ? AND status IN ('queued','leased')", (self.now_text(), case_id))
            self._enqueue(conn, case_id, case["version"] + 1)
            self._bump(conn, case_id, status="queued", status_reason=None)
        self.audit(actor, "case.retry", case_id, "ok")

    def admin_delete(self, case_id: str, actor: str) -> None:
        with self.db.transaction() as conn:
            if conn.execute("SELECT 1 FROM cases WHERE id = ?", (case_id,)).fetchone() is None:
                raise AdminError("Fall nicht vorhanden")
            self._purge_case(conn, case_id, retire=True)
        self.audit(actor, "case.delete", case_id, "ok")

    def _admin_case(self, conn, case_id: str, expected_version: int) -> sqlite3.Row:
        case = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if case is None or parse_time(case["expires_at"]) <= self.now():
            raise AdminError("Fall ist nicht (mehr) vorhanden")
        if case["version"] != expected_version:
            raise AdminError("Der Fall wurde zwischenzeitlich geaendert. Bitte Seite neu laden.")
        return case

    def list_clients(self) -> list[sqlite3.Row]:
        return self.db.query(
            "SELECT c.*, (SELECT COUNT(*) FROM cases x WHERE x.client_id = c.id) AS case_count FROM clients c ORDER BY created_at DESC"
        )

    def revoke_client(self, client_id: str, actor: str) -> None:
        with self.db.transaction() as conn:
            if conn.execute("UPDATE clients SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL", (self.now_text(), client_id)).rowcount != 1:
                raise AdminError("Client nicht vorhanden oder bereits widerrufen")
        self.audit(actor, "client.revoke", None, "ok", f"client={client_id}")

    def list_invitations(self) -> list[sqlite3.Row]:
        return self.db.query("SELECT * FROM invitations ORDER BY created_at DESC")

    def revoke_invitation(self, invitation_id: str, actor: str) -> None:
        with self.db.transaction() as conn:
            if conn.execute("UPDATE invitations SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL", (self.now_text(), invitation_id)).rowcount != 1:
                raise AdminError("Einladung nicht vorhanden oder bereits widerrufen")
        self.audit(actor, "invitation.revoke", None, "ok", f"invitation={invitation_id}")

    def audit_entries(self, limit: int = 200) -> list[sqlite3.Row]:
        return self.db.query("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))

    # ------------------------------------------------------------------ Bereinigung

    def cleanup(self) -> dict:
        """Physische Bereinigung abgelaufener Faelle, Einladungen, Tombstones und Auditeintraege."""
        now = self.now()
        now_text = format_time(now)
        removed = {"cases": 0, "invitations": 0, "idempotency": 0, "audit": 0, "leases": self.expire_stale_leases()}
        with self.db.transaction() as conn:
            for case in conn.execute("SELECT id FROM cases WHERE expires_at <= ?", (now_text,)).fetchall():
                self._purge_case(conn, case["id"], retire=True)
                removed["cases"] += 1
            removed["invitations"] = conn.execute(
                "DELETE FROM invitations WHERE expires_at <= ? AND (uses >= max_uses OR expires_at <= ?)", (now_text, now_text)
            ).rowcount
            # Tombstones leben bis zum Ablauf des Clientzugangs.
            removed["idempotency"] = conn.execute(
                "DELETE FROM idempotency WHERE client_id IN (SELECT id FROM clients WHERE expires_at <= ? OR revoked_at IS NOT NULL)", (now_text,)
            ).rowcount
            conn.execute(
                "DELETE FROM case_ledger WHERE received_at <= ?", (format_time(now - timedelta(days=2)),)
            )
            removed["audit"] = conn.execute(
                "DELETE FROM audit WHERE at <= ?", (format_time(now - timedelta(days=self.settings.audit_retention_days)),)
            ).rowcount
            conn.execute("DELETE FROM ai_budget WHERE day < ?", ((now - timedelta(days=2)).strftime("%Y-%m-%d"),))
        self.db.checkpoint()
        if removed["cases"]:
            self.audit("cleanup", "case.expire", None, "ok", f"count={removed['cases']}")
        return removed


def _iter_strings(value, pointer: str = ""):
    if isinstance(value, str):
        yield pointer or "/", value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_strings(item, f"{pointer}/{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _iter_strings(item, f"{pointer}/{index}")
