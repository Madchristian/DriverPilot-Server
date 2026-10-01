"""Konfiguration aus Umgebungsvariablen. Keine Geheimnisse im Repo.

Alle Limits sind Pilotdefaults aus contract/v1/rules.json. Sie duerfen per
Umgebung verschaerft, aber nicht ueber die Schemagrenzen hinaus gelockert werden
(wird in Settings.__post_init__ erzwungen).
"""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parent
CONTRACT_DIR = Path(os.environ.get("DP_CONTRACT_DIR", REPO_DIR / "contract" / "v1"))

PROTOCOL_VERSION = "1.0"
REPORT_SCHEMA_VERSIONS = ["1.0"]
RESULT_SCHEMA_VERSION = "1.0"

# Harte Obergrenzen aus den Schemas (capabilities.schema.json). Eine Konfiguration darf
# darueber nicht hinaus.
SCHEMA_MAX = {
    "max_upload_bytes": 262144,
    "max_scan_age_seconds": 900,
    "max_future_skew_seconds": 300,
    "case_retention_days": 7,
}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("DP_DATA_DIR", REPO_DIR / "data")))
    api_host: str = field(default_factory=lambda: os.environ.get("DP_API_HOST", "0.0.0.0"))
    api_port: int = field(default_factory=lambda: _env_int("DP_API_PORT", 8140))
    admin_host: str = field(default_factory=lambda: os.environ.get("DP_ADMIN_HOST", "0.0.0.0"))
    admin_port: int = field(default_factory=lambda: _env_int("DP_ADMIN_PORT", 8141))

    # Reverse Proxies, deren Forwarded-/Client-IP-Header vertraut wird (API-Seite).
    api_trusted_proxies: list[str] = field(default_factory=lambda: _env_list("DP_API_TRUSTED_PROXIES", []))
    # Gemeinsames Token zwischen SvelteKit-Oberflaeche (web/) und interner Admin-API (Port 8141).
    admin_api_token: str = field(default_factory=lambda: os.environ.get("DP_ADMIN_API_TOKEN", ""))

    privacy_notice_version: str = field(default_factory=lambda: os.environ.get("DP_PRIVACY_NOTICE_VERSION", "2026-10-01.2"))
    privacy_notice_file: Path = field(
        default_factory=lambda: Path(os.environ.get("DP_PRIVACY_NOTICE_FILE", REPO_DIR / "privacy_notice.txt"))
    )

    # Modelladapter: none (Default, rein manuell) | test (synthetisch, klar markiert) | codex (ChatGPT-OAuth).
    ai_provider: str = field(default_factory=lambda: os.environ.get("DP_AI_PROVIDER", "none"))
    codex_model: str = field(default_factory=lambda: os.environ.get("DP_CODEX_MODEL", "gpt-5.6-sol"))
    codex_reasoning: str = field(default_factory=lambda: os.environ.get("DP_CODEX_REASONING", ""))
    codex_client_id: str = field(default_factory=lambda: os.environ.get("DP_CODEX_OAUTH_CLIENT_ID", "app_EMoamEEZ73f0CkXaXp7hrann"))
    codex_issuer: str = field(default_factory=lambda: os.environ.get("DP_CODEX_OAUTH_ISSUER", "https://auth.openai.com"))
    codex_base_url: str = field(default_factory=lambda: os.environ.get("DP_CODEX_BASE_URL", "https://chatgpt.com/backend-api/codex"))
    ai_daily_calls: int = field(default_factory=lambda: _env_int("DP_AI_DAILY_CALLS", 10))
    ai_timeout_seconds: int = field(default_factory=lambda: _env_int("DP_AI_TIMEOUT_SECONDS", 90))
    ai_max_attempts: int = field(default_factory=lambda: _env_int("DP_AI_MAX_ATTEMPTS", 2))
    worker_lease_seconds: int = field(default_factory=lambda: _env_int("DP_WORKER_LEASE_SECONDS", 180))

    # Limits (rules.json). Verschaerfen erlaubt, lockern nicht.
    max_upload_bytes: int = field(default_factory=lambda: _env_int("DP_MAX_UPLOAD_BYTES", 262144))
    max_result_bytes: int = 65536
    max_scan_age_seconds: int = field(default_factory=lambda: _env_int("DP_MAX_SCAN_AGE_SECONDS", 900))
    max_future_skew_seconds: int = field(default_factory=lambda: _env_int("DP_MAX_FUTURE_SKEW_SECONDS", 300))
    max_observation_window_seconds: int = 86400
    invitation_ttl_seconds: int = field(default_factory=lambda: _env_int("DP_INVITATION_TTL_SECONDS", 86400))
    access_token_ttl_days: int = field(default_factory=lambda: _env_int("DP_ACCESS_TOKEN_TTL_DAYS", 30))
    case_retention_days: int = field(default_factory=lambda: _env_int("DP_CASE_RETENTION_DAYS", 7))
    max_feedback_per_case: int = 10
    max_new_cases_per_client_per_day: int = field(default_factory=lambda: _env_int("DP_MAX_NEW_CASES_PER_CLIENT_PER_DAY", 5))
    max_new_cases_global_per_day: int = field(default_factory=lambda: _env_int("DP_MAX_NEW_CASES_GLOBAL_PER_DAY", 30))
    max_open_cases_global: int = field(default_factory=lambda: _env_int("DP_MAX_OPEN_CASES_GLOBAL", 100))
    client_requests_per_minute: int = field(default_factory=lambda: _env_int("DP_CLIENT_REQUESTS_PER_MINUTE", 30))
    pairing_failures_per_ip: int = field(default_factory=lambda: _env_int("DP_PAIRING_FAILURES_PER_IP", 5))
    pairing_failure_window_seconds: int = field(default_factory=lambda: _env_int("DP_PAIRING_FAILURE_WINDOW_SECONDS", 900))
    audit_retention_days: int = 30

    public_base_url: str = field(default_factory=lambda: os.environ.get("DP_PUBLIC_BASE_URL", ""))
    # Release-Dateien des Windows-Clients fuer die oeffentliche Downloadseite (read-only Verzeichnis).
    downloads_dir: Path = field(default_factory=lambda: Path(os.environ.get("DP_DOWNLOADS_DIR", REPO_DIR / "downloads")))
    # Release-Sync von GitHub: Repo des Windows-Clients, Token (Contents: read), Webhook-Secret,
    # Bearer-Token fuer POST /hooks/sync-release. Leer = Funktion aus.
    client_repo: str = field(default_factory=lambda: os.environ.get("DP_CLIENT_REPO", "Madchristian/DriverPilot"))
    github_token: str = field(default_factory=lambda: os.environ.get("DP_GITHUB_TOKEN", ""))
    github_webhook_secret: str = field(default_factory=lambda: os.environ.get("DP_GITHUB_WEBHOOK_SECRET", ""))
    release_sync_token: str = field(default_factory=lambda: os.environ.get("DP_RELEASE_SYNC_TOKEN", ""))
    releases_keep: int = field(default_factory=lambda: _env_int("DP_RELEASES_KEEP", 2))

    def __post_init__(self) -> None:
        if self.ai_provider not in ("none", "test", "codex"):
            raise ValueError(f"DP_AI_PROVIDER unbekannt: {self.ai_provider!r} (erlaubt: none, test, codex)")
        for key, ceiling in SCHEMA_MAX.items():
            value = getattr(self, key)
            if value < 1 or value > ceiling:
                raise ValueError(f"{key}={value} liegt ausserhalb von 1..{ceiling}")
        self.data_dir = Path(self.data_dir)
        self.privacy_notice_file = Path(self.privacy_notice_file)
        self.downloads_dir = Path(self.downloads_dir)

    @property
    def ai_configured(self) -> bool:
        """Ein Adapter ist konfiguriert; ob er gerade verfuegbar ist (Login), weiss nur der Adapter."""
        return self.ai_provider != "none"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "driverpilot.sqlite3"

    def load_privacy_notice(self) -> str:
        text = self.privacy_notice_file.read_text("utf-8").strip()
        if not text:
            raise ValueError("Datenschutzhinweis ist leer")
        return text

    def load_or_create_secret(self) -> bytes:
        """Serverlokales Geheimnis fuer ETag-HMAC und CSRF; liegt nur im Datenverzeichnis."""
        path = self.data_dir / "server.secret"
        if path.exists():
            return path.read_bytes().strip()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        secret = secrets.token_bytes(32).hex().encode("ascii")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(secret)
        return secret

    def describe(self) -> dict:
        """Nicht geheime Konfiguration fuer die Adminansicht."""
        return {
            "ai_provider": self.ai_provider,
            "codex_model": self.codex_model if self.ai_provider == "codex" else None,
            "ai_daily_calls": self.ai_daily_calls,
            "ai_timeout_seconds": self.ai_timeout_seconds,
            "max_upload_bytes": self.max_upload_bytes,
            "max_scan_age_seconds": self.max_scan_age_seconds,
            "case_retention_days": self.case_retention_days,
            "max_new_cases_per_client_per_day": self.max_new_cases_per_client_per_day,
            "max_new_cases_global_per_day": self.max_new_cases_global_per_day,
            "max_open_cases_global": self.max_open_cases_global,
            "privacy_notice_version": self.privacy_notice_version,
            "public_base_url": self.public_base_url,
            "releases_keep": self.releases_keep,
            "client_repo": self.client_repo,
        }

    def to_json(self) -> str:
        return json.dumps(self.describe(), ensure_ascii=False, indent=2)
