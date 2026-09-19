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


async def require_graph_projection(request: Request) -> None:
    """Graph projection gate: selected Neo4j must never serve a memory graph when unready.

    When Neo4j is operational (connected and projection synced), data operations
    proceed cleanly. If not operational, fail with 503 rather than serving an un-synced graph.
    """
    if request.app.state.settings.graph_backend != "neo4j":
        return
    path = request.url.path.removeprefix("/api/v1").rstrip("/") or "/"
    if path in {"/", "/health", "/ready", "/system/status", "/auth/login"}:
        return
    
    neo4j_conn = getattr(request.app.state, "neo4j", None)
    if neo4j_conn is not None and getattr(neo4j_conn, "is_operational", False):
        return

    from backend.app.api.errors import ExternalServiceUnavailableError

    raise ExternalServiceUnavailableError(
        "Neo4j graph projection is not yet operational; data operations are unavailable.",
        details={"graph_backend": "neo4j", "projection": "not_operational"},
    )


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


def get_document_service(
    repo: RepositoryType = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> Any:
    from backend.app.services.document_service import DocumentService
    return DocumentService(repo, audit_svc)


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


def get_proactive_intelligence_service(
    request: Request,
    repo: InMemoryBackendRepository = Depends(get_repository),
) -> Any:
    """Return the shared or per-request ProactiveIntelligenceService instance."""
    proactive_svc = getattr(request.app.state, "proactive_intelligence_service", None)
    if proactive_svc is not None:
        return proactive_svc
    from backend.app.services.proactive_intelligence_service import ProactiveIntelligenceService
    proactive_svc = ProactiveIntelligenceService(repo)
    request.app.state.proactive_intelligence_service = proactive_svc
    return proactive_svc


def get_intelligence_pulse_service(
    request: Request,
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_service: AuditService = Depends(get_audit_service),
    auth_policy: EvidenceAuthorizationPolicy = Depends(get_evidence_authorization_policy),
) -> Any:
    """Return the shared or per-request IntelligencePulseService instance."""
    pulse_svc = getattr(request.app.state, "intelligence_pulse_service", None)
    if pulse_svc is not None:
        return pulse_svc
    from backend.app.services.intelligence_pulse_service import IntelligencePulseService
    pulse_svc = IntelligencePulseService(repo, audit_service=audit_service, auth_policy=auth_policy)
    request.app.state.intelligence_pulse_service = pulse_svc
    return pulse_svc


def get_identity_drift_service(
    request: Request,
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> Any:
    """Return the shared or per-request IdentityDriftService instance."""
    drift_svc = getattr(request.app.state, "identity_drift_service", None)
    if drift_svc is not None:
        return drift_svc
    from backend.app.services.identity_drift_service import IdentityDriftService
    drift_svc = IdentityDriftService(repo, audit_service=audit_service)
    request.app.state.identity_drift_service = drift_svc
    return drift_svc


def get_network_adaptation_service(
    request: Request,
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> Any:
    """Return the shared or per-request NetworkAdaptationService instance."""
    adapt_svc = getattr(request.app.state, "network_adaptation_service", None)
    if adapt_svc is not None:
        return adapt_svc
    from backend.app.services.network_adaptation_service import NetworkAdaptationService
    adapt_svc = NetworkAdaptationService(repo, audit_service=audit_service)
    request.app.state.network_adaptation_service = adapt_svc
    return adapt_svc


def get_digital_shadow_service(
    request: Request,
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> Any:
    """Return the shared or per-request DigitalShadowService instance."""
    shadow_svc = getattr(request.app.state, "digital_shadow_service", None)
    if shadow_svc is not None:
        return shadow_svc
    from backend.app.services.digital_shadow_service import DigitalShadowService
    shadow_svc = DigitalShadowService(repo, audit_service=audit_service)
    request.app.state.digital_shadow_service = shadow_svc
    return shadow_svc


def get_case_dna_service(
    request: Request,
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> Any:
    """Return the shared or per-request CaseDNAService instance."""
    dna_svc = getattr(request.app.state, "case_dna_service", None)
    if dna_svc is not None:
        return dna_svc
    from backend.app.services.case_dna_service import CaseDNAService
    dna_svc = CaseDNAService(repo, audit_service=audit_service)
    request.app.state.case_dna_service = dna_svc
    return dna_svc





