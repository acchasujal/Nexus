"""backend/app/config.py

Application settings for the NEXUS Criminal Intelligence Platform.
Local-first, deterministic defaults with PostgreSQL, Neo4j, and Docker support.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from secrets import token_urlsafe
from typing import Literal
from urllib.parse import urlsplit
import re

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@lru_cache(maxsize=1)
def development_jwt_secret() -> str:
    """Ephemeral per-process development key; never a committed credential."""
    return token_urlsafe(48)


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
    nexus_repository: str = Field(default="memory", alias="NEXUS_REPOSITORY")
    database_url: str = Field(default="", alias="DATABASE_URL", repr=False, exclude=True)
    graph_backend: Literal["memory", "neo4j"] = Field(default="memory", alias="GRAPH_BACKEND")
    neo4j_uri: str = Field(default="", alias="NEO4J_URI", repr=False)
    neo4j_user: str = Field(default="", alias="NEO4J_USER", repr=False)
    neo4j_password: SecretStr = Field(default=SecretStr(""), alias="NEO4J_PASSWORD", exclude=True)
    neo4j_database: str = Field(default="neo4j", alias="NEO4J_DATABASE")
    neo4j_connection_timeout: float = Field(default=5.0, gt=0, le=120, alias="NEO4J_CONNECTION_TIMEOUT")
    neo4j_query_timeout: float = Field(default=10.0, gt=0, le=300, alias="NEO4J_QUERY_TIMEOUT")
    neo4j_failure_policy: Literal["required", "degraded"] = Field(
        default="required", alias="NEO4J_FAILURE_POLICY",
    )

    # ── Auth & Security ─────────────────────────────────────────────────────
    auth_mode: str = Field(default="demo", alias="AUTH_MODE")
    jwt_secret_key: str = Field(
        default_factory=development_jwt_secret, alias="JWT_SECRET_KEY", repr=False, exclude=True,
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
        hide_input_in_errors=True,
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def empty_development_key(cls, value: str) -> str:
        return value or development_jwt_secret()

    @model_validator(mode="after")
    def validate_dependencies(self) -> "Settings":
        if self.is_production and self.jwt_secret_key == development_jwt_secret():
            raise ValueError("JWT_SECRET_KEY must be explicitly configured in production")
        if self.nexus_repository.lower() in ("postgres", "postgresql") and not self.database_url.strip():
            raise ValueError("DATABASE_URL is required for PostgreSQL")
        if self.graph_backend == "neo4j":
            if not self.neo4j_uri or not self.neo4j_user.strip() or not self.neo4j_password.get_secret_value().strip():
                raise ValueError("Neo4j mode requires NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD")
            try:
                uri = urlsplit(self.neo4j_uri)
                port = uri.port
                valid = (
                    uri.scheme in ("bolt", "bolt+s", "bolt+ssc", "neo4j", "neo4j+s", "neo4j+ssc")
                    and bool(uri.hostname) and uri.username is None and uri.password is None
                    and not uri.path and not uri.query and not uri.fragment
                    and (port is None or 1 <= port <= 65535)
                    and not any(c.isspace() for c in self.neo4j_uri)
                )
            except ValueError:
                valid = False
            if not valid:
                raise ValueError("NEO4J_URI must be a Bolt/Neo4j URI without embedded credentials or path")
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9.-]{2,62}", self.neo4j_database) or self.neo4j_database.lower() == "system":
                raise ValueError("NEO4J_DATABASE must name a user database (3-63 letters, digits, dots or hyphens)")
        return self

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
