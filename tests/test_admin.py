"""Adminansicht: Identitaet nur vom Proxy, CSRF, Entwurf/Freigabe ueber Formulare."""

from __future__ import annotations

import json
import re

from starlette.testclient import TestClient

from conftest import KEY_A, RESULT_CONTENT, Harness
from driverpilot_server.admin import create_admin_app


def csrf_from(html: str) -> str:
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def test_dev_user_pages_render(h):
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    for path in ("/", f"/cases/{case_id}", "/invitations", "/clients", "/audit"):
        response = h.admin.get(path)
        assert response.status_code == 200, path
        assert "no-store" in response.headers["cache-control"]
    page = h.admin.get(f"/cases/{case_id}").text
    assert "Schlachtzug" in page and "&lt;script&gt;" not in page
    assert h.admin.get("/cases/00000000-0000-4000-8000-000000000000").status_code == 404


def test_csrf_required_and_fetch_site_checked(h):
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    page = h.admin.get(f"/cases/{case_id}")
    csrf = csrf_from(page.text)
    no_token = h.admin.post(f"/cases/{case_id}/take-over", data={"version": "1"})
    assert no_token.status_code == 403
    cross = h.admin.post(f"/cases/{case_id}/delete", data={"csrf": csrf}, headers={"Sec-Fetch-Site": "cross-site"})
    assert cross.status_code == 403
    assert h.service._case(case_id) is not None
    wrong_origin = h.admin.post(f"/cases/{case_id}/delete", data={"csrf": csrf}, headers={"Origin": "https://evil.test"})
    assert wrong_origin.status_code == 403


def test_draft_release_via_forms(h):
    token = h.pair()["access_token"]
    case_id = h.create_case(token).json()["case_id"]
    page = h.admin.get(f"/cases/{case_id}")
    csrf = csrf_from(page.text)
    bad = h.admin.post(f"/cases/{case_id}/draft", data={"csrf": csrf, "version": "1", "draft": "{nicht json"}, follow_redirects=True)
    assert "Fehler" in bad.text and "JSON" in bad.text
    ok = h.admin.post(f"/cases/{case_id}/draft", data={"csrf": csrf, "version": "1", "draft": json.dumps(RESULT_CONTENT)}, follow_redirects=True)
    assert "Entwurf gespeichert" in ok.text
    draft_id = re.search(r'name="draft_id" value="([^"]+)"', ok.text).group(1)
    version = h.service._case(case_id)["version"]
    released = h.admin.post(f"/cases/{case_id}/release", data={"csrf": csrf, "version": str(version), "draft_id": draft_id}, follow_redirects=True)
    assert "Revision 1 freigegeben" in released.text
    assert h.api.get(f"/api/v1/cases/{case_id}", headers=h.headers(token)).json()["status"] == "released"
    stale = h.admin.post(f"/cases/{case_id}/release", data={"csrf": csrf, "version": str(version), "draft_id": draft_id}, follow_redirects=True)
    assert "Fehler" in stale.text


def test_invitation_form_shows_code_once(h):
    page = h.admin.get("/invitations")
    csrf = csrf_from(page.text)
    created = h.admin.post("/invitations", data={"csrf": csrf, "label": "Max", "days": "3", "max_uses": "2"})
    assert created.status_code == 200
    code = re.search(r"Einladungscode: ([A-Za-z0-9_-]+)", created.text).group(1)
    assert h.admin.get("/invitations").text.count(code) == 0  # nie wieder sichtbar
    assert h.api.post("/api/v1/pairings/redeem", json={"invitation_code": code}).status_code == 201
    assert "1 / 2" in h.admin.get("/invitations").text


def test_proxy_identity_required(tmp_path, contract):
    h = Harness(tmp_path, contract, DP_ADMIN_TRUSTED_PROXIES="10.0.30.5", DP_ADMIN_DEV_USER="")
    try:
        app = create_admin_app(h.service)
        direct = TestClient(app, base_url="https://admin.test", client=("10.0.30.99", 1234))
        assert direct.get("/", headers={"X-authentik-username": "christian", "X-authentik-groups": "Homelab-Admins"}).status_code == 403
        via_proxy = TestClient(app, base_url="https://admin.test", client=("10.0.30.5", 1234))
        assert via_proxy.get("/").status_code == 403
        assert via_proxy.get("/", headers={"X-authentik-username": "gast", "X-authentik-groups": "Gaeste"}).status_code == 403
        ok = via_proxy.get("/", headers={"X-authentik-username": "christian", "X-authentik-groups": "Gaeste|Homelab-Admins"})
        assert ok.status_code == 200 and "christian" in ok.text
    finally:
        h.close()
