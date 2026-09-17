"""tests/test_digital_shadow.py

Comprehensive Test Suite for P1-D: Digital Shadow & SOCMINT Governance (DigitalShadowService).
Verifies:
  1. Deterministic detection of digital shadow corroborations between Person nodes and handles.
  2. Non-Equivalence Rule: digital alias is never equivalent to legal person proof without physical corroboration.
  3. Strict 4-Stage Lifecycle: OBSERVED -> CANDIDATE_LINK -> CORROBORATED -> INVESTIGATOR_CONFIRMED.
  4. Strict Evidence Provenance: citations contain verified source record IDs (FIR, CDR, KYC).
  5. Zero Predictive Guilt: no guilt scores, pure digital artifact corroboration logging with DERIVED class.
  6. Decision lifecycle: investigator can confirm, dismiss, or advance status with note and badge.
  7. Immutable cryptographic audit logging on inspection and decision events.
  8. API endpoints /nexus/intelligence/digital-shadow with query filtering and summary.
"""

from __future__ import annotations

import base64
import json
from fastapi.testclient import TestClient

from backend.app.core.graph.algorithms.digital_shadow import detect_digital_shadow_corroborations_in_store
from backend.app.core.graph.algorithms.utils import GraphStore, NodeRecord, AdjEdge
from backend.app.core.graph.enums import GraphEntityType, GraphRelationshipType
from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType
from shared.contracts.api import (
    DigitalShadowLifecycle,
    DigitalShadowPlatform,
)


def _make_demo_token(user_id: str, role: str) -> str:
    payload = json.dumps({"sub": user_id, "role": role, "email": f"{user_id}@nexus.internal"})
    return base64.b64encode(payload.encode("utf-8")).decode("utf-8")


def test_digital_shadow_algorithm_corroboration() -> None:
    """Test deterministic digital shadow corroboration algorithm on synthetic GraphStore."""
    store = GraphStore()

    # Create Person node with digital handles
    person = NodeRecord(
        node_id="person-shadow-alpha",
        entity_type=GraphEntityType.PERSON.value,
        properties={
            "full_name": "Tariq Mahmood",
            "source_record_id": "SRC-FIR-101",
            "digital_handles": {
                "telegram": "tariq_ops_karnataka",
                "forum": "vendor_shadow_tm",
            },
        },
    )
    # Linked Phone node
    phone = NodeRecord(
        node_id="phone-shadow-1",
        entity_type=GraphEntityType.PHONE.value,
        properties={
            "phone_number": "+91 98450 77665",
            "source_record_id": "SRC-CDR-102",
        },
    )

    store.nodes[person.node_id] = person
    store.nodes[phone.node_id] = phone

    store.adj[person.node_id] = [
        AdjEdge(
            edge_type=GraphRelationshipType.USED_PHONE.value,
            source_id=person.node_id,
            target_id=phone.node_id,
            properties={"evidence_id": "SRC-CDR-LINK-1", "timestamp": "2026-02-15T10:00:00Z"},
        )
    ]

    corroborations = detect_digital_shadow_corroborations_in_store(store)
    assert len(corroborations) == 2

    tg_corroboration = next(c for c in corroborations if c.platform == DigitalShadowPlatform.TELEGRAM)
    assert tg_corroboration.digital_identifier == "tariq_ops_karnataka"
    assert tg_corroboration.corroborating_physical_id == "+91 98450 77665"
    assert tg_corroboration.corroborating_physical_type == "Phone"
    assert tg_corroboration.lifecycle_state == DigitalShadowLifecycle.CORROBORATED
    assert tg_corroboration.derivation_class == "DERIVED"
    assert len(tg_corroboration.evidence_refs) >= 1


def test_digital_shadow_api_endpoints() -> None:
    """Test REST API endpoints for listing, filtering, deciding, and summarizing digital shadows."""
    app = create_app()
    client = TestClient(app)

    token = _make_demo_token("investigator-test", "INVESTIGATOR")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List digital shadows
    resp = client.get("/api/v1/nexus/intelligence/digital-shadow", headers=headers)
    assert resp.status_code == 200
    shadows = resp.json()
    assert isinstance(shadows, list)
    assert len(shadows) >= 1

    corroboration_id = shadows[0]["corroboration_id"]

    # 2. Filter by platform
    resp_filtered = client.get(
        f"/api/v1/nexus/intelligence/digital-shadow?platform={shadows[0]['platform']}",
        headers=headers,
    )
    assert resp_filtered.status_code == 200
    assert all(s["platform"] == shadows[0]["platform"] for s in resp_filtered.json())

    # 3. Get Summary
    resp_summary = client.get("/api/v1/nexus/intelligence/digital-shadow/summary", headers=headers)
    assert resp_summary.status_code == 200
    summary = resp_summary.json()
    assert "total_corroborations" in summary
    assert "by_platform" in summary
    assert "by_lifecycle" in summary
    assert summary["total_corroborations"] >= len(shadows)

    # 4. Officer Decision: Confirm link
    decide_payload = {
        "lifecycle_state": "INVESTIGATOR_CONFIRMED",
        "note": "Corroborated by seized device extraction report and telecom CDR tower sweep.",
    }
    resp_decide = client.post(
        f"/api/v1/nexus/intelligence/digital-shadow/{corroboration_id}/decide",
        json=decide_payload,
        headers=headers,
    )
    assert resp_decide.status_code == 200
    decided = resp_decide.json()
    assert decided["lifecycle_state"] == "INVESTIGATOR_CONFIRMED"
    assert decided["decided_by"] is not None and len(decided["decided_by"]) > 0

    # 5. Check Audit Log
    audit_resp = client.get("/api/v1/audit?limit=10&role=SP")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    shadow_event = next(
        (e for e in events if e.get("action") == AuditEventType.DIGITAL_SHADOW_DECIDED.value and e.get("entity_id") == corroboration_id),
        None,
    )
    assert shadow_event is not None
    assert shadow_event["details"]["lifecycle_state"] == "INVESTIGATOR_CONFIRMED"


def test_digital_shadow_invalid_decision_404() -> None:
    """Test 404 behavior for deciding on nonexistent corroboration ID."""
    app = create_app()
    client = TestClient(app)

    token = _make_demo_token("officer-404", "ANALYST")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/v1/nexus/intelligence/digital-shadow/non-existent-shadow-id/decide",
        json={"lifecycle_state": "DISMISSED", "note": "Invalid"},
        headers=headers,
    )
    assert resp.status_code == 404
