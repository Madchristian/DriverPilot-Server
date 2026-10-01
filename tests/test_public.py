"""Oeffentliche Seiten: Anleitung, Datenschutz, Downloads (nur erlaubte Dateien, kein Pfadausbruch)."""

from __future__ import annotations

import hashlib

from conftest import Harness


def test_pages_render(h):
    for path, needle in (("/", "Anleitung für Freunde"), ("/anleitung", "Koppeln"), ("/datenschutz", "Datenschutzhinweis")):
        response = h.api.get(path)
        assert response.status_code == 200, path
        assert needle in response.text
        assert "noindex" in response.headers["x-robots-tag"]
        assert "default-src 'none'" in response.headers["content-security-policy"]
    assert h.api.get("/robots.txt").text.startswith("User-agent")
    assert h.api.get("/downloads", follow_redirects=False).status_code == 308


def test_downloads_listing_and_file(tmp_path, contract):
    downloads = tmp_path / "dl"
    downloads.mkdir()
    (downloads / "DriverPilot-0.3.4-win-x64.zip").write_bytes(b"PK\x03\x04synthetic")
    (downloads / "SHA256SUMS.txt").write_text("abc  x\n")
    (downloads / "secret.sqlite3").write_bytes(b"nope")  # nicht erlaubte Endung
    (downloads / ".hidden.txt").write_text("nope")  # versteckt
    h = Harness(tmp_path, contract, DP_DOWNLOADS_DIR=str(downloads))
    try:
        listing = h.api.get("/downloads/")
        assert listing.status_code == 200
        assert "DriverPilot-0.3.4-win-x64.zip" in listing.text and "SHA256SUMS.txt" in listing.text
        assert "secret.sqlite3" not in listing.text and ".hidden.txt" not in listing.text
        assert hashlib.sha256(b"PK\x03\x04synthetic").hexdigest() in listing.text
        assert "Portable Version" in listing.text

        file = h.api.get("/downloads/DriverPilot-0.3.4-win-x64.zip")
        assert file.status_code == 200 and file.content == b"PK\x03\x04synthetic"
        assert file.headers["content-type"] == "application/zip"
        assert "attachment" in file.headers["content-disposition"]

        for bad in ("secret.sqlite3", ".hidden.txt", "..%2F..%2Fetc%2Fpasswd", "nope.zip", "a%00.zip"):
            assert h.api.get(f"/downloads/{bad}").status_code == 404, bad
        # API bleibt JSON, Seiten bleiben HTML
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
        text = h.api.get("/downloads/").text
        assert text.index("DriverPilot-0.3.4-Setup-x64.zip") < text.index("DriverPilot-0.3.4-win-x64.zip")
        assert "Installation (empfohlen)" in text
    finally:
        h.close()


def test_missing_downloads_dir_is_harmless(tmp_path, contract):
    h = Harness(tmp_path, contract, DP_DOWNLOADS_DIR=str(tmp_path / "gibt-es-nicht"))
    try:
        response = h.api.get("/downloads/")
        assert response.status_code == 200 and "keine Dateien" in response.text
    finally:
        h.close()
