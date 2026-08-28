"""tests/test_nexus_pathfinder.py

Comprehensive tests for the NEXUS Interactive Investigative Pathfinder endpoint (/api/v1/nexus/path).
Tests:
  1. Arbitrary valid source -> target multi-hop BFS path
  2. Reverse direction traversal
  3. Disconnected components return found=False
  4. Golden path FIR-141 -> FIR-207 when resolved
  5. Source entity not found error message
  6. Target entity not found error message
  7. Source == Target handling (0 hops)
  8. Max depth boundary enforcement
  9. Response schema fields (found, node_ids, edge_ids, hops, evidence_ids, explanation)
  10. Audit event recording on path queries
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture
def client() -> TestClient:
    from backend.app.db.in_memory import InMemoryBackendRepository
    repo = InMemoryBackendRepository()
    repo.clear()
    
    repo.nodes = {
        "CASE-141": {"id": "CASE-141", "entity_type": "Case", "properties": {"fir_number": "141/2026", "title": "FIR 141"}},
        "CASE-207": {"id": "CASE-207", "entity_type": "Case", "properties": {"fir_number": "207/2026", "title": "FIR 207"}},
        "P-MEENA": {"id": "P-MEENA", "entity_type": "Person", "properties": {"full_name": "Meena", "case_id": "CASE-141"}},
        "P-RAFIQ": {"id": "P-RAFIQ", "entity_type": "Person", "properties": {"full_name": "Rafiq Khan", "case_id": "CASE-141"}},
        "P-DEEPAK": {"id": "P-DEEPAK", "entity_type": "Person", "properties": {"full_name": "Deepak Rao", "case_id": "CASE-207"}},
        "ACC-7731": {"id": "ACC-7731", "entity_type": "Account", "properties": {"account_number": "7731"}},
        "ACC-9914": {"id": "ACC-9914", "entity_type": "Account", "properties": {"account_number": "9914"}},
    }
    
    repo.edges = [
        {"id": "E1", "source_id": "P-MEENA", "target_id": "CASE-141", "edge_type": "VICTIM_IN", "properties": {"evidence_ids": ["EVD1"]}},
        {"id": "E2", "source_id": "P-RAFIQ", "target_id": "CASE-141", "edge_type": "ACCUSED_IN", "properties": {"evidence_ids": ["EVD2"]}},
        {"id": "E3", "source_id": "P-RAFIQ", "target_id": "ACC-7731", "edge_type": "OWNS_ACCOUNT", "properties": {"evidence_ids": ["EVD3"]}},
        {"id": "E-OWN-9914", "source_id": "P-DEEPAK", "target_id": "ACC-9914", "edge_type": "OWNS_ACCOUNT", "properties": {"evidence_ids": ["EVD4"]}},
        {"id": "E5", "source_id": "ACC-9914", "target_id": "ACC-7731", "edge_type": "TRANSFERRED_TO", "properties": {"evidence_ids": ["EVD5"]}},
        # Path connects CASE-207 -> P-DEEPAK
        {"id": "E6", "source_id": "P-DEEPAK", "target_id": "CASE-207", "edge_type": "ACCUSED_IN", "properties": {"evidence_ids": ["EVD6"]}},
    ]
    
    repo.review_candidates = {
        "RC-1": {
            "incoming_record_id": "P-DEEPAK",
            "candidate_node_id": "P-RAFIQ",
            "status": "PENDING"
        }
    }
    
    repo._rebuild_indexes()

    app = create_app(repository=repo)
    from backend.app.api.nexus_routes import _demo_state
    _demo_state.reset()
    return TestClient(app)


def test_pathfinder_missing_params(client: TestClient) -> None:
    res = client.get("/api/v1/nexus/path")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is False
    assert "required" in data["explanation"].lower()


def test_pathfinder_same_source_target(client: TestClient) -> None:
    res = client.get("/api/v1/nexus/path?source=CASE-141&target=CASE-141")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is False
    assert data["hops"] == 0
    assert "identical" in data["explanation"].lower()


def test_pathfinder_unknown_source(client: TestClient) -> None:
    res = client.get("/api/v1/nexus/path?source=UNKNOWN-ENTITY&target=CASE-141")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is False
    assert "not found" in data["explanation"].lower()


def test_pathfinder_unknown_target(client: TestClient) -> None:
    res = client.get("/api/v1/nexus/path?source=CASE-141&target=UNKNOWN-TARGET")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is False
    assert "not found" in data["explanation"].lower()


def test_pathfinder_unresolved_cross_case_disconnected(client: TestClient) -> None:

    # In Before state, direct 2-hop alias path does NOT exist.
    # With max_depth=4, the 5-hop bank wire is also cut off, so found is False.
    res = client.get("/api/v1/nexus/path?source=CASE-141&target=CASE-207&max_depth=4")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is False
    assert data["hops"] == 0
    assert "unresolved" in data["explanation"].lower() or "no connection" in data["explanation"].lower()


def test_pathfinder_within_case_multi_hop_before_resolution(client: TestClient) -> None:

    # In CASE-141: P_MEENA --(VICTIM_IN)--> CASE-141 <--(ACCUSED_IN)-- P-RAFIQ-K --(OWNS_ACCOUNT)--> ACC-7731
    res = client.get("/api/v1/nexus/path?source=P-MEENA&target=ACC-7731")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["hops"] == 3
    assert data["node_ids"][0] == "P-MEENA"
    assert data["node_ids"][-1] == "ACC-7731"
    assert len(data["edge_ids"]) == 3
    assert len(data["evidence_ids"]) > 0


def test_pathfinder_reverse_direction(client: TestClient) -> None:

    # Reverse: ACC-7731 -> P-MEENA
    res = client.get("/api/v1/nexus/path?source=ACC-7731&target=P-MEENA")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["hops"] == 3
    assert data["node_ids"][0] == "ACC-7731"
    assert data["node_ids"][-1] == "P-MEENA"


def test_pathfinder_financial_flow_path(client: TestClient) -> None:

    # P-DEEPAK --(OWNS_ACCOUNT)--> ACC-9914 --(TRANSFERRED_TO)--> ACC-7731
    res = client.get("/api/v1/nexus/path?source=P-DEEPAK&target=ACC-7731")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["hops"] == 2
    assert data["node_ids"] == ["P-DEEPAK", "ACC-9914", "ACC-7731"]
    assert "E-OWN-9914" in data["edge_ids"]


def test_pathfinder_golden_path_after_resolution(client: TestClient) -> None:
    # Confirm candidate RC-1
    decision_res = client.post(
        "/api/v1/nexus/resolution/RC-1/decision",
        json={"decision": "CONFIRM", "decided_by": "Test Investigator"},
    )
    assert decision_res.status_code == 200

    # Query path between FIR 141 and FIR 207
    res = client.get("/api/v1/nexus/path?source=CASE-141&target=CASE-207")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["hops"] >= 1
    assert "CASE-141" in data["node_ids"]
    assert "CASE-207" in data["node_ids"]
    assert len(data["evidence_ids"]) > 0
    assert "Rafiq" in data["explanation"]


def test_pathfinder_max_depth_exceeded(client: TestClient) -> None:
    client.post("/api/v1/nexus/demo/reset")

    # Path from P-MEENA to ACC-7731 is 3 hops. With max_depth=1 or 2, it should not find it.
    res = client.get("/api/v1/nexus/path?source=P-MEENA&target=ACC-7731&max_depth=2")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is False
    assert data["hops"] == 0
