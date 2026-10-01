"""Release-Sync gegen ein nachgebildetes GitHub: Warten auf Dateien, Pruefsummen, Aufraeumen,
Webhook-Signatur und Bearer-Endpunkt."""

from __future__ import annotations

import hashlib
import hmac
import json

import httpx
import pytest

from conftest import Harness
from driverpilot_server.releases import ReleaseSync, SyncError, verify_github_signature

REPO = "Madchristian/DriverPilot"


class FakeGitHub:
    """Release mit Dateien; `uploaded` steuert, welche Dateien schon am Release haengen."""

    def __init__(self, tag: str, files: dict[str, bytes], sums_override: str | None = None, prerelease: bool = False):
        self.tag = tag
        self.prerelease = prerelease
        self.files = dict(files)
        sums = "\n".join(f"{hashlib.sha256(data).hexdigest()}  {name}" for name, data in files.items()) + "\n"
        self.files["SHA256SUMS.txt"] = (sums_override or sums).encode()
        self.uploaded = set(self.files)
        self.calls = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        path = request.url.path
        if request.headers.get("authorization") != "Bearer SYNTHETIC-token":
            return httpx.Response(401)
        if path in (f"/repos/{REPO}/releases/tags/{self.tag}", f"/repos/{REPO}/releases/latest"):
            assets = [{"name": n, "url": f"https://api.test/assets/{n}", "size": len(self.files[n]), "state": "uploaded"} for n in sorted(self.uploaded)]
            if path.endswith("/latest") and self.prerelease:
                return httpx.Response(404)
            return httpx.Response(200, json={"tag_name": self.tag, "draft": False, "prerelease": self.prerelease, "assets": assets})
        if path.startswith("/assets/"):
            name = path.split("/")[-1]
            if name in self.uploaded:
                return httpx.Response(200, content=self.files[name])
        return httpx.Response(404)


def make_sync(tmp_path, fake: FakeGitHub, **kwargs) -> ReleaseSync:
    client = httpx.Client(transport=httpx.MockTransport(fake.handler))
    return ReleaseSync(REPO, "SYNTHETIC-token", tmp_path / "dl", http=client, api_base="https://api.test", poll_seconds=0, wait_seconds=1, **kwargs)


def test_sync_downloads_verifies_and_prunes(tmp_path):
    fake = FakeGitHub("v0.4.0", {"DriverPilot-0.4.0-Setup-x64.exe": b"EXE4", "DriverPilot-0.4.0-win-x64.zip": b"ZIP4", "DriverPilot.cer": b"CER"})
    sync = make_sync(tmp_path, fake, keep_versions=1)
    dl = tmp_path / "dl"
    dl.mkdir()
    (dl / "DriverPilot-0.3.4-Setup-x64.exe").write_bytes(b"old")
    (dl / "DriverPilot-0.3.4-win-x64.zip").write_bytes(b"old")
    files = sync.run("v0.4.0")
    assert files == ["DriverPilot-0.4.0-Setup-x64.exe", "DriverPilot-0.4.0-Setup-x64.zip", "DriverPilot-0.4.0-win-x64.zip", "DriverPilot.cer", "SHA256SUMS.txt"]
    assert (dl / "DriverPilot-0.4.0-win-x64.zip").read_bytes() == b"ZIP4"
    assert not (dl / "DriverPilot-0.3.4-win-x64.zip").exists()  # keep_versions=1
    assert not any(p.name.startswith(".incoming") for p in dl.iterdir())
    assert oct((dl / "DriverPilot.cer").stat().st_mode & 0o777) == "0o644"


def test_setup_zip_is_created_and_pruned_per_kind(tmp_path):
    import zipfile

    fake = FakeGitHub("v0.4.0", {"DriverPilot-0.4.0-Setup-x64.exe": b"EXE4", "DriverPilot-0.4.0-win-x64.zip": b"ZIP4",
                                 "DriverPilot.cer": b"CER", "ZERTIFIKAT-ANLEITUNG.txt": b"TXT"})
    sync = make_sync(tmp_path, fake, keep_versions=1)
    dl = tmp_path / "dl"
    dl.mkdir()
    for old in ("DriverPilot-0.3.4-Setup-x64.exe", "DriverPilot-0.3.4-Setup-x64.zip", "DriverPilot-0.3.4-win-x64.zip"):
        (dl / old).write_bytes(b"old")
    files = sync.run("v0.4.0")
    assert "DriverPilot-0.4.0-Setup-x64.zip" in files
    with zipfile.ZipFile(dl / "DriverPilot-0.4.0-Setup-x64.zip") as archive:
        assert sorted(archive.namelist()) == ["DriverPilot-0.4.0-Setup-x64.exe", "DriverPilot.cer", "ZERTIFIKAT-ANLEITUNG.txt"]
        assert archive.read("DriverPilot-0.4.0-Setup-x64.exe") == b"EXE4"
    remaining = sorted(p.name for p in dl.iterdir() if not p.name.startswith("."))
    assert remaining == ["DriverPilot-0.4.0-Setup-x64.exe", "DriverPilot-0.4.0-Setup-x64.zip", "DriverPilot-0.4.0-win-x64.zip",
                         "DriverPilot.cer", "SHA256SUMS.txt", "ZERTIFIKAT-ANLEITUNG.txt"]


def test_manifest_switches_generation_and_hides_leftovers(tmp_path):
    from driverpilot_server.releases import read_manifest

    fake = FakeGitHub("v0.4.0", {"DriverPilot-0.4.0-Setup-x64.exe": b"EXE4", "DriverPilot.cer": b"CER"})
    sync = make_sync(tmp_path, fake, keep_versions=5)
    dl = tmp_path / "dl"
    dl.mkdir()
    (dl / "DriverPilot-0.3.4-win-x64.zip").write_bytes(b"old")  # bleibt liegen (keep=5), aber nicht sichtbar
    sync.run("v0.4.0")
    manifest = read_manifest(dl)
    assert manifest["tag"] == "v0.4.0" and manifest["source"] == "sync"
    assert manifest["files"] == ["DriverPilot-0.4.0-Setup-x64.exe", "DriverPilot-0.4.0-Setup-x64.zip", "DriverPilot.cer", "SHA256SUMS.txt"]
    assert sync.current_tag() == "v0.4.0"


def test_prerelease_is_refused_by_sync_and_webhook(tmp_path, contract):
    fake = FakeGitHub("v0.5.0-rc1", {"DriverPilot-0.5.0-win-x64.zip": b"RC"}, prerelease=True)
    with pytest.raises(SyncError, match="Vorabversion"):
        make_sync(tmp_path, fake).run("v0.5.0-rc1")
    assert not (tmp_path / "dl" / ".manifest.json").exists()
    h = Harness(tmp_path, contract, DP_GITHUB_WEBHOOK_SECRET="hook-secret", DP_GITHUB_TOKEN="SYNTHETIC-token")
    try:
        triggered = []
        h.service.releases.trigger = lambda tag, source: triggered.append(tag) or True
        body, headers = signed("hook-secret", {"action": "published", "repository": {"full_name": REPO}, "release": {"tag_name": "v0.5.0-rc1", "prerelease": True}}, "release")
        assert h.api.post("/hooks/github", content=body, headers=headers).json()["reason"] == "prerelease"
        assert triggered == []
    finally:
        h.close()


def test_reconcile_triggers_only_when_latest_differs(tmp_path):
    fake = FakeGitHub("v0.4.1", {"DriverPilot-0.4.1-win-x64.zip": b"Z"})
    sync = make_sync(tmp_path, fake)
    triggered = []
    sync.trigger = lambda tag, source: triggered.append((tag, source)) or True
    assert sync.reconcile() == "triggered" and triggered == [("v0.4.1", "reconcile")]
    sync.run("v0.4.1")  # Generation jetzt aktuell
    assert sync.reconcile() == "current" and sync.last_reconcile["message"] == "aktuell"
    unconfigured = ReleaseSync(REPO, "", tmp_path / "x")
    assert unconfigured.reconcile() == "unconfigured"


def test_sync_waits_until_all_assets_uploaded(tmp_path):
    fake = FakeGitHub("v0.4.0", {"DriverPilot-0.4.0-win-x64.zip": b"ZIP4"})
    fake.uploaded = {"SHA256SUMS.txt"}  # zip fehlt noch
    sync = make_sync(tmp_path, fake)
    original = fake.handler

    def later(request):
        if fake.calls >= 3:
            fake.uploaded = set(fake.files)
        return original(request)

    sync.http = httpx.Client(transport=httpx.MockTransport(later))
    assert sync.run("v0.4.0") == ["DriverPilot-0.4.0-win-x64.zip", "SHA256SUMS.txt"]


def test_sync_rejects_checksum_mismatch_and_leaves_nothing(tmp_path):
    bad_sums = f"{'0' * 64}  DriverPilot-0.4.0-win-x64.zip\n"
    fake = FakeGitHub("v0.4.0", {"DriverPilot-0.4.0-win-x64.zip": b"ZIP4"}, sums_override=bad_sums)
    sync = make_sync(tmp_path, fake)
    with pytest.raises(SyncError, match="Pruefsumme"):
        sync.run("v0.4.0")
    dl = tmp_path / "dl"
    assert not (dl / "DriverPilot-0.4.0-win-x64.zip").exists() and not any(dl.iterdir())


def test_sync_missing_sums_times_out(tmp_path):
    fake = FakeGitHub("v0.4.0", {"DriverPilot-0.4.0-win-x64.zip": b"ZIP4"})
    fake.uploaded = {"DriverPilot-0.4.0-win-x64.zip"}
    with pytest.raises(SyncError, match="SHA256SUMS"):
        make_sync(tmp_path, fake).run("v0.4.0")


def test_sync_unconfigured(tmp_path):
    sync = ReleaseSync(REPO, "", tmp_path / "dl")
    with pytest.raises(SyncError, match="nicht konfiguriert"):
        sync.run(None)


def test_signature_helper():
    body = b'{"x":1}'
    good = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert verify_github_signature("s3cret", body, good)
    assert not verify_github_signature("s3cret", body, "sha256=00")
    assert not verify_github_signature("", body, good)
    assert not verify_github_signature("s3cret", body, None)


def signed(secret: str, payload: dict, event: str) -> tuple[bytes, dict]:
    body = json.dumps(payload).encode()
    return body, {"X-Hub-Signature-256": "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(), "X-GitHub-Event": event, "Content-Type": "application/json"}


def test_webhook_and_sync_endpoint(tmp_path, contract, monkeypatch):
    h = Harness(tmp_path, contract, DP_GITHUB_WEBHOOK_SECRET="hook-secret", DP_RELEASE_SYNC_TOKEN="sync-token", DP_GITHUB_TOKEN="SYNTHETIC-token")
    try:
        triggered = []
        h.service.releases.trigger = lambda tag, source: triggered.append((tag, source)) or True
        release = {"action": "published", "repository": {"full_name": REPO}, "release": {"tag_name": "v0.4.0"}}

        body, headers = signed("hook-secret", release, "release")
        assert h.api.post("/hooks/github", content=body, headers=headers).status_code == 202
        assert triggered == [("v0.4.0", "github-webhook")]

        body, headers = signed("falsch", release, "release")
        assert h.api.post("/hooks/github", content=body, headers=headers).status_code == 401
        body, headers = signed("hook-secret", {"zen": "x"}, "ping")
        assert h.api.post("/hooks/github", content=body, headers=headers).json()["event"] == "ping"
        body, headers = signed("hook-secret", dict(release, action="deleted"), "release")
        assert h.api.post("/hooks/github", content=body, headers=headers).json()["reason"] == "ignored"
        body, headers = signed("hook-secret", dict(release, repository={"full_name": "someone/else"}), "release")
        assert h.api.post("/hooks/github", content=body, headers=headers).json()["reason"] == "ignored"
        assert len(triggered) == 1

        assert h.api.post("/hooks/sync-release", json={"tag": "v0.4.1"}).status_code == 401
        assert h.api.post("/hooks/sync-release", json={"tag": "v0.4.1"}, headers={"Authorization": "Bearer wrong"}).status_code == 401
        ok = h.api.post("/hooks/sync-release", json={"tag": "v0.4.1"}, headers={"Authorization": "Bearer sync-token"})
        assert ok.status_code == 202 and triggered[-1] == ("v0.4.1", "sync-endpoint")
        latest = h.api.post("/hooks/sync-release", headers={"Authorization": "Bearer sync-token"})
        assert latest.status_code == 202 and triggered[-1] == (None, "sync-endpoint")
        assert h.api.post("/hooks/sync-release", json={"tag": "../x"}, headers={"Authorization": "Bearer sync-token"}).status_code == 400

        page = h.admin.get("/admin-api/releases")
        assert page.status_code == 200 and page.json()["configured"] is True and page.json()["webhook_configured"] is True
    finally:
        h.close()


def test_hooks_absent_when_unconfigured(h):
    assert h.api.post("/hooks/github", content=b"{}").status_code == 404
    assert h.api.post("/hooks/sync-release", content=b"{}").status_code == 404
    assert h.api.post("/hooks/github", content=b"{}").json()["error"]["code"] == "not_found"
