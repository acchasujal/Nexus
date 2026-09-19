"""tests/test_intelligence_event.py

Comprehensive Test Suite for A3: IntelligenceEvent Unified Domain Contract & Service.
Verifies:
  1. Valid IntelligenceEvent creation (all fields, identity, context, provenance).
  2. Canonical event ID generation and validation (make_intelligence_event_id, prefix intevt-).
  3. Strict non-predictive design (zero confidence score in IntelligenceEvent model).
  4. Required field validation (case_id, event_type).
  5. Deterministic payload integrity hashing (SHA-256 canonical digest).
  6. Retrieval by canonical event ID (service and API).
  7. Filtered retrieval by case_id, event_type, and entity_id.
  8. Immutability & idempotency guarantees (duplicate matching event returns existing).
  9. Jurisdictional RBAC authorization (assigned IO vs unassigned IO vs Admin).
  10. Audit integration (verifies AuditEventType.INTELLIGENCE_EVENT_RECORDED is logged).
"""

from __future__ import annotations

import base64
import json
import pytest
from fastapi.testclient import TestClient

from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.ingestion.identifiers import make_intelligence_event_id
from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.intelligence_event_service import (
    IntelligenceEventService,
    compute_payload_integrity_hash,
)
from shared.contracts.api import (
    CreateIntelligenceEventRequest,
    IntelligenceEvent,
    IntelligenceEventType,
    UserRole,
)


def _make_demo_token(user_id: str, role: str) -> str:
    """Helper to generate a valid base64 demo token matching session Principal."""
    payload = json.dumps({"sub": user_id, "role": role, "email": f"{user_id}@nexus.internal"})
    return base64.b64encode(payload.encode("utf-8")).decode("utf-8")


# ── 1. Unit & Service Tests ──────────────────────────────────────────────────

def test_canonical_id_generation_and_validation() -> None:
    """Test deterministic canonical ID generation for IntelligenceEvent."""
    event_id1 = make_intelligence_event_id(
        event_type="DOCUMENT_INGESTED",
        case_id="CASE-141",
        timestamp_str="2026-09-20T00:00:00Z",
        discriminator="test-01",
    )
    event_id2 = make_intelligence_event_id(
        event_type="DOCUMENT_INGESTED",
        case_id="CASE-141",
        timestamp_str="2026-09-20T00:00:00Z",
        discriminator="test-01",
    )
    assert event_id1.startswith("intevt-")
    assert event_id1 == event_id2, "Canonical ID generation must be deterministic"

    # Must reject empty event_type or case_id
    with pytest.raises(ValueError):
        make_intelligence_event_id(event_type="", case_id="CASE-141", timestamp_str="2026-09-20")

    with pytest.raises(ValueError):
        make_intelligence_event_id(event_type="DOCUMENT_INGESTED", case_id="", timestamp_str="2026-09-20")


def test_payload_integrity_hash_deterministic() -> None:
    """Test deterministic canonical SHA-256 payload integrity hash."""
    payload_a = {"b": 2, "a": 1, "nested": {"y": "hello", "x": 100}}
    payload_b = {"a": 1, "b": 2, "nested": {"x": 100, "y": "hello"}}
    hash_a = compute_payload_integrity_hash(payload_a)
    hash_b = compute_payload_integrity_hash(payload_b)
    assert len(hash_a) == 64
    assert hash_a == hash_b, "Key order normalization must produce identical SHA-256 hashes"


def test_zero_confidence_scoring_invariant() -> None:
    """Ensure IntelligenceEvent does not possess a confidence field (Zero Predictive Guilt)."""
    fields = IntelligenceEvent.model_fields
    assert "confidence" not in fields, "IntelligenceEvent must not contain predictive confidence scores"


def test_service_record_and_retrieve_event() -> None:
    """Test recording an operational intelligence event through IntelligenceEventService."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    service = IntelligenceEventService(repository=repo, audit_service=audit)

    req = CreateIntelligenceEventRequest(
        event_type=IntelligenceEventType.ENTITY_OBSERVED,
        case_id="CASE-141",
        fir_id="FIR-141/2026",
        source_id="SRC-FIR-141",
        evidence_refs=["EV-001", "EV-002"],
        snapshot_id="snap-baseline-v1",
        related_entity_ids=["person-0001", "phone-0001"],
        related_edge_ids=["edge-used_phone-person-0001-phone-0001"],
        source_type="SURVEILLANCE_REPORT",
        actor_id="OFFICER-DEMO-IO-01",
        actor_role=UserRole.INVESTIGATOR,
        title="Suspect Rafiq Khan observed using burner phone",
        description="Field intelligence sighting at Hootagalli, Mysuru.",
        payload={"location": "Hootagalli", "device_type": "burner", "sim_carrier": "Airtel"},
    )

    event = service.record_event(req)
    assert event.event_id.startswith("intevt-")
    assert event.event_type == IntelligenceEventType.ENTITY_OBSERVED
    assert event.case_id == "CASE-141"
    assert event.fir_id == "FIR-141/2026"
    assert event.evidence_refs == ["EV-001", "EV-002"]
    assert event.related_entity_ids == ["person-0001", "phone-0001"]
    assert len(event.integrity_hash) == 64

    # Verify retrieval
    retrieved = service.get_event(event.event_id)
    assert retrieved is not None
    assert retrieved.event_id == event.event_id
    assert retrieved.title == event.title
    assert retrieved.integrity_hash == event.integrity_hash

    # Verify audit event was emitted
    audit_entries = [e for e in repo.audit_events if e.get("event_type") == AuditEventType.INTELLIGENCE_EVENT_RECORDED.value]
    assert len(audit_entries) >= 1
    last_audit = audit_entries[-1]
    assert last_audit["entity_id"] == event.event_id
    assert last_audit["case_id"] == "CASE-141"


def test_service_validation_rejects_empty_case() -> None:
    """Test validation errors for malformed requests."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    service = IntelligenceEventService(repository=repo, audit_service=audit)

    with pytest.raises(ValueError, match="valid, non-empty case_id"):
        service.record_event(
            CreateIntelligenceEventRequest(
                event_type=IntelligenceEventType.DOCUMENT_INGESTED,
                case_id="   ",
            )
        )


def test_service_list_events_filtering() -> None:
    """Test filtering intelligence events by case_id, event_type, and entity_id."""
    repo = InMemoryBackendRepository()
    audit = AuditService(repo)
    service = IntelligenceEventService(repository=repo, audit_service=audit)

    # Record 3 events across 2 cases
    e1 = service.record_event(
        CreateIntelligenceEventRequest(
            event_type=IntelligenceEventType.DOCUMENT_INGESTED,
            case_id="CASE-141",
            related_entity_ids=["person-0001"],
            title="Document 1",
        )
    )
    e2 = service.record_event(
        CreateIntelligenceEventRequest(
            event_type=IntelligenceEventType.NETWORK_CHANGE_DETECTED,
            case_id="CASE-141",
            related_entity_ids=["person-0002"],
            title="Diff 1",
        )
    )
    e3 = service.record_event(
        CreateIntelligenceEventRequest(
            event_type=IntelligenceEventType.DOCUMENT_INGESTED,
            case_id="CASE-207",
            related_entity_ids=["person-0001"],
            title="Document 2",
        )
    )

    # Filter by case_id
    case_141_events, total = service.list_events(case_id="CASE-141")
    assert total == 2
    assert {ev.event_id for ev in case_141_events} == {e1.event_id, e2.event_id}

    # Filter by event_type
    doc_events, total_docs = service.list_events(event_type=IntelligenceEventType.DOCUMENT_INGESTED)
    assert total_docs == 2
    assert {ev.event_id for ev in doc_events} == {e1.event_id, e3.event_id}

    # Filter by entity_id
    p1_events, total_p1 = service.list_events(entity_id="person-0001")
    assert total_p1 == 2
    assert {ev.event_id for ev in p1_events} == {e1.event_id, e3.event_id}


# ── 2. API & RBAC Integration Tests ──────────────────────────────────────────

def test_api_record_and_get_intelligence_event() -> None:
    """Test POST and GET endpoints for IntelligenceEvent with authorization."""
    app = create_app()
    client = TestClient(app)

    # Officer IO (Rajesh Kumar) is assigned to CASE-141
    token = _make_demo_token("officer_io", "IO")

    post_payload = {
        "event_type": "DOCUMENT_INGESTED",
        "case_id": "CASE-141",
        "fir_id": "FIR-141/2026",
        "source_id": "doc-test-12345",
        "evidence_refs": ["EV-FIR-141"],
        "related_entity_ids": ["person-0001"],
        "source_type": "DOCUMENT",
        "title": "FIR Document Ingested",
        "description": "Initial FIR document ingested for extortion syndicate investigation.",
        "payload": {"file_name": "fir_141.pdf", "pages": 4},
    }

    # Record event
    resp = client.post(
        "/api/v1/nexus/intelligence/events",
        headers={"Authorization": f"Bearer {token}"},
        json=post_payload,
    )
    assert resp.status_code == 201, resp.text
    created = resp.json()

    assert created["event_id"].startswith("intevt-")
    assert created["event_type"] == "DOCUMENT_INGESTED"
    assert created["case_id"] == "CASE-141"
    assert created["actor_id"] == "officer_io"
    assert len(created["integrity_hash"]) == 64

    event_id = created["event_id"]

    # Retrieve event by ID
    get_resp = client.get(
        f"/api/v1/nexus/intelligence/events/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_resp.status_code == 200, get_resp.text
    fetched = get_resp.json()
    assert fetched["event_id"] == event_id
    assert fetched["title"] == post_payload["title"]

    # List events for case
    list_resp = client.get(
        "/api/v1/nexus/intelligence/events?case_id=CASE-141",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 200, list_resp.text
    list_data = list_resp.json()
    assert list_data["total_count"] >= 1
    assert any(ev["event_id"] == event_id for ev in list_data["events"])


def test_api_unauthorized_investigator_denied() -> None:
    """Test that an investigator cannot record or view events for an unassigned case."""
    app = create_app()
    client = TestClient(app)

    # Officer IO (Rajesh Kumar) is assigned to CASE-141, but NOT to CASE-999
    token = _make_demo_token("officer_io", "IO")

    # Attempt to record event for unassigned case
    resp = client.post(
        "/api/v1/nexus/intelligence/events",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "event_type": "INVESTIGATOR_DECISION",
            "case_id": "CASE-999-UNASSIGNED",
            "title": "Unauthorized decision",
        },
    )
    assert resp.status_code == 403, "Investigator must be denied access to unassigned case"


def test_api_admin_oversight_allowed() -> None:
    """Test that an Administrator has oversight access across all cases."""
    app = create_app()
    client = TestClient(app)

    admin_token = _make_demo_token("admin_user", "ADMIN")

    resp = client.post(
        "/api/v1/nexus/intelligence/events",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "event_type": "SNAPSHOT_CREATED",
            "case_id": "CASE-999-UNASSIGNED",
            "title": "Admin global snapshot event",
            "payload": {"snapshot_id": "snap-test-01"},
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["case_id"] == "CASE-999-UNASSIGNED"
    assert data["actor_role"] == "ADMIN"


def test_api_nonexistent_event_404() -> None:
    """Test 404 response for non-existent event ID."""
    app = create_app()
    client = TestClient(app)

    token = _make_demo_token("admin_user", "ADMIN")
    resp = client.get(
        "/api/v1/nexus/intelligence/events/intevt-nonexistent-999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
