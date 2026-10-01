"""Worker, Testadapter, Budget, Lease, spaete Antworten und Admin-Uebergaenge."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from conftest import KEY_A, KEY_B, MINIMAL_BYTES, RESULT_CONTENT
from driverpilot_server.service import AdminError


def run(coro):
    return asyncio.run(coro)


def test_manual_consent_never_creates_job(h_ai):
    h = h_ai
    token = h.pair()["access_token"]
    accepted = h.create_case(token, KEY_A, MINIMAL_BYTES).json()  # external_ai_allowed=false
    assert accepted["status"] == "awaiting_review"
    assert h.service.db.one("SELECT COUNT(*) FROM jobs")[0] == 0
    assert run(h.worker().run_once()) is False
    assert h.service.db.one("SELECT COUNT(*) FROM ai_runs")[0] == 0


def test_provider_none_never_creates_job_even_with_consent(h):
    token = h.pair()["access_token"]
    assert h.create_case(token).json()["status"] == "awaiting_review"
    assert h.service.db.one("SELECT COUNT(*) FROM jobs")[0] == 0
    assert h.api.get("/api/v1/capabilities").json()["external_ai_offered"] is False


def test_ai_draft_then_release(h_ai):
    h = h_ai
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    assert h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token)).json()["status"] == "queued"
    assert run(h.worker().run_once()) is True
    case = h.service._case(case_id)
    assert case["status"] == "awaiting_review" and case["attempts"] == 1
    view = h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token)).json()
    assert view["result"] is None  # Client sieht nie den Entwurf
    detail = h.service.case_detail(case_id)
    draft = detail["current_draft"]
    assert draft["origin"] == "ai" and "TESTADAPTER" in draft["body_json"]
    assert detail["runs"][0]["outcome"] == "draft"
    revision = h.service.release(case_id, draft["id"], case["version"], "tester")
    assert revision == 1
    result = h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token)).json()["result"]
    assert result["origin"] == "ai_assisted_human_reviewed"
    assert h.service.ai_budget_used() == 1


def test_transient_error_retries_once_then_fails(h_ai):
    h = h_ai
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    worker = h.worker(mode="transient")
    assert run(worker.run_once())
    assert h.service._case(case_id)["status"] == "queued"
    assert run(worker.run_once())
    case = h.service._case(case_id)
    assert (case["status"], case["status_reason"], case["attempts"]) == ("analysis_failed", "provider_unavailable", 2)
    view = h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token)).json()
    assert view["status_reason"] == "provider_unavailable" and view["poll_after_seconds"] is None
    assert run(worker.run_once()) is False  # kein automatischer dritter Versuch
    # Admin: Neuversuch ist ausdruecklich und budgetiert; danach uebernimmt er manuell.
    h.service.retry(case_id, case["version"], "tester")
    assert h.service._case(case_id)["status"] == "queued"
    assert run(h.worker(mode="ok").run_once())
    assert h.service._case(case_id)["status"] == "awaiting_review"


def test_invalid_output_is_rejected(h_ai):
    h = h_ai
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    assert run(h.worker(mode="invalid").run_once())
    case = h.service._case(case_id)
    assert (case["status"], case["status_reason"]) == ("analysis_failed", "output_rejected")
    assert h.service.db.one("SELECT COUNT(*) FROM drafts")[0] == 0
    h.service.take_over(case_id, case["version"], "tester")
    assert h.service._case(case_id)["status"] == "awaiting_review"


def test_budget_exhausted(tmp_path, contract):
    from conftest import Harness

    h = Harness(tmp_path, contract, DP_AI_PROVIDER="test", DP_AI_DAILY_CALLS=1)
    try:
        token = h.pair()["access_token"]
        first = h.create_case(token, KEY_A).json()["case_id"]
        second = h.create_case(token, KEY_B).json()["case_id"]
        worker = h.worker()
        assert run(worker.run_once()) and run(worker.run_once())
        assert h.service._case(first)["status"] == "awaiting_review"
        case = h.service._case(second)
        assert (case["status"], case["status_reason"]) == ("analysis_failed", "budget_exhausted")
        assert h.service.db.one("SELECT COUNT(*) FROM ai_runs")[0] == 1  # kein Providerlauf ohne Budget
    finally:
        h.close()


def test_timeout_is_outcome_unknown_without_retry(h_ai):
    h = h_ai
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    assert run(h.worker(delay=2.0).run_once())  # Timeout ist 1 s
    case = h.service._case(case_id)
    assert (case["status"], case["status_reason"]) == ("analysis_failed", "outcome_unknown")
    assert h.service.db.one("SELECT status FROM jobs")["status"] == "failed"


def test_late_worker_answer_after_delete_or_take_over(h_ai):
    h = h_ai
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    job, _ = h.service.lease_job("w1")
    run_id = h.service.record_ai_run(job, "test", "m", "p")
    assert h.api.delete(f"/api/v1/cases/{case_id}", headers=h.headers(token)).status_code == 204
    assert h.service.complete_job(job, run_id, RESULT_CONTENT, "test", "m", "p", {}) is False
    assert h.service.db.one("SELECT COUNT(*) FROM drafts")[0] == 0
    assert h.service.fail_job(job, run_id, "provider_unavailable", True) == "cancelled"

    # Worker haengt: Lease laeuft ab, Admin uebernimmt, danach kommt die Antwort doch noch.
    case_id = h.create_case(token, KEY_B).json()["case_id"]
    job, _ = h.service.lease_job("w1")
    case = h.service._case(case_id)
    assert case["status"] == "analyzing"
    for action in (lambda: h.service.release(case_id, "x", case["version"], "tester"), lambda: h.service.take_over(case_id, case["version"], "tester")):
        try:
            action()
            raise AssertionError("Adminaktion aus analyzing")
        except AdminError:
            pass
    h.clock.fixed += timedelta(seconds=h.settings.worker_lease_seconds + 1)
    assert h.service.expire_stale_leases() == 1
    case = h.service._case(case_id)
    h.service.take_over(case_id, case["version"], "tester")
    assert h.service.complete_job(job, h.service.record_ai_run(job, "test", None, None), RESULT_CONTENT, "test", None, None, {}) is False
    assert h.service._case(case_id)["status"] == "awaiting_review"
    assert h.service.db.one("SELECT COUNT(*) FROM drafts")[0] == 0

    # Admin uebernimmt einen wartenden Fall: der Auftrag ist entwertet, der Worker findet nichts.
    case_id = h.create_case(token, "dddddddd-0000-4000-8000-000000000000").json()["case_id"]
    case = h.service._case(case_id)
    h.service.take_over(case_id, case["version"], "tester")
    assert h.service.lease_job("w2") is None


def test_stale_lease_after_restart(h_ai):
    h = h_ai
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    h.service.lease_job("crashed")
    assert h.service.expire_stale_leases() == 0
    h.clock.fixed += timedelta(seconds=h.settings.worker_lease_seconds + 1)
    assert h.service.expire_stale_leases() == 1
    case = h.service._case(case_id)
    assert (case["status"], case["status_reason"]) == ("analysis_failed", "outcome_unknown")


def test_worker_loop_stops(h_ai):
    worker = h_ai.worker()

    async def scenario():
        task = asyncio.create_task(worker.run())
        await asyncio.sleep(0.05)
        worker.stop()
        await asyncio.wait_for(task, timeout=2)

    run(scenario())
