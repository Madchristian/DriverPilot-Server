"""Gemeinsame Testbasis: Service mit Testuhr auf der Szenariozeit der Vertrags-Fixtures."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from driverpilot_server.admin import create_admin_app
from driverpilot_server.api import create_api_app
from driverpilot_server.config import REPO_DIR, Settings
from driverpilot_server.contract import Contract, parse_time
from driverpilot_server.db import Database
from driverpilot_server.service import Clock, Service
from driverpilot_server.worker import TestAdapter, Worker

FIXTURES = REPO_DIR / "contract" / "v1" / "fixtures"
SCENARIO = json.loads((FIXTURES / "scenario.json").read_text("utf-8"))
REPORT_BYTES = (FIXTURES / SCENARIO["report"]).read_bytes()
REPORT_SHA256 = (FIXTURES / "valid/case-create-request/wow-crash.sha256").read_text("ascii").strip()
# manual-minimal.json verweist auf den Szenario-Fall als Vorgaenger; ohne ihn ist previous_case_id null.
MINIMAL_FIXTURE_BYTES = (FIXTURES / "valid/case-create-request/manual-minimal.json").read_bytes()
MINIMAL_BYTES = MINIMAL_FIXTURE_BYTES.replace(b'"previous_case_id": "5f0c2a7e-3b1d-4c8a-9e21-7a4d0b6c1f02"', b'"previous_case_id": null')


def shift_days(body: bytes, days: int) -> bytes:
    """Verschiebt alle Fixture-Zeitpunkte (2026-10-02/03) um ganze Tage, fuer Tests ueber Tagesgrenzen."""
    for day in (3, 2):
        body = body.replace(f"2026-10-0{day}T".encode(), f"2026-10-{day + days:02d}T".encode())
    return body
RESULT_FIXTURE = json.loads((FIXTURES / "valid/result/ai-assisted.json").read_text("utf-8"))
RESULT_CONTENT = {k: RESULT_FIXTURE[k] for k in ("summary", "facts", "hypotheses", "next_steps", "open_questions", "warnings", "sources")}

KEY_A = "11111111-1111-4111-8111-111111111111"
KEY_B = "22222222-2222-4222-8222-222222222222"
KEY_C = "33333333-3333-4333-8333-333333333333"


@pytest.fixture
def contract() -> Contract:
    return Contract()


def make_settings(tmp_path: Path, **overrides) -> Settings:
    env = {
        "DP_DATA_DIR": str(tmp_path / "data"),
        "DP_ADMIN_API_TOKEN": "SYNTHETIC-admin-api-token",
        "DP_PRIVACY_NOTICE_VERSION": SCENARIO["privacy_notice_version"],
        "DP_AI_PROVIDER": "none",
    }
    env.update({k: str(v) for k, v in overrides.items()})
    old = {k: os.environ.get(k) for k in env}
    os.environ.update(env)
    try:
        return Settings()
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class Harness:
    def __init__(self, tmp_path: Path, contract: Contract, **overrides):
        self.settings = make_settings(tmp_path, **overrides)
        self.clock = Clock()
        self.clock.fixed = parse_time(SCENARIO["now"])
        self.db = Database(self.settings.db_path)
        self.service = Service(self.settings, contract, self.db, self.clock)
        self.api_app = create_api_app(self.service)
        self.admin_app = create_admin_app(self.service)
        self.api = TestClient(self.api_app, raise_server_exceptions=False)
        self.admin = TestClient(self.admin_app, raise_server_exceptions=False, base_url="http://server:8141",
                                headers={"Authorization": "Bearer SYNTHETIC-admin-api-token", "X-DP-Actor": "tester"})

    def pair(self, label: str = "test") -> dict:
        _, code = self.service.create_invitation(label, "tester")
        response = self.api.post("/api/v1/pairings/redeem", json={"invitation_code": code})
        assert response.status_code == 201, response.text
        return response.json()

    @staticmethod
    def headers(token: str, key: str | None = None) -> dict:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json; charset=utf-8"}
        if key:
            headers["Idempotency-Key"] = key
        return headers

    def create_case(self, token: str, key: str = KEY_A, body: bytes = REPORT_BYTES):
        return self.api.post("/api/v1/cases", content=body, headers=self.headers(token, key))

    def release(self, case_id: str, content: dict | None = None, actor: str = "tester") -> int:
        content = content or RESULT_CONTENT
        case = self.service._case(case_id)
        if case["status"] not in ("awaiting_review", "released"):
            self.service.take_over(case_id, case["version"], actor)
            case = self.service._case(case_id)
        draft_id = self.service.save_draft(case_id, content, actor, ai_assisted=False)
        return self.service.release(case_id, draft_id, case["version"], actor)

    def worker(self, **adapter_kwargs) -> Worker:
        return Worker(self.service, TestAdapter(**adapter_kwargs))

    def close(self):
        self.db.close()


@pytest.fixture
def h(tmp_path, contract):
    harness = Harness(tmp_path, contract)
    yield harness
    harness.close()


@pytest.fixture
def h_ai(tmp_path, contract):
    harness = Harness(tmp_path, contract, DP_AI_PROVIDER="test", DP_AI_DAILY_CALLS=3, DP_AI_TIMEOUT_SECONDS=1)
    yield harness
    harness.close()
