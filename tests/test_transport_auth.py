"""Transportfaelle ohne Datei-Fixture (README Tabelle), Zugang, Falltrennung, Limits."""

from __future__ import annotations

import gzip
from datetime import timedelta

from conftest import KEY_A, KEY_B, REPORT_BYTES, shift_days


def test_oversized_body_with_content_length(h):
    token = h.pair()["access_token"]
    body = REPORT_BYTES + b" " * (262144 - len(REPORT_BYTES) + 1)
    response = h.create_case(token, KEY_A, body)
    assert (response.status_code, response.json()["error"]["code"]) == (413, "payload_too_large")


def test_oversized_body_chunked_without_content_length(h):
    token = h.pair()["access_token"]

    def chunks():
        sent = 0
        while sent < 300000:
            yield b" " * 4096
            sent += 4096

    headers = h.headers(token, KEY_A)
    headers["Transfer-Encoding"] = "chunked"
    response = h.api.post("/api/v1/cases", content=chunks(), headers=headers)
    assert (response.status_code, response.json()["error"]["code"]) == (413, "payload_too_large")


def test_exact_limit_is_accepted_as_bytes(h):
    """Ein Body mit genau 262144 Bytes ist erlaubt (Limit ist inklusiv), 262145 nicht."""
    token = h.pair()["access_token"]
    padding = 262144 - len(REPORT_BYTES)
    body = REPORT_BYTES[:-1] + b" " * padding + b"}"
    assert len(body) == 262144
    assert h.create_case(token, KEY_A, body).status_code == 202
    assert h.create_case(token, KEY_B, body + b" ").status_code == 413


def test_content_encoding_and_media_type(h):
    token = h.pair()["access_token"]
    headers = h.headers(token, KEY_A)
    headers["Content-Encoding"] = "gzip"
    response = h.api.post("/api/v1/cases", content=gzip.compress(REPORT_BYTES), headers=headers)
    assert (response.status_code, response.json()["error"]["code"]) == (415, "unsupported_content_encoding")
    headers = h.headers(token, KEY_A)
    headers["Content-Type"] = "text/plain"
    response = h.api.post("/api/v1/cases", content=REPORT_BYTES, headers=headers)
    assert (response.status_code, response.json()["error"]["code"]) == (415, "unsupported_media_type")
    headers["Content-Type"] = "application/json"
    assert h.api.post("/api/v1/cases", content=REPORT_BYTES, headers=headers).status_code == 202


def test_idempotency_key_required(h):
    token = h.pair()["access_token"]
    response = h.create_case(token, None)
    assert (response.status_code, response.json()["error"]["code"]) == (400, "idempotency_key_required")
    response = h.create_case(token, "NOT-A-UUID")
    assert response.status_code == 400
    response = h.create_case(token, "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee".upper())  # nur Kleinschreibung
    assert response.status_code == 400


def test_token_missing_unknown_revoked_expired(h):
    response = h.api.post("/api/v1/cases", content=REPORT_BYTES, headers={"Content-Type": "application/json", "Idempotency-Key": KEY_A})
    assert (response.status_code, response.json()["error"]["code"]) == (401, "token_invalid")
    assert response.headers["www-authenticate"] == "Bearer"
    assert h.create_case("x" * 43, KEY_A).status_code == 401
    pairing = h.pair()
    token, client_id = pairing["access_token"], pairing["client_id"]
    assert h.create_case(token, KEY_A).status_code == 202
    h.service.revoke_client(client_id, "tester")
    assert h.create_case(token, KEY_B).status_code == 401
    pairing = h.pair()
    token = pairing["access_token"]
    assert h.api.get("/api/v1/capabilities").status_code == 200
    h.clock.fixed += timedelta(days=30, seconds=1)
    assert h.create_case(token, KEY_A).status_code == 401


def test_invitation_single_use_expired_revoked_and_multi_use(h):
    _, code = h.service.create_invitation("einmal", "tester")
    assert h.api.post("/api/v1/pairings/redeem", json={"invitation_code": code}).status_code == 201
    second = h.api.post("/api/v1/pairings/redeem", json={"invitation_code": code})
    assert (second.status_code, second.json()["error"]["code"]) == (401, "invitation_invalid")
    assert h.api.post("/api/v1/pairings/redeem", json={"invitation_code": "A" * 30}).status_code == 401
    assert h.api.post("/api/v1/pairings/redeem", json={"invitation_code": "zu-kurz"}).status_code == 422
    assert h.api.post("/api/v1/pairings/redeem", content=b"{", headers={"Content-Type": "application/json"}).status_code == 400

    _, expired = h.service.create_invitation("alt", "tester", ttl_seconds=60)
    h.clock.fixed += timedelta(seconds=61)
    assert h.api.post("/api/v1/pairings/redeem", json={"invitation_code": expired}).status_code == 401

    invitation_id, multi = h.service.create_invitation("gruppe", "tester", ttl_seconds=86400, max_uses=2)
    assert h.api.post("/api/v1/pairings/redeem", json={"invitation_code": multi}).status_code == 201
    assert h.api.post("/api/v1/pairings/redeem", json={"invitation_code": multi}).status_code == 201
    assert h.api.post("/api/v1/pairings/redeem", json={"invitation_code": multi}).status_code == 401
    revoked_id, revoked = h.service.create_invitation("weg", "tester", max_uses=5)
    h.service.revoke_invitation(revoked_id, "tester")
    assert h.api.post("/api/v1/pairings/redeem", json={"invitation_code": revoked}).status_code == 401


def test_pairing_failures_are_rate_limited_per_ip(h):
    for _ in range(5):
        assert h.api.post("/api/v1/pairings/redeem", json={"invitation_code": "B" * 30}).status_code == 401
    response = h.api.post("/api/v1/pairings/redeem", json={"invitation_code": "B" * 30})
    assert (response.status_code, response.json()["error"]["code"]) == (429, "rate_limited")
    assert int(response.headers["retry-after"]) == response.json()["retry_after_seconds"] >= 1


def test_client_isolation(h, contract):
    a, b = h.pair("A")["access_token"], h.pair("B")["access_token"]
    case_id = h.create_case(a).json()["case_id"]
    own = h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(a))
    assert own.status_code == 200 and "etag" in own.headers

    foreign = h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(b))
    unknown = h.api.get("/api/v1/cases/00000000-0000-4000-8000-000000000000", headers=h.headers(b))
    not_uuid = h.api.get("/api/v1/cases/not-a-uuid", headers=h.headers(b))
    for response in (foreign, unknown, not_uuid):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert "etag" not in response.headers
        assert contract.violations("error", response.json()) == []
    assert foreign.json()["error"] == unknown.json()["error"] == not_uuid.json()["error"]

    assert h.api.delete(f"/api/v1/cases/{case_id}", headers=h.headers(b)).status_code == 204
    assert h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(a)).status_code == 200  # B konnte nichts loeschen
    feedback = h.api.post(f"/api/v1/cases/{case_id}/feedback", json={"outcome": "unchanged", "note": None, "result_revision": 1}, headers=h.headers(b, KEY_B))
    assert feedback.status_code == 404
    # previous_case_id auf fremden Fall: nicht unterscheidbar von unbekannt
    body = REPORT_BYTES.replace(b'"previous_case_id": null', f'"previous_case_id": "{case_id}"'.encode())
    response = h.create_case(b, KEY_B, body)
    assert (response.status_code, response.json()["error"]["code"]) == (422, "previous_case_not_found")
    assert h.create_case(a, KEY_B, body).status_code == 202  # eigener Vorgaenger ist erlaubt


def test_unknown_routes_return_error_object(h):
    for response in (h.api.get("/api/v1/nope"), h.api.post("/api/v1/cases/abc"), h.api.get("/api/v1/")):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
    assert h.api.get("/healthz").text == "ok"
    assert h.api.get("/readyz").status_code == 200


def test_client_rate_limit(h):
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    statuses = [h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token)).status_code for _ in range(31)]
    assert statuses.count(200) == 29 and statuses[-1] == 429


def test_daily_limits_and_capacity(tmp_path, contract):
    from conftest import Harness

    h = Harness(tmp_path, contract, DP_MAX_NEW_CASES_GLOBAL_PER_DAY=7, DP_MAX_OPEN_CASES_GLOBAL=100)
    try:
        token = h.pair()["access_token"]
        keys = [f"aaaaaaaa-0000-4000-8000-00000000000{i}" for i in range(7)]
        for key in keys[:5]:
            assert h.create_case(token, key).status_code == 202
        response = h.create_case(token, keys[5])
        assert (response.status_code, response.json()["error"]["code"]) == (429, "daily_case_limit_reached")
        assert "retry-after" in response.headers
        other = h.pair("other")["access_token"]
        assert h.create_case(other, keys[0]).status_code == 202
        assert h.create_case(other, keys[1]).status_code == 202
        response = h.create_case(other, keys[2])
        assert (response.status_code, response.json()["error"]["code"]) == (503, "capacity_exhausted")
        assert h.service.db.one("SELECT COUNT(*) FROM cases")[0] == 7
        # Loeschen aendert die Tageszaehlung nicht (Ledger bleibt).
        case_id = h.service.list_cases()[0]["id"]
        h.service.admin_delete(case_id, "tester")
        assert h.create_case(other, keys[3]).status_code == 503
        # Naechster Tag (mit frischem Scan): wieder frei.
        h.clock.fixed += timedelta(days=1)
        assert h.create_case(other, keys[4], shift_days(REPORT_BYTES, 1)).status_code == 202
    finally:
        h.close()
