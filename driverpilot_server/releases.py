"""Release-Sync: Dateien eines DriverPilot-Releases von GitHub in den Download-Ordner holen.

Ausloeser sind der signierte GitHub-Webhook (Ereignis `release`) oder der Endpunkt
`POST /hooks/sync-release` mit Bearer-Token (CI oder Hand) sowie die Adminseite „Releases“.
Der Workflow im Client-Repo legt das Release mit `gh release create <tag> ./*` an; GitHub meldet
`published` schon, bevor alle Dateien hochgeladen sind. Der Sync wartet deshalb, bis
`SHA256SUMS.txt` und alle darin gelisteten Dateien am Release haengen, prueft jede Datei gegen
die Pruefsumme und tauscht erst dann atomar in den Download-Ordner.

Es laeuft hoechstens ein Sync gleichzeitig. Token und Secret stehen nur in der Umgebung.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import shutil
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .public import ALLOWED_SUFFIXES, FILENAME_RE

log = logging.getLogger("driverpilot.releases")
SUMS_NAME = "SHA256SUMS.txt"
MANIFEST_NAME = ".manifest.json"
VERSIONED_RE = re.compile(r"^DriverPilot-(\d+\.\d+\.\d+)-(.*\.(?:exe|zip))$")
SETUP_EXE_RE = re.compile(r"^(DriverPilot-\d+\.\d+\.\d+-Setup-[A-Za-z0-9]+)\.exe$")
SETUP_ZIP_EXTRAS = ("DriverPilot.cer", "ZERTIFIKAT-ANLEITUNG.txt")


def ensure_setup_zips(downloads_dir: Path) -> list[str]:
    """Legt zu jeder Setup-EXE eine gleichnamige ZIP an (EXE, Zertifikat, Zertifikat-Anleitung).

    Browser und SmartScreen blockieren den direkten Download einer EXE ohne Reputation oft; als ZIP
    kommt die Datei an. Der Inhalt bleibt die unveraenderte, signierte EXE. Defender prueft sie beim
    Entpacken und Starten wie jede andere Datei.
    """
    created = []
    downloads_dir = Path(downloads_dir)
    if not downloads_dir.is_dir():
        return created
    for exe in sorted(downloads_dir.iterdir()):
        match = SETUP_EXE_RE.match(exe.name)
        if not match or not exe.is_file():
            continue
        target = downloads_dir / f"{match.group(1)}.zip"
        if target.exists() and target.stat().st_mtime >= exe.stat().st_mtime:
            continue
        tmp = downloads_dir / f".{target.name}.tmp"
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.write(exe, exe.name)
            for extra in SETUP_ZIP_EXTRAS:
                if (downloads_dir / extra).is_file():
                    archive.write(downloads_dir / extra, extra)
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
        created.append(target.name)
        log.info("Setup-ZIP angelegt: %s", target.name)
    manifest = read_manifest(downloads_dir)
    if created and manifest is not None:
        write_manifest(downloads_dir, manifest.get("tag", "?"), list(manifest["files"]) + created, manifest.get("source", "startup"))
    return created
MAX_ASSET_BYTES = 600 * 1024 * 1024


class SyncError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_manifest(downloads_dir: Path) -> dict | None:
    """Aktuelle Generation: {"tag", "files", "switched_at"} oder None (kein Manifest, flache Liste)."""
    path = Path(downloads_dir) / MANIFEST_NAME
    try:
        data = json.loads(path.read_text("utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        return None
    return data


def write_manifest(downloads_dir: Path, tag: str, files: list[str], source: str) -> None:
    """Atomar: Die sichtbare Dateimenge wechselt mit genau einem rename."""
    path = Path(downloads_dir) / MANIFEST_NAME
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"tag": tag, "files": sorted(set(files)), "switched_at": _now(), "source": source}, indent=2), "utf-8")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def verify_github_signature(secret: str, body: bytes, header: str | None) -> bool:
    if not secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[len("sha256="):])


class ReleaseSync:
    def __init__(self, repo: str, token: str, downloads_dir: Path, keep_versions: int = 2,
                 http: httpx.Client | None = None, audit=None, wait_seconds: int = 900, poll_seconds: int = 20,
                 api_base: str = "https://api.github.com"):
        self.repo = repo
        self.token = token
        self.downloads_dir = Path(downloads_dir)
        self.keep_versions = max(1, keep_versions)
        self.http = http or httpx.Client(timeout=httpx.Timeout(120, connect=20), follow_redirects=True)
        self.audit = audit
        self.wait_seconds = wait_seconds
        self.poll_seconds = poll_seconds
        self.api_base = api_base.rstrip("/")
        self.lock = threading.Lock()
        self.last: dict = {"state": "idle"}
        self.last_reconcile: dict = {"state": "idle"}

    # ------------------------------------------------------------------ Ausloeser

    def configured(self) -> bool:
        return bool(self.repo and self.token)

    def trigger(self, tag: str | None, source: str) -> bool:
        """Startet den Sync im Hintergrund. False, wenn gerade einer laeuft."""
        if not self.lock.acquire(blocking=False):
            return False
        self.last = {"state": "running", "tag": tag or "latest", "source": source, "started_at": _now()}
        threading.Thread(target=self._run_locked, args=(tag, source), daemon=True, name="release-sync").start()
        return True

    def _run_locked(self, tag: str | None, source: str) -> None:
        try:
            files = self.run(tag)
            self.last.update(state="done", finished_at=_now(), files=files, message=f"{len(files)} Dateien uebernommen")
            if self.audit:
                self.audit(source, "release.sync", None, "ok", f"tag={self.last.get('tag')} files={len(files)}")
        except Exception as exc:  # noqa: BLE001 - Ergebnis landet sichtbar auf der Adminseite
            log.warning("Release-Sync fehlgeschlagen (%s): %s", tag or "latest", exc)
            self.last.update(state="failed", finished_at=_now(), message=str(exc)[:300])
            if self.audit:
                self.audit(source, "release.sync", None, "failed", str(exc)[:200])
        finally:
            self.lock.release()

    # ------------------------------------------------------------------ Ablauf

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "driverpilot-server"}

    def _release(self, tag: str | None) -> dict:
        path = f"/repos/{self.repo}/releases/tags/{tag}" if tag else f"/repos/{self.repo}/releases/latest"
        response = self.http.get(self.api_base + path, headers=self._headers())
        if response.status_code == 404:
            raise SyncError("Release nicht gefunden (oder Token ohne Zugriff)")
        if response.status_code == 401:
            raise SyncError("GitHub-Token ungueltig (401)")
        if response.status_code >= 400:
            raise SyncError(f"GitHub API HTTP {response.status_code}")
        return response.json()

    def _wait_for_assets(self, tag: str | None) -> tuple[dict, dict[str, str]]:
        """Pollt, bis SHA256SUMS.txt und alle gelisteten Dateien am Release haengen."""
        deadline = time.monotonic() + self.wait_seconds
        while True:
            release = self._release(tag)
            if release.get("draft"):
                raise SyncError("Release ist noch ein Entwurf")
            assets = {a["name"]: a for a in release.get("assets", []) if a.get("state", "uploaded") == "uploaded"}
            if SUMS_NAME in assets:
                sums = self._parse_sums(self._download_bytes(assets[SUMS_NAME]))
                missing = [name for name in sums if name not in assets]
                if not missing:
                    return release, sums
                reason = f"warte auf Dateien: {', '.join(missing)}"
            else:
                reason = f"warte auf {SUMS_NAME}"
            if time.monotonic() >= deadline:
                raise SyncError(f"Release {release.get('tag_name')} unvollstaendig, {reason}")
            self.last["message"] = reason
            time.sleep(self.poll_seconds)

    @staticmethod
    def _parse_sums(data: bytes) -> dict[str, str]:
        sums = {}
        for line in data.decode("utf-8", "replace").splitlines():
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            digest, name = parts[0].lower(), parts[-1].lstrip("*").split("/")[-1]
            if re.fullmatch(r"[0-9a-f]{64}", digest) and FILENAME_RE.match(name):
                sums[name] = digest
        if not sums:
            raise SyncError(f"{SUMS_NAME} ist leer oder unlesbar")
        return sums

    def _download_bytes(self, asset: dict) -> bytes:
        response = self.http.get(asset["url"], headers={**self._headers(), "Accept": "application/octet-stream"})
        if response.status_code >= 400:
            raise SyncError(f"Download {asset['name']}: HTTP {response.status_code}")
        return response.content

    def _download_to(self, asset: dict, target: Path) -> str:
        if asset.get("size", 0) > MAX_ASSET_BYTES:
            raise SyncError(f"{asset['name']} ist groesser als erlaubt")
        digest = hashlib.sha256()
        total = 0
        with self.http.stream("GET", asset["url"], headers={**self._headers(), "Accept": "application/octet-stream"}) as response:
            if response.status_code >= 400:
                raise SyncError(f"Download {asset['name']}: HTTP {response.status_code}")
            with target.open("wb") as handle:
                for chunk in response.iter_bytes(1 << 20):
                    total += len(chunk)
                    if total > MAX_ASSET_BYTES:
                        raise SyncError(f"{asset['name']} ist groesser als erlaubt")
                    digest.update(chunk)
                    handle.write(chunk)
        return digest.hexdigest()

    def run(self, tag: str | None) -> list[str]:
        if not self.configured():
            raise SyncError("Release-Sync nicht konfiguriert (DP_CLIENT_REPO / DP_GITHUB_TOKEN)")
        release, sums = self._wait_for_assets(tag)
        if release.get("prerelease"):
            raise SyncError(f"Release {release.get('tag_name')} ist eine Vorabversion und wird nicht veroeffentlicht")
        tag_name = release.get("tag_name") or tag or "latest"
        self.last["tag"] = tag_name
        assets = {a["name"]: a for a in release.get("assets", [])}
        wanted = {name for name in sums} | {SUMS_NAME}
        for name in wanted:
            if not FILENAME_RE.match(name) or Path(name).suffix.lower() not in ALLOWED_SUFFIXES:
                raise SyncError(f"Dateiname nicht erlaubt: {name}")

        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        incoming = self.downloads_dir / f".incoming-{re.sub(r'[^A-Za-z0-9._-]', '_', tag_name)}"
        if incoming.exists():
            shutil.rmtree(incoming)
        incoming.mkdir()
        try:
            # 1. Komplette Generation im Staging-Ordner: laden, pruefen, Setup-ZIP bauen.
            for name in sorted(wanted):
                self.last["message"] = f"lade {name}"
                digest = self._download_to(assets[name], incoming / name)
                if name != SUMS_NAME and digest != sums[name]:
                    raise SyncError(f"Pruefsumme von {name} stimmt nicht mit {SUMS_NAME} ueberein")
            generation = sorted(wanted | set(ensure_setup_zips(incoming)))
            # 2. Dateien unter ihrem Namen bereitstellen (alte Generation bleibt bis zum Manifestwechsel sichtbar).
            for name in generation:
                os.chmod(incoming / name, 0o644)
                os.replace(incoming / name, self.downloads_dir / name)
            # 3. Ein rename schaltet die sichtbare Dateimenge um.
            write_manifest(self.downloads_dir, tag_name, generation, self.last.get("source", "sync"))
        finally:
            shutil.rmtree(incoming, ignore_errors=True)
        self._prune()
        log.info("Release %s uebernommen: %s", tag_name, ", ".join(generation))
        return generation

    def current_tag(self) -> str | None:
        manifest = read_manifest(self.downloads_dir)
        return manifest.get("tag") if manifest else None

    def reconcile(self) -> str:
        """Regelmaessiger Abgleich: neuestes stabiles Release laut GitHub vs. aktuelle Generation."""
        if not self.configured():
            return "unconfigured"
        try:
            latest = self._release(None)  # /releases/latest: ohne Entwuerfe und Vorabversionen
        except SyncError as exc:
            self.last_reconcile = {"state": "failed", "at": _now(), "message": str(exc)[:200]}
            return "failed"
        tag = latest.get("tag_name")
        current = self.current_tag()
        self.last_reconcile = {"state": "done", "at": _now(), "latest": tag, "current": current}
        if tag and tag != current:
            started = self.trigger(tag, source="reconcile")
            self.last_reconcile["message"] = f"{tag} fehlt, Sync {'gestartet' if started else 'laeuft bereits'}"
            return "triggered" if started else "busy"
        self.last_reconcile["message"] = "aktuell"
        return "current"

    def _prune(self) -> None:
        """Behaelt je Dateiart (Setup-EXE, Setup-ZIP, portable ZIP) die neuesten `keep_versions` Versionen."""
        groups: dict[str, list[tuple[tuple[int, ...], Path]]] = {}
        for path in self.downloads_dir.iterdir():
            match = VERSIONED_RE.match(path.name)
            if match and path.is_file():
                version = tuple(int(x) for x in match.group(1).split("."))
                groups.setdefault(match.group(2), []).append((version, path))
        for paths in groups.values():
            paths.sort(reverse=True)
            for _, old in paths[self.keep_versions:]:
                try:
                    old.unlink()
                    log.info("alte Release-Datei entfernt: %s", old.name)
                except OSError:
                    pass
