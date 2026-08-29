"""backend/app/main.py

FastAPI entry point for the NEXUS Criminal Intelligence Platform.
Wires together:
  - Local-first config-driven settings & CORS
  - Request-ID correlation middleware & structured error handlers
  - Core investigation, entity resolution, network explorer, and copilot routers
  - Dependency-injected in-memory/persistent repository on app.state
"""

from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from backend.app.api.core_routes import create_core_router
from backend.app.api.errors import install_error_handlers
from backend.app.api.graph_routes import create_graph_router
from backend.app.api.nexus_routes import create_nexus_router
from backend.app.api.routes import chat
from backend.app.api.system_routes import create_system_router
from backend.app.config import Settings, get_settings
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.postgres import PostgresBackendRepository
from backend.app.db.ingestion.pipeline import CsvIngestionPipeline
from backend.app.services.audit_service import AuditService
from backend.app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)


def create_app(
    repository: InMemoryBackendRepository | PostgresBackendRepository | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Application factory for NEXUS backend."""
    cfg = settings or get_settings()

    # ── Repository ───────────────────────────────────────────────────────────
    if repository is None:
        use_postgres = cfg.nexus_repository.lower() in ("postgres", "postgresql") or "postgres" in cfg.database_url
        if use_postgres and cfg.database_url:
            try:
                artifact_path: Path | None = None
                if cfg.artifact_path and cfg.artifact_path.exists():
                    artifact_path = cfg.artifact_path

                repository = PostgresBackendRepository(
                    database_url=cfg.database_url,
                    artifact_path=artifact_path,
                    state_path=cfg.effective_state_path,
                )
                logger.info("NEXUS backend initialized with PostgreSQL repository.")
            except Exception as exc:
                logger.warning("Failed to initialize PostgreSQL repository (%s), falling back to in-memory.", exc)
                repository = None

        if repository is None:
            artifact_path: Path | None = None
            if cfg.artifact_path and cfg.artifact_path.exists():
                artifact_path = cfg.artifact_path

            state_path = cfg.effective_state_path
            repository = InMemoryBackendRepository(
                artifact_path=artifact_path,
                state_path=state_path,
            )
            logger.info("NEXUS backend initialized with in-memory repository.")

    # ── FastAPI App ───────────────────────────────────────────────────────────
    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        description="Evidence-Grounded Criminal Network Intelligence Platform for SIH 2026 PS 26189.",
    )

    # Store repository on app.state for dependency injection
    app.state.repository = repository
    app.state.settings = cfg
    
    # Store shared pipeline instance to maintain resolution registries
    app.state.pipeline = CsvIngestionPipeline()

    # ── Middleware and error handlers ────────────────────────────────────────
    install_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins_list,
        allow_origin_regex=r"^https:\/\/.*\.vercel\.app$|^http:\/\/localhost(:\d+)?$|^http:\/\/127\.0\.0\.1(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    # Core routes (both root and /api/v1 prefixes)
    core_router = create_core_router()
    app.include_router(core_router)
    app.include_router(core_router, prefix="/api/v1")

    # NEXUS Prototype Golden-Path routes (both root and /api/v1 prefixes)
    nexus_router = create_nexus_router()
    app.include_router(nexus_router)
    app.include_router(nexus_router, prefix="/api/v1")

    # Graph intelligence routes
    graph_repo = GraphRepository(repository.to_graph_store())
    app.state.graph_repo = graph_repo
    
    app.state.ingestion_service = IngestionService(
        repository=repository,
        graph_repo=graph_repo,
        audit_service=AuditService(repository),
        pipeline=app.state.pipeline,
    )

    app.include_router(
        create_graph_router(graph_repo),
        prefix="/api/v1",
    )

    # System routes (both root /health and /api/v1/health)
    system_router = create_system_router()
    app.include_router(system_router)
    app.include_router(system_router, prefix="/api/v1")

    # Chat / Copilot routes
    app.include_router(chat.router, prefix="/api")

    return app


# Module-level instance for uvicorn: uvicorn backend.app.main:app
app = create_app()
