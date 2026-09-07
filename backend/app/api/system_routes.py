"""backend/app/api/system_routes.py

Read-only status, telemetry, and graph health endpoints for NEXUS.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from backend.app.api.dependencies import get_principal, get_repository
from backend.app.auth.principal import Principal
from backend.app.db.postgres import PostgresBackendRepository

_START_TIME = time.time()


def _postgres_available(repo: PostgresBackendRepository) -> bool:
    """Run blocking psycopg work in a thread, never on the ASGI event loop."""
    try:
        with repo._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL statement_timeout = '2000ms'")
                cur.execute("SELECT 1")
                return cur.fetchone() == (1,)
    except Exception:
        return False


class SystemHealthResponse(BaseModel):
    status: str
    version: str
    total_nodes: int
    total_edges: int
    total_cases: int
    total_persons: int
    total_phones: int
    total_accounts: int
    uptime_seconds: float = 0.0
    evidence_hash_version: str = "SHA256-BSA-S63-V1"


def create_system_router() -> APIRouter:
    router = APIRouter(tags=["system-monitoring"])

    @router.get("/health")
    def health_check() -> dict[str, Any]:
        """Process liveness probe for cloud deployments (e.g. Render)."""
        return {
            "status": "healthy",
            "service": "nexus-backend",
            "uptime_seconds": round(max(0.0, time.time() - _START_TIME), 2),
        }

    @router.get("/ready")
    async def readiness_check(request: Request, response: Response, repo: Any = Depends(get_repository)) -> dict[str, Any]:
        """Probe required storage and expose the connection/projection distinction."""
        nodes = getattr(repo, "nodes", {})
        edges = getattr(repo, "edges", [])
        cfg = request.app.state.settings
        postgres = isinstance(repo, PostgresBackendRepository)
        storage_ok = not request.app.state.repository_fallback
        if postgres:
            storage_ok = await run_in_threadpool(_postgres_available, repo)
        connection = request.app.state.neo4j
        graph_connected = await connection.check()
        # Step 2 implements connectivity only. Required graph mode is deliberately
        # unready even when Bolt connects, until durable projection reads exist.
        graph_operational = cfg.graph_backend == "memory"
        graph_required = cfg.neo4j_failure_policy == "required"
        ready = storage_ok and (graph_operational or not graph_required)
        response.status_code = 200 if ready else 503
        return {
            "status": ("ready" if graph_operational else "degraded") if ready else "not_ready",
            "service": "nexus-backend",
            "storage": "postgres" if postgres else "in_memory",
            "storage_available": storage_ok,
            "dependencies_ready": storage_ok and (graph_connected or not graph_required),
            "graph": {
                "backend": cfg.graph_backend,
                "connection": connection.status,
                "failure_policy": cfg.neo4j_failure_policy,
                "operational": graph_operational,
                "projection": "not_applicable" if graph_operational else "not_implemented",
            },
            "total_nodes": len(nodes) if graph_operational else 0,
            "total_edges": len(edges) if graph_operational else 0,
        }

    @router.get("/system/status", response_model=SystemHealthResponse)
    def system_status(
        request: Request,
        principal: Principal = Depends(get_principal),
        repo: Any = Depends(get_repository),
    ) -> SystemHealthResponse:
        nodes = getattr(repo, "nodes", {})
        edges = getattr(repo, "edges", [])

        cases = sum(1 for n in nodes.values() if n.get("entity_type") in ("Case", "CASE"))
        persons = sum(1 for n in nodes.values() if n.get("entity_type") in ("Person", "PERSON"))
        phones = sum(1 for n in nodes.values() if n.get("entity_type") in ("Phone", "PHONE"))
        accounts = sum(1 for n in nodes.values() if n.get("entity_type") in ("Account", "ACCOUNT"))

        uptime = max(0.0, time.time() - _START_TIME)

        return SystemHealthResponse(
            status="healthy" if request.app.state.settings.graph_backend == "memory" else "degraded",
            version="1.0.0",
            total_nodes=len(nodes),
            total_edges=len(edges),
            total_cases=cases,
            total_persons=persons,
            total_phones=phones,
            total_accounts=accounts,
            uptime_seconds=round(uptime, 2),
            evidence_hash_version="SHA256-BSA-S63-V1",
        )

    return router
