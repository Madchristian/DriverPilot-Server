"""Interne Admin-JSON-API: Token-Pflicht, Faelle, Entwurf/Freigabe, Einladungen, Zugaenge, Audit."""

from __future__ import annotations

from starlette.testclient import TestClient

from conftest import KEY_A, RESULT_CONTENT
from driverpilot_server.admin import create_admin_app


def test_token_and_actor_required(h):
    app = create_admin_app(h.service)
    bare = TestClient(app, base_url="http://server:8141")
    assert bare.get("/admin-api/overview").status_code == 401
    assert bare.get("/admin-api/overview", headers={"Authorization": "Bearer falsch", "X-DP-Actor": "x"}).status_code == 401
    assert bare.get("/admin-api/overview", headers={"Authorization": "Bearer SYNTHETIC-admin-api-token"}).status_code == 401
    assert bare.get("/admin-api/overview", headers={"Authorization": "Bearer SYNTHETIC-admin-api-token", "X-DP-Actor": "<script>"}).status_code == 401
    assert h.admin.get("/admin-api/overview").status_code == 200


def test_empty_token_locks_everything(tmp_path, contract):
    from conftest import Harness

    h = Harness(tmp_path, contract, DP_ADMIN_API_TOKEN="")
    try:
        assert h.admin.get("/admin-api/overview").status_code == 401
    finally:
        h.close()


def test_overview_and_case_detail(h):
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    overview = h.admin.get("/admin-api/overview").json()
    assert overview["stats"]["open"] == 1 and overview["cases"][0]["id"] == case_id
    detail = h.admin.get(f"/admin-api/cases/{case_id}").json()
    assert detail["case"]["status"] == "awaiting_review" and "report_bytes" not in detail["case"]
    assert detail["report"]["symptom"]["category"] == "wow_crash"
    assert detail["draft"]["saved"] is False and detail["can"]["release"] is True
    assert h.admin.get("/admin-api/cases/00000000-0000-4000-8000-000000000000").status_code == 404
    assert h.admin.get("/admin-api/cases/kaputt").status_code == 404


def test_draft_validate_save_release(h):
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    bad = dict(RESULT_CONTENT, facts=[{"id": "x", "text": "Ohne Beleg", "references": [{"kind": "finding", "id": "f-999"}]}])
    check = h.admin.post(f"/admin-api/cases/{case_id}/validate", json={"content": bad}).json()
    assert any("f-999" in p for p in check["problems"])
    refused = h.admin.post(f"/admin-api/cases/{case_id}/draft", json={"content": bad})
    assert refused.status_code == 409 and "f-999" in refused.json()["error"]
    saved = h.admin.post(f"/admin-api/cases/{case_id}/draft", json={"content": RESULT_CONTENT, "ai_assisted": False})
    assert saved.status_code == 200
    draft_id = saved.json()["draft_id"]
    version = h.admin.get(f"/admin-api/cases/{case_id}").json()["case"]["version"]
    released = h.admin.post(f"/admin-api/cases/{case_id}/release", json={"draft_id": draft_id, "version": version})
    assert released.status_code == 200 and released.json()["revision"] == 1
    assert h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token)).json()["status"] == "released"
    stale = h.admin.post(f"/admin-api/cases/{case_id}/release", json={"draft_id": draft_id, "version": version})
    assert stale.status_code == 409
    assert h.admin.post(f"/admin-api/cases/{case_id}/release", json={"draft_id": draft_id}).status_code == 400
    detail = h.admin.get(f"/admin-api/cases/{case_id}").json()
    assert detail["results"][0]["body"]["revision"] == 1
    assert detail["draft"]["saved"] is False and detail["draft"]["base_revision"] == 1
    assert detail["draft"]["content"]["summary"] == RESULT_CONTENT["summary"]
    assert h.admin.post(f"/admin-api/cases/{case_id}/delete", json={}).status_code == 200
    assert h.admin.get(f"/admin-api/cases/{case_id}").status_code == 404


def test_invitations_clients_audit(h):
    created = h.admin.post("/admin-api/invitations", json={"label": "Max", "days": 3, "max_uses": 2})
    assert created.status_code == 201
    code = created.json()["code"]
    listing = h.admin.get("/admin-api/invitations").json()["invitations"]
    assert listing[0]["label"] == "Max" and "code" not in listing[0] and code not in str(listing)
    assert h.api.post("/api/v1/pairings/redeem", json={"invitation_code": code}).status_code == 201
    assert h.admin.get("/admin-api/invitations").json()["invitations"][0]["uses"] == 1
    clients = h.admin.get("/admin-api/clients").json()["clients"]
    assert len(clients) == 1 and "token_hash" in clients[0]
    assert h.admin.post(f"/admin-api/clients/{clients[0]['id']}/revoke", json={}).status_code == 200
    assert h.admin.post(f"/admin-api/clients/{clients[0]['id']}/revoke", json={}).status_code == 409
    assert h.admin.post(f"/admin-api/invitations/{created.json()['id']}/revoke", json={}).status_code == 200
    operations = [e["operation"] for e in h.admin.get("/admin-api/audit").json()["entries"]]
    assert {"invitation.create", "pairing.redeem", "client.revoke", "invitation.revoke"} <= set(operations)
    assert all(e["actor"] != "" for e in h.admin.get("/admin-api/audit").json()["entries"])
    assert h.admin.post("/admin-api/invitations", json={"days": "x"}).status_code == 400
