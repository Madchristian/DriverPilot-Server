"""Interne Admin-JSON-API (Port 8141, nur im Docker-Netz) fuer die SvelteKit-Oberflaeche.

Die Oberflaeche (`web/`) prueft die Authentik-Identitaet am Rand (nur vom konfigurierten
Pi-Traefik, Gruppe Homelab-Admins) und ruft diese API mit einem gemeinsamen Token auf:

    Authorization: Bearer <DP_ADMIN_API_TOKEN>
    X-DP-Actor: <Authentik-Benutzername>

Ohne gueltiges Token gibt es 401. Der Akteur landet im Audit. Diese API ist nie oeffentlich
geroutet; im Compose-Stack ist der Port nicht auf dem Host veroeffentlicht.
"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
import re
from dataclasses import asdict, is_dataclass

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from .contract import is_uuid
from .public import Public
from .service import RESULT_CONTENT_KEYS, AdminError, Service

log = logging.getLogger("driverpilot.admin")
ACTOR_RE = re.compile(r"^[A-Za-z0-9@._+-]{1,80}$")
TAG_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
MAX_BODY = 512 * 1024


class Unauthorized(Exception):
    pass


class BadRequest(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def row(value) -> dict | None:
    return dict(value) if value is not None else None


def rows(values) -> list[dict]:
    return [dict(v) for v in values]


def strip_body(value) -> dict:
    return {k: v for k, v in dict(value).items() if k not in ("body_json", "report_bytes")}


class AdminApi:
    def __init__(self, service: Service):
        self.service = service
        self.settings = service.settings

    # ------------------------------------------------------------------ Rahmen

    def actor(self, request: Request) -> str:
        token = self.settings.admin_api_token
        scheme, _, given = request.headers.get("authorization", "").partition(" ")
        if not token or scheme.lower() != "bearer" or not hmac.compare_digest(given.strip(), token):
            raise Unauthorized()
        actor = request.headers.get("x-dp-actor", "").strip()
        if not ACTOR_RE.match(actor):
            raise Unauthorized()
        return actor

    async def body(self, request: Request) -> dict:
        data = b""
        async for chunk in request.stream():
            data += chunk
            if len(data) > MAX_BODY:
                raise BadRequest("Anfrage zu groß")
        if not data.strip():
            return {}
        try:
            value = json.loads(data.decode("utf-8"))
        except ValueError:
            raise BadRequest("Kein gültiges JSON") from None
        if not isinstance(value, dict):
            raise BadRequest("JSON-Objekt erwartet")
        return value

    @staticmethod
    def ok(data, status: int = 200) -> JSONResponse:
        return JSONResponse(data, status_code=status, headers={"Cache-Control": "no-store"})

    # ------------------------------------------------------------------ Uebersicht und Faelle

    async def overview(self, request: Request) -> Response:
        self.actor(request)
        return self.ok({
            "now": self.service.now_text(),
            "stats": self.service.stats(),
            "settings": self.settings.describe(),
            "ai_offered": self.service.external_ai_offered(),
            "cases": rows(self.service.list_cases()),
        })

    def _case_payload(self, case_id: str) -> dict:
        detail = self.service.case_detail(case_id)
        if detail is None:
            raise HTTPException(404)
        case = strip_body(detail["case"])
        current = detail["current_draft"]
        base_revision = None
        if current is not None:
            content = json.loads(current["body_json"])
            problems = self.service.validate_draft(case["id"], content)
        elif detail["results"]:
            # Nach einer Freigabe: die zuletzt freigegebene Revision als Ausgangspunkt fuer die naechste.
            latest = json.loads(detail["results"][0]["body_json"])
            content = {key: latest[key] for key in RESULT_CONTENT_KEYS}
            base_revision = latest["revision"]
            problems = []
        else:
            content = self.service.draft_skeleton(detail["report"])
            problems = []
        contract = self.service.contract
        return {
            "now": self.service.now_text(),
            "case": case,
            "report": detail["report"],
            "client": row(detail["client"]),
            "draft": {
                "id": current["id"] if current is not None else None,
                "origin": current["origin"] if current is not None else None,
                "author": current["author"] if current is not None else None,
                "created_at": current["created_at"] if current is not None else None,
                "model": current["model"] if current is not None else None,
                "content": content,
                "saved": current is not None,
                "base_revision": base_revision,
            },
            "problems": [p for p in problems if "(Hinweis" not in p],
            "hints": [p for p in problems if "(Hinweis" in p],
            "drafts": [strip_body(d) for d in detail["drafts"]],
            "results": [{**strip_body(r), "body": json.loads(r["body_json"])} for r in detail["results"]],
            "feedback": rows(detail["feedback"]),
            "runs": rows(detail["runs"]),
            "jobs": rows(detail["jobs"]),
            "can": {
                "release": contract.transition_allowed(case["status"], "released", "admin"),
                "take_over": contract.transition_allowed(case["status"], "awaiting_review", "admin"),
                "retry": bool(self.service.external_ai_offered() and case["external_ai_allowed"]
                              and contract.transition_allowed(case["status"], "queued", "admin")),
            },
        }

    async def case(self, request: Request) -> Response:
        self.actor(request)
        case_id = request.path_params["case_id"]
        if not is_uuid(case_id):
            raise HTTPException(404)
        return self.ok(self._case_payload(case_id))

    async def case_action(self, request: Request) -> Response:
        actor = self.actor(request)
        case_id = request.path_params["case_id"]
        action = request.path_params["action"]
        if not is_uuid(case_id):
            raise HTTPException(404)
        data = await self.body(request)
        version = data.get("version")
        if action in ("release", "take-over", "retry") and not isinstance(version, int):
            raise BadRequest("version fehlt")
        if action in ("draft", "validate"):
            content = data.get("content")
            if not isinstance(content, dict):
                raise BadRequest("content muss ein Objekt sein")
            if action == "validate":
                problems = self.service.validate_draft(case_id, content)
                return self.ok({"problems": [p for p in problems if "(Hinweis" not in p],
                                "hints": [p for p in problems if "(Hinweis" in p]})
            draft_id = self.service.save_draft(case_id, content, actor, ai_assisted=bool(data.get("ai_assisted")))
            return self.ok({"message": "Entwurf gespeichert.", "draft_id": draft_id})
        if action == "release":
            revision = self.service.release(case_id, str(data.get("draft_id", "")), version, actor)
            return self.ok({"message": f"Revision {revision} freigegeben.", "revision": revision})
        if action == "take-over":
            self.service.take_over(case_id, version, actor)
            return self.ok({"message": "Fall übernommen; manuelle Analyse."})
        if action == "retry":
            self.service.retry(case_id, version, actor)
            return self.ok({"message": "Neuversuch eingereiht."})
        if action == "delete":
            self.service.admin_delete(case_id, actor)
            return self.ok({"message": "Fall gelöscht."})
        raise HTTPException(404)

    # ------------------------------------------------------------------ Einladungen und Zugaenge

    async def invitations(self, request: Request) -> Response:
        self.actor(request)
        return self.ok({"now": self.service.now_text(), "public_base_url": self.settings.public_base_url,
                        "invitations": rows(self.service.list_invitations())})

    async def invitations_create(self, request: Request) -> Response:
        actor = self.actor(request)
        data = await self.body(request)
        try:
            days = max(1, min(365, int(data.get("days") or 1)))
            max_uses = max(1, min(500, int(data.get("max_uses") or 1)))
        except (TypeError, ValueError):
            raise BadRequest("Tage und Einlösungen müssen Zahlen sein") from None
        label = str(data.get("label") or "").strip()[:80] or "ohne Bezeichnung"
        invitation_id, code = self.service.create_invitation(label, actor, days * 86400, max_uses)
        return self.ok({"id": invitation_id, "code": code, "label": label, "days": days, "max_uses": max_uses,
                        "base_url": self.settings.public_base_url}, status=201)

    async def invitation_revoke(self, request: Request) -> Response:
        actor = self.actor(request)
        self.service.revoke_invitation(request.path_params["invitation_id"], actor)
        return self.ok({"message": "Einladung widerrufen."})

    async def clients(self, request: Request) -> Response:
        self.actor(request)
        return self.ok({"now": self.service.now_text(), "clients": rows(self.service.list_clients())})

    async def client_revoke(self, request: Request) -> Response:
        actor = self.actor(request)
        self.service.revoke_client(request.path_params["client_id"], actor)
        return self.ok({"message": "Zugang widerrufen; wirkt beim nächsten Request."})

    async def audit(self, request: Request) -> Response:
        self.actor(request)
        return self.ok({"entries": rows(self.service.audit_entries())})

    # ------------------------------------------------------------------ Codex

    def _codex_status(self) -> dict | None:
        auth = self.service.codex_auth
        if auth is None:
            return None
        status = auth.status()
        device = status.get("device")
        status["device"] = asdict(device) if is_dataclass(device) else None
        return status

    async def codex(self, request: Request) -> Response:
        self.actor(request)
        return self.ok({
            "provider": self.settings.ai_provider,
            "model": self.settings.codex_model,
            "status": self._codex_status(),
            "ai_offered": self.service.external_ai_offered(),
            "budget_used": self.service.ai_budget_used(),
            "budget_total": self.settings.ai_daily_calls,
        })

    async def codex_action(self, request: Request) -> Response:
        actor = self.actor(request)
        data = await self.body(request)
        auth = self.service.codex_auth
        action = request.path_params["action"]
        if auth is None:
            raise BadRequest("Adapter codex ist nicht konfiguriert (DP_AI_PROVIDER).")
        try:
            if action == "login":
                device = await asyncio.to_thread(auth.start_device_login)
                message = f"Code {device.user_code} auf {device.verification_url} eingeben."
            elif action == "cancel":
                auth.cancel_device_login()
                message = "Login abgebrochen."
            elif action == "logout":
                auth.logout()
                message = "Abgemeldet; Tokendatei gelöscht."
            elif action == "import":
                auth.import_auth_json(str(data.get("auth_json", "")))
                message = "auth.json übernommen."
            else:
                raise HTTPException(404)
        except (ValueError, RuntimeError) as exc:
            raise BadRequest(str(exc)) from None
        self.service.audit(actor, f"codex.{action}", None, "ok")
        return self.ok({"message": message, "status": self._codex_status()})

    # ------------------------------------------------------------------ Releases

    async def releases(self, request: Request) -> Response:
        self.actor(request)
        sync = self.service.releases
        return self.ok({
            "configured": bool(sync and sync.configured()),
            "webhook_configured": bool(self.settings.github_webhook_secret),
            "endpoint_configured": bool(self.settings.release_sync_token),
            "client_repo": self.settings.client_repo,
            "keep": self.settings.releases_keep,
            "last": dict(sync.last) if sync else {"state": "idle"},
            "last_reconcile": dict(sync.last_reconcile) if sync else {"state": "idle"},
            "current_tag": sync.current_tag() if sync else None,
            "reconcile_minutes": self.settings.release_reconcile_minutes,
            "files": Public(self.settings).entries_json(),
            "public_base_url": self.settings.public_base_url,
        })

    async def releases_fetch(self, request: Request) -> Response:
        actor = self.actor(request)
        data = await self.body(request)
        sync = self.service.releases
        if sync is None or not sync.configured():
            raise BadRequest("Release-Sync ist nicht konfiguriert (DP_GITHUB_TOKEN).")
        tag = str(data.get("tag") or "").strip() or None
        if tag and not TAG_RE.match(tag):
            raise BadRequest("Ungültiger Tag.")
        started = sync.trigger(tag, source=actor)
        return self.ok({"message": "Sync gestartet." if started else "Es läuft bereits ein Sync.", "started": started}, status=202)

    # ------------------------------------------------------------------ Fehler

    async def healthz(self, request: Request) -> Response:
        return Response("ok", media_type="text/plain")

    async def handle_unauthorized(self, request: Request, exc: Unauthorized) -> Response:
        return JSONResponse({"error": "Nicht autorisiert."}, status_code=401)

    async def handle_bad_request(self, request: Request, exc: BadRequest) -> Response:
        return JSONResponse({"error": exc.message}, status_code=400)

    async def handle_admin_error(self, request: Request, exc: AdminError) -> Response:
        return JSONResponse({"error": str(exc)}, status_code=409)

    async def handle_http(self, request: Request, exc: HTTPException) -> Response:
        return JSONResponse({"error": "Nicht gefunden." if exc.status_code in (404, 405) else "Fehler."},
                            status_code=404 if exc.status_code == 405 else exc.status_code)

    async def handle_unexpected(self, request: Request, exc: Exception) -> Response:
        log.exception("Admin-API-Fehler")
        return JSONResponse({"error": "Interner Fehler."}, status_code=500)


def create_admin_app(service: Service) -> Starlette:
    api = AdminApi(service)
    p = "/admin-api"
    routes = [
        Route(f"{p}/overview", api.overview, methods=["GET"]),
        Route(f"{p}/cases/{{case_id}}", api.case, methods=["GET"]),
        Route(f"{p}/cases/{{case_id}}/{{action}}", api.case_action, methods=["POST"]),
        Route(f"{p}/invitations", api.invitations, methods=["GET"]),
        Route(f"{p}/invitations", api.invitations_create, methods=["POST"]),
        Route(f"{p}/invitations/{{invitation_id}}/revoke", api.invitation_revoke, methods=["POST"]),
        Route(f"{p}/clients", api.clients, methods=["GET"]),
        Route(f"{p}/clients/{{client_id}}/revoke", api.client_revoke, methods=["POST"]),
        Route(f"{p}/audit", api.audit, methods=["GET"]),
        Route(f"{p}/codex", api.codex, methods=["GET"]),
        Route(f"{p}/codex/{{action}}", api.codex_action, methods=["POST"]),
        Route(f"{p}/releases", api.releases, methods=["GET"]),
        Route(f"{p}/releases/fetch", api.releases_fetch, methods=["POST"]),
        Route("/healthz", api.healthz, methods=["GET"]),
    ]
    app = Starlette(
        routes=routes,
        exception_handlers={
            Unauthorized: api.handle_unauthorized,
            BadRequest: api.handle_bad_request,
            AdminError: api.handle_admin_error,
            HTTPException: api.handle_http,
            Exception: api.handle_unexpected,
        },
    )
    app.state.admin = api
    return app
