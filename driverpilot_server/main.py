"""Einstieg: API-Server, Admin-Server, Worker und Bereinigung in einem Prozess."""

from __future__ import annotations

import asyncio
import logging
import signal

import uvicorn

from .admin import create_admin_app
from .api import create_api_app
from .config import Settings
from .contract import Contract
from .db import Database
from .service import Service
from .worker import Worker, build_adapter, cleanup_loop, reconcile_loop

log = logging.getLogger("driverpilot")


def build(settings: Settings | None = None) -> tuple[Service, Worker]:
    settings = settings or Settings()
    contract = Contract()
    db = Database(settings.db_path)
    service = Service(settings, contract, db)
    adapter = build_adapter(settings.ai_provider, settings=settings)
    if adapter is not None:
        service.ai_available = adapter.available
        service.codex_auth = getattr(adapter, "auth", None)
    worker = Worker(service, adapter)
    return service, worker


async def serve() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # keine Request-Zeilen des Modellaufrufs im Log
    settings = Settings()
    if not settings.admin_api_token:
        log.warning("DP_ADMIN_API_TOKEN ist leer: die Admin-API lehnt alle Anfragen ab")
    service, worker = build(settings)
    service.expire_stale_leases()
    log.info(
        "DriverPilot Ferndiagnose-Server: api=%s:%s admin=%s:%s adapter=%s datenschutzhinweis=%s",
        settings.api_host, settings.api_port, settings.admin_host, settings.admin_port, settings.ai_provider,
        settings.privacy_notice_version,
    )

    api_server = uvicorn.Server(
        uvicorn.Config(create_api_app(service), host=settings.api_host, port=settings.api_port, log_level="warning",
                       access_log=False, proxy_headers=False, server_header=False, date_header=True, lifespan="off")
    )
    admin_server = uvicorn.Server(
        uvicorn.Config(create_admin_app(service), host=settings.admin_host, port=settings.admin_port, log_level="warning",
                       access_log=False, proxy_headers=False, server_header=False, lifespan="off")
    )
    stop = asyncio.Event()

    def shutdown(*_):
        log.info("Beende ...")
        api_server.should_exit = True
        admin_server.should_exit = True
        worker.stop()
        stop.set()

    tasks = [
        asyncio.create_task(api_server.serve(), name="api"),
        asyncio.create_task(admin_server.serve(), name="admin"),
        asyncio.create_task(worker.run(), name="worker"),
        asyncio.create_task(cleanup_loop(service, 3600, stop), name="cleanup"),
        asyncio.create_task(reconcile_loop(service, settings.release_reconcile_minutes, stop), name="reconcile"),
    ]
    await asyncio.sleep(0.5)  # uvicorn installiert eigene Signalhandler; danach unsere darueberlegen.
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)
    await asyncio.gather(*tasks, return_exceptions=True)
    service.db.close()


def main() -> None:
    asyncio.run(serve())


if __name__ == "__main__":
    main()
