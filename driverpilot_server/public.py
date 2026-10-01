"""Oeffentliche Daten fuer die SvelteKit-Seiten und Auslieferung der Release-Dateien.

Die Seiten selbst (Start, Anleitung, Datenschutz, Downloads, Einladung) rendert `web/`.
Python liefert:

- `GET /public-api/downloads`: Liste der Dateien mit Groesse, SHA-256 und Beschreibung,
- `GET /public-api/privacy`: Datenschutzhinweis mit Version (dieselbe Quelle wie /capabilities),
- `GET /downloads/<datei>`: die Datei selbst.

Dateinamen werden streng geprueft, damit nichts ausserhalb des Download-Ordners ausgeliefert wird.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, PlainTextResponse, Response

from .config import Settings

log = logging.getLogger("driverpilot.public")
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
_HASH_CACHE: dict[str, tuple[int, int, str]] = {}  # Pfad -> (Groesse, mtime_ns, sha256)


def describe(name: str) -> tuple[str, str]:
    """(Art, Beschreibung) fuer die Downloadseite."""
    lower = name.lower()
    if "-setup-" in lower and lower.endswith(".zip"):
        return "setup", "Installation (empfohlen): enthält Setup, Zertifikat und Zertifikat-Anleitung"
    if lower.endswith("-win-x64.zip"):
        return "portable", "Portable Version und Updatepaket für eine installierte Version"
    if lower.endswith(".cer"):
        return "cert", "Christians Zertifikat (öffentlicher Teil)"
    if lower.startswith("zertifikat"):
        return "cert-guide", "Anleitung zum Zertifikat mit Fingerabdruck"
    if lower.startswith("sha256sums"):
        return "sums", "Prüfsummen aus dem GitHub-Release"
    if "-setup-" in lower and lower.endswith(".exe"):
        return "setup-exe", "Setup direkt; Browser und Defender blockieren diesen Download oft, dann die Setup-ZIP nehmen"
    return "other", ""


RANK = {"setup": 0, "portable": 1, "cert": 2, "cert-guide": 3, "sums": 4, "setup-exe": 5, "other": 6}


class Public:
    def __init__(self, settings: Settings, privacy_notice: str = ""):
        self.settings = settings
        self.privacy_notice = privacy_notice
        self.downloads_dir = Path(settings.downloads_dir)

    def entries_json(self) -> list[dict]:
        entries = []
        if not self.downloads_dir.is_dir():
            return entries
        for path in self.downloads_dir.iterdir():
            if not path.is_file() or not FILENAME_RE.match(path.name) or path.suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            stat = path.stat()
            key = str(path)
            cached = _HASH_CACHE.get(key)
            if cached is None or cached[0] != stat.st_size or cached[1] != stat.st_mtime_ns:
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1 << 20), b""):
                        digest.update(chunk)
                cached = (stat.st_size, stat.st_mtime_ns, digest.hexdigest())
                _HASH_CACHE[key] = cached
            kind, text = describe(path.name)
            version = re.search(r"-(\d+\.\d+\.\d+)-", path.name)
            entries.append({
                "name": path.name, "size": stat.st_size, "sha256": cached[2], "mtime": stat.st_mtime,
                "kind": kind, "description": text, "version": version.group(1) if version else None,
            })
        entries.sort(key=lambda e: (RANK[e["kind"]], e["name"]))
        return entries

    async def downloads_json(self, request: Request) -> Response:
        return JSONResponse({"files": self.entries_json()}, headers={"Cache-Control": "no-store"})

    async def privacy_json(self, request: Request) -> Response:
        return JSONResponse({"version": self.settings.privacy_notice_version, "text": self.privacy_notice},
                            headers={"Cache-Control": "no-store"})

    async def download_file(self, request: Request) -> Response:
        name = request.path_params["name"]
        not_found = PlainTextResponse("Datei nicht gefunden.", status_code=404, headers={"Cache-Control": "no-store"})
        if not FILENAME_RE.match(name) or Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
            return not_found
        path = self.downloads_dir / name
        if not path.is_file() or path.resolve().parent != self.downloads_dir.resolve():
            return not_found
        response = FileResponse(str(path), media_type=MEDIA_TYPES[path.suffix.lower()], filename=name)
        response.headers["Cache-Control"] = "public, max-age=3600"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response
