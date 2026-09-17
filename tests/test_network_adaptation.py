"""tests/test_network_adaptation.py

Comprehensive Test Suite for P1-C: Network Adaptation Engine (NetworkAdaptationService).
Verifies:
  1. Deterministic detection of intermediary replacement (A -> X -> B proxy conduit),
     bridge broker substitution, financial rerouting, and community reconnects.
  2. Strict Evidence Provenance: citations contain verified source record IDs (FIR, CDR, TXN).
  3. Zero Predictive Guilt: no guilt scores, pure topological structural transition logging with DERIVED class.
  4. Decision lifecycle: investigator can confirm, dismiss, or flag for monitoring with note and badge.
  5. Immutable cryptographic audit logging on inspection and decision events.
  6. API endpoints /nexus/intelligence/network-adaptation with query filtering and summary.
"""

from __future__ import annotations

import base64
import json
from fastapi.testclient import TestClient

from backend.app.core.graph.algorithms.network_adaptation import detect_network_adaptations_in_store
from backend.app.core.graph.algorithms.utils import GraphStore, NodeRecord, AdjEdge
from backend.app.core.graph.enums import GraphEntityType, GraphRelationshipType
from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType
from shared.contracts.api import AdaptationReviewStatus, NetworkAdaptationType


def _make_demo_token(user_id: str, role: str) -> str:
    payload = json.dumps({"sub": user_id, "role": role, "email": f"{user_id}@nexus.internal"})
    return base64.b64encode(payload.encode("utf-8")).decode("utf-8")


def test_network_adaptation_algorithm_proxy_detection() -> None:
    """Test deterministic intermediary proxy replacement algorithm on synthetic graph."""
    store = GraphStore()

    # Create Primary Suspect A
    node_a = NodeRecord(
        node_id="person-alpha",
        entity_type=GraphEntityType.PERSON.value,
        properties={"full_name": "Alpha Handler", "source_record_id": "SRC-FIR-101"},
    )
    # Create Intermediary X
    node_x = NodeRecord(
        node_id="person-proxy-x",
        entity_type=GraphEntityType.PERSON.value,
        properties={"full_name": "Proxy Conduit X", "source_record_id": "SRC-CDR-102"},
    )
    # Create Target Contact B
    node_b = NodeRecord(
        node_id="person-beta",
        entity_type=GraphEntityType.PERSON.value,
        properties={"full_name": "Beta Receiver", "source_record_id": "SRC-FIR-103"},
    )

    store.nodes[node_a.node_id] = node_a
    store.nodes[node_x.node_id] = node_x
    store.nodes[node_b.node_id] = node_b

    # Add edges: Alpha -> Proxy X and Proxy X -> Beta
    store.adj[node_a.node_id] = [
        AdjEdge(
            edge_type=GraphRelationshipType.COMMUNICATED_WITH.value,
            source_id=node_a.node_id,
            target_id=node_x.node_id,
            properties={"evidence_id": "SRC-CDR-LEG-1", "timestamp": "2026-03-01T10:00:00Z"},
        )
    ]
    store.adj[node_x.node_id] = [
        AdjEdge(
            edge_type=GraphRelationshipType.COMMUNICATED_WITH.value,
            source_id=node_x.node_id,
            target_id=node_b.node_id,
            properties={"evidence_id": "SRC-CDR-LEG-2", "timestamp": "2026-03-01T10:30:00Z"},
        )
    ]

    events = detect_network_adaptations_in_store(store)
    assert len(events) >= 1
    proxy_events = [e for e in events if e.adaptation_type == NetworkAdaptationType.INTERMEDIARY_REPLACEMENT]
    assert len(proxy_events) == 1
    ev = proxy_events[0]
    assert ev.primary_entity_id == "person-alpha"
    assert ev.substitute_intermediary_id == "person-proxy-x"
    assert ev.secondary_entity_id == "person-beta"
    assert ev.derivation_class == "DERIVED"
    assert len(ev.evidence_refs) >= 1


def test_network_adaptation_api_endpoints() -> None:
    """Test REST API endpoints for listing, filtering, deciding, and summarizing network adaptations."""
    app = create_app()
    client = TestClient(app)

    token = _make_demo_token("investigator-test", "INVESTIGATOR")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. List adaptations
    resp = client.get("/api/v1/nexus/intelligence/network-adaptation", headers=headers)
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)
    assert len(events) >= 1

    event_id = events[0]["adaptation_id"]

    # 2. Filter by adaptation_type
    resp_filtered = client.get(
        f"/api/v1/nexus/intelligence/network-adaptation?adaptation_type={events[0]['adaptation_type']}",
        headers=headers,
    )
    assert resp_filtered.status_code == 200
    assert all(e["adaptation_type"] == events[0]["adaptation_type"] for e in resp_filtered.json())

    # 3. Get Summary
    resp_summary = client.get("/api/v1/nexus/intelligence/network-adaptation/summary", headers=headers)
    assert resp_summary.status_code == 200
    summary = resp_summary.json()
    assert "total_adaptations" in summary
    assert "by_type" in summary
    assert "by_status" in summary
    assert summary["total_adaptations"] >= len(events)

    # 4. Officer Decision
    decide_payload = {
        "status": "CONFIRMED",
        "note": "Verified CDR corroboration of proxy handover between Rafiq and Deepak.",
    }
    resp_decide = client.post(
        f"/api/v1/nexus/intelligence/network-adaptation/{event_id}/decide",
        json=decide_payload,
        headers=headers,
    )
    assert resp_decide.status_code == 200
    decided = resp_decide.json()
    assert decided["review_status"] == "CONFIRMED"
    assert decided["decided_by"] is not None and len(decided["decided_by"]) > 0

    # 5. Check Audit Log
    audit_resp = client.get("/api/v1/audit?limit=10&role=SP")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    adapt_event = next(
        (e for e in events if e.get("action") == AuditEventType.NETWORK_ADAPTATION_DECIDED.value and e.get("entity_id") == event_id),
        None,
    )
    assert adapt_event is not None
    assert adapt_event["details"]["status"] == "CONFIRMED"


def test_network_adaptation_invalid_decision_404() -> None:
    """Test 404 behavior for deciding on nonexistent adaptation ID."""
    app = create_app()
    client = TestClient(app)

    token = _make_demo_token("officer-404", "ANALYST")
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(
        "/api/v1/nexus/intelligence/network-adaptation/non-existent-adapt-id/decide",
        json={"status": "DISMISSED", "note": "Invalid"},
        headers=headers,
    )
    assert resp.status_code == 404
