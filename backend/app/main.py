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
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from backend.app.api.core_routes import create_core_router
from backend.app.api.dependencies import require_graph_projection
from backend.app.api.errors import install_error_handlers
from backend.app.api.graph_routes import create_graph_router
from backend.app.api.nexus_routes import create_nexus_router
from backend.app.api.routes import chat
from backend.app.api.system_routes import create_system_router
from backend.app.config import Settings, get_settings
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.postgres import PostgresBackendRepository
from backend.app.db.neo4j import Neo4jConnection
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
    repository_fallback = False

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
            except Exception:
                if cfg.graph_backend == "neo4j":
                    raise RuntimeError("Required PostgreSQL repository is unavailable; no fallback permitted") from None
                logger.warning("Failed to initialize PostgreSQL repository; using memory with unready status.")
                repository_fallback = True
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

    connection = Neo4jConnection(cfg)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            await connection.start()
            if cfg.graph_backend == "neo4j" and connection.status == "connected":
                try:
                    await connection.ensure_schema()
                    nodes = list(repository.nodes.values())
                    edges = repository.edges
                    await connection.sync_projection(nodes, edges)
                except Exception as ex:
                    logger.warning("Failed to project graph into Neo4j: %s", ex)
                    if cfg.neo4j_failure_policy == "required":
                        await connection.close()
                        raise
            async with original_lifespan(app):
                yield
        finally:
            await connection.close()

    # ── FastAPI App ───────────────────────────────────────────────────────────
    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        description="Evidence-Grounded Criminal Network Intelligence Platform for SIH 2026 PS 26189.",
        dependencies=[Depends(require_graph_projection)],
    )
    # Wrap the framework's existing lifecycle, preserving startup/shutdown hooks
    # without relying on removed APIRouter.startup()/shutdown() methods.
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = lifespan

    # Store repository on app.state for dependency injection
    app.state.repository = repository
    app.state.settings = cfg
    app.state.neo4j = connection
    app.state.repository_fallback = repository_fallback
    
    # Store shared pipeline instance to maintain resolution registries
    app.state.pipeline = CsvIngestionPipeline()

    # Store shared permissioned ledger instance
    from backend.app.core.blockchain.ledger import PermissionedLedger
    from backend.app.services.audit_anchor_service import AuditAnchorService
    from backend.app.services.audit_service import AuditEventType
    app.state.permissioned_ledger = PermissionedLedger()
    audit_svc = AuditService(repository)
    app.state.audit_anchor_service = AuditAnchorService(
        ledger=app.state.permissioned_ledger,
        audit_service=audit_svc,
    )

    # Seed baseline audit events if ledger has only genesis block
    if len(app.state.permissioned_ledger.chain) <= 1:
        initial_events = [
            (AuditEventType.INVESTIGATION_VIEWED, "officer-sharma", "CASE-141", "Case", {"role": "INVESTIGATOR", "station": "Central Crime Branch"}),
            (AuditEventType.GRAPH_QUERY_EXECUTED, "officer-sharma", "person-0001", "Person", {"role": "INVESTIGATOR", "depth": 2}),
            (AuditEventType.ENTITY_RESOLUTION_EXECUTED, "analyst-reddy", "person-0001", "Person", {"role": "ANALYST", "resolution": "CONFIRMED"}),
            (AuditEventType.SIMILARITY_SEARCH_EXECUTED, "officer-sharma", "CASE-141", "Case", {"role": "INVESTIGATOR", "top_k": 10}),
            (AuditEventType.EVIDENCE_VERIFIED, "officer-sharma", "SRC-FIR-141", "Evidence", {"role": "INVESTIGATOR", "status": "AUTHENTIC"}),
        ]
        for ev_type, actor, entity_id, entity_type, details in initial_events:
            audit_svc.record(event_type=ev_type, actor_id=actor, case_id="CASE-141", entity_id=entity_id, entity_type=entity_type, details=details)
        try:
            app.state.audit_anchor_service.anchor_audit_batch(limit=50, actor_id="system-boot")
            logger.info("Successfully anchored initial Section 63 BSA audit batch #1 to ledger.")
        except Exception as exc:
            logger.warning("Failed to anchor initial audit batch: %s", exc)

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
    graph_repo = GraphRepository(repository.to_graph_store() if cfg.graph_backend == "memory" else None)
    app.state.graph_repo = graph_repo

    from backend.app.auth.policy import EvidenceAuthorizationPolicy
    from backend.app.services.intelligence_event_service import IntelligenceEventService
    audit_svc = AuditService(repository)
    auth_policy = EvidenceAuthorizationPolicy(repository, audit_svc)
    intel_event_svc = IntelligenceEventService(repository, audit_service=audit_svc, auth_policy=auth_policy)
    app.state.intelligence_event_service = intel_event_svc
    
    app.state.ingestion_service = IngestionService(
        repository=repository,
        graph_repo=graph_repo,
        audit_service=audit_svc,
        pipeline=app.state.pipeline,
        neo4j_conn=connection,
        intelligence_event_service=intel_event_svc,
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
