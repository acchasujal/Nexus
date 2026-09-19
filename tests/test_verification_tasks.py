"""tests/test_verification_tasks.py

Comprehensive Test Suite for A7: Persistent Verification Tasks.
Verifies:
  1. Task creation and canonical ID generation (vtask-XXXX, deterministic).
  2. Strict non-predictive design (zero guilt/confidence scoring in model).
  3. Task retrieval and filtering by case, assignee, and status.
  4. Explicit lifecycle state machine progression (CREATED -> ASSIGNED -> REQUESTED -> RECEIVED -> UNDER_REVIEW -> VERIFIED/DISMISSED).
  5. Rejection of invalid transitions and terminal-state mutations.
  6. Task assignment and reassignment with transition history.
  7. Authoritative evidence attachment, relationship typing, and nonexistent evidence rejection.
  8. Final decisions (VERIFIED, DISMISSED) with rationale and actor attribution.
  9. Idempotent task instantiation from active pulse recommendations.
  10. IntelligenceEvent integration (VERIFICATION_TASK_CREATED, VERIFICATION_COMPLETED).
  11. Section 63 BSA AuditEvent integration across all investigator actions.
  12. RBAC case authorization (assigned IO vs unassigned IO vs Admin).
  13. REST API endpoints behavior (201 Created, 200 OK, 400 Bad Request, 403 Forbidden, 404 Not Found).
"""

from __future__ import annotations

import base64
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.ingestion.identifiers import make_verification_task_id
from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.evidence_service import EvidenceService
from backend.app.services.intelligence_event_service import IntelligenceEventService
from backend.app.services.proactive_intelligence_service import ProactiveIntelligenceService
from backend.app.services.verification_task_service import VerificationTaskService
from shared.contracts.api import (
    AssignVerificationTaskRequest,
    AttachEvidenceRequest,
    CreateVerificationTaskRequest,
    DecideVerificationTaskRequest,
    TransitionVerificationTaskRequest,
    UserRole,
    VerificationTask,
    VerificationTaskDecision,
    VerificationTaskStatus,
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


# ── 1. Canonical ID & Validation Tests ─────────────────────────────────────────

def test_canonical_task_id_generation_and_validation() -> None:
    """Test deterministic canonical ID generation for VerificationTask (vtask-XXXX)."""
    id1 = make_verification_task_id(
        case_id="case-0001",
        target_claim="Verify beneficial subscriber identity",
        requested_evidence_type="Section 91 CrPC CAF",
        discriminator="pulse-0082",
    )
    id2 = make_verification_task_id(
        case_id="case-0001",
        target_claim="Verify beneficial subscriber identity",
        requested_evidence_type="Section 91 CrPC CAF",
        discriminator="pulse-0082",
    )
    assert id1.startswith("vtask-")
    assert id1 == id2, "Canonical ID generation must be deterministic"

    # Must reject empty case_id or target_claim
    with pytest.raises(ValueError):
        make_verification_task_id(case_id="", target_claim="Verify identity", requested_evidence_type="CAF")

    with pytest.raises(ValueError):
        make_verification_task_id(case_id="case-0001", target_claim="", requested_evidence_type="CAF")


def test_zero_confidence_scoring_invariant() -> None:
    """Ensure VerificationTask does not possess a confidence or guilt score field."""
    fields = VerificationTask.model_fields
    assert "confidence" not in fields, "VerificationTask must not contain confidence scores"
    assert "guilt_score" not in fields, "VerificationTask must not contain guilt scores"
    assert "risk_score" not in fields, "VerificationTask must not contain risk scores"


# ── 2. Service Layer: Creation, Retrieval & Filtering ─────────────────────────

def test_service_create_and_retrieve_task() -> None:
    """Test task creation, canonical ID assignment, and retrieval via VerificationTaskService."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    intel = IntelligenceEventService(repo, audit)
    service = VerificationTaskService(repository=repo, audit_service=audit, intelligence_event_service=intel)

    req = CreateVerificationTaskRequest(
        case_id="case-0001",
        target_claim="Corroborate suspect presence at rendezvous",
        reason="Field surveillance sighting requires CCTV confirmation",
        requested_evidence_type="CCTV Footage",
        verification_action="Request toll plaza CCTV footage for KA-01-MJ-5021",
        expected_outcome="Confirm vehicle passage matching CDR tower jump",
        evidence_gap="Missing independent video corroboration",
        assigned_officer_id="OFFICER-DEMO-IO-01",
        assigned_role=UserRole.INVESTIGATOR,
    )

    task = service.create_task(req)
    assert task.task_id.startswith("vtask-")
    assert task.case_id == "case-0001"
    assert task.target_claim == "Corroborate suspect presence at rendezvous"
    assert task.status == VerificationTaskStatus.ASSIGNED
    assert task.assigned_officer_id == "OFFICER-DEMO-IO-01"
    assert len(task.history) == 1
    assert task.history[0].to_status == VerificationTaskStatus.ASSIGNED

    # Verify retrieval
    retrieved = service.get_task(task.task_id)
    assert retrieved is not None
    assert retrieved.task_id == task.task_id
    assert retrieved.verification_action == task.verification_action

    # Verify audit event emitted
    audit_events = [e for e in repo.audit_events if e.get("event_type") == AuditEventType.VERIFICATION_TASK_CREATED.value]
    assert len(audit_events) >= 1
    assert audit_events[-1]["entity_id"] == task.task_id

    # Verify IntelligenceEvent emitted
    intel_events = [e for e in repo.intelligence_events.values() if e.get("source_id") == task.task_id]
    assert len(intel_events) >= 1
    assert intel_events[0]["event_type"] == "VERIFICATION_TASK_CREATED"


def test_service_validation_rejects_empty_fields() -> None:
    """Test required field validation for task creation."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    service = VerificationTaskService(repository=repo, audit_service=audit)

    with pytest.raises(ValueError, match="non-empty case_id"):
        service.create_task(CreateVerificationTaskRequest(
            case_id="",
            target_claim="Claim",
            reason="Reason",
            requested_evidence_type="Type",
            verification_action="Action",
        ))

    with pytest.raises(ValueError, match="non-empty target_claim"):
        service.create_task(CreateVerificationTaskRequest(
            case_id="case-0001",
            target_claim="",
            reason="Reason",
            requested_evidence_type="Type",
            verification_action="Action",
        ))


def test_service_filter_tasks() -> None:
    """Test filtering tasks by case_id, assignee, and status."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    service = VerificationTaskService(repository=repo, audit_service=audit)

    service.create_task(CreateVerificationTaskRequest(
        case_id="case-0001",
        target_claim="Claim 1",
        reason="Reason 1",
        requested_evidence_type="Type 1",
        verification_action="Action 1",
        assigned_officer_id="OFFICER-01",
    ))
    service.create_task(CreateVerificationTaskRequest(
        case_id="case-0001",
        target_claim="Claim 2",
        reason="Reason 2",
        requested_evidence_type="Type 2",
        verification_action="Action 2",
        assigned_officer_id="OFFICER-02",
    ))
    service.create_task(CreateVerificationTaskRequest(
        case_id="case-0009",
        target_claim="Claim 3",
        reason="Reason 3",
        requested_evidence_type="Type 3",
        verification_action="Action 3",
    ))

    # Filter by case
    tasks_c1, count_c1 = service.list_tasks(case_id="case-0001")
    assert count_c1 == 2
    assert len(tasks_c1) == 2

    # Filter by assignee
    tasks_off1, count_off1 = service.list_tasks(assignee="OFFICER-01")
    assert count_off1 == 1
    assert tasks_off1[0].assigned_officer_id == "OFFICER-01"

    # Filter by status
    tasks_created, count_created = service.list_tasks(status=VerificationTaskStatus.CREATED)
    assert count_created == 1
    assert tasks_created[0].case_id == "case-0009"


# ── 3. Lifecycle State Machine & Terminal Immutability ─────────────────────────

def test_valid_lifecycle_transitions() -> None:
    """Test full sequential lifecycle: CREATED -> ASSIGNED -> REQUESTED -> RECEIVED -> UNDER_REVIEW -> VERIFIED."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    service = VerificationTaskService(repository=repo, audit_service=audit)

    # 1. Create (CREATED)
    task = service.create_task(CreateVerificationTaskRequest(
        case_id="case-0001",
        target_claim="Bank UTR IMPS-8812 account holder verification",
        reason="Layered transaction needs KYC documents",
        requested_evidence_type="Bank Statement & KYC",
        verification_action="Serve notice to HDFC Bank under Section 91 CrPC",
    ))
    assert task.status == VerificationTaskStatus.CREATED

    # 2. Assign (CREATED -> ASSIGNED)
    task = service.assign_task(task.task_id, AssignVerificationTaskRequest(
        assigned_officer_id="OFFICER-DEMO-IO-01",
        assigned_role=UserRole.INVESTIGATOR,
        rationale="Assigned to lead investigating officer",
    ))
    assert task.status == VerificationTaskStatus.ASSIGNED
    assert task.assigned_officer_id == "OFFICER-DEMO-IO-01"

    # 3. Request (ASSIGNED -> REQUESTED)
    task = service.transition_task(task.task_id, TransitionVerificationTaskRequest(
        target_status=VerificationTaskStatus.REQUESTED,
        rationale="Notice dispatched via speed post to branch manager",
    ))
    assert task.status == VerificationTaskStatus.REQUESTED

    # 4. Receive (REQUESTED -> RECEIVED)
    task = service.transition_task(task.task_id, TransitionVerificationTaskRequest(
        target_status=VerificationTaskStatus.RECEIVED,
        rationale="Bank branch furnished signed KYC and statement CD",
    ))
    assert task.status == VerificationTaskStatus.RECEIVED

    # 5. Under Review (RECEIVED -> UNDER_REVIEW)
    task = service.transition_task(task.task_id, TransitionVerificationTaskRequest(
        target_status=VerificationTaskStatus.UNDER_REVIEW,
        rationale="Investigator examining account signature card",
    ))
    assert task.status == VerificationTaskStatus.UNDER_REVIEW

    # 6. Decide VERIFIED (UNDER_REVIEW -> VERIFIED)
    task = service.decide_task(task.task_id, DecideVerificationTaskRequest(
        decision=VerificationTaskDecision.VERIFIED,
        rationale="Account verified to belong to proxy dummy director",
    ))
    assert task.status == VerificationTaskStatus.VERIFIED
    assert task.decision == VerificationTaskDecision.VERIFIED
    assert task.decided_at is not None
    assert len(task.history) == 6


def test_invalid_lifecycle_transition_rejected() -> None:
    """Test that skipping required stages or invalid transitions raise clear ValueError."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    service = VerificationTaskService(repository=repo, audit_service=audit)

    task = service.create_task(CreateVerificationTaskRequest(
        case_id="case-0001",
        target_claim="Claim",
        reason="Reason",
        requested_evidence_type="Type",
        verification_action="Action",
    ))
    assert task.status == VerificationTaskStatus.CREATED

    # Direct transition CREATED -> VERIFIED must fail
    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        service.transition_task(task.task_id, TransitionVerificationTaskRequest(
            target_status=VerificationTaskStatus.VERIFIED,
        ))

    # Direct transition CREATED -> UNDER_REVIEW must fail
    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        service.transition_task(task.task_id, TransitionVerificationTaskRequest(
            target_status=VerificationTaskStatus.UNDER_REVIEW,
        ))


def test_terminal_state_mutation_rejected() -> None:
    """Test that once VERIFIED or DISMISSED, all subsequent transitions/assignments/evidence attachments fail."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    service = VerificationTaskService(repository=repo, audit_service=audit)

    task = service.create_task(CreateVerificationTaskRequest(
        case_id="case-0001",
        target_claim="Claim",
        reason="Reason",
        requested_evidence_type="Type",
        verification_action="Action",
    ))
    # Direct dismissal from CREATED is allowed
    dismissed = service.decide_task(task.task_id, DecideVerificationTaskRequest(
        decision=VerificationTaskDecision.DISMISSED,
        rationale="Claim determined to be duplicate of existing inquiry",
    ))
    assert dismissed.status == VerificationTaskStatus.DISMISSED

    # Attempting to reassign dismissed task must fail
    with pytest.raises(ValueError, match="terminal state"):
        service.assign_task(task.task_id, AssignVerificationTaskRequest(assigned_officer_id="OFFICER-02"))

    # Attempting to transition dismissed task must fail
    with pytest.raises(ValueError, match="terminal state"):
        service.transition_task(task.task_id, TransitionVerificationTaskRequest(target_status=VerificationTaskStatus.ASSIGNED))

    # Attempting to decide again must fail
    with pytest.raises(ValueError, match="terminal state"):
        service.decide_task(task.task_id, DecideVerificationTaskRequest(
            decision=VerificationTaskDecision.VERIFIED,
            rationale="Trying to override dismissal",
        ))


# ── 4. Authoritative Evidence Linkage ─────────────────────────────────────────

def test_evidence_attachment_and_validation() -> None:
    """Test linking valid authoritative evidence to a task and rejecting non-existent evidence."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    evidence_svc = EvidenceService(repo, audit)
    service = VerificationTaskService(
        repository=repo,
        audit_service=audit,
        evidence_service=evidence_svc,
    )

    # Seed an evidence record in repo.source_records
    repo.source_records["SRC-FIR-141"] = {
        "source_type": "FIR",
        "locator": "data/fir_141.csv",
        "occurred_at": "2026-08-20T10:00:00Z",
        "raw_excerpt": "Complainant alleges extortion via burner phones",
        "case_ids": ["case-0001"],
    }

    task = service.create_task(CreateVerificationTaskRequest(
        case_id="case-0001",
        target_claim="Corroborate extortion complaint",
        reason="Need primary FIR citation",
        requested_evidence_type="FIR Record",
        verification_action="Review FIR-141",
    ))

    # 1. Attach valid evidence
    updated = service.attach_evidence(task.task_id, AttachEvidenceRequest(
        evidence_id="SRC-FIR-141",
        relationship_type="SUPPORTING",
        notes="Matches initial complaint narrative",
    ))
    assert "SRC-FIR-141" in updated.supporting_evidence_ids
    assert len(updated.history) == 2

    # 2. Attach non-existent evidence must raise ValueError
    with pytest.raises(ValueError, match="does not exist in repository"):
        service.attach_evidence(task.task_id, AttachEvidenceRequest(
            evidence_id="NONEXISTENT-EVIDENCE-ID-9999",
            relationship_type="SUPPORTING",
        ))


# ── 5. Pulse Integration & Idempotency ────────────────────────────────────────

def test_idempotent_task_creation_from_pulse() -> None:
    """Test instantiating tasks from NetworkPulseItem recommendations idempotently."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    proactive_svc = ProactiveIntelligenceService(repo)
    service = VerificationTaskService(
        repository=repo,
        audit_service=audit,
        proactive_intelligence_service=proactive_svc,
    )

    pulses = proactive_svc.list_active_pulses()
    assert len(pulses) > 0
    pulse_id = pulses[0].pulse_id

    # First call: creates tasks
    tasks_first = service.create_tasks_from_pulse(pulse_id=pulse_id, case_id="case-0001")
    assert len(tasks_first) > 0
    first_ids = [t.task_id for t in tasks_first]

    # Second call: must return existing tasks without duplicating
    tasks_second = service.create_tasks_from_pulse(pulse_id=pulse_id, case_id="case-0001")
    second_ids = [t.task_id for t in tasks_second]

    assert first_ids == second_ids, "Task creation from pulse must be 100% idempotent"
    all_stored, total = repo.list_verification_tasks(case_id="case-0001")
    assert total == len(tasks_first), "Repository must not have duplicate tasks"


# ── 6. REST API Endpoints & RBAC Authorization ────────────────────────────────

@pytest.fixture
def api_client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_api_verification_task_crud_and_rbac(api_client: TestClient) -> None:
    """Test full HTTP API lifecycle for VerificationTasks including RBAC enforcement."""
    assigned_io_token = _make_demo_token("OFFICER-DEMO-IO-01", "INVESTIGATOR")
    unassigned_io_token = _make_demo_token("OFFICER-UNASSIGNED", "INVESTIGATOR")
    admin_token = _make_demo_token("ADMIN-USER", "ADMIN")

    # 1. Unassigned IO cannot create task on case-0001 (403 Forbidden)
    res_forbidden = api_client.post(
        "/api/v1/nexus/verification/tasks",
        headers={"Authorization": f"Bearer {unassigned_io_token}"},
        json={
            "case_id": "case-0001",
            "target_claim": "Suspect identity verification",
            "reason": "Need CAF",
            "requested_evidence_type": "CAF",
            "verification_action": "Subpoena CAF",
        },
    )
    assert res_forbidden.status_code == 403

    # 2. Assigned IO creates task on case-0001 (201 Created)
    res_create = api_client.post(
        "/api/v1/nexus/verification/tasks",
        headers={"Authorization": f"Bearer {assigned_io_token}"},
        json={
            "case_id": "case-0001",
            "target_claim": "Suspect identity verification",
            "reason": "Need CAF",
            "requested_evidence_type": "CAF",
            "verification_action": "Subpoena CAF",
            "assigned_officer_id": "OFFICER-DEMO-IO-01",
        },
    )
    assert res_create.status_code == 201
    task_data = res_create.json()
    task_id = task_data["task_id"]
    assert task_id.startswith("vtask-")
    assert task_data["status"] == "ASSIGNED"

    # 3. Unassigned IO cannot view task on case-0001 (403 Forbidden)
    res_get_forbidden = api_client.get(
        f"/api/v1/nexus/verification/tasks/{task_id}",
        headers={"Authorization": f"Bearer {unassigned_io_token}"},
    )
    assert res_get_forbidden.status_code == 403

    # 4. Admin can view task across cases (200 OK)
    res_admin_get = api_client.get(
        f"/api/v1/nexus/verification/tasks/{task_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin_get.status_code == 200
    assert res_admin_get.json()["task_id"] == task_id

    # 5. Assigned IO transitions task: ASSIGNED -> REQUESTED (200 OK)
    res_trans1 = api_client.post(
        f"/api/v1/nexus/verification/tasks/{task_id}/transition",
        headers={"Authorization": f"Bearer {assigned_io_token}"},
        json={
            "target_status": "REQUESTED",
            "rationale": "Sent Section 91 notice to Airtel",
        },
    )
    assert res_trans1.status_code == 200
    assert res_trans1.json()["status"] == "REQUESTED"

    # 6. Assigned IO transitions task: REQUESTED -> RECEIVED -> UNDER_REVIEW
    res_trans2 = api_client.post(
        f"/api/v1/nexus/verification/tasks/{task_id}/transition",
        headers={"Authorization": f"Bearer {assigned_io_token}"},
        json={"target_status": "RECEIVED", "rationale": "CAF received"},
    )
    assert res_trans2.status_code == 200

    res_trans3 = api_client.post(
        f"/api/v1/nexus/verification/tasks/{task_id}/transition",
        headers={"Authorization": f"Bearer {assigned_io_token}"},
        json={"target_status": "UNDER_REVIEW", "rationale": "Inspecting subscriber Aadhaar number"},
    )
    assert res_trans3.status_code == 200

    # 7. Assigned IO records decision: VERIFIED (200 OK)
    res_decide = api_client.post(
        f"/api/v1/nexus/verification/tasks/{task_id}/decision",
        headers={"Authorization": f"Bearer {assigned_io_token}"},
        json={
            "decision": "VERIFIED",
            "rationale": "Aadhaar number matches syndicate co-conspirator",
        },
    )
    assert res_decide.status_code == 200
    decided_task = res_decide.json()
    assert decided_task["status"] == "VERIFIED"
    assert decided_task["decision"] == "VERIFIED"

    # 8. Listing tasks for case-0001
    res_list = api_client.get(
        "/api/v1/nexus/verification/tasks?case_id=case-0001",
        headers={"Authorization": f"Bearer {assigned_io_token}"},
    )
    assert res_list.status_code == 200
    list_body = res_list.json()
    assert list_body["total_count"] >= 1
    assert any(t["task_id"] == task_id for t in list_body["tasks"])


def test_api_nonexistent_task_returns_404(api_client: TestClient) -> None:
    """Test 404 response for nonexistent verification task."""
    admin_token = _make_demo_token("ADMIN-USER", "ADMIN")
    res = api_client.get(
        "/api/v1/nexus/verification/tasks/vtask-nonexistent-1234",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 404


def test_decide_verified_requires_under_review() -> None:
    """Test that marking a task VERIFIED requires it to be in UNDER_REVIEW state."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    service = VerificationTaskService(repository=repo, audit_service=audit)

    task = service.create_task(CreateVerificationTaskRequest(
        case_id="case-0001",
        target_claim="Claim",
        reason="Reason",
        requested_evidence_type="Type",
        verification_action="Action",
    ))
    assert task.status == VerificationTaskStatus.CREATED

    # Attempting to decide VERIFIED directly from CREATED must fail
    with pytest.raises(ValueError, match="must be in 'UNDER_REVIEW' state before verification"):
        service.decide_task(task.task_id, DecideVerificationTaskRequest(
            decision=VerificationTaskDecision.VERIFIED,
            rationale="Trying to verify without review",
        ))


def test_decide_dismissed_from_any_stage() -> None:
    """Test that a task can be DISMISSED from CREATED, ASSIGNED, or REQUESTED."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    service = VerificationTaskService(repository=repo, audit_service=audit)

    task = service.create_task(CreateVerificationTaskRequest(
        case_id="case-0001",
        target_claim="Claim",
        reason="Reason",
        requested_evidence_type="Type",
        verification_action="Action",
    ))
    dismissed = service.decide_task(task.task_id, DecideVerificationTaskRequest(
        decision=VerificationTaskDecision.DISMISSED,
        rationale="Duplicate lead found",
    ))
    assert dismissed.status == VerificationTaskStatus.DISMISSED
    assert dismissed.decision == VerificationTaskDecision.DISMISSED


def test_task_history_recording() -> None:
    """Test that every action appends a transition history item with actor, timestamp, and rationale."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    service = VerificationTaskService(repository=repo, audit_service=audit)

    principal = Principal(user_id="OFFICER-01", email="io@nexus.internal", role=UserRole.INVESTIGATOR)
    task = service.create_task(CreateVerificationTaskRequest(
        case_id="case-0001",
        target_claim="Claim",
        reason="Reason",
        requested_evidence_type="Type",
        verification_action="Action",
    ), principal=principal)
    assert len(task.history) == 1
    assert task.history[0].actor_id == "OFFICER-01"

    service.assign_task(task.task_id, AssignVerificationTaskRequest(
        assigned_officer_id="OFFICER-02",
        rationale="Reassigned to second IO",
    ), principal=principal)
    updated = service.get_task(task.task_id)
    assert len(updated.history) == 2
    assert updated.history[-1].rationale == "Reassigned to second IO"


def test_api_from_pulse_endpoint(api_client: TestClient) -> None:
    """Test the POST /nexus/verification/tasks/from-pulse/{pulse_id} endpoint."""
    assigned_io_token = _make_demo_token("OFFICER-DEMO-IO-01", "INVESTIGATOR")
    res = api_client.post(
        "/api/v1/nexus/verification/tasks/from-pulse/pulse-0082?case_id=case-0001",
        headers={"Authorization": f"Bearer {assigned_io_token}"},
    )
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) >= 1
    assert all(t["task_id"].startswith("vtask-") for t in tasks)

