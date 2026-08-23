"""backend/app/config.py

Application settings for CaseClock backend.

Values are loaded from environment variables, falling back to sensible
development defaults.  Production deployments set them via AppSail
environment configuration; never hard-code secrets here.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Service identity ────────────────────────────────────────────────────
    app_name: str = "CaseClock Backend"
    app_version: str = "0.1.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # ── CORS ────────────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins.  Production sets this to the
    # deployed Catalyst Slate URL; development defaults to local Vite dev server.
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    # ── Paths ───────────────────────────────────────────────────────────────
    # The synthetic graph artifact used as data source in the in-memory adapter.
    # Tests may override via ARTIFACT_PATH env var.
    artifact_path: Path = Field(
        default=Path("artifacts/synthetic_graph/synthetic_graph.json"),
        alias="ARTIFACT_PATH",
    )

    # State path for the in-memory adapter's mutable runtime JSON.
    # Set to empty string to disable persistence (test environments).
    state_path: str = Field(
        default="",
        alias="STATE_PATH",
    )

    caseclock_repository: str = Field(default="local", alias="CASECLOCK_REPOSITORY")
    caseclock_auth_enabled: bool = Field(default=False, alias="CASECLOCK_AUTH_ENABLED")
    auth_mode: str = Field(default="demo", alias="AUTH_MODE")
    catalyst_project_id: str = Field(default="", alias="CASECLOCK_PROJECT_ID")
    catalyst_client_id: str = Field(default="", alias="CASECLOCK_CLIENT_ID")
    catalyst_jwks_url: str = Field(default="", alias="CASECLOCK_AUTH_JWKS_URL")
    catalyst_auth_issuer: str = Field(default="", alias="CASECLOCK_AUTH_ISSUER")
    cron_secret: str = Field(default="", alias="CRON_SECRET")
    convokraft_public_key: str = Field(default="", alias="CONVOKRAFT_PUBLIC_KEY")
    convokraft_verify_signature: bool = Field(default=True, alias="CONVOKRAFT_VERIFY_SIGNATURE")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Allow extra fields from .env without raising errors during development
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parsed list of allowed CORS origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_state_path(self) -> Path | None:
        """Returns state path as Path if set, None if empty (disables persistence)."""
        if self.state_path:
            return Path(self.state_path)
        return None

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton.

    Use this in FastAPI dependency injection:
        settings: Settings = Depends(get_settings)
    """
    return Settings()
