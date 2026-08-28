"""backend/app/api/dependencies.py

FastAPI dependency providers for NEXUS.
Wires together repositories, verifiers, services, and audit logging per request.
"""

from __future__ import annotations

from typing import Any
from fastapi import Depends, Request

from backend.app.auth.principal import Principal
from backend.app.auth.verifier import make_verifier
from backend.app.config import Settings, get_settings
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditService
from backend.app.services.case_service import InvestigationService
from backend.app.services.copilot_service import CopilotService
from backend.app.services.entity_service import EntityService
from backend.app.services.evidence_service import EvidenceService
from backend.app.services.export_service import ExportService


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


def get_evidence_service(
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> EvidenceService:
    return EvidenceService(repo, audit_svc)


def get_entity_service(
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> EntityService:
    evidence_svc = EvidenceService(repo, audit_svc)
    return EntityService(repo, audit_svc, evidence_svc)


def get_export_service(
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> ExportService:
    evidence_svc = EvidenceService(repo, audit_svc)
    return ExportService(repo, audit_svc, evidence_svc)


def get_lead_service(
    request: Request,
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> Any:
    lead_svc = getattr(request.app.state, "lead_service", None)
    if lead_svc is not None:
        return lead_svc

    from backend.app.ai.context_builder import GraphRAGContextBuilder
    from backend.app.ai.llm_client import get_llm_client
    from backend.app.services.lead_service import LeadPipelineService

    llm = get_llm_client()
    context_builder = GraphRAGContextBuilder(repo, audit_service=audit_svc)
    lead_svc = LeadPipelineService(repo, audit_svc, context_builder=context_builder, llm_client=llm)
    request.app.state.lead_service = lead_svc
    return lead_svc


