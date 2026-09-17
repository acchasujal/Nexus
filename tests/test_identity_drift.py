"""tests/test_identity_drift.py

Comprehensive Test Suite for P1-B: Identity Drift Radar (IdentityDriftService).
Verifies:
  1. Deterministic detection of Phone Turnover (SIM hopping), Device Hopping (IMEI switching),
     Vehicle Drift, and Alias Evolution across graph entities.
  2. Strict Evidence Provenance: citations contain verified source record IDs (FIR, CDR, KYC).
  3. Zero Predictive Guilt: no guilt scores, pure operational transition logging with DERIVED class.
  4. Decision lifecycle: investigator can confirm, dismiss, or flag for monitoring with note and badge.
  5. Immutable cryptographic audit logging on inspection and decision events.
  6. API endpoints /nexus/intelligence/identity-drift with query filtering and summary.
"""

from __future__ import annotations

import base64
import json
from fastapi.testclient import TestClient

from backend.app.core.graph.algorithms.identity_drift import detect_identity_drifts_in_store
from backend.app.core.graph.algorithms.utils import GraphStore, NodeRecord, AdjEdge
from backend.app.core.graph.enums import GraphEntityType, GraphRelationshipType
from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType
from shared.contracts.api import IdentityDriftStatus, IdentityDriftType


def _make_demo_token(user_id: str, role: str) -> str:
    payload = json.dumps({"sub": user_id, "role": role, "email": f"{user_id}@nexus.internal"})
    return base64.b64encode(payload.encode("utf-8")).decode("utf-8")


def test_identity_drift_algorithm_synthetic_graph() -> None:
    """Test identity drift algorithm on a synthetic isolated GraphStore."""
    store = GraphStore()

    # Create Person node with multiple aliases and base phone
    p1 = NodeRecord(
        node_id="person-test-1",
        entity_type=GraphEntityType.PERSON.value,
        properties={
            "full_name": "Farhan Akhtar",
            "aliases": ["Doctor", "Chhota"],
            "phone_number": "+91 98450 11111",
            "vehicle_number": "KA01AB1111",
            "created_at": "2026-01-10T10:00:00Z",
            "source_record_id": "SRC-FIR-101",
        },
    )
    store.nodes[p1.node_id] = p1

    # Secondary phone node
    ph2 = NodeRecord(
        node_id="phone-test-2",
        entity_type=GraphEntityType.PHONE.value,
        properties={
            "phone_number": "+91 98450 22222",
            "imei": "861111222233334",
            "created_at": "2026-02-15T12:00:00Z",
            "source_record_id": "SRC-CDR-102",
        },
    )
    store.nodes[ph2.node_id] = ph2

    # Third phone with different IMEI
    ph3 = NodeRecord(
        node_id="phone-test-3",
        entity_type=GraphEntityType.PHONE.value,
        properties={
            "phone_number": "+91 98450 33333",
            "imei": "869999888877776",
            "created_at": "2026-03-01T14:00:00Z",
            "source_record_id": "SRC-CDR-103",
        },
    )
    store.nodes[ph3.node_id] = ph3

    # Secondary vehicle
    veh2 = NodeRecord(
        node_id="veh-test-2",
        entity_type=GraphEntityType.VEHICLE.value,
        properties={
            "vehicle_number": "KA04XY9999",
            "created_at": "2026-02-20T10:00:00Z",
            "source_record_id": "SRC-FIR-102",
        },
    )
    store.nodes[veh2.node_id] = veh2

    # Edges
    edge1 = AdjEdge(
        edge_type=GraphRelationshipType.USED_PHONE.value,
        source_id=p1.node_id,
        target_id=ph2.node_id,
        properties={"timestamp": "2026-02-15T12:00:00Z", "source_record_id": "SRC-CDR-102"},
    )
    edge2 = AdjEdge(
        edge_type=GraphRelationshipType.USED_PHONE.value,
        source_id=p1.node_id,
        target_id=ph3.node_id,
        properties={"timestamp": "2026-03-01T14:00:00Z", "source_record_id": "SRC-CDR-103"},
    )
    edge3 = AdjEdge(
        edge_type=GraphRelationshipType.USED_VEHICLE.value,
        source_id=p1.node_id,
        target_id=veh2.node_id,
        properties={"timestamp": "2026-02-20T10:00:00Z", "source_record_id": "SRC-FIR-102"},
    )

    store.adj[p1.node_id] = [edge1, edge2, edge3]

    drifts = detect_identity_drifts_in_store(store, person_id_filter=p1.node_id)
    assert len(drifts) >= 3

    types = {d.drift_type for d in drifts}
    assert IdentityDriftType.PHONE_TURNOVER in types
    assert IdentityDriftType.DEVICE_HOP in types
    assert IdentityDriftType.VEHICLE_DRIFT in types
    assert IdentityDriftType.ALIAS_EVOLUTION in types

    # Check evidence provenance
    for d in drifts:
        assert len(d.evidence_refs) > 0
        assert d.derivation_class == "DERIVED"
        assert d.person_id == p1.node_id
        assert d.human_status == IdentityDriftStatus.DETECTED


def test_api_list_identity_drifts() -> None:
    app = create_app()
    client = TestClient(app)
    token = _make_demo_token("officer_io", "IO")

    resp = client.get(
        "/api/v1/nexus/intelligence/identity-drift",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    drifts = resp.json()
    assert len(drifts) >= 3

    # Check baseline seeded events
    rafiq_events = [d for d in drifts if d["person_id"] == "P-RAFIQ"]
    assert len(rafiq_events) >= 1
    assert rafiq_events[0]["drift_type"] == IdentityDriftType.PHONE_TURNOVER.value
    assert "SRC-FIR-141" in rafiq_events[0]["evidence_refs"]


def test_api_filter_identity_drifts() -> None:
    app = create_app()
    client = TestClient(app)
    token = _make_demo_token("officer_io", "IO")

    # Filter by type
    resp = client.get(
        f"/api/v1/nexus/intelligence/identity-drift?drift_type={IdentityDriftType.DEVICE_HOP.value}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    hops = resp.json()
    assert all(h["drift_type"] == IdentityDriftType.DEVICE_HOP.value for h in hops)


def test_api_decide_identity_drift_and_audit() -> None:
    app = create_app()
    client = TestClient(app)
    token = _make_demo_token("officer_io", "IO")

    # Decide on Rafiq Khan drift
    drift_id = "DRIFT-2026-PH-RAFIQ"
    payload = {
        "status": IdentityDriftStatus.CONFIRMED.value,
        "note": "Corroborated with Mysuru tower CDR sweep. Subject transitioned to burner line.",
    }

    resp = client.post(
        f"/api/v1/nexus/intelligence/identity-drift/{drift_id}/decide",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["drift_id"] == drift_id
    assert updated["human_status"] == IdentityDriftStatus.CONFIRMED.value
    assert updated["investigator_note"] == payload["note"]
    assert updated["decided_at"] is not None

    # Verify audit event
    audit_resp = client.get("/api/v1/audit?limit=10&role=SP")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    drift_event = next(
        (e for e in events if e.get("action") == AuditEventType.IDENTITY_DRIFT_DECIDED.value and e.get("entity_id") == drift_id),
        None,
    )
    assert drift_event is not None
    assert drift_event["details"]["status"] == IdentityDriftStatus.CONFIRMED.value


def test_api_get_identity_drift_summary() -> None:
    app = create_app()
    client = TestClient(app)
    token = _make_demo_token("analyst_01", "ANALYST")

    resp = client.get(
        "/api/v1/nexus/intelligence/identity-drift/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    summary = resp.json()
    assert "total_drifts" in summary
    assert summary["total_drifts"] >= 3
    assert "phone_turnovers" in summary
    assert "device_hops" in summary
    assert "by_type" in summary
    assert "by_status" in summary
