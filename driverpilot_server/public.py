"""Oeffentliche Seiten auf dem API-Host: Anleitung, Datenschutzhinweis, Downloads.

Alles hier ist rein lesend und ohne Zugangsdaten erreichbar (hinter Cloudflare, CrowdSec und
Rate-Limit des Traefik). Die Downloads kommen aus einem read-only Verzeichnis; Dateinamen werden
streng geprueft, damit nichts ausserhalb davon ausgeliefert wird.
"""

from __future__ import annotations

import hashlib
import html
import logging
import re
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse, Response

from .config import REPO_DIR, Settings

log = logging.getLogger("driverpilot.public")
TEMPLATES = Path(__file__).resolve().parent / "templates"
DOCS = REPO_DIR / "docs" / "public"
FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
ALLOWED_SUFFIXES = {".exe", ".zip", ".cer", ".txt", ".sha256", ".pdf", ".md"}
MEDIA_TYPES = {
    ".exe": "application/vnd.microsoft.portable-executable",
    ".zip": "application/zip",
    ".cer": "application/pkix-cert",
    ".txt": "text/plain; charset=utf-8",
    ".sha256": "text/plain; charset=utf-8",
    ".pdf": "application/pdf",
    ".md": "text/markdown; charset=utf-8",
}
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; img-src 'self'; base-uri 'none'; form-action 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "X-Robots-Tag": "noindex, nofollow",
}


class Public:
    def __init__(self, settings: Settings, privacy_notice: str):
        self.settings = settings
        self.privacy_notice = privacy_notice
        self.downloads_dir = Path(settings.downloads_dir)
        self.env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))
        self._hash_cache: dict[str, tuple[int, int, str]] = {}  # name -> (size, mtime_ns, sha256)
        self._pages: dict[str, str] = {}

    # ------------------------------------------------------------------ Rendern

    def _page(self, request: Request, title: str, body_html: str, status: int = 200) -> HTMLResponse:
        page = self.env.get_template("public.html").render(title=title, body=body_html, base_url=self.settings.public_base_url)
        response = HTMLResponse(page, status_code=status)
        response.headers.update(SECURITY_HEADERS)
        response.headers["Cache-Control"] = "public, max-age=300"
        return response

    def _markdown(self, name: str) -> str:
        path = DOCS / name
        key = f"{name}:{path.stat().st_mtime_ns}"
        if key not in self._pages:
            text = path.read_text("utf-8")
            self._pages.clear()
            self._pages[key] = markdown.markdown(text, extensions=["tables", "toc"], output_format="html5")
        return self._pages[key]

    # ------------------------------------------------------------------ Downloads

    def _entries(self) -> list[dict]:
        entries = []
        if not self.downloads_dir.is_dir():
            return entries
        for path in sorted(self.downloads_dir.iterdir()):
            if not path.is_file() or not FILENAME_RE.match(path.name) or path.suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            stat = path.stat()
            cached = self._hash_cache.get(path.name)
            if cached is None or cached[0] != stat.st_size or cached[1] != stat.st_mtime_ns:
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1 << 20), b""):
                        digest.update(chunk)
                cached = (stat.st_size, stat.st_mtime_ns, digest.hexdigest())
                self._hash_cache[path.name] = cached
            entries.append({"name": path.name, "size": stat.st_size, "sha256": cached[2], "mtime": stat.st_mtime})
        return entries

    @staticmethod
    def _human_size(size: int) -> str:
        if size >= 1 << 20:
            return f"{size / (1 << 20):.1f} MB"
        if size >= 1 << 10:
            return f"{size / (1 << 10):.0f} KB"
        return f"{size} B"

    # ------------------------------------------------------------------ Endpunkte

    async def index(self, request: Request) -> Response:
        body = (
            "<h1>DriverPilot: Hilfe von Christian</h1>"
            "<p>Hier findest du die Anleitung, den Datenschutzhinweis und die Programmdateien von DriverPilot.</p>"
            "<ul>"
            '<li><a href="/anleitung">Anleitung für Freunde</a>: Installation, Koppeln, Bericht senden, Antwort lesen.</li>'
            '<li><a href="/downloads/">Downloads</a>: Setup, portable ZIP, Zertifikat und Prüfsummen.</li>'
            '<li><a href="/datenschutz">Datenschutzhinweis</a>: was gesendet wird, wer es sieht, wann es gelöscht wird.</li>'
            "</ul>"
            "<p>Die Programmschnittstelle für DriverPilot liegt unter <code>/api/v1</code>; sie ist nur mit Einladungscode nutzbar.</p>"
        )
        return self._page(request, "DriverPilot", body)

    async def anleitung(self, request: Request) -> Response:
        return self._page(request, "Anleitung", self._markdown("anleitung.md"))

    async def datenschutz(self, request: Request) -> Response:
        paragraphs = "".join(f"<p>{html.escape(block)}</p>" for block in self.privacy_notice.split("\n\n") if block.strip())
        body = (
            f"<h1>Datenschutzhinweis</h1><p class=\"muted\">Version {html.escape(self.settings.privacy_notice_version)}. "
            "Genau diesen Text zeigt DriverPilot vor dem Senden an.</p>" + paragraphs
        )
        return self._page(request, "Datenschutzhinweis", body)

    async def downloads(self, request: Request) -> Response:
        entries = self._entries()
        rows = "".join(
            f'<tr><td><a href="/downloads/{html.escape(e["name"])}">{html.escape(e["name"])}</a></td>'
            f'<td>{self._human_size(e["size"])}</td><td><code>{e["sha256"]}</code></td></tr>'
            for e in entries
        )
        table = (
            f"<table><thead><tr><th>Datei</th><th>Größe</th><th>SHA-256</th></tr></thead><tbody>{rows}</tbody></table>"
            if entries else "<p>Zurzeit liegen keine Dateien bereit.</p>"
        )
        body = (
            "<h1>Downloads</h1>"
            "<p>Alle Dateien sind mit Christians Zertifikat signiert. Vor der Installation den Fingerabdruck des "
            "Zertifikats mit Christian abgleichen, siehe <a href=\"/anleitung\">Anleitung</a>, Abschnitt 1. "
            "Die Prüfsumme einer heruntergeladenen Datei zeigt PowerShell mit "
            "<code>Get-FileHash .\\&lt;Datei&gt; -Algorithm SHA256</code>.</p>" + table
        )
        return self._page(request, "Downloads", body)

    async def download_file(self, request: Request) -> Response:
        name = request.path_params["name"]
        if not FILENAME_RE.match(name) or Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
            return self._page(request, "Nicht gefunden", "<h1>Datei nicht gefunden</h1>", status=404)
        path = (self.downloads_dir / name)
        if not path.is_file() or path.resolve().parent != self.downloads_dir.resolve():
            return self._page(request, "Nicht gefunden", "<h1>Datei nicht gefunden</h1>", status=404)
        response = FileResponse(str(path), media_type=MEDIA_TYPES[path.suffix.lower()], filename=name)
        response.headers["Cache-Control"] = "public, max-age=3600"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    async def downloads_redirect(self, request: Request) -> Response:
        return RedirectResponse("/downloads/", status_code=308)

    async def robots(self, request: Request) -> Response:
        return PlainTextResponse("User-agent: *\nDisallow: /\n")
