"""Vertragsregeln der Ferndiagnose-API v1 (contract/v1).

Laedt die JSON-Schemas, den Fehlerkatalog und rules.json unveraendert aus dem
Vertragsverzeichnis. Die Pruefreihenfolge fuer POST /cases steht in README.md
des Vertrags (Schritte 5 bis 12) und wird hier genau so umgesetzt.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .config import CONTRACT_DIR, REPORT_SCHEMA_VERSIONS

REPORT_SCHEMA = "case-create-request"
FEEDBACK_SCHEMA = "feedback-request"
PAIRING_SCHEMA = "pairing-redeem-request"
RESULT_SCHEMA = "result"
CASE_SCHEMA = "case"
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

# Feste Meldungen je Fehlercode. Sie geben nie Eingaben wieder.
ERROR_MESSAGES = {
    "invalid_json": "Der Inhalt der Anfrage ist kein gültiges JSON-Objekt.",
    "idempotency_key_required": "Der Anfrage fehlt eine gültige Idempotency-Key-Kennung.",
    "token_invalid": "Der Zugang ist ungültig oder abgelaufen. Bitte Christian um eine neue Einladung bitten.",
    "invitation_invalid": "Die Einladung ist unbekannt, abgelaufen oder bereits eingelöst.",
    "not_found": "Dieser Fall ist nicht vorhanden.",
    "idempotency_key_conflict": "Diese Anfrage wurde bereits mit anderem Inhalt gesendet.",
    "request_retired": "Dieser Fall wurde gelöscht und wird nicht neu angelegt.",
    "result_revision_conflict": "Die Rückmeldung bezieht sich nicht auf die aktuell freigegebene Ergebnisrevision.",
    "feedback_limit_reached": "Für diesen Fall wurden bereits alle möglichen Rückmeldungen gespeichert.",
    "payload_too_large": "Der Bericht ist zu groß.",
    "unsupported_media_type": "Die Anfrage muss als application/json gesendet werden.",
    "unsupported_content_encoding": "Komprimierte Anfragen werden nicht angenommen.",
    "unsupported_schema_version": "Diese Berichtsversion wird vom Server nicht angenommen. Bitte DriverPilot aktualisieren.",
    "schema_violation": "Der Bericht entspricht nicht dem erwarteten Aufbau.",
    "consent_required": "Ohne ausdrückliche Zustimmung wird kein Bericht angenommen.",
    "privacy_notice_outdated": "Der Datenschutzhinweis hat sich geändert. Bitte erneut lesen und zustimmen.",
    "scan_too_old": "Der Scan ist zu alt. Bitte einen neuen Scan durchführen und erneut senden.",
    "clock_skew": "Die Uhr des PCs scheint falsch zu gehen. Bitte Datum und Uhrzeit prüfen.",
    "time_range_invalid": "Die Zeitangaben des Berichts sind nicht stimmig.",
    "reference_invalid": "Die internen Verweise des Berichts sind nicht stimmig.",
    "text_rejected": "Ein Textfeld enthält möglicherweise persönliche Daten, Pfade oder Geheimnisse. Bitte ohne solche Angaben formulieren.",
    "previous_case_not_found": "Der angegebene frühere Fall ist nicht vorhanden.",
    "rate_limited": "Zu viele Anfragen. Bitte später erneut versuchen.",
    "daily_case_limit_reached": "Für heute wurden bereits alle möglichen Fälle gesendet. Bitte morgen erneut versuchen.",
    "internal_error": "Ein unerwarteter Fehler ist aufgetreten.",
    "capacity_exhausted": "Der Dienst nimmt gerade keine neuen Fälle an. Es wurde nichts gespeichert.",
    "service_unavailable": "Der Dienst kann den Fall gerade nicht annehmen. Es wurde nichts gespeichert.",
}


class ContractError(Exception):
    """Ein Request, der nach dem Vertrag abzulehnen ist."""

    def __init__(self, code: str, retry_after: int | None = None):
        super().__init__(code)
        self.code = code
        self.retry_after = retry_after


def parse_time(value: str) -> datetime:
    """RFC-3339-Zeitpunkt in UTC (das Schema erzwingt bereits das Z-Format)."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_strict_json(data: bytes) -> dict:
    """UTF-8 ohne BOM, keine doppelten Schluessel, Wurzel ist ein Objekt."""
    if data.startswith(b"\xef\xbb\xbf"):
        raise ContractError("invalid_json")

    def reject_duplicates(pairs):
        keys = [key for key, _ in pairs]
        if len(keys) != len(set(keys)):
            raise ContractError("invalid_json")
        return dict(pairs)

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise ContractError("invalid_json") from None
    if not isinstance(value, dict):
        raise ContractError("invalid_json")
    return value


def resolve_pointer(document, pointer: str):
    for part in pointer.strip("/").split("/"):
        document = document.get(part) if isinstance(document, dict) else None
    return document


@dataclass(frozen=True)
class TimeLimits:
    max_scan_age_seconds: int
    max_future_skew_seconds: int
    max_observation_window_seconds: int


class Contract:
    def __init__(self, root: Path = CONTRACT_DIR):
        self.root = root
        schema_dir = root / "schemas"
        self.schemas = {
            path.name.removesuffix(".schema.json"): json.loads(path.read_text("utf-8"))
            for path in sorted(schema_dir.glob("*.schema.json"))
        }
        self.base_uri = schema_dir.resolve().as_uri() + "/"
        registry = Registry().with_resources(
            (self.base_uri + f"{name}.schema.json", Resource.from_contents(document))
            for name, document in self.schemas.items()
        )
        self._validators = {
            name: Draft202012Validator({"$ref": self.base_uri + f"{name}.schema.json"}, registry=registry)
            for name in self.schemas
        }
        self.errors = {entry["code"]: entry for entry in json.loads((root / "errors.json").read_text("utf-8"))["errors"]}
        self.rules = json.loads((root / "rules.json").read_text("utf-8"))
        self.states = json.loads((root / "states.json").read_text("utf-8"))
        self.forbidden_text = [
            (entry["id"], re.compile(entry["pattern"], re.IGNORECASE))
            for entry in self.rules["forbidden_text"]["patterns"]
        ]
        self.text_fields = self.rules["forbidden_text"]["applies_to"]
        self.allowed_transitions = {
            (entry["from"], entry["to"], entry["trigger"]) for entry in self.states["transitions"]
        }
        missing = set(ERROR_MESSAGES) ^ set(self.errors)
        if missing:
            raise RuntimeError(f"Fehlerkatalog und Meldungen weichen ab: {sorted(missing)}")

    # --- Schema -----------------------------------------------------------

    def violations(self, name: str, instance) -> list[str]:
        return [
            f"{'/'.join(map(str, error.absolute_path)) or '<root>'}: {error.message[:200]}"
            for error in self._validators[name].iter_errors(instance)
        ]

    def is_valid(self, name: str, instance) -> bool:
        return not self.violations(name, instance)

    def status_for(self, code: str) -> int:
        return self.errors[code]["status"]

    # --- Annahme eines Berichts: Schritte 6 bis 12 ---------------------------

    def check_report_schema(self, report: dict) -> None:
        """Schritte 6 bis 8: Version, Zustimmung, uebrige Schemapruefung."""
        if report.get("schema_version") not in REPORT_SCHEMA_VERSIONS:
            raise ContractError("unsupported_schema_version")
        consent = report.get("consent")
        if not isinstance(consent, dict) or consent.get("upload_approved") is not True:
            raise ContractError("consent_required")
        if self.violations(REPORT_SCHEMA, report):
            raise ContractError("schema_violation")

    def check_report_rules(self, report: dict, now: datetime, limits: TimeLimits, privacy_version: str) -> None:
        """Schritte 9 bis 12 ohne previous_case_id (das prueft der Dienst gegen die Datenbank)."""
        if report["consent"]["privacy_notice_version"] != privacy_version:
            raise ContractError("privacy_notice_outdated")

        scanned = parse_time(report["scanned_at"])
        start, end = parse_time(report["observation_start"]), parse_time(report["observation_end"])
        accepted = parse_time(report["consent"]["accepted_at"])
        occurred_raw = report["symptom"]["occurred_at"]
        occurred = parse_time(occurred_raw) if occurred_raw else None
        findings = [(parse_time(f["first_seen"]), parse_time(f["last_seen"])) for f in report["findings"]]
        moments = [scanned, start, end, accepted, *(moment for pair in findings for moment in pair)]
        if occurred:
            moments.append(occurred)

        if max(moments) > now + timedelta(seconds=limits.max_future_skew_seconds):
            raise ContractError("clock_skew")
        if now - scanned > timedelta(seconds=limits.max_scan_age_seconds):
            raise ContractError("scan_too_old")
        ordered = start <= end <= scanned <= accepted
        window_ok = end - start <= timedelta(seconds=limits.max_observation_window_seconds)
        findings_ok = all(start <= first <= last <= end for first, last in findings)
        occurred_ok = occurred is None or occurred <= scanned
        if not (ordered and window_ok and findings_ok and occurred_ok):
            raise ContractError("time_range_invalid")

        device_ids = [device["id"] for device in report["devices"]]
        finding_ids = [finding["id"] for finding in report["findings"]]
        refs = {finding["device_ref"] for finding in report["findings"]} - {None}
        unique = len(set(device_ids)) == len(device_ids) and len(set(finding_ids)) == len(finding_ids)
        if not unique or not refs <= set(device_ids):
            raise ContractError("reference_invalid")

    def check_text(self, name: str, instance: dict) -> None:
        """Schritt 12: Textmarker. Nennt weder Feld noch Fundstelle."""
        for pointer in self.text_fields.get(name, []):
            value = resolve_pointer(instance, pointer)
            if isinstance(value, str) and any(pattern.search(value) for _, pattern in self.forbidden_text):
                raise ContractError("text_rejected")

    def text_hits(self, text: str) -> list[str]:
        """Fuer die Adminansicht: welche Marker in einem Entwurfstext anschlagen wuerden."""
        return [marker for marker, pattern in self.forbidden_text if pattern.search(text)]

    # --- Ergebnis -------------------------------------------------------------

    def result_problems(self, result: dict, report: dict, max_bytes: int) -> list[str]:
        """Schemapruefung plus Belegpruefung gegen den Bericht; leer = freigebbar."""
        problems = self.violations(RESULT_SCHEMA, result)
        if problems:
            return problems
        known = {
            "finding": {f["id"] for f in report["findings"]},
            "device": {d["id"] for d in report["devices"]},
        }
        fact_ids = [fact["id"] for fact in result["facts"]]
        if len(set(fact_ids)) != len(fact_ids):
            problems.append("facts: ids sind nicht eindeutig")
        for fact in result["facts"]:
            for reference in fact["references"]:
                if reference["kind"] == "report_field":
                    if resolve_pointer(report, reference["pointer"]) is None and not _pointer_exists(report, reference["pointer"]):
                        problems.append(f"facts/{fact['id']}: Zeiger {reference['pointer']} existiert nicht im Bericht")
                elif reference["id"] not in known[reference["kind"]]:
                    problems.append(f"facts/{fact['id']}: unbekanntes {reference['kind']} {reference['id']}")
        for index, hypothesis in enumerate(result["hypotheses"]):
            for ref in set(hypothesis["fact_refs"]) - set(fact_ids):
                problems.append(f"hypotheses/{index}: unbekannter Fakt {ref}")
        size = len(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        if size > max_bytes:
            problems.append(f"Ergebnis ist mit {size} Bytes groesser als {max_bytes}")
        return problems

    def transition_allowed(self, source: str, target: str, trigger: str) -> bool:
        return (source, target, trigger) in self.allowed_transitions


def _pointer_exists(document, pointer: str) -> bool:
    """Ein Zeiger auf ein Feld mit Wert null ist ein gueltiger Beleg (z.B. /hardware/system_model)."""
    for part in pointer.strip("/").split("/"):
        if isinstance(document, dict) and part in document:
            document = document[part]
        elif isinstance(document, list) and part.isdigit() and int(part) < len(document):
            document = document[int(part)]
        else:
            return False
    return True


def is_uuid(value: str | None) -> bool:
    return isinstance(value, str) and bool(UUID_RE.match(value))
