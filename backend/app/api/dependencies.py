"""backend/app/api/dependencies.py

FastAPI dependency providers for NEXUS.
Wires together repositories, verifiers, services, and audit logging per request.
"""

from __future__ import annotations

from fastapi import Depends, Request

from backend.app.auth.principal import Principal
from backend.app.auth.verifier import make_verifier
from backend.app.config import Settings, get_settings
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditService
from backend.app.services.case_service import InvestigationService
from backend.app.services.copilot_service import CopilotService


def get_settings_dep(request: Request) -> Settings:
    state_settings = getattr(request.app.state, "settings", None)
    if state_settings is not None:
        return state_settings  # type: ignore[no-any-return]
    return get_settings()


def get_repository(request: Request) -> InMemoryBackendRepository:
    return request.app.state.repository  # type: ignore[no-any-return]


async def get_principal(request: Request) -> Principal:
    settings: Settings = request.app.state.settings
    verifier = make_verifier(settings)
    return await verifier.verify(request)


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def get_audit_service(
    repo: InMemoryBackendRepository = Depends(get_repository),
) -> AuditService:
    return AuditService(repo)


def get_case_service(
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> InvestigationService:
    return InvestigationService(repo, audit_svc)


def get_copilot_service(
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> CopilotService:
    return CopilotService(repo, audit_svc)
