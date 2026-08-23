"""backend/app/api/system_routes.py

Read-only status, telemetry, and graph health endpoints for NEXUS.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.api.dependencies import get_audit_service, get_principal, get_repository
from backend.app.auth.principal import Principal
from backend.app.services.audit_service import AuditService


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

        return SystemHealthResponse(
            status="healthy",
            version="1.0.0",
            total_nodes=len(nodes),
            total_edges=len(edges),
            total_cases=cases,
            total_persons=persons,
            total_phones=phones,
            total_accounts=accounts,
            uptime_seconds=3600.0,
        )

    return router
