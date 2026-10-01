"""Client-API /api/v1 nach contract/v1/openapi.yaml.

Die HTTP-Schicht prueft die Schritte 1 bis 3 der Annahme (Token, Anfragelimit,
Medientyp/Encoding, Bodygroesse, Idempotency-Key) und reicht dann an den
Dienst weiter. Jede Fehlerantwort ist das Fehlerobjekt aus error.schema.json.
Es werden keine Bodies, Tokens oder Einladungen protokolliert.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import uuid

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from .contract import ERROR_MESSAGES, ContractError, is_uuid
from .public import Public
from .ratelimit import SlidingWindow
from .service import Service

log = logging.getLogger("driverpilot.api")
CONTENT_TYPE_RE = re.compile(r"^application/json\s*(;\s*charset\s*=\s*\"?utf-8\"?\s*)?$", re.IGNORECASE)


class ApiError(Exception):
    def __init__(self, code: str, retry_after: int | None = None):
        self.code = code
        self.retry_after = retry_after


class Api:
    def __init__(self, service: Service):
        self.service = service
        settings = service.settings
        self.trusted_proxies = [ipaddress.ip_network(net, strict=False) for net in settings.api_trusted_proxies]
        self.client_limiter = SlidingWindow(settings.client_requests_per_minute, 60)
        self.ip_limiter = SlidingWindow(settings.client_requests_per_minute * 2, 60)
        self.pairing_failures = SlidingWindow(settings.pairing_failures_per_ip, settings.pairing_failure_window_seconds)

    # ------------------------------------------------------------------ Hilfen

    def client_ip(self, request: Request) -> str:
        peer = request.client.host if request.client else "0.0.0.0"
        try:
            peer_ip = ipaddress.ip_address(peer)
        except ValueError:
            return peer
        if any(peer_ip in net for net in self.trusted_proxies):
            forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "")
            candidate = forwarded.split(",")[0].strip()
            if candidate:
                try:
                    return str(ipaddress.ip_address(candidate))
                except ValueError:
                    pass
        return peer

    def error(self, code: str, retry_after: int | None = None, request_id: str | None = None) -> JSONResponse:
        status = self.service.contract.status_for(code)
        body = {
            "error": {"code": code, "message": ERROR_MESSAGES[code]},
            "request_id": request_id or str(uuid.uuid4()),
            "retry_after_seconds": retry_after if status in (429, 503) else None,
        }
        headers = {"Cache-Control": "no-store"}
        if status == 401 and code == "token_invalid":
            headers["WWW-Authenticate"] = "Bearer"
        if status in (429, 503) and retry_after:
            headers["Retry-After"] = str(retry_after)
        return JSONResponse(body, status_code=status, headers=headers)

    def json(self, body, status: int = 200, headers: dict | None = None) -> JSONResponse:
        merged = {"Cache-Control": "no-store"}
        merged.update(headers or {})
        return JSONResponse(body, status_code=status, headers=merged)

    def authenticate(self, request: Request):
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise ApiError("token_invalid")
        client = self.service.authenticate(token.strip())
        wait = self.client_limiter.check(client["id"])
        if wait:
            raise ApiError("rate_limited", wait)
        return client

    def limit_ip(self, request: Request) -> None:
        wait = self.ip_limiter.check(self.client_ip(request))
        if wait:
            raise ApiError("rate_limited", wait)

    def check_media(self, request: Request) -> None:
        if request.headers.get("content-encoding"):
            raise ApiError("unsupported_content_encoding")
        if not CONTENT_TYPE_RE.match(request.headers.get("content-type", "").strip()):
            raise ApiError("unsupported_media_type")

    async def read_body(self, request: Request) -> bytes:
        """Liest hoechstens max_upload_bytes; zaehlt tatsaechliche Bytes, auch chunked."""
        limit = self.service.settings.max_upload_bytes
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            raise ApiError("payload_too_large")
        chunks: list[bytes] = []
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > limit:
                raise ApiError("payload_too_large")
            chunks.append(chunk)
        return b"".join(chunks)

    @staticmethod
    def idempotency_key(request: Request) -> str:
        key = request.headers.get("idempotency-key", "")
        if not is_uuid(key):
            raise ApiError("idempotency_key_required")
        return key

    # ------------------------------------------------------------------ Endpunkte

    async def capabilities(self, request: Request) -> Response:
        self.limit_ip(request)
        return self.json(self.service.capabilities(), headers={"Cache-Control": "no-store"})

    async def redeem(self, request: Request) -> Response:
        ip = self.client_ip(request)
        wait = self.pairing_failures.blocked(ip)
        if wait:
            raise ApiError("rate_limited", wait)
        self.limit_ip(request)
        self.check_media(request)
        body = await self.read_body(request)
        try:
            result = self.service.redeem_invitation(body)
        except ContractError as exc:
            if exc.code == "invitation_invalid":
                self.pairing_failures.record(ip)
            raise
        return self.json(result, status=201)

    async def create_case(self, request: Request) -> Response:
        client = self.authenticate(request)
        self.check_media(request)
        body = await self.read_body(request)
        key = self.idempotency_key(request)
        return self.json(self.service.create_case(client, key, body), status=202)

    async def get_case(self, request: Request) -> Response:
        client = self.authenticate(request)
        found = self.service.get_case(client, request.path_params["case_id"])
        if found is None:
            raise ApiError("not_found")
        body, etag = found
        if_none_match = request.headers.get("if-none-match", "")
        candidates = [part.strip() for part in if_none_match.split(",")]
        if etag in candidates:
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "no-store"})
        return self.json(body, headers={"ETag": etag})

    async def delete_case(self, request: Request) -> Response:
        client = self.authenticate(request)
        self.service.delete_case(client, request.path_params["case_id"])
        return Response(status_code=204, headers={"Cache-Control": "no-store"})

    async def create_feedback(self, request: Request) -> Response:
        client = self.authenticate(request)
        case_id = request.path_params["case_id"]
        if self.service.visible_case(client["id"], case_id) is None:
            raise ApiError("not_found")
        self.check_media(request)
        body = await self.read_body(request)
        key = self.idempotency_key(request)
        return self.json(self.service.create_feedback(client, case_id, key, body), status=201)

    async def healthz(self, request: Request) -> Response:
        return Response("ok", media_type="text/plain")

    async def readyz(self, request: Request) -> Response:
        if self.service.db.healthy():
            return Response("ready", media_type="text/plain")
        return Response("not ready", status_code=503, media_type="text/plain")

    async def not_found(self, request: Request) -> Response:
        return self.error("not_found")

    # ------------------------------------------------------------------ Fehlerbehandlung

    async def handle_api_error(self, request: Request, exc: ApiError) -> Response:
        return self.error(exc.code, exc.retry_after)

    async def handle_contract_error(self, request: Request, exc: ContractError) -> Response:
        return self.error(exc.code, exc.retry_after)

    async def handle_http_exception(self, request: Request, exc: HTTPException) -> Response:
        if exc.status_code in (404, 405):
            return self.error("not_found")
        if exc.status_code == 413:
            return self.error("payload_too_large")
        log.warning("http %s auf %s", exc.status_code, request.url.path)
        return self.error("internal_error")

    async def handle_unexpected(self, request: Request, exc: Exception) -> Response:
        request_id = str(uuid.uuid4())
        log.exception("unerwarteter Fehler request_id=%s route=%s", request_id, request.scope.get("route_name", "?"))
        return self.error("internal_error", request_id=request_id)


def create_api_app(service: Service) -> Starlette:
    api = Api(service)
    public = Public(service.settings, service.privacy_notice_text)
    prefix = "/api/v1"
    routes = [
        # Oeffentliche Seiten fuer Menschen (Anleitung, Downloads); alles unter /api/v1 bleibt JSON.
        Route("/", public.index, methods=["GET"]),
        Route("/anleitung", public.anleitung, methods=["GET"]),
        Route("/datenschutz", public.datenschutz, methods=["GET"]),
        Route("/downloads", public.downloads_redirect, methods=["GET"]),
        Route("/downloads/", public.downloads, methods=["GET"]),
        Route("/downloads/{name}", public.download_file, methods=["GET"]),
        Route("/robots.txt", public.robots, methods=["GET"]),
        Route(f"{prefix}/capabilities", api.capabilities, methods=["GET"]),
        Route(f"{prefix}/pairings/redeem", api.redeem, methods=["POST"]),
        Route(f"{prefix}/cases", api.create_case, methods=["POST"]),
        Route(f"{prefix}/cases/{{case_id}}", api.get_case, methods=["GET"]),
        Route(f"{prefix}/cases/{{case_id}}", api.delete_case, methods=["DELETE"]),
        Route(f"{prefix}/cases/{{case_id}}/feedback", api.create_feedback, methods=["POST"]),
        Route("/healthz", api.healthz, methods=["GET"]),
        Route("/readyz", api.readyz, methods=["GET"]),
        Route("/{path:path}", api.not_found),
    ]
    app = Starlette(
        routes=routes,
        exception_handlers={
            ApiError: api.handle_api_error,
            ContractError: api.handle_contract_error,
            HTTPException: api.handle_http_exception,
            Exception: api.handle_unexpected,
        },
    )
    app.state.api = api
    app.state.public = public
    return app
