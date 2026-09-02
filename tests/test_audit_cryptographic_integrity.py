"""tests/test_audit_cryptographic_integrity.py

Comprehensive tests for NEXUS Trust Layer - Phase 3:
Cryptographic Audit Integrity (Canonical Serialization & SHA-256).

Tests cover:
  1. Deterministic canonical serialization (stable field ordering, consistent timestamps).
  2. Identical events produce identical hashes.
  3. Different events produce different hashes.
  4. Audit events receive SHA-256 hashes at creation.
  5. Valid event verifies successfully.
  6. Tamper-detection test: Mutating an event field causes verification to fail (MANDATORY DEMO TEST).
  7. Integrity hash itself is excluded from the hashed payload.
  8. Previous-hash chaining creates a tamper-evident sequence (H2 references H1).
  9. Verification API endpoint:
     - Authenticated supervisor/SP can verify event -> 200 OK with verification result.
     - Unauthorized/anonymous user cannot verify -> 403 Forbidden.
     - Nonexistent event returns 404.
"""

from __future__ import annotations

import base64
import json
from fastapi.testclient import TestClient

from backend.app.core.crypto.audit_integrity import (
    canonicalize_audit_payload,
    compute_audit_event_hash,
    verify_audit_event_integrity,
)
from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType, AuditService


def _make_demo_token(user_id: str, role: str) -> str:
    """Helper to generate a valid base64 demo token matching frontend AuthContext session."""
    payload = json.dumps({"sub": user_id, "role": role, "email": f"{user_id}@nexus.internal"})
    return base64.b64encode(payload.encode("utf-8")).decode("utf-8")


# 1. Deterministic canonical serialization
def test_canonical_serialization_deterministic() -> None:
    # Event with keys in arbitrary order
    event1 = {
        "timestamp": "2026-09-02T10:00:00Z",
        "actor_id": "officer_io",
        "event_type": "evidence_viewed",
        "details": {"b": 2, "a": 1},
        "id": "evt-1234",
        "case_id": "case-0001",
        "entity_id": "ev-9999",
        "entity_type": "Evidence",
        "request_id": "req-1",
        "previous_hash": None,
        "integrity_hash": "should_be_ignored",
    }
    event2 = {
        "id": "evt-1234",
        "details": {"a": 1, "b": 2},
        "actor_id": "officer_io",
        "timestamp": "2026-09-02T10:00:00+00:00",
        "case_id": "case-0001",
        "event_type": "evidence_viewed",
        "request_id": "req-1",
        "entity_type": "Evidence",
        "entity_id": "ev-9999",
        "previous_hash": None,
    }

    canon1 = canonicalize_audit_payload(event1)
    canon2 = canonicalize_audit_payload(event2)

    assert canon1 == canon2
    assert "should_be_ignored" not in canon1


# 2. Identical events produce identical hashes
def test_identical_events_produce_identical_hashes() -> None:
    event1 = {
        "id": "evt-5555",
        "event_type": "lead_actioned",
        "actor_id": "officer_io",
        "timestamp": "2026-09-02T12:00:00Z",
        "details": {"status": "ACCEPTED"},
    }
    event2 = {
        "actor_id": "officer_io",
        "id": "evt-5555",
        "details": {"status": "ACCEPTED"},
        "event_type": "lead_actioned",
        "timestamp": "2026-09-02T12:00:00+00:00",
    }
    hash1 = compute_audit_event_hash(event1)
    hash2 = compute_audit_event_hash(event2)
    assert len(hash1) == 64
    assert hash1 == hash2


# 3. Different events produce different hashes
def test_different_events_produce_different_hashes() -> None:
    event1 = {
        "id": "evt-0001",
        "event_type": "evidence_viewed",
        "actor_id": "officer_io",
        "timestamp": "2026-09-02T12:00:00Z",
    }
    event2 = {
        "id": "evt-0002",
        "event_type": "evidence_viewed",
        "actor_id": "officer_io",
        "timestamp": "2026-09-02T12:00:00Z",
    }
    assert compute_audit_event_hash(event1) != compute_audit_event_hash(event2)


# 4. Audit events receive SHA-256 hashes at creation
def test_audit_service_records_hashes_at_creation() -> None:
    app = create_app()
    repo = app.state.repository
    audit_svc = AuditService(repo)

    audit_svc.record(
        event_type=AuditEventType.EVIDENCE_VIEWED,
        actor_id="officer_io",
        case_id="case-0001",
        entity_id="ev-1234",
        details={"allowed": True},
    )

    events = repo.audit_events
    last_event = events[-1]

    assert "integrity_hash" in last_event
    assert last_event["integrity_hash"] is not None
    assert len(last_event["integrity_hash"]) == 64


# 5. Valid event verifies successfully
def test_valid_event_verifies_successfully() -> None:
    app = create_app()
    repo = app.state.repository
    audit_svc = AuditService(repo)

    audit_svc.record(
        event_type=AuditEventType.INVESTIGATION_VIEWED,
        actor_id="officer_io",
        case_id="case-0001",
        details={"section": "overview"},
    )

    last_event = repo.audit_events[-1]
    res = verify_audit_event_integrity(last_event)

    assert res.verified is True
    assert res.stored_hash == res.computed_hash
    assert "Hash matches canonical" in res.reason


# 6. Tamper-detection test: Mutating an event field causes verification to fail (MANDATORY TEST)
def test_tamper_detection_fails_on_mutation() -> None:
    app = create_app()
    repo = app.state.repository
    audit_svc = AuditService(repo)

    # 1. Create an audit event
    audit_svc.record(
        event_type=AuditEventType.LEAD_ACTIONED,
        actor_id="officer_io",
        case_id="case-0001",
        details={"decision": "ACCEPT", "note": "Verified by IO"},
    )

    created_event = repo.audit_events[-1]
    original_hash = created_event["integrity_hash"]
    event_id = created_event["id"]

    # 2. Confirm verification succeeds initially
    initial_verification = verify_audit_event_integrity(created_event)
    assert initial_verification.verified is True
    assert initial_verification.stored_hash == original_hash

    # 3. Simulate unauthorized tampering: mutate non-hash field
    # (e.g., adversary attempts to alter the decision details or actor attribution)
    tampered_event = dict(created_event)
    tampered_event["details"] = {"decision": "REJECT", "note": "Tampered note"}

    # 4. Re-run verification on tampered event
    tampered_verification = verify_audit_event_integrity(tampered_event)

    # 5. Must FAIL CLOSED
    assert tampered_verification.verified is False
    assert tampered_verification.stored_hash == original_hash
    assert tampered_verification.computed_hash != original_hash
    assert "mismatch" in tampered_verification.reason.lower()


# 7. Previous-hash chaining creates a tamper-evident sequence
def test_previous_hash_chaining_sequence() -> None:
    app = create_app()
    repo = app.state.repository
    audit_svc = AuditService(repo)

    # Record Event 1
    audit_svc.record(
        event_type=AuditEventType.INVESTIGATION_VIEWED,
        actor_id="officer_1",
        case_id="case-0001",
    )
    event1 = repo.audit_events[-1]
    h1 = event1["integrity_hash"]

    # Record Event 2
    audit_svc.record(
        event_type=AuditEventType.EVIDENCE_VIEWED,
        actor_id="officer_2",
        case_id="case-0001",
    )
    event2 = repo.audit_events[-1]
    h2 = event2["integrity_hash"]

    # Record Event 3
    audit_svc.record(
        event_type=AuditEventType.LEAD_ACTIONED,
        actor_id="officer_3",
        case_id="case-0001",
    )
    event3 = repo.audit_events[-1]
    h3 = event3["integrity_hash"]

    # Verify chain linkages
    assert event2["previous_hash"] == h1
    assert event3["previous_hash"] == h2
    assert h1 != h2 != h3


# 8. Verification API endpoint
def test_audit_verification_api_endpoint() -> None:
    app = create_app()
    client = TestClient(app)

    # Record an event via audit_svc
    audit_svc = AuditService(app.state.repository)
    audit_svc.record(
        event_type=AuditEventType.INVESTIGATION_VIEWED,
        actor_id="officer_io",
        case_id="case-0001",
        details={"action": "test"},
    )
    event_id = app.state.repository.audit_events[-1]["id"]

    # Supervisor/SP token has audit view permission
    sp_token = _make_demo_token("officer_sp", "SP")
    resp = client.get(
        f"/api/v1/audit/{event_id}/verify",
        headers={"Authorization": f"Bearer {sp_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_id"] == event_id
    assert data["verified"] is True
    assert len(data["computed_hash"]) == 64

    # Anonymous call fails
    anon_resp = client.get(f"/api/v1/audit/{event_id}/verify")
    assert anon_resp.status_code == 403

    # Nonexistent event returns 404
    missing_resp = client.get(
        "/api/v1/audit/nonexistent-event-9999/verify",
        headers={"Authorization": f"Bearer {sp_token}"},
    )
    assert missing_resp.status_code == 404
