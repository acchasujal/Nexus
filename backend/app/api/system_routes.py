"""backend/app/api/system_routes.py

Read-only status, telemetry, and graph health endpoints for NEXUS.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.api.dependencies import get_principal, get_repository
from backend.app.auth.principal import Principal

_START_TIME = time.time()


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
    router = APIRouter(prefix="/system", tags=["system-monitoring"])

    @router.get("/status", response_model=SystemHealthResponse)
    def system_status(
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
            status="healthy",
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
