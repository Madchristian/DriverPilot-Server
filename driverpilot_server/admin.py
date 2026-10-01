"""Adminansicht (eigener Port). Identitaet kommt per Authentik-ForwardAuth vom
LAN-Traefik; die Header werden nur akzeptiert, wenn der Request von einem der
konfigurierten Proxys stammt. Jede Mutation braucht einen CSRF-Token
(HMAC-signiertes Cookie + Formularfeld) und einen passenden Fetch-Kontext.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import secrets
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from starlette.routing import Route

from .service import AdminError, Service

log = logging.getLogger("driverpilot.admin")
TEMPLATES = Path(__file__).resolve().parent / "templates"
CSRF_COOKIE = "dp_admin_csrf"


class Forbidden(Exception):
    pass


class Admin:
    def __init__(self, service: Service):
        self.service = service
        self.settings = service.settings
        self.trusted = [ipaddress.ip_network(net, strict=False) for net in self.settings.admin_trusted_proxies]
        self.env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))
        self.env.filters["json"] = lambda value: json.dumps(value, ensure_ascii=False, indent=2)
        self.env.filters["short"] = lambda value: (value or "")[:8]

    # ------------------------------------------------------------------ Identitaet und CSRF

    def identity(self, request: Request) -> str:
        peer = request.client.host if request.client else ""
        try:
            peer_ip = ipaddress.ip_address(peer)
            via_proxy = any(peer_ip in net for net in self.trusted)
        except ValueError:
            via_proxy = False
        if via_proxy:
            user = request.headers.get("x-authentik-username", "").strip()
            groups = [g.strip() for g in request.headers.get("x-authentik-groups", "").split("|")]
            if user and self.settings.admin_group in groups:
                return user
            raise Forbidden()
        if self.settings.admin_dev_user and not self.trusted:
            return self.settings.admin_dev_user
        raise Forbidden()

    def _sign(self, value: str) -> str:
        return hmac.new(self.service.secret, value.encode("ascii"), hashlib.sha256).hexdigest()

    def csrf_token(self, request: Request) -> tuple[str, bool]:
        """Gibt (Token, neu_gesetzt) zurueck. Das Cookie traegt token.signatur."""
        raw = request.cookies.get(CSRF_COOKIE, "")
        token, _, signature = raw.partition(".")
        if token and signature and hmac.compare_digest(self._sign(token), signature):
            return token, False
        return secrets.token_urlsafe(24), True

    def set_csrf_cookie(self, response: Response, token: str) -> None:
        response.set_cookie(
            CSRF_COOKIE, f"{token}.{self._sign(token)}", httponly=True, secure=True, samesite="strict", max_age=12 * 3600, path="/"
        )

    async def check_csrf(self, request: Request) -> dict:
        site = request.headers.get("sec-fetch-site")
        if site not in (None, "same-origin", "none"):
            raise Forbidden()
        origin = request.headers.get("origin")
        host = request.headers.get("host", "")
        if origin and origin.split("://", 1)[-1] != host:
            raise Forbidden()
        form = await request.form()
        token, fresh = self.csrf_token(request)
        if fresh or not hmac.compare_digest(form.get("csrf", ""), token):
            raise Forbidden()
        return dict(form)

    # ------------------------------------------------------------------ Rendern

    def render(self, request: Request, template: str, **context) -> HTMLResponse:
        user = self.identity(request)
        token, fresh = self.csrf_token(request)
        html = self.env.get_template(template).render(
            user=user, csrf=token, settings=self.settings.describe(), now=self.service.now_text(),
            flash=request.query_params.get("m"), **context,
        )
        response = HTMLResponse(html)
        if fresh:
            self.set_csrf_cookie(response, token)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @staticmethod
    def redirect(path: str, message: str | None = None) -> RedirectResponse:
        from urllib.parse import quote

        target = f"{path}?m={quote(message)}" if message else path
        return RedirectResponse(target, status_code=303)

    # ------------------------------------------------------------------ Seiten

    async def index(self, request: Request) -> Response:
        self.identity(request)
        return self.render(request, "index.html", stats=self.service.stats(), cases=self.service.list_cases())

    async def case(self, request: Request) -> Response:
        self.identity(request)
        detail = self.service.case_detail(request.path_params["case_id"])
        if detail is None:
            raise HTTPException(404)
        current = detail["current_draft"]
        if current is not None:
            draft_text = json.dumps(json.loads(current["body_json"]), ensure_ascii=False, indent=2)
            ai_assisted = current["origin"] == "ai"
            problems = self.service.validate_draft(detail["case"]["id"], json.loads(current["body_json"]))
        else:
            draft_text = json.dumps(self.service.draft_skeleton(detail["report"]), ensure_ascii=False, indent=2)
            ai_assisted = False
            problems = []
        results = [dict(r, body=json.loads(r["body_json"])) for r in detail["results"]]
        return self.render(
            request, "case.html", d=detail, draft_text=draft_text, ai_assisted=ai_assisted, problems=problems,
            blocking=[p for p in problems if "(Hinweis" not in p],
            results=results, report_json=json.dumps(detail["report"], ensure_ascii=False, indent=2),
            can_release=self.service.contract.transition_allowed(detail["case"]["status"], "released", "admin"),
            can_take_over=self.service.contract.transition_allowed(detail["case"]["status"], "awaiting_review", "admin"),
            can_retry=self.service.external_ai_offered() and detail["case"]["external_ai_allowed"]
            and self.service.contract.transition_allowed(detail["case"]["status"], "queued", "admin"),
        )

    async def case_action(self, request: Request) -> Response:
        user = self.identity(request)
        form = await self.check_csrf(request)
        case_id = request.path_params["case_id"]
        action = request.path_params["action"]
        back = f"/cases/{case_id}"
        try:
            version = int(form.get("version", "0"))
            if action == "draft":
                try:
                    content = json.loads(form.get("draft", ""))
                except json.JSONDecodeError as exc:
                    raise AdminError(f"Entwurf ist kein gueltiges JSON: {exc.msg} (Zeile {exc.lineno})")
                if not isinstance(content, dict):
                    raise AdminError("Entwurf muss ein JSON-Objekt sein")
                self.service.save_draft(case_id, content, user, ai_assisted=form.get("ai_assisted") == "1")
                message = "Entwurf gespeichert."
            elif action == "release":
                revision = self.service.release(case_id, form.get("draft_id", ""), version, user)
                message = f"Revision {revision} freigegeben."
            elif action == "take-over":
                self.service.take_over(case_id, version, user)
                message = "Fall uebernommen; manuelle Analyse."
            elif action == "retry":
                self.service.retry(case_id, version, user)
                message = "Neuversuch eingereiht."
            elif action == "delete":
                self.service.admin_delete(case_id, user)
                return self.redirect("/", "Fall geloescht.")
            else:
                raise HTTPException(404)
        except AdminError as exc:
            return self.redirect(back, f"Fehler: {exc}")
        return self.redirect(back, message)

    async def invitations(self, request: Request) -> Response:
        self.identity(request)
        return self.render(request, "invitations.html", invitations=self.service.list_invitations(), new_code=None)

    async def invitations_create(self, request: Request) -> Response:
        user = self.identity(request)
        form = await self.check_csrf(request)
        try:
            days = max(1, min(365, int(form.get("days", "1") or 1)))
            max_uses = max(1, min(500, int(form.get("max_uses", "1") or 1)))
            label = (form.get("label") or "ohne Bezeichnung").strip()[:80]
            invitation_id, code = self.service.create_invitation(label, user, days * 86400, max_uses)
        except (AdminError, ValueError) as exc:
            return self.redirect("/invitations", f"Fehler: {exc}")
        return self.render(
            request, "invitations.html", invitations=self.service.list_invitations(),
            new_code=code, new_label=label, base_url=self.settings.public_base_url,
        )

    async def invitation_revoke(self, request: Request) -> Response:
        user = self.identity(request)
        await self.check_csrf(request)
        try:
            self.service.revoke_invitation(request.path_params["invitation_id"], user)
        except AdminError as exc:
            return self.redirect("/invitations", f"Fehler: {exc}")
        return self.redirect("/invitations", "Einladung widerrufen.")

    async def clients(self, request: Request) -> Response:
        self.identity(request)
        return self.render(request, "clients.html", clients=self.service.list_clients())

    async def client_revoke(self, request: Request) -> Response:
        user = self.identity(request)
        await self.check_csrf(request)
        try:
            self.service.revoke_client(request.path_params["client_id"], user)
        except AdminError as exc:
            return self.redirect("/clients", f"Fehler: {exc}")
        return self.redirect("/clients", "Zugang widerrufen; wirkt beim naechsten Request.")

    async def audit(self, request: Request) -> Response:
        self.identity(request)
        return self.render(request, "audit.html", entries=self.service.audit_entries())

    # ------------------------------------------------------------------ Codex (ChatGPT-OAuth)

    async def codex(self, request: Request) -> Response:
        self.identity(request)
        auth = self.service.codex_auth
        return self.render(
            request, "codex.html", auth=auth, status=auth.status() if auth else None,
            ai_offered=self.service.external_ai_offered(), budget_used=self.service.ai_budget_used(),
        )

    async def codex_action(self, request: Request) -> Response:
        user = self.identity(request)
        form = await self.check_csrf(request)
        auth = self.service.codex_auth
        action = request.path_params["action"]
        if auth is None:
            return self.redirect("/codex", "Fehler: Adapter codex ist nicht konfiguriert (DP_AI_PROVIDER).")
        try:
            if action == "login":
                device = await request.app.state.run_blocking(auth.start_device_login)
                message = f"Code {device.user_code} auf {device.verification_url} eingeben."
            elif action == "cancel":
                auth.cancel_device_login()
                message = "Login abgebrochen."
            elif action == "logout":
                auth.logout()
                message = "Abgemeldet; Tokendatei geloescht."
            elif action == "import":
                auth.import_auth_json(form.get("auth_json", ""))
                message = "auth.json uebernommen."
            else:
                raise HTTPException(404)
        except (ValueError, RuntimeError) as exc:
            return self.redirect("/codex", f"Fehler: {exc}")
        self.service.audit(user, f"codex.{action}", None, "ok")
        return self.redirect("/codex", message)

    # ------------------------------------------------------------------ Releases (Downloads)

    def _download_entries(self) -> list[dict]:
        from .public import Public

        return Public(self.settings, "")._entries()

    async def releases(self, request: Request) -> Response:
        self.identity(request)
        sync = self.service.releases
        return self.render(
            request, "releases.html", files=self._download_entries(), sync=sync,
            last=(sync.last if sync else {"state": "idle"}), configured=bool(sync and sync.configured()),
            webhook_configured=bool(self.settings.github_webhook_secret), endpoint_configured=bool(self.settings.release_sync_token),
        )

    async def releases_fetch(self, request: Request) -> Response:
        user = self.identity(request)
        form = await self.check_csrf(request)
        sync = self.service.releases
        if sync is None or not sync.configured():
            return self.redirect("/releases", "Fehler: Release-Sync ist nicht konfiguriert (DP_GITHUB_TOKEN).")
        tag = (form.get("tag") or "").strip() or None
        import re as _re

        if tag and not _re.fullmatch(r"[A-Za-z0-9._-]{1,64}", tag):
            return self.redirect("/releases", "Fehler: ungueltiger Tag.")
        started = sync.trigger(tag, source=user)
        return self.redirect("/releases", "Sync gestartet." if started else "Es laeuft bereits ein Sync.")

    async def healthz(self, request: Request) -> Response:
        return PlainTextResponse("ok")

    async def handle_forbidden(self, request: Request, exc: Forbidden) -> Response:
        return PlainTextResponse("Zugriff verweigert.", status_code=403)

    async def handle_http(self, request: Request, exc: HTTPException) -> Response:
        return PlainTextResponse("Nicht gefunden." if exc.status_code == 404 else "Fehler.", status_code=exc.status_code)

    async def handle_unexpected(self, request: Request, exc: Exception) -> Response:
        log.exception("Adminfehler")
        return PlainTextResponse("Interner Fehler.", status_code=500)


def create_admin_app(service: Service) -> Starlette:
    admin = Admin(service)
    routes = [
        Route("/", admin.index, methods=["GET"]),
        Route("/cases/{case_id}", admin.case, methods=["GET"]),
        Route("/cases/{case_id}/{action}", admin.case_action, methods=["POST"]),
        Route("/invitations", admin.invitations, methods=["GET"]),
        Route("/invitations", admin.invitations_create, methods=["POST"]),
        Route("/invitations/{invitation_id}/revoke", admin.invitation_revoke, methods=["POST"]),
        Route("/clients", admin.clients, methods=["GET"]),
        Route("/clients/{client_id}/revoke", admin.client_revoke, methods=["POST"]),
        Route("/audit", admin.audit, methods=["GET"]),
        Route("/releases", admin.releases, methods=["GET"]),
        Route("/releases/fetch", admin.releases_fetch, methods=["POST"]),
        Route("/codex", admin.codex, methods=["GET"]),
        Route("/codex/{action}", admin.codex_action, methods=["POST"]),
        Route("/healthz", admin.healthz, methods=["GET"]),
    ]
    app = Starlette(
        routes=routes,
        exception_handlers={Forbidden: admin.handle_forbidden, HTTPException: admin.handle_http, Exception: admin.handle_unexpected},
    )
    app.state.admin = admin
    import asyncio

    app.state.run_blocking = lambda fn, *args: asyncio.to_thread(fn, *args)
    return app
