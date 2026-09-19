"""tests/test_evidence_assessment.py

Comprehensive Test Suite for A5: First-Class Evidence Assessment.
Verifies:
  1. Valid SUPPORTS assessment creation.
  2. Valid CONFLICTS assessment creation.
  3. Valid MISSING assessment creation.
  4. Valid INFERRED assessment creation.
  5. Valid VERIFIED assessment creation.
  6. Required claim validation (empty claim rejected).
  7. Evidence reference validation and provenance preservation.
  8. Nonexistent evidence rejection with ValueError.
  9. Unauthorized case rejection via EvidenceAuthorizationPolicy / Principal.
  10. Assessment retrieval by canonical ID (evasmt-XXXX).
  11. Filtering assessments by case_id.
  12. Filtering assessments by state.
  13. Filtering assessments by entity_id.
  14. Filtering assessments by edge_id.
  15. Rationale requirement (empty or trivial rationale rejected).
  16. Provenance preservation from authoritative evidence records.
  17. Immutable revision/history behavior (prior states preserved in history list).
  18. A3 EVIDENCE_ASSESSED IntelligenceEvent emission.
  19. AuditEvent emission (EVIDENCE_ASSESSMENT_CREATED & EVIDENCE_ASSESSMENT_REVISED).
  20. Existing NetworkPulse behavior remains 100% compatible.
  21. REST API endpoints (201 Created, 200 OK, 400 Bad Request, 403 Forbidden, 404 Not Found).
"""

from __future__ import annotations

import base64
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.ingestion.identifiers import make_evidence_assessment_id
from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.evidence_assessment_service import EvidenceAssessmentService
from backend.app.services.evidence_service import EvidenceService
from backend.app.services.intelligence_event_service import IntelligenceEventService
from backend.app.services.proactive_intelligence_service import ProactiveIntelligenceService
from shared.contracts.api import (
    AssessmentBasis,
    CreateEvidenceAssessmentRequest,
    EpistemicState,
    EvidenceAssessment,
    EvidenceAssessmentItem,
    IntelligenceEventType,
    ReviseEvidenceAssessmentRequest,
    UserRole,
)


def _make_demo_token(user_id: str, role: str, officer_id: str | None = None) -> str:
    """Generate a base64 encoded JWT mock token for testing."""
    payload = {
        "sub": user_id,
        "role": role,
        "email": f"{user_id}@nexus.internal",
        "officer_id": officer_id or user_id,
    }
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


@pytest.fixture
def repo() -> InMemoryBackendRepository:
    repository = InMemoryBackendRepository()
    repository.clear()
    return repository


@pytest.fixture
def audit_service(repo: InMemoryBackendRepository) -> AuditService:
    return AuditService(repo)


@pytest.fixture
def auth_policy(repo: InMemoryBackendRepository, audit_service: AuditService) -> EvidenceAuthorizationPolicy:
    return EvidenceAuthorizationPolicy(repo, audit_service)


@pytest.fixture
def evidence_service(repo: InMemoryBackendRepository, audit_service: AuditService) -> EvidenceService:
    return EvidenceService(repo, audit_service)


@pytest.fixture
def intel_service(
    repo: InMemoryBackendRepository,
    audit_service: AuditService,
    auth_policy: EvidenceAuthorizationPolicy,
) -> IntelligenceEventService:
    return IntelligenceEventService(repo, audit_service=audit_service, auth_policy=auth_policy)


@pytest.fixture
def service(
    repo: InMemoryBackendRepository,
    audit_service: AuditService,
    evidence_service: EvidenceService,
    intel_service: IntelligenceEventService,
    auth_policy: EvidenceAuthorizationPolicy,
) -> EvidenceAssessmentService:
    return EvidenceAssessmentService(
        repository=repo,
        audit_service=audit_service,
        evidence_service=evidence_service,
        intelligence_event_service=intel_service,
        auth_policy=auth_policy,
    )


@pytest.fixture
def authorized_principal() -> Principal:
    return Principal(
        user_id="OFFICER-DEMO-IO-01",
        email="io@nexus.internal",
        role=UserRole.INVESTIGATOR,
        officer_id="OFFICER-DEMO-IO-01",
    )


@pytest.fixture
def unauthorized_principal() -> Principal:
    return Principal(
        user_id="OFFICER-UNASSIGNED",
        email="unassigned@nexus.internal",
        role=UserRole.INVESTIGATOR,
        officer_id="OFFICER-UNASSIGNED",
    )


@pytest.fixture
def sample_evidence_id(repo: InMemoryBackendRepository) -> str:
    """Find or create a known authoritative evidence source in the repository."""
    # Check source_records in repo
    if repo.source_records:
        return next(iter(repo.source_records.keys()))
    # Or create one for testing
    ev_id = "EV-CDR-TEST-0001"
    repo.source_records[ev_id] = {
        "source_type": "CDR",
        "occurred_at": "2026-09-18T10:00:00Z",
        "case_ids": ["case-0001"],
        "raw_excerpt": "Subscriber phone-0001 called phone-0002 for 120 seconds.",
    }
    return ev_id


# ── 1. Epistemic States: SUPPORTS, CONFLICTS, MISSING, INFERRED, VERIFIED ────

def test_assessment_creation_supports(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
    sample_evidence_id: str,
) -> None:
    """1. Valid SUPPORTS assessment creation."""
    req = CreateEvidenceAssessmentRequest(
        case_id="case-0001",
        claim="Suspect phone communicated with broker device",
        claim_type="COMMUNICATION",
        state=EpistemicState.SUPPORTS,
        rationale="Telecom CDR records 14 distinct calls between subject and broker within window.",
        assessment_basis=AssessmentBasis.DIRECT,
        target_entity_id="person-0001",
        target_edge_id="rel_person-0001_COMMUNICATED_WITH_person-0002",
        evidence_ids=[sample_evidence_id],
        supporting_evidence_ids=[sample_evidence_id],
    )
    asmt = service.create_assessment(req, principal=authorized_principal)

    assert asmt.assessment_id.startswith("evasmt-")
    assert asmt.case_id == "case-0001"
    assert asmt.state == EpistemicState.SUPPORTS
    assert asmt.assessment_basis == AssessmentBasis.DIRECT
    assert sample_evidence_id in asmt.evidence_ids
    assert sample_evidence_id in asmt.supporting_evidence_ids
    assert len(asmt.history) == 0


def test_assessment_creation_conflicts(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
    sample_evidence_id: str,
) -> None:
    """2. Valid CONFLICTS assessment creation."""
    req = CreateEvidenceAssessmentRequest(
        case_id="case-0001",
        claim="Suspect claimed to be present in Mumbai during extortion call",
        claim_type="ALIBI",
        state=EpistemicState.CONFLICTS,
        rationale="Cell tower telemetry places subscriber device in Delhi sector during window.",
        assessment_basis=AssessmentBasis.CONFLICTING,
        target_entity_id="person-0001",
        evidence_ids=[sample_evidence_id],
        conflicting_evidence_ids=[sample_evidence_id],
    )
    asmt = service.create_assessment(req, principal=authorized_principal)

    assert asmt.state == EpistemicState.CONFLICTS
    assert asmt.assessment_basis == AssessmentBasis.CONFLICTING
    assert sample_evidence_id in asmt.conflicting_evidence_ids


def test_assessment_creation_missing(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
) -> None:
    """3. Valid MISSING assessment creation."""
    req = CreateEvidenceAssessmentRequest(
        case_id="case-0001",
        claim="Beneficial owner identity for remittance account",
        claim_type="FINANCIAL",
        state=EpistemicState.MISSING,
        rationale="No KYC or bank account opening forms available in current docket.",
        assessment_basis=AssessmentBasis.MISSING,
        target_entity_id="account-0001",
        missing_evidence_types=["Section 91 CrPC Bank KYC Registry"],
    )
    asmt = service.create_assessment(req, principal=authorized_principal)

    assert asmt.state == EpistemicState.MISSING
    assert asmt.assessment_basis == AssessmentBasis.MISSING
    assert "Section 91 CrPC Bank KYC Registry" in asmt.missing_evidence_types


def test_assessment_creation_inferred(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
    sample_evidence_id: str,
) -> None:
    """4. Valid INFERRED assessment creation."""
    req = CreateEvidenceAssessmentRequest(
        case_id="case-0001",
        claim="Secondary device co-location indicates shared physical courier",
        claim_type="RELATIONSHIP",
        state=EpistemicState.INFERRED,
        rationale="Consecutive tower hops match within 3-minute interval across multiple days.",
        assessment_basis=AssessmentBasis.INFERRED,
        evidence_ids=[sample_evidence_id],
    )
    asmt = service.create_assessment(req, principal=authorized_principal)

    assert asmt.state == EpistemicState.INFERRED
    assert asmt.assessment_basis == AssessmentBasis.INFERRED


def test_assessment_creation_verified(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
    sample_evidence_id: str,
) -> None:
    """5. Valid VERIFIED assessment creation."""
    req = CreateEvidenceAssessmentRequest(
        case_id="case-0001",
        claim="Registered legal entity ownership corroborated by MCA registry",
        claim_type="CORPORATE",
        state=EpistemicState.VERIFIED,
        rationale="Official MCA21 corporate registry certificate verified with digital signature.",
        assessment_basis=AssessmentBasis.DIRECT,
        evidence_ids=[sample_evidence_id],
        supporting_evidence_ids=[sample_evidence_id],
    )
    asmt = service.create_assessment(req, principal=authorized_principal)

    assert asmt.state == EpistemicState.VERIFIED


# ── 2. Validation & Error Handling ───────────────────────────────────────────

def test_empty_claim_rejected(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
) -> None:
    """6. Required claim validation (empty claim rejected)."""
    with pytest.raises(ValueError, match="valid, non-empty claim"):
        service.create_assessment(
            CreateEvidenceAssessmentRequest(
                case_id="case-0001",
                claim="   ",
                state=EpistemicState.SUPPORTS,
                rationale="Valid rationale here.",
            ),
            principal=authorized_principal,
        )


def test_empty_rationale_rejected(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
) -> None:
    """15. Rationale requirement (empty or trivial rationale rejected)."""
    with pytest.raises(ValueError, match="non-empty rationale"):
        service.create_assessment(
            CreateEvidenceAssessmentRequest(
                case_id="case-0001",
                claim="Valid claim",
                state=EpistemicState.SUPPORTS,
                rationale="  ",
            ),
            principal=authorized_principal,
        )

    with pytest.raises(ValueError, match="explainable evidence basis"):
        service.create_assessment(
            CreateEvidenceAssessmentRequest(
                case_id="case-0001",
                claim="Valid claim",
                state=EpistemicState.SUPPORTS,
                rationale="tiny",
            ),
            principal=authorized_principal,
        )


def test_nonexistent_evidence_rejected(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
) -> None:
    """8. Nonexistent evidence rejection."""
    with pytest.raises(ValueError, match="does not exist in authoritative records"):
        service.create_assessment(
            CreateEvidenceAssessmentRequest(
                case_id="case-0001",
                claim="Valid claim",
                state=EpistemicState.SUPPORTS,
                rationale="Evidence reference is completely fabricated.",
                evidence_ids=["EV-FABRICATED-NONEXISTENT-9999"],
            ),
            principal=authorized_principal,
        )


def test_unauthorized_case_rejected(
    service: EvidenceAssessmentService,
    unauthorized_principal: Principal,
) -> None:
    """9. Unauthorized case rejection via RBAC."""
    with pytest.raises(PermissionError, match="Access denied"):
        service.create_assessment(
            CreateEvidenceAssessmentRequest(
                case_id="case-0001",
                claim="Valid claim",
                state=EpistemicState.MISSING,
                rationale="Officer does not have access to case-0001.",
            ),
            principal=unauthorized_principal,
        )


# ── 3. Retrieval, Filtering & Provenance ──────────────────────────────────────

def test_canonical_id_and_retrieval(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
) -> None:
    """10. Assessment deterministic ID and retrieval by ID."""
    req = CreateEvidenceAssessmentRequest(
        case_id="case-0001",
        claim="Deterministic ID check for test",
        claim_type="RELATIONSHIP",
        state=EpistemicState.MISSING,
        rationale="Testing canonical evasmt-XXXX generation and lookup.",
    )
    created = service.create_assessment(req, principal=authorized_principal)
    assert created.assessment_id.startswith("evasmt-")

    retrieved = service.get_assessment(created.assessment_id, principal=authorized_principal)
    assert retrieved is not None
    assert retrieved.assessment_id == created.assessment_id
    assert retrieved.claim == created.claim


def test_filtering_by_case_and_state(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
) -> None:
    """11, 12. Filtering assessments by case_id and state."""
    service.create_assessment(
        CreateEvidenceAssessmentRequest(
            case_id="case-0001",
            claim="Filter claim 1",
            state=EpistemicState.SUPPORTS,
            rationale="Rationale for filter claim 1.",
        ),
        principal=authorized_principal,
    )
    service.create_assessment(
        CreateEvidenceAssessmentRequest(
            case_id="case-0009",
            claim="Filter claim 2",
            state=EpistemicState.MISSING,
            rationale="Rationale for filter claim 2.",
        ),
        principal=authorized_principal,
    )

    # Filter by case
    res1 = service.list_assessments(case_id="case-0001", principal=authorized_principal)
    assert all(a.case_id == "case-0001" for a in res1.assessments)

    # Filter by state
    res2 = service.list_assessments(state=EpistemicState.MISSING, principal=authorized_principal)
    assert all(a.state == EpistemicState.MISSING for a in res2.assessments)


def test_filtering_by_entity_and_edge(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
) -> None:
    """13, 14. Filtering assessments by entity_id and edge_id."""
    service.create_assessment(
        CreateEvidenceAssessmentRequest(
            case_id="case-0001",
            claim="Entity specific claim",
            state=EpistemicState.SUPPORTS,
            rationale="Rationale for entity specific claim.",
            target_entity_id="entity-TARGET-99",
            target_edge_id="edge-TARGET-101",
        ),
        principal=authorized_principal,
    )

    res_ent = service.list_assessments(entity_id="entity-TARGET-99", principal=authorized_principal)
    assert any(a.target_entity_id == "entity-TARGET-99" for a in res_ent.assessments)

    res_edge = service.list_assessments(edge_id="edge-TARGET-101", principal=authorized_principal)
    assert any(a.target_edge_id == "edge-TARGET-101" for a in res_edge.assessments)


def test_provenance_preservation(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
    sample_evidence_id: str,
) -> None:
    """16. Provenance preservation from authoritative evidence records."""
    req = CreateEvidenceAssessmentRequest(
        case_id="case-0001",
        claim="Subscriber identity proven by telecom CAF",
        state=EpistemicState.SUPPORTS,
        rationale="Customer Application Form matches government ID number exactly.",
        evidence_ids=[sample_evidence_id],
    )
    asmt = service.create_assessment(req, principal=authorized_principal)

    assert sample_evidence_id in asmt.evidence_ids
    assert len(asmt.source_ids) > 0
    assert len(asmt.provenance_refs) > 0


# ── 4. Append-Only Revision & History ────────────────────────────────────────

def test_immutable_revision_history(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
    sample_evidence_id: str,
) -> None:
    """17. Immutable revision/history behavior."""
    # 1. Create initial assessment in MISSING state
    initial = service.create_assessment(
        CreateEvidenceAssessmentRequest(
            case_id="case-0001",
            claim="Subscriber ownership of phone-0002",
            state=EpistemicState.MISSING,
            rationale="Initial assessment: no subscriber registration on file.",
            missing_evidence_types=["Section 91 CrPC CAF"],
        ),
        principal=authorized_principal,
    )
    assert initial.state == EpistemicState.MISSING
    assert len(initial.history) == 0

    # 2. Revise assessment to SUPPORTS when evidence is obtained
    revised = service.revise_assessment(
        assessment_id=initial.assessment_id,
        request=ReviseEvidenceAssessmentRequest(
            state=EpistemicState.SUPPORTS,
            rationale="Obtained certified subscriber registration sheet from telecom operator confirming identity.",
            assessment_basis=AssessmentBasis.DIRECT,
            additional_evidence_ids=[sample_evidence_id],
            supporting_evidence_ids=[sample_evidence_id],
            missing_evidence_types=[],
        ),
        principal=authorized_principal,
    )

    assert revised.assessment_id == initial.assessment_id
    assert revised.state == EpistemicState.SUPPORTS
    assert len(revised.history) == 1

    h0 = revised.history[0]
    assert h0.revision_number == 1
    assert h0.from_state == EpistemicState.MISSING
    assert h0.to_state == EpistemicState.SUPPORTS
    assert h0.actor_id == authorized_principal.user_id
    assert "telecom operator" in h0.rationale


# ── 5. Events & Auditing ──────────────────────────────────────────────────────

def test_intelligence_and_audit_event_emission(
    service: EvidenceAssessmentService,
    audit_service: AuditService,
    repo: InMemoryBackendRepository,
    authorized_principal: Principal,
    sample_evidence_id: str,
) -> None:
    """18, 19. A3 IntelligenceEvent and Section 63 BSA AuditEvent emission."""
    req = CreateEvidenceAssessmentRequest(
        case_id="case-0001",
        claim="IMPS laundering hop assessment",
        state=EpistemicState.SUPPORTS,
        rationale="Bank transaction statement confirms immediate pass-through routing.",
        evidence_ids=[sample_evidence_id],
    )
    asmt = service.create_assessment(req, principal=authorized_principal)

    # Verify AuditEvent
    audit_records = repo.audit_events
    create_audit = next(
        (
            e for e in audit_records
            if e.get("action") == AuditEventType.EVIDENCE_ASSESSMENT_CREATED.value
            and e.get("entity_id") == asmt.assessment_id
        ),
        None,
    )
    assert create_audit is not None, "EVIDENCE_ASSESSMENT_CREATED audit event must be recorded"
    assert create_audit.get("case_id") == "case-0001"

    # Verify IntelligenceEvent
    intel_events = list(repo.intelligence_events.values())
    assessed_event = next(
        (
            e for e in intel_events
            if e.get("event_type") == IntelligenceEventType.EVIDENCE_ASSESSED.value
            and e.get("payload", {}).get("assessment_id") == asmt.assessment_id
        ),
        None,
    )
    assert assessed_event is not None, "A3 EVIDENCE_ASSESSED IntelligenceEvent must be emitted"
    assert assessed_event.get("case_id") == "case-0001"


# ── 6. Pulse Compatibility ────────────────────────────────────────────────────

def test_network_pulse_compatibility(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
) -> None:
    """20. Existing NetworkPulse behavior remains compatible."""
    # 1. Test to_pulse_item conversion
    req = CreateEvidenceAssessmentRequest(
        case_id="case-0001",
        claim="Direct CDR call connection verified",
        state=EpistemicState.SUPPORTS,
        rationale="Direct telecom CDR call connection verified with timestamp corroboration.",
        target_edge_id="rel_person-0001_COMMUNICATED_WITH_person-0002",
    )
    asmt = service.create_assessment(req, principal=authorized_principal)
    pulse_item = service.to_pulse_item(asmt)

    assert isinstance(pulse_item, EvidenceAssessmentItem)
    assert pulse_item.claim_id == asmt.assessment_id
    assert pulse_item.target_relationship_id == "rel_person-0001_COMMUNICATED_WITH_person-0002"
    assert pulse_item.state == EpistemicState.SUPPORTS
    assert pulse_item.source_quality == 1.0

    # 2. Test round-trip from_pulse_item
    reconstructed = EvidenceAssessment.from_pulse_item(pulse_item, case_id="case-0001")
    assert reconstructed.assessment_id == asmt.assessment_id
    assert reconstructed.state == EpistemicState.SUPPORTS


# ── 7. REST API Endpoints ─────────────────────────────────────────────────────

@pytest.fixture
def api_client(repo: InMemoryBackendRepository) -> TestClient:
    app = create_app()
    return TestClient(app)


def test_api_create_and_retrieve_assessment(api_client: TestClient) -> None:
    """21. REST API endpoints: POST /nexus/evidence/assessments and GET."""
    token = _make_demo_token("OFFICER-DEMO-IO-01", "INVESTIGATOR")
    headers = {"Authorization": f"Bearer {token}"}

    create_payload = {
        "case_id": "case-0001",
        "claim": "API test claim for subscriber verification",
        "claim_type": "SUBSCRIBER",
        "state": "MISSING",
        "rationale": "Testing API endpoint creation for evidence assessment.",
        "assessment_basis": "MISSING",
        "missing_evidence_types": ["CAF Form"],
    }

    # 1. Create
    res_create = api_client.post(
        "/api/v1/nexus/evidence/assessments",
        json=create_payload,
        headers=headers,
    )
    assert res_create.status_code == 201
    created_data = res_create.json()
    asmt_id = created_data["assessment_id"]
    assert asmt_id.startswith("evasmt-")

    # 2. Retrieve
    res_get = api_client.get(
        f"/api/v1/nexus/evidence/assessments/{asmt_id}",
        headers=headers,
    )
    assert res_get.status_code == 200
    retrieved_data = res_get.json()
    assert retrieved_data["assessment_id"] == asmt_id
    assert retrieved_data["state"] == "MISSING"

    # 3. List
    res_list = api_client.get(
        "/api/v1/nexus/evidence/assessments?case_id=case-0001",
        headers=headers,
    )
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total_count"] >= 1
    assert any(a["assessment_id"] == asmt_id for a in list_data["assessments"])

    # 4. Revise
    revise_payload = {
        "state": "SUPPORTS",
        "rationale": "Investigator received certified document from registrar confirming claim.",
        "assessment_basis": "DIRECT",
    }
    res_rev = api_client.post(
        f"/api/v1/nexus/evidence/assessments/{asmt_id}/revise",
        json=revise_payload,
        headers=headers,
    )
    assert res_rev.status_code == 200
    revised_data = res_rev.json()
    assert revised_data["state"] == "SUPPORTS"
    assert len(revised_data["history"]) == 1
    assert revised_data["history"][0]["from_state"] == "MISSING"
    assert revised_data["history"][0]["to_state"] == "SUPPORTS"


def test_zero_confidence_scoring_in_model() -> None:
    """22. Strict non-predictive invariant: verify zero confidence/risk/guilt fields in EvidenceAssessment."""
    fields = EvidenceAssessment.model_fields
    forbidden = ["confidence", "probability", "score", "risk", "guilt", "threat", "danger"]
    for field_name in fields:
        for f in forbidden:
            assert f not in field_name.lower(), f"Forbidden scoring field '{field_name}' in EvidenceAssessment"


def test_idempotent_creation(
    service: EvidenceAssessmentService,
    authorized_principal: Principal,
) -> None:
    """23. Idempotent assessment creation: creating identical assessment returns existing entity."""
    req = CreateEvidenceAssessmentRequest(
        case_id="case-0001",
        claim="Idempotency test claim",
        state=EpistemicState.MISSING,
        rationale="Testing that duplicate creations yield identical canonical ID and stored instance.",
    )
    first = service.create_assessment(req, principal=authorized_principal)
    second = service.create_assessment(req, principal=authorized_principal)

    assert first.assessment_id == second.assessment_id
    assert first.created_at == second.created_at

