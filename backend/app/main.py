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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.core_routes import create_core_router
from backend.app.api.errors import install_error_handlers
from backend.app.api.graph_routes import create_graph_router
from backend.app.api.nexus_routes import create_nexus_router
from backend.app.api.routes import chat
from backend.app.api.system_routes import create_system_router
from backend.app.config import Settings, get_settings
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.db.in_memory import InMemoryBackendRepository

logger = logging.getLogger(__name__)


def create_app(
    repository: InMemoryBackendRepository | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Application factory for NEXUS backend."""
    cfg = settings or get_settings()

    # ── Repository ───────────────────────────────────────────────────────────
    if repository is None:
        artifact_path: Path | None = None
        if cfg.artifact_path and cfg.artifact_path.exists():
            artifact_path = cfg.artifact_path

        state_path = cfg.effective_state_path
        repository = InMemoryBackendRepository(
            artifact_path=artifact_path,
            state_path=state_path,
        )

    # ── FastAPI App ───────────────────────────────────────────────────────────
    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        description="Evidence-Grounded Criminal Network Intelligence Platform for SIH 2026 PS 26189.",
    )

    # Store repository on app.state for dependency injection
    app.state.repository = repository
    app.state.settings = cfg

    # ── Middleware and error handlers ────────────────────────────────────────
    install_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins_list,
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
    app.include_router(
        create_graph_router(graph_repo),
        prefix="/api/v1",
    )

    # System routes
    app.include_router(
        create_system_router(),
        prefix="/api/v1",
    )

    # Chat / Copilot routes
    app.include_router(chat.router, prefix="/api")

    return app


# Module-level instance for uvicorn: uvicorn backend.app.main:app
app = create_app()
