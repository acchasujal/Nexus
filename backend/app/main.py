"""FastAPI entry point for the CaseClock backend.

Wires together:
  - Application settings (config-driven CORS, paths)
  - Error handlers and request-ID middleware
  - Core routes and graph routes
  - Repository stored on app.state for dependency injection
"""
from __future__ import annotations

import sys
from pathlib import Path
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.config import Settings, get_settings
from backend.app.api.core_routes import create_core_router
from backend.app.api.errors import install_error_handlers
from backend.app.api.graph_routes import create_graph_router

# Add project root to sys.path to allow absolute 'backend' imports
# when running uvicorn from the backend directory
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))




logger = logging.getLogger(__name__)


def create_app(
    repository: InMemoryBackendRepository | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Application factory.

    Args:
        repository: Override the repository for testing.  If None the default
            in-memory repository is constructed from settings.
        settings: Override settings for testing.  If None the cached singleton
            from the environment is used.

    Returns:
        Configured FastAPI application.
    """
    cfg = settings or get_settings()

    # ── Repository ───────────────────────────────────────────────────────────
    if repository is None:
        artifact_path: Path | None = None
        if cfg.artifact_path and cfg.artifact_path != Path("artifacts/synthetic_graph/synthetic_graph.json"):
            artifact_path = cfg.artifact_path

        state_path = cfg.effective_state_path
        # Phase 1 acceptance criterion: no production default JSON state path.
        # In production (ENVIRONMENT=production), state_path must be explicitly
        # configured; otherwise we refuse to run with a mutable local file.
        if cfg.is_production and state_path is None and cfg.caseclock_repository.lower() != "catalyst":
            logger.warning(
                "Running in production without a configured STATE_PATH. "
                "Dependency mutations will not be persisted across restarts. "
                "Set STATE_PATH or integrate Catalyst Data Store (Phase 2)."
            )

        if cfg.caseclock_repository.lower() == "catalyst":
            try:
                from backend.app.db.catalyst import CatalystBackendRepository
                repository = CatalystBackendRepository()
            except Exception as err:
                logger.warning(
                    "Failed to initialize CatalystBackendRepository (%s); falling back to InMemoryBackendRepository.",
                    err,
                )
                repository = InMemoryBackendRepository(
                    artifact_path=artifact_path,
                    state_path=state_path,
                )
        else:
            repository = InMemoryBackendRepository(
                artifact_path=artifact_path,
                state_path=state_path,
            )

    # ── FastAPI app ───────────────────────────────────────────────────────────
    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        description="Deterministic legal-clock-aware investigation backend.",
    )

    # Store repository on app.state so route dependencies can access it without
    # a module-level singleton (enables isolation between test clients).
    app.state.repository = repository
    app.state.settings = cfg

    # ── Middleware and error handlers ────────────────────────────────────────
    # install_error_handlers adds RequestIDMiddleware first (innermost),
    # so request IDs are set before any handler runs.
    install_error_handlers(app)

    # In production (e.g. Catalyst AppSail environment), Catalyst's reverse proxy / gateway
    # (Whitelisting & Authorized Domains) automatically injects CORS headers for cross-origin calls.
    # Emitting CORS headers in FastAPI in production causes duplicate Access-Control-Allow-Origin headers.
    # Thus, CORS middleware is only enabled in development for local testing.
    if cfg.is_development:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cfg.cors_origins_list,
            allow_origin_regex=r"https://.*\.onslate\.in|https://.*\.catalystappsail\.in",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    from backend.app.api.cron_routes import create_cron_router
    from backend.app.api.document_routes import create_document_router
    from backend.app.api.routes import chat
    from backend.app.api.system_routes import create_system_router
    from backend.app.api.convokraft_routes import create_convokraft_router

    # ── Routes ───────────────────────────────────────────────────────────────
    app.include_router(create_core_router())
    app.include_router(create_cron_router())
    app.include_router(
        create_document_router(),
        prefix="/api/v1",
    )
    app.include_router(
        create_graph_router(repository.graph_repository),
        prefix="/api/v1",
    )
    app.include_router(
        create_system_router(),
        prefix="/api/v1",
    )
    app.include_router(chat.router, prefix="/api")
    app.include_router(create_convokraft_router())

    return app


# Module-level app instance for uvicorn: `uvicorn backend.app.main:app`
app = create_app()
