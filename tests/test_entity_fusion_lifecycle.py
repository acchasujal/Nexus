"""tests/test_entity_fusion_lifecycle.py

Tests the authoritative Entity Fusion decision lifecycle across all 3 branches:
- CONFIRM: mutates authoritative graph, creates new snapshot, records audit
- REJECT: no graph mutation, retains audit history, no new snapshot
- DEFER: no graph mutation, retains proposed state, verification pending, no new snapshot
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app
from backend.app.services.proactive_intelligence_service import (
    CANONICAL_SNAPSHOT_CURRENT,
    ProactiveIntelligenceService,
)


@pytest.fixture
def test_setup():
    repo = InMemoryBackendRepository()
    proactive_svc = ProactiveIntelligenceService(repo.to_graph_store())
    app = create_app(repository=repo)
    client = TestClient(app)
    return client, repo, proactive_svc


def test_entity_fusion_lifecycle_confirm(test_setup) -> None:
    client, repo, proactive_svc = test_setup
    client.post("/api/v1/nexus/demo/reset", headers={"X-Role": "INVESTIGATOR"})

    resp = client.post(
        "/api/v1/nexus/resolution/RC-1/decision",
        json={"decision": "CONFIRM", "decided_by": "Senior IO"},
        headers={"X-Role": "INVESTIGATOR"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["candidate_id"] == "RC-1"
    assert data["status"] == "CONFIRMED"
    assert data["new_snapshot_id"] is not None
    assert len(data["affected_node_ids"]) > 0

    # Verify audit log recorded decision
    audit_resp = client.get("/api/v1/audit?limit=20&role=INVESTIGATOR")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    confirm_events = [e for e in events if e.get("entity_id") == "RC-1" and e.get("details", {}).get("decision") == "CONFIRM"]
    assert len(confirm_events) >= 1
    assert confirm_events[0]["details"]["new_snapshot_id"] == data["new_snapshot_id"]


def test_entity_fusion_lifecycle_reject(test_setup) -> None:
    client, repo, proactive_svc = test_setup
    client.post("/api/v1/nexus/demo/reset", headers={"X-Role": "INVESTIGATOR"})

    resp = client.post(
        "/api/v1/nexus/resolution/RC-1/decision",
        json={"decision": "REJECT", "decided_by": "Senior IO", "note": "False positive match on shared surname"},
        headers={"X-Role": "INVESTIGATOR"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["candidate_id"] == "RC-1"
    assert data["status"] == "REJECTED"
    assert data["new_snapshot_id"] is None
    assert data["affected_node_ids"] == []

    # Verify audit log retained history
    audit_resp = client.get("/api/v1/audit?limit=20&role=INVESTIGATOR")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    reject_events = [e for e in events if e.get("entity_id") == "RC-1" and e.get("details", {}).get("decision") == "REJECT"]
    assert len(reject_events) >= 1
    assert reject_events[0]["details"]["note"] == "False positive match on shared surname"


def test_entity_fusion_lifecycle_defer(test_setup) -> None:
    client, repo, proactive_svc = test_setup
    client.post("/api/v1/nexus/demo/reset", headers={"X-Role": "INVESTIGATOR"})

    resp = client.post(
        "/api/v1/nexus/resolution/RC-1/decision",
        json={"decision": "DEFER", "decided_by": "Senior IO", "note": "Pending biometrics verification"},
        headers={"X-Role": "INVESTIGATOR"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["candidate_id"] == "RC-1"
    assert data["status"] == "DEFERRED"
    assert data["new_snapshot_id"] is None
    assert data["affected_node_ids"] == []

    # Verify audit log recorded deferral
    audit_resp = client.get("/api/v1/audit?limit=20&role=INVESTIGATOR")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    defer_events = [e for e in events if e.get("entity_id") == "RC-1" and e.get("details", {}).get("decision") == "DEFER"]
    assert len(defer_events) >= 1
    assert defer_events[0]["details"]["decision"] == "DEFER"
