"""backend/app/main.py

FastAPI entry point for the NEXUS Criminal Intelligence Platform.
Wires together:
  - Local-first config-driven settings & CORS
  - Request-ID correlation middleware & structured error handlers
  - Core investigation, entity resolution, network explorer, and copilot routers
  - Dependency-injected in-memory/persistent repository on app.state
"""

from __future__ import annotations

import asyncio
import logging
from time import perf_counter
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
from backend.app.db.neo4j import Neo4jConnection, Neo4jUnavailableError
from backend.app.db.ingestion.pipeline import CsvIngestionPipeline
from backend.app.services.audit_service import AuditService
from backend.app.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)


def create_app(
    repository: InMemoryBackendRepository | PostgresBackendRepository | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    """Application factory for NEXUS backend."""
    factory_started = perf_counter()
    cfg = settings or get_settings()
    repository_fallback = False
    background_graph = cfg.neo4j_background_startup if cfg.neo4j_background_startup is not None else cfg.is_production

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
                    migration_url=cfg.database_url_unpooled,
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

    logger.info("startup stage=repository_total elapsed_ms=%.1f", (perf_counter() - factory_started) * 1000)
    connection = Neo4jConnection(cfg)

    async def initialize_graph(app: FastAPI) -> None:
        started = perf_counter()
        app.state.graph_initialization = {"status": "starting", "stage": "connect"}
        try:
            step = perf_counter()
            for attempt in range(3 if background_graph else 1):
                app.state.graph_initialization["attempt"] = attempt + 1
                if attempt:
                    await asyncio.sleep(2 ** attempt)
                try:
                    if attempt == 0 or connection.status == "closed":
                        await connection.start()
                    else:
                        await connection.check(verify=True)
                except Neo4jUnavailableError:
                    if not background_graph:
                        raise
                if cfg.graph_backend == "memory" or connection.status == "connected":
                    break
            if connection.status != "connected" and cfg.graph_backend == "neo4j":
                app.state.graph_initialization["failure_type"] = connection.failure_type
            logger.info("startup stage=neo4j_connect elapsed_ms=%.1f", (perf_counter() - step) * 1000)
            if cfg.graph_backend == "neo4j" and connection.status == "connected":
                step = perf_counter()
                app.state.graph_initialization["stage"] = "schema"
                await connection.ensure_schema()
                logger.info("startup stage=neo4j_schema elapsed_ms=%.1f", (perf_counter() - step) * 1000)
                step = perf_counter()
                app.state.graph_initialization["stage"] = "sync"
                await connection.sync_projection(list(repository.nodes.values()), repository.edges)
                # Keep mutation/traversal gates closed until the durable read completes.
                connection.is_operational = False
                logger.info("startup stage=neo4j_sync elapsed_ms=%.1f", (perf_counter() - step) * 1000)
                step = perf_counter()
                app.state.graph_initialization["stage"] = "read"
                app.state.graph_repo.replace_store(await connection.to_graph_store())
                connection.is_operational = True
                logger.info("startup stage=neo4j_read elapsed_ms=%.1f", (perf_counter() - step) * 1000)
            app.state.graph_initialization["status"] = "ready" if connection.is_operational else "unavailable"
            if connection.is_operational:
                app.state.graph_initialization["stage"] = "complete"
        except asyncio.CancelledError:
            connection.is_operational = False
            raise
        except Exception as exc:
            connection.is_operational = False
            app.state.graph_initialization.update(status="failed", failure_type=type(exc).__name__)
            logger.warning("Graph initialization failed; stage=%s type=%s; live graph operations remain gated.",
                           app.state.graph_initialization["stage"], type(exc).__name__)
            if not background_graph and cfg.neo4j_failure_policy == "required":
                raise
        finally:
            app.state.graph_initialization["elapsed_ms"] = round((perf_counter() - started) * 1000, 1)
            logger.info("startup stage=graph_total elapsed_ms=%.1f", (perf_counter() - started) * 1000)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        graph_task = None
        try:
            if cfg.graph_backend == "neo4j" and background_graph:
                graph_task = asyncio.create_task(initialize_graph(app))
            else:
                await initialize_graph(app)
            async with original_lifespan(app):
                app.state.startup_timings["factory_to_http_ready_ms"] = round((perf_counter() - factory_started) * 1000, 1)
                logger.info("startup stage=http_ready elapsed_ms=%.1f", (perf_counter() - factory_started) * 1000)
                yield
        finally:
            if graph_task is not None:
                graph_task.cancel()
                try:
                    await graph_task
                except asyncio.CancelledError:
                    pass
            await connection.close()
            if hasattr(repository, "_pool"):
                repository.close()

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
    app.state.startup_timings = {}
    app.state.graph_initialization = {"status": "not_started", "stage": "not_started"}
    app.state.repository = repository
    app.state.settings = cfg
    app.state.neo4j = connection
    app.state.repository_fallback = repository_fallback
    from backend.app.services.proactive_intelligence_service import ProactiveIntelligenceService
    diff_started = perf_counter()
    app.state.proactive_intelligence_service = ProactiveIntelligenceService(repository)
    app.state.proactive_intelligence_service.compute_network_diff()
    logger.info("startup stage=canonical_diff elapsed_ms=%.1f", (perf_counter() - diff_started) * 1000)
    app.state.evidence_object_storage = None
    if cfg.evidence_storage_backend == "s3":
        from backend.app.services.object_storage import EvidenceObjectStorage
        app.state.evidence_object_storage = EvidenceObjectStorage(cfg)
    
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

    # Explicit, idempotent demo bootstrap (production startup only verifies state)
    audit_started = perf_counter()
    if cfg.auth_mode == "demo" or not cfg.is_production:
        try:
            app.state.audit_anchor_service.bootstrap_demo_audit()
            logger.info("AuditAnchorService: Explicit demo audit bootstrap completed successfully.")
        except Exception as exc:
            logger.warning("Failed to bootstrap demo audit events: %s", exc)
    else:
        logger.info("Production mode: Audit bootstrap skipped; production audit ledger state verified.")

    logger.info("startup stage=audit_bootstrap elapsed_ms=%.1f", (perf_counter() - audit_started) * 1000)

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
