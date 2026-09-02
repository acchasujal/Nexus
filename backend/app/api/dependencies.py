"""backend/app/api/dependencies.py

FastAPI dependency providers for NEXUS.
Wires together repositories, verifiers, services, and audit logging per request.
"""

from __future__ import annotations

from typing import Any
from fastapi import Depends, Request

from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.auth.verifier import make_verifier
from backend.app.config import Settings, get_settings
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.postgres import PostgresBackendRepository
from backend.app.services.audit_service import AuditService
from backend.app.services.case_service import InvestigationService
from backend.app.services.copilot_service import CopilotService
from backend.app.services.entity_service import EntityService
from backend.app.services.evidence_service import EvidenceService
from backend.app.services.export_service import ExportService
from backend.app.services.ingestion_service import IngestionService

RepositoryType = InMemoryBackendRepository | PostgresBackendRepository | Any


def get_settings_dep(request: Request) -> Settings:
    state_settings = getattr(request.app.state, "settings", None)
    if state_settings is not None:
        return state_settings  # type: ignore[no-any-return]
    return get_settings()


def get_repository(request: Request) -> RepositoryType:
    return request.app.state.repository  # type: ignore[no-any-return]


async def get_principal(request: Request) -> Principal:
    settings: Settings = request.app.state.settings
    verifier = make_verifier(settings)
    return await verifier.verify(request)


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def get_audit_service(
    repo: RepositoryType = Depends(get_repository),
) -> AuditService:
    return AuditService(repo)


def get_audit_anchor_service(
    request: Request,
    audit_svc: AuditService = Depends(get_audit_service),
) -> Any:
    anchor_svc = getattr(request.app.state, "audit_anchor_service", None)
    if anchor_svc is not None:
        return anchor_svc
    from backend.app.core.blockchain.ledger import PermissionedLedger
    from backend.app.services.audit_anchor_service import AuditAnchorService
    ledger = getattr(request.app.state, "permissioned_ledger", None)
    if ledger is None:
        ledger = PermissionedLedger()
        request.app.state.permissioned_ledger = ledger
    anchor_svc = AuditAnchorService(ledger=ledger, audit_service=audit_svc)
    request.app.state.audit_anchor_service = anchor_svc
    return anchor_svc


def get_case_service(
    repo: RepositoryType = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> InvestigationService:
    return InvestigationService(repo, audit_svc)


def get_copilot_service(
    repo: RepositoryType = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> CopilotService:
    return CopilotService(repo, audit_svc)


def get_evidence_authorization_policy(
    repo: RepositoryType = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> EvidenceAuthorizationPolicy:
    return EvidenceAuthorizationPolicy(repo, audit_svc)


def get_evidence_service(
    repo: RepositoryType = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> EvidenceService:
    return EvidenceService(repo, audit_svc)


def get_entity_service(
    repo: RepositoryType = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> EntityService:
    evidence_svc = EvidenceService(repo, audit_svc)
    return EntityService(repo, audit_svc, evidence_svc)


def get_export_service(
    repo: RepositoryType = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> ExportService:
    evidence_svc = EvidenceService(repo, audit_svc)
    return ExportService(repo, audit_svc, evidence_svc)


def get_lead_service(
    request: Request,
    repo: RepositoryType = Depends(get_repository),
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


def get_evidence_dossier_service(
    request: Request,
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> Any:
    dossier_svc = getattr(request.app.state, "evidence_dossier_service", None)
    if dossier_svc is not None:
        return dossier_svc

    from backend.app.services.evidence_dossier_service import EvidenceDossierService
    evidence_svc = EvidenceService(repo, audit_svc)
    lead_svc = get_lead_service(request, repo, audit_svc)
    dossier_svc = EvidenceDossierService(repo, audit_svc, evidence_service=evidence_svc, lead_service=lead_svc)
    request.app.state.evidence_dossier_service = dossier_svc
    return dossier_svc



def get_ingestion_service(request: Request) -> IngestionService:
    """Return the application-level shared IngestionService instance."""
    return request.app.state.ingestion_service  # type: ignore[no-any-return]


def get_graph_repository(request: Request):
    from backend.app.core.graph.repositories.graph_repository import GraphRepository
    return request.app.state.graph_repo  # type: ignore[no-any-return]


def get_offender_service(
    repo: InMemoryBackendRepository = Depends(get_repository),
) -> Any:
    from backend.app.core.graph.repositories.graph_repository import GraphRepository
    from backend.app.core.graph.services.offender_service import OffenderService
    store = repo.to_graph_store()
    return OffenderService(GraphRepository(store))


def get_hotspot_service(
    repo: InMemoryBackendRepository = Depends(get_repository),
) -> Any:
    from backend.app.core.graph.repositories.graph_repository import GraphRepository
    from backend.app.core.graph.services.hotspot_service import HotspotService
    from backend.app.core.graph.services.offender_service import OffenderService
    store = repo.to_graph_store()
    graph_repo = GraphRepository(store)
    offender_svc = OffenderService(graph_repo)
    return HotspotService(graph_repo, offender_service=offender_svc)

