"""Oeffentliche Daten-Endpunkte und Datei-Auslieferung (nur erlaubte Dateien, kein Pfadausbruch)."""

from __future__ import annotations

import hashlib

from conftest import SCENARIO, Harness


def test_privacy_json(h):
    data = h.api.get("/public-api/privacy").json()
    assert data["version"] == SCENARIO["privacy_notice_version"] and "Datenschutzhinweis" in data["text"]


def test_downloads_listing_and_file(tmp_path, contract):
    downloads = tmp_path / "dl"
    downloads.mkdir()
    (downloads / "DriverPilot-0.3.4-win-x64.zip").write_bytes(b"PK\x03\x04synthetic")
    (downloads / "SHA256SUMS.txt").write_text("abc  x\n")
    (downloads / "secret.sqlite3").write_bytes(b"nope")  # nicht erlaubte Endung
    (downloads / ".hidden.txt").write_text("nope")  # versteckt
    h = Harness(tmp_path, contract, DP_DOWNLOADS_DIR=str(downloads))
    try:
        files = h.api.get("/public-api/downloads").json()["files"]
        names = [f["name"] for f in files]
        assert names == ["DriverPilot-0.3.4-win-x64.zip", "SHA256SUMS.txt"]
        assert files[0]["sha256"] == hashlib.sha256(b"PK\x03\x04synthetic").hexdigest()
        assert files[0]["kind"] == "portable" and files[0]["version"] == "0.3.4"

        file = h.api.get("/downloads/DriverPilot-0.3.4-win-x64.zip")
        assert file.status_code == 200 and file.content == b"PK\x03\x04synthetic"
        assert file.headers["content-type"] == "application/zip"
        assert "attachment" in file.headers["content-disposition"]

        for bad in ("secret.sqlite3", ".hidden.txt", "..%2F..%2Fetc%2Fpasswd", "nope.zip", "a%00.zip"):
            response = h.api.get(f"/downloads/{bad}")
            assert response.status_code == 404, bad
            assert response.headers["cache-control"] == "no-store"
        assert h.api.get("/api/v1/nope").json()["error"]["code"] == "not_found"
    finally:
        h.close()


def test_setup_zip_created_on_startup_and_listed_first(tmp_path, contract):
    downloads = tmp_path / "dl"
    downloads.mkdir()
    (downloads / "DriverPilot-0.3.4-Setup-x64.exe").write_bytes(b"MZ-synthetic")
    (downloads / "DriverPilot-0.3.4-win-x64.zip").write_bytes(b"PK-synthetic")
    (downloads / "DriverPilot.cer").write_bytes(b"CER")
    h = Harness(tmp_path, contract, DP_DOWNLOADS_DIR=str(downloads))
    try:
        assert (downloads / "DriverPilot-0.3.4-Setup-x64.zip").is_file()
        files = h.api.get("/public-api/downloads").json()["files"]
        assert [f["kind"] for f in files] == ["setup", "portable", "cert", "setup-exe"]
    finally:
        h.close()


def test_missing_downloads_dir_is_harmless(tmp_path, contract):
    h = Harness(tmp_path, contract, DP_DOWNLOADS_DIR=str(tmp_path / "gibt-es-nicht"))
    try:
        assert h.api.get("/public-api/downloads").json() == {"files": []}
    finally:
        h.close()
