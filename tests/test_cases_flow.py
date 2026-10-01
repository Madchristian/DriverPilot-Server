"""Idempotenz, Zustandsautomat, Freigabe, ETag, Rueckmeldung, Loeschung und Ablauf."""

from __future__ import annotations

import json
import threading
from datetime import timedelta

from conftest import KEY_A, KEY_B, KEY_C, REPORT_BYTES, RESULT_CONTENT


def test_idempotent_replay_conflict_and_retired(h):
    token = h.pair()["access_token"]
    first = h.create_case(token, KEY_A)
    second = h.create_case(token, KEY_A)
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    assert h.service.db.one("SELECT COUNT(*) FROM cases")[0] == 1

    other_bytes = REPORT_BYTES.replace(b"20 Minuten", b"21 Minuten")
    conflict = h.create_case(token, KEY_A, other_bytes)
    assert (conflict.status_code, conflict.json()["error"]["code"]) == (409, "idempotency_key_conflict")

    case_id = first.json()["case_id"]
    assert h.api.delete(f"/api/v1/cases/{case_id}", headers=h.headers(token)).status_code == 204
    assert h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token)).status_code == 404
    assert h.api.delete(f"/api/v1/cases/{case_id}", headers=h.headers(token)).status_code == 204
    retired = h.create_case(token, KEY_A)
    assert (retired.status_code, retired.json()["error"]["code"]) == (409, "request_retired")
    assert h.service.db.one("SELECT COUNT(*) FROM cases")[0] == 0
    # Derselbe Bericht mit neuem Key ist ein neuer Fall.
    assert h.create_case(token, KEY_B).status_code == 202


def test_parallel_uploads_create_exactly_one_case_and_job(tmp_path, contract):
    from conftest import Harness

    h = Harness(tmp_path, contract, DP_AI_PROVIDER="test")
    try:
        token = h.pair()["access_token"]
        results = []

        def upload():
            results.append(h.create_case(token, KEY_A).status_code)

        threads = [threading.Thread(target=upload) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert results == [202] * 8
        assert h.service.db.one("SELECT COUNT(*) FROM cases")[0] == 1
        assert h.service.db.one("SELECT COUNT(*) FROM jobs")[0] == 1
    finally:
        h.close()


def test_replay_after_release_shows_current_state(h):
    token = h.pair()["access_token"]
    case_id = h.create_case(token, KEY_A).json()["case_id"]
    h.release(case_id)
    replay = h.create_case(token, KEY_A).json()
    assert replay["status"] == "released" and replay["poll_after_seconds"] is None
    assert h.service.db.one("SELECT COUNT(*) FROM jobs")[0] == 0  # keine neue Analyse


def test_etag_and_304(h):
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    first = h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token))
    etag = first.headers["etag"]
    assert etag.startswith('"') and len(etag) <= 130
    headers = h.headers(token)
    headers["If-None-Match"] = etag
    cached = h.api.get(f"/api/v1/cases/{case_id}", headers=headers)
    assert cached.status_code == 304 and cached.content == b"" and cached.headers["etag"] == etag
    h.release(case_id)
    changed = h.api.get(f"/api/v1/cases/{case_id}", headers=headers)
    assert changed.status_code == 200 and changed.headers["etag"] != etag


def test_release_revisions_and_feedback(h, contract):
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    # Rueckmeldung vor Freigabe: Revisionkonflikt.
    early = h.api.post(f"/api/v1/cases/{case_id}/feedback", json={"outcome": "unchanged", "note": None, "result_revision": 1}, headers=h.headers(token, KEY_B))
    assert (early.status_code, early.json()["error"]["code"]) == (409, "result_revision_conflict")

    assert h.release(case_id) == 1
    body = {"outcome": "improved", "note": "Besser.", "result_revision": 1}
    first = h.api.post(f"/api/v1/cases/{case_id}/feedback", json=body, headers=h.headers(token, KEY_B))
    assert first.status_code == 201
    replay = h.api.post(f"/api/v1/cases/{case_id}/feedback", json=body, headers=h.headers(token, KEY_B))
    assert replay.status_code == 201 and replay.json() == first.json()
    conflict = h.api.post(f"/api/v1/cases/{case_id}/feedback", json={**body, "note": "Anders."}, headers=h.headers(token, KEY_B))
    assert conflict.json()["error"]["code"] == "idempotency_key_conflict"
    assert h.service.db.one("SELECT COUNT(*) FROM feedback")[0] == 1

    # Neue Revision: alte Rueckmeldung bleibt, Revision 1 ist nicht mehr adressierbar.
    content = dict(RESULT_CONTENT, summary="Zweite Revision.")
    assert h.release(case_id, content) == 2
    case = h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token)).json()
    assert case["result"]["revision"] == 2 and case["result"]["summary"] == "Zweite Revision."
    old = h.api.post(f"/api/v1/cases/{case_id}/feedback", json={**body, "result_revision": 1}, headers=h.headers(token, KEY_C))
    assert old.json()["error"]["code"] == "result_revision_conflict"
    # Revision 1 bleibt unveraendert gespeichert.
    stored = json.loads(h.service.db.one("SELECT body_json FROM results WHERE case_id = ? AND revision = 1", (case_id,))["body_json"])
    assert stored["summary"] == RESULT_CONTENT["summary"]

    # Hoechstens zehn Rueckmeldungen je Fall.
    for i in range(9):
        key = f"bbbbbbbb-0000-4000-8000-00000000000{i}"
        assert h.api.post(f"/api/v1/cases/{case_id}/feedback", json={**body, "result_revision": 2, "note": f"n{i}"}, headers=h.headers(token, key)).status_code == 201
    limit = h.api.post(f"/api/v1/cases/{case_id}/feedback", json={**body, "result_revision": 2, "note": "zu viel"}, headers=h.headers(token, "cccccccc-0000-4000-8000-000000000000"))
    assert (limit.status_code, limit.json()["error"]["code"]) == (409, "feedback_limit_reached")


def test_release_requires_valid_result_and_version(h):
    from driverpilot_server.service import AdminError

    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    case = h.service._case(case_id)
    bad = dict(RESULT_CONTENT, facts=[{"id": "x", "text": "Ohne Beleg", "references": [{"kind": "finding", "id": "f-999"}]}])
    try:
        h.service.save_draft(case_id, bad, "tester", False)
        raise AssertionError("ungueltiger Entwurf wurde gespeichert")
    except AdminError as exc:
        assert "f-999" in str(exc)
    draft_id = h.service.save_draft(case_id, RESULT_CONTENT, "tester", False)
    try:
        h.service.release(case_id, draft_id, case["version"] + 5, "tester")
        raise AssertionError("Freigabe trotz falscher Version")
    except AdminError as exc:
        assert "zwischenzeitlich" in str(exc)
    assert h.service.release(case_id, draft_id, case["version"], "tester") == 1
    try:  # derselbe Entwurf ist nach Freigabe verbraucht
        h.service.release(case_id, draft_id, case["version"] + 1, "tester")
        raise AssertionError("Entwurf zweimal freigegeben")
    except AdminError:
        pass


def test_retention_expiry_and_cleanup(h):
    token = h.pair()["access_token"]
    case_id = h.create_case(token, KEY_A).json()["case_id"]
    h.release(case_id)
    h.api.post(f"/api/v1/cases/{case_id}/feedback", json={"outcome": "not_tried", "note": None, "result_revision": 1}, headers=h.headers(token, KEY_B))
    h.clock.fixed += timedelta(days=7)  # exakt expires_at: ab jetzt gesperrt
    assert h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token)).status_code == 404
    assert h.create_case(token, KEY_A).json()["error"]["code"] == "request_retired"
    assert h.service.case_detail(case_id) is None
    assert h.service.db.one("SELECT COUNT(*) FROM cases")[0] == 1  # physisch noch da ...
    removed = h.service.cleanup()
    assert removed["cases"] == 1
    for table in ("cases", "results", "feedback", "drafts", "jobs"):
        assert h.service.db.one(f"SELECT COUNT(*) FROM {table}")[0] == 0, table
    assert h.service.db.one("SELECT retired FROM idempotency WHERE key = ?", (KEY_A,))["retired"] == 1
    assert h.create_case(token, KEY_A).json()["error"]["code"] == "request_retired"
    # Tombstone verschwindet mit dem Ablauf des Zugangs.
    h.clock.fixed += timedelta(days=30)
    h.service.cleanup()
    assert h.service.db.one("SELECT COUNT(*) FROM idempotency")[0] == 0


def test_delete_purges_everything_and_cancels_jobs(h_ai):
    h = h_ai
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    assert h.service._case(case_id)["status"] == "queued"
    assert h.service.db.one("SELECT status FROM jobs")["status"] == "queued"
    assert h.api.delete(f"/api/v1/cases/{case_id}", headers=h.headers(token)).status_code == 204
    assert h.service.db.one("SELECT COUNT(*) FROM jobs")[0] == 0
    assert h.service.db.one("SELECT COUNT(*) FROM cases")[0] == 0
    audit = [row["operation"] for row in h.service.audit_entries()]
    assert "case.delete" in audit and "case.create" in audit
    for row in h.service.audit_entries():
        assert "Schlachtzug" not in (row["detail"] or "")  # kein Berichtsinhalt im Audit
