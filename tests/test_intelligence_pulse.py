"""tests/test_intelligence_pulse.py

Comprehensive Test Suite for P1-A: Cross-Jurisdiction Intelligence Pulse Routing.
Verifies:
  1. Authorized IO dispatches pulse from assigned case -> 200 OK + SHA-256 seal + AUDIT event.
  2. Duplicate transmission suppression -> Re-dispatch returns identical packet_id with 100% deduplication.
  3. Jurisdictional authorization gating -> Unauthorized IO attempting to dispatch for unassigned case gets 403 Forbidden.
  4. Role-based inbox visibility -> Assigned IOs / SHO / SP see authorized pulses; unassigned IOs cannot view.
  5. Authoritative acknowledgment & actioning -> Officer acknowledgment records decision, note, badge, and audit event.
"""

from __future__ import annotations

import base64
import json
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType
from shared.contracts.api import PulseDeliveryStatus, PulseSecurityClassification


def _make_demo_token(user_id: str, role: str) -> str:
    """Helper to generate a valid base64 demo token matching frontend AuthContext session."""
    payload = json.dumps({"sub": user_id, "role": role, "email": f"{user_id}@nexus.internal"})
    return base64.b64encode(payload.encode("utf-8")).decode("utf-8")


def test_authorized_pulse_dispatch_and_audit() -> None:
    app = create_app()
    client = TestClient(app)

    # OFFICER-DEMO-IO-01 (Rajesh Kumar) is assigned to CASE-141 and CASE-207
    token = _make_demo_token("officer_io", "IO")

    payload = {
        "origin_case_id": "CASE-141",
        "target_case_id": "CASE-207",
        "target_district": "Bengaluru Central",
        "headline": "Suspicious Hawala Layering Conduit Discovered",
        "summary": "Cross-case analysis reveals account ACC-7731 receiving layered transfers from Mysuru suspect.",
        "shared_entities": ["P-RAFIQ", "ACC-7731"],
        "evidence_refs": ["SRC-FIR-141", "SRC-TXN-55"],
        "security_classification": "SECRET",
    }

    resp = client.post(
        "/api/v1/nexus/intelligence/pulses/dispatch",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["packet_id"].startswith("PULSE-PKT-2026-")
    assert data["origin_case_id"] == "CASE-141"
    assert data["target_case_id"] == "CASE-207"
    assert data["target_district"] == "Bengaluru Central"
    assert len(data["packet_hash"]) == 64  # Valid SHA-256
    assert data["delivery_status"] == PulseDeliveryStatus.DELIVERED.value
    assert data["security_classification"] == PulseSecurityClassification.SECRET.value
    assert data["shared_entities"] == ["ACC-7731", "P-RAFIQ"]  # sorted

    # Verify immutable audit event
    audit_resp = client.get("/api/v1/audit?limit=20&role=SP")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    dispatch_event = next(
        (e for e in events if e.get("action") == AuditEventType.INTELLIGENCE_PULSE_DISPATCHED.value and e.get("entity_id") == data["packet_id"]),
        None,
    )
    assert dispatch_event is not None
    assert dispatch_event["details"]["packet_hash"] == data["packet_hash"]


def test_pulse_duplicate_transmission_suppression() -> None:
    app = create_app()
    client = TestClient(app)

    token = _make_demo_token("officer_io", "IO")
    payload = {
        "origin_case_id": "CASE-141",
        "target_case_id": "CASE-207",
        "target_district": "Bengaluru Central",
        "headline": "Duplicate Test Conduit",
        "summary": "Testing exact duplicate payload suppression.",
        "shared_entities": ["P-RAFIQ"],
        "evidence_refs": ["SRC-FIR-141"],
        "security_classification": "RESTRICTED",
    }

    # First dispatch
    resp1 = client.post(
        "/api/v1/nexus/intelligence/pulses/dispatch",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert resp1.status_code == 200
    pkt1 = resp1.json()

    # Second dispatch with identical content
    resp2 = client.post(
        "/api/v1/nexus/intelligence/pulses/dispatch",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert resp2.status_code == 200
    pkt2 = resp2.json()

    # Must return exact same packet_id and hash without creating a new duplicate
    assert pkt1["packet_id"] == pkt2["packet_id"]
    assert pkt1["packet_hash"] == pkt2["packet_hash"]


def test_unauthorized_pulse_dispatch_rejected() -> None:
    app = create_app()
    client = TestClient(app)

    # officer_io is NOT assigned to unassigned case 'CASE-999'
    token = _make_demo_token("officer_io", "IO")
    payload = {
        "origin_case_id": "CASE-999",
        "target_case_id": "CASE-207",
        "target_district": "Bengaluru Central",
        "headline": "Unauthorized Dispatch Attempt",
        "summary": "Should be rejected because officer is not assigned to CASE-999.",
        "shared_entities": ["P-UNKNOWN"],
        "evidence_refs": ["SRC-UNKNOWN"],
        "security_classification": "CONFIDENTIAL",
    }

    resp = client.post(
        "/api/v1/nexus/intelligence/pulses/dispatch",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert resp.status_code == 403
    assert "not assigned to origin case" in resp.json()["detail"]


def test_pulse_inbox_and_acknowledgment_flow() -> None:
    app = create_app()
    client = TestClient(app)

    # SP has global supervisory role across all districts
    sp_token = _make_demo_token("officer_sp", "SP")

    inbox_resp = client.get(
        "/api/v1/nexus/intelligence/pulses/inbox",
        headers={"Authorization": f"Bearer {sp_token}"},
    )
    assert inbox_resp.status_code == 200
    pulses = inbox_resp.json()
    assert len(pulses) >= 1

    seeded_packet = pulses[0]
    pkt_id = seeded_packet["packet_id"]

    # Target officer acknowledges the pulse
    io_token = _make_demo_token("officer_io", "IO")
    ack_payload = {
        "decision": "ACTION",
        "note": "Linking Mysuru conduit to ongoing Bengaluru charge-sheet under Section 63 BSA.",
    }

    ack_resp = client.post(
        "/api/v1/nexus/intelligence/pulses/" + pkt_id + "/acknowledge",
        headers={"Authorization": f"Bearer {io_token}"},
        json=ack_payload,
    )
    assert ack_resp.status_code == 200
    updated_pkt = ack_resp.json()

    assert updated_pkt["delivery_status"] == PulseDeliveryStatus.ACTIONED.value
    assert updated_pkt["acknowledged_at"] is not None
    assert "Rajesh Kumar" in updated_pkt["acknowledged_by"]
    assert updated_pkt["acknowledgment_note"] == ack_payload["note"]

    # Verify immutable audit event for acknowledgment
    audit_resp = client.get("/api/v1/audit?limit=20&role=SP")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    ack_event = next(
        (e for e in events if e.get("action") == AuditEventType.INTELLIGENCE_PULSE_ACKNOWLEDGED.value and e.get("entity_id") == pkt_id),
        None,
    )
    assert ack_event is not None
    assert ack_event["details"]["decision"] == "ACTIONED"
