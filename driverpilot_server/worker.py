"""Hintergrundworker und Modelladapter.

Adapter `none`: es gibt keinen Worker-Lauf, alle Faelle werden manuell bearbeitet.
Adapter `test`: synthetischer, reproduzierbarer Entwurf ohne Netzwerk. Er ist in
jedem Text als TESTADAPTER gekennzeichnet und ersetzt keinen echten Providerlauf.

Ein echter Anbieter wird erst nach Christians Freigabe (Anbieter, Datenregion,
Budget) ergaenzt; die Schnittstelle ist `Adapter.analyze(report) -> AdapterResult`.
Der Berichtstext ist dabei untrusted data und darf nie als Anweisung an das
Modell gelten.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
from dataclasses import dataclass, field

from .service import Service

log = logging.getLogger("driverpilot.worker")


class AdapterTransientError(Exception):
    """Vorlaeufiger Fehler (Netz, 429, 5xx): darf einmal wiederholt werden."""


class AdapterRejected(Exception):
    """Antwort unbrauchbar (Schema, Laenge): kein Neuversuch."""


@dataclass
class AdapterResult:
    content: dict
    model: str | None = None
    prompt_version: str | None = None
    usage: dict = field(default_factory=dict)


class TestAdapter:
    """Synthetischer Adapter. DP_TEST_ADAPTER_MODE: ok | transient | timeout | invalid."""

    name = "test"
    model = "TESTADAPTER"
    prompt_version = "test-1"

    def __init__(self, mode: str | None = None, delay: float = 0.0):
        self.mode = mode or os.environ.get("DP_TEST_ADAPTER_MODE", "ok")
        self.delay = delay

    def analyze(self, report: dict) -> AdapterResult:
        if self.delay:
            import time

            time.sleep(self.delay)
        if self.mode == "transient":
            raise AdapterTransientError("synthetischer vorlaeufiger Fehler")
        if self.mode == "invalid":
            return AdapterResult({"summary": "", "facts": "kaputt"}, self.model, self.prompt_version)
        facts = []
        for finding in report["findings"][:5]:
            facts.append(
                {
                    "id": f"fact-{finding['id']}",
                    "text": (
                        f"TESTADAPTER: Quelle {finding['source']} meldete Ereignis {finding['event_id']} "
                        f"{finding['count']}-mal ({finding['severity']})."
                    ),
                    "references": [{"kind": "finding", "id": finding["id"]}]
                    + ([{"kind": "device", "id": finding["device_ref"]}] if finding["device_ref"] else []),
                }
            )
        if not facts:
            facts.append(
                {
                    "id": "fact-symptom",
                    "text": f"TESTADAPTER: Es wurden keine Ereignisgruppen uebermittelt; Symptomkategorie {report['symptom']['category']}.",
                    "references": [{"kind": "report_field", "pointer": "/symptom/category"}],
                }
            )
        content = {
            "summary": "TESTADAPTER (synthetisch): Dieser Entwurf stammt aus dem Testadapter und enthaelt keine echte Analyse.",
            "facts": facts,
            "hypotheses": [
                {
                    "text": "TESTADAPTER: Platzhalter-Hypothese ohne Aussagekraft.",
                    "proven": False,
                    "fact_refs": [facts[0]["id"]],
                }
            ],
            "next_steps": [
                {
                    "title": "TESTADAPTER: Platzhalter-Schritt",
                    "rationale": "Dient nur dem Test des Freigabewegs.",
                    "instructions": "Nichts tun. Dieser Schritt stammt aus dem Testadapter.",
                    "risk_class": "read_only",
                    "required_privileges": "none",
                    "expected_outcome": "Keine Aenderung.",
                    "rollback": None,
                    "abort_condition": None,
                }
            ],
            "open_questions": [],
            "warnings": ["TESTADAPTER: Kein echtes Ergebnis."],
            "sources": [],
        }
        return AdapterResult(content, self.model, self.prompt_version, {"input_tokens": 0, "output_tokens": 0})


def build_adapter(provider: str, **kwargs):
    if provider == "none":
        return None
    if provider == "test":
        return TestAdapter(**kwargs)
    raise ValueError(f"unbekannter Adapter {provider}")


class Worker:
    def __init__(self, service: Service, adapter, poll_interval: float = 5.0):
        self.service = service
        self.adapter = adapter
        self.poll_interval = poll_interval
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}"
        self._stop = asyncio.Event()

    def stop(self) -> None:
        self._stop.set()

    async def run_once(self) -> bool:
        """Bearbeitet hoechstens einen Auftrag. True, wenn einer bearbeitet wurde."""
        if self.adapter is None:
            return False
        leased = self.service.lease_job(self.worker_id)
        if leased is None:
            return False
        job, report_bytes = leased
        import json

        report = json.loads(report_bytes.decode("utf-8"))
        if not self.service.reserve_ai_budget():
            self.service.fail_job(job, None, "budget_exhausted", transient=False)
            return True
        run_id = self.service.record_ai_run(job, self.adapter.name, getattr(self.adapter, "model", None), getattr(self.adapter, "prompt_version", None))
        timeout = self.service.settings.ai_timeout_seconds
        try:
            result: AdapterResult = await asyncio.wait_for(asyncio.to_thread(self.adapter.analyze, report), timeout=timeout)
        except asyncio.TimeoutError:
            # Ausgang beim Anbieter unbekannt: nicht blind erneut abrechnen.
            self.service.fail_job(job, run_id, "outcome_unknown", transient=False)
            return True
        except AdapterTransientError:
            self.service.fail_job(job, run_id, "provider_unavailable", transient=True)
            return True
        except AdapterRejected:
            self.service.fail_job(job, run_id, "output_rejected", transient=False)
            return True
        except Exception:
            log.exception("Adapterfehler job=%s", job["id"])
            self.service.fail_job(job, run_id, "provider_unavailable", transient=True)
            return True
        problems = [p for p in self.service.validate_draft(job["case_id"], result.content) if "(Hinweis" not in p]
        if problems:
            log.warning("Entwurf abgelehnt job=%s: %s", job["id"], "; ".join(problems[:3]))
            self.service.fail_job(job, run_id, "output_rejected", transient=False)
            return True
        self.service.complete_job(job, run_id, result.content, self.adapter.name, result.model, result.prompt_version, result.usage)
        return True

    async def run(self) -> None:
        log.info("Worker gestartet (adapter=%s)", getattr(self.adapter, "name", "none"))
        while not self._stop.is_set():
            try:
                busy = await self.run_once()
            except Exception:
                log.exception("Workerlauf fehlgeschlagen")
                busy = False
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=0.2 if busy else self.poll_interval)
            except asyncio.TimeoutError:
                pass


async def cleanup_loop(service: Service, interval_seconds: int, stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            removed = await asyncio.to_thread(service.cleanup)
            if any(removed.values()):
                log.info("Bereinigung: %s", removed)
        except Exception:
            log.exception("Bereinigung fehlgeschlagen")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass
