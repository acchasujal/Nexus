"""backend/app/config.py

Application settings for the NEXUS Criminal Intelligence Platform.
Local-first, deterministic defaults with PostgreSQL, Neo4j, and Docker support.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Service Identity ────────────────────────────────────────────────────
    app_name: str = "NEXUS Criminal Intelligence Platform"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # ── CORS ────────────────────────────────────────────────────────────────
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,https://nexus-eight-weld-33.vercel.app",
        alias="CORS_ORIGINS",
    )

    # ── Paths ───────────────────────────────────────────────────────────────
    artifact_path: Path = Field(
        default=Path("artifacts/nexus_graph/nexus_graph.json"),
        alias="ARTIFACT_PATH",
    )
    state_path: str = Field(
        default="",
        alias="STATE_PATH",
    )

    # ── Database & Graph ─────────────────────────────────────────────────────
    nexus_repository: str = Field(default="local", alias="NEXUS_REPOSITORY")
    database_url: str = Field(
        default="postgresql://nexus:nexus@localhost:5432/nexus_db",
        alias="DATABASE_URL",
    )
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="nexuspassword", alias="NEO4J_PASSWORD")

    # ── Auth & Security ─────────────────────────────────────────────────────
    auth_mode: str = Field(default="demo", alias="AUTH_MODE")
    jwt_secret_key: str = Field(
        default="nexus-dev-secret-key-2026-sih",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 86400

    # ── AI & Groq / LLM Provider ─────────────────────────────────────────────
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")
    llm_model: str = Field(default="openai/gpt-oss-120b", alias="LLM_MODEL")
    llm_base_url: str = Field(
        default="https://api.groq.com/openai/v1",
        alias="LLM_BASE_URL",
    )
    nexus_use_mock_llm: bool = Field(default=False, alias="NEXUS_USE_MOCK_LLM")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_state_path(self) -> Path | None:
        if self.state_path:
            return Path(self.state_path)
        return None

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


_DEV_JWT_SECRET = "nexus-dev-secret-key-2026-sih"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    import logging as _logging

    settings = Settings()
    if settings.is_production and settings.jwt_secret_key == _DEV_JWT_SECRET:
        _logging.getLogger(__name__).warning(
            "WARNING: Using default JWT secret in production. "
            "Set JWT_SECRET_KEY environment variable to a strong random value."
        )
    return settings
