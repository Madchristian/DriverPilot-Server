"""Jedes Fixture des Vertrags gegen den laufenden Server: Positivfaelle werden angenommen,
Negativfaelle scheitern mit genau dem erwarteten Status und Code."""

from __future__ import annotations

import json

import pytest

from conftest import FIXTURES, KEY_A, KEY_B, KEY_C, REPORT_BYTES, REPORT_SHA256, RESULT_CONTENT, SCENARIO

CASE_INVALID = sorted(k for k in SCENARIO["invalid"] if k.startswith("case-create-request/"))
FEEDBACK_INVALID = sorted(k for k in SCENARIO["invalid"] if k.startswith("feedback-request/"))
RESULT_INVALID = sorted(k for k in SCENARIO["invalid"] if k.startswith("result/"))


def test_capabilities_matches_schema(h, contract):
    response = h.api.get("/api/v1/capabilities")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert contract.violations("capabilities", response.json()) == []
    assert response.json()["privacy_notice"]["version"] == SCENARIO["privacy_notice_version"]
    assert response.json()["external_ai_offered"] is False


@pytest.mark.parametrize("name", ["wow-crash.json", "manual-minimal.json"])
def test_valid_reports_are_accepted(h, contract, name):
    token = h.pair()["access_token"]
    body = (FIXTURES / "valid/case-create-request" / name).read_bytes()
    if name == "manual-minimal.json":
        # Das Fixture verweist auf den Szenario-Fall; hier ist der Vorgaenger der eigene wow-crash-Fall.
        previous = h.create_case(token, KEY_C).json()["case_id"]
        body = body.replace(b"5f0c2a7e-3b1d-4c8a-9e21-7a4d0b6c1f02", previous.encode())
    response = h.create_case(token, KEY_A, body)
    assert response.status_code == 202, response.text
    accepted = response.json()
    assert contract.violations("case-accepted", accepted) == []
    assert accepted["status"] == "awaiting_review"  # Adapter none: kein Providerrequest
    assert accepted["poll_after_seconds"] == 30
    if name == "wow-crash.json":
        assert accepted["report_sha256"] == REPORT_SHA256
    assert accepted["received_at"] == SCENARIO["now"]
    assert accepted["expires_at"] == "2026-10-10T14:06:41Z"


@pytest.mark.parametrize("key", CASE_INVALID)
def test_invalid_reports_are_rejected(h, key):
    expected = SCENARIO["invalid"][key]
    token = h.pair()["access_token"]
    response = h.create_case(token, KEY_A, (FIXTURES / "invalid" / key).read_bytes())
    assert response.status_code == expected["status"], (key, response.text)
    assert response.json()["error"]["code"] == expected["code"], key
    # Abgelehnte Requests binden den Key nicht: derselbe Key nimmt danach einen gueltigen Bericht an.
    assert h.create_case(token, KEY_A, REPORT_BYTES).status_code == 202


def test_error_bodies_match_schema_and_leak_nothing(h, contract):
    token = h.pair()["access_token"]
    body = (FIXTURES / "invalid/case-create-request/text-with-email.json").read_bytes()
    response = h.create_case(token, KEY_A, body)
    error = response.json()
    assert contract.violations("error", error) == []
    assert "@" not in error["error"]["message"]
    assert error["retry_after_seconds"] is None


@pytest.mark.parametrize("key", FEEDBACK_INVALID)
def test_invalid_feedback_is_rejected(h, key):
    expected = SCENARIO["invalid"][key]
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    h.release(case_id)
    response = h.api.post(
        f"/api/v1/cases/{case_id}/feedback", content=(FIXTURES / "invalid" / key).read_bytes(), headers=h.headers(token, KEY_B)
    )
    assert response.status_code == expected["status"], (key, response.text)
    assert response.json()["error"]["code"] == expected["code"]


@pytest.mark.parametrize("name", ["not-tried.json", "unchanged.json"])
def test_valid_feedback_is_stored(h, contract, name):
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    h.release(case_id)
    response = h.api.post(
        f"/api/v1/cases/{case_id}/feedback", content=(FIXTURES / "valid/feedback-request" / name).read_bytes(), headers=h.headers(token, KEY_B)
    )
    assert response.status_code == 201, response.text
    assert contract.violations("feedback-response", response.json()) == []
    assert response.json()["case_id"] == case_id


@pytest.mark.parametrize("key", RESULT_INVALID)
def test_invalid_results_cannot_be_released(h, key):
    """Ergebnis-Negativfixtures: der Server weigert sich, so etwas freizugeben."""
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    bad = json.loads((FIXTURES / "invalid" / key).read_text("utf-8"))
    content = {k: bad.get(k) for k in RESULT_CONTENT}
    problems = h.service.validate_draft(case_id, content)
    assert any("(Hinweis" not in p for p in problems), key


def test_released_case_matches_case_schema(h, contract):
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    h.release(case_id)
    response = h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token))
    assert response.status_code == 200
    body = response.json()
    assert contract.violations("case", body) == []
    assert body["status"] == "released" and body["poll_after_seconds"] is None
    result = body["result"]
    assert contract.violations("result", result) == []
    assert (result["case_id"], result["scan_id"], result["report_sha256"], result["revision"], result["origin"]) == (
        case_id, "c1a9d3e4-52b7-4f60-8a1c-0d9e8f7a6b54", REPORT_SHA256, 1, "human",
    )
    assert "<script>" in json.dumps(result)  # Plaintext bleibt Plaintext, nichts wird gefiltert oder gerendert
