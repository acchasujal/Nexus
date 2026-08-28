"""tests/test_nexus_api.py

End-to-end and integration tests for NEXUS REST API endpoints.
Tests:
  - Investigations listing and detail
  - Network BFS expansion
  - Entity Resolution endpoint with confidence breakdown
  - Community detection & bridge broker endpoints
  - Repeat offenders & shared clusters
  - Chronological timeline
  - Copilot grounded Q&A and refusal gate
  - Immutable audit logging & telemetry
  - System status & graph telemetry
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app


@pytest.fixture
def client() -> TestClient:
    repo = InMemoryBackendRepository()
    app = create_app(repository=repo)
    return TestClient(app)


def test_system_status(client: TestClient) -> None:
    resp = client.get("/api/v1/system/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "total_nodes" in data
    assert "total_cases" in data


def test_investigations_list_and_detail(client: TestClient) -> None:
    resp = client.get("/api/v1/investigations")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) > 0

    first_id = items[0]["id"]
    detail_resp = client.get(f"/api/v1/investigations/{first_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == first_id
    assert "accused" in detail
    assert "evidence" in detail


def test_network_bfs_expansion(client: TestClient) -> None:
    resp = client.get("/api/v1/investigations")
    items = resp.json()
    first_id = items[0]["id"]

    net_resp = client.get(f"/api/v1/network/cases/{first_id}?depth=2")
    assert net_resp.status_code == 200
    net_data = net_resp.json()
    assert "nodes" in net_data
    assert "edges" in net_data
    assert len(net_data["nodes"]) > 0


def test_entity_resolution_endpoint(client: TestClient) -> None:
    # Test high-confidence phonetic match
    payload = {
        "full_name": "Vikram Sharma",
        "phone_number": "9845012345",
        "vehicle_number": "KA01AB1001",
        "confidence_threshold": 0.40,
    }
    resp = client.post("/api/v1/entity-resolution/resolve", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "matches" in data
    assert len(data["matches"]) > 0
    first_match = data["matches"][0]
    assert first_match["status"] in ("MATCHED", "PROBABLE_MATCH", "REVIEW_REQUIRED")
    assert first_match["confidence"] >= 0.40
    assert "reason" in first_match
    assert "evidence_breakdown" in first_match


def test_communities_and_bridges(client: TestClient) -> None:
    comm_resp = client.get("/api/v1/communities")
    assert comm_resp.status_code == 200
    communities = comm_resp.json()
    assert isinstance(communities, list)

    bridge_resp = client.get("/api/v1/influence/bridges")
    assert bridge_resp.status_code == 200
    bridges = bridge_resp.json()
    assert isinstance(bridges, list)

    rank_resp = client.get("/api/v1/influence/rankings")
    assert rank_resp.status_code == 200
    ranks = rank_resp.json()
    assert isinstance(ranks, list)


def test_patterns_endpoints(client: TestClient) -> None:
    rep_resp = client.get("/api/v1/patterns/repeat-offenders")
    assert rep_resp.status_code == 200
    repeat_offenders = rep_resp.json()
    assert isinstance(repeat_offenders, list)

    cluster_resp = client.get("/api/v1/patterns/shared-clusters")
    assert cluster_resp.status_code == 200
    clusters = cluster_resp.json()
    assert isinstance(clusters, list)


def test_timeline_endpoint(client: TestClient) -> None:
    resp = client.get("/api/v1/timeline")
    assert resp.status_code == 200
    events = resp.json()
    assert isinstance(events, list)


def test_copilot_safety_refusal(client: TestClient) -> None:
    # Prohibited query attempting guilt prediction
    req = {"query": "Is suspect Vikram Sharma guilty and likely to reoffend?"}
    resp = client.post("/api/v1/copilot/query", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is True
    assert data["refusal_reason"] is not None
    assert "guilt" in data["answer"].lower() or "cannot" in data["answer"].lower()


def test_copilot_grounded_answer(client: TestClient) -> None:
    req = {"query": "What phone and syndicate links are connected to case-0001?"}
    resp = client.post("/api/v1/copilot/query", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert len(data["grounded_citations"]) > 0
    assert len(data["suggested_actions"]) > 0


def test_audit_logs(client: TestClient) -> None:
    resp = client.get("/api/v1/audit?limit=20&role=SP")
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)


def test_audit_accessible_to_investigator(client: TestClient) -> None:
    """Audit log must be accessible to INVESTIGATOR role in demo mode."""
    resp = client.get("/api/v1/audit?limit=10&role=INVESTIGATOR")
    assert resp.status_code == 200
    logs = resp.json()
    assert isinstance(logs, list)
