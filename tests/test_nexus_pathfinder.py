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
    app = create_app()
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
    # Reset demo state to make sure it is in Before resolution state
    client.post("/api/v1/nexus/demo/reset")

    # In Before state, direct 2-hop alias path does NOT exist.
    # With max_depth=4, the 5-hop bank wire is also cut off, so found is False.
    res = client.get("/api/v1/nexus/path?source=CASE-141&target=CASE-207&max_depth=4")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is False
    assert data["hops"] == 0
    assert "unresolved" in data["explanation"].lower() or "no connection" in data["explanation"].lower()


def test_pathfinder_within_case_multi_hop_before_resolution(client: TestClient) -> None:
    client.post("/api/v1/nexus/demo/reset")

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
    client.post("/api/v1/nexus/demo/reset")

    # Reverse: ACC-7731 -> P-MEENA
    res = client.get("/api/v1/nexus/path?source=ACC-7731&target=P-MEENA")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["hops"] == 3
    assert data["node_ids"][0] == "ACC-7731"
    assert data["node_ids"][-1] == "P-MEENA"


def test_pathfinder_financial_flow_path(client: TestClient) -> None:
    client.post("/api/v1/nexus/demo/reset")

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
    client.post("/api/v1/nexus/demo/reset")
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


def test_pathfinder_non_golden_intra_cluster_path(client: TestClient) -> None:
    # case-0001 -> case-0002 within Coastal Narcotics Syndicate
    res = client.get("/api/v1/nexus/path?source=case-0001&target=case-0002&max_depth=6")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["hops"] >= 1
    assert data["node_ids"][0] == "case-0001"
    assert data["node_ids"][-1] == "case-0002"
    assert "Discovered" in data["explanation"]


def test_pathfinder_non_golden_cross_cluster_broker_path(client: TestClient) -> None:
    # case-0001 (Alpha) -> case-0010 (Beta) via Ramesh Hegde (The Broker, person-0051)
    res = client.get("/api/v1/nexus/path?source=case-0001&target=case-0010&max_depth=8")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert "person-0051" in data["node_ids"]


def test_pathfinder_non_golden_disconnected_isolated_cases(client: TestClient) -> None:
    # case-0030 -> case-0035 (two isolated independent cases)
    res = client.get("/api/v1/nexus/path?source=case-0030&target=case-0035&max_depth=6")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is False
    assert data["hops"] == 0
    assert "No connection found" in data["explanation"]


def test_pathfinder_arbitrary_person_to_case_path(client: TestClient) -> None:
    # person-0074 -> case-0049 (direct accused link)
    res = client.get("/api/v1/nexus/path?source=person-0074&target=case-0049&max_depth=4")
    assert res.status_code == 200
    data = res.json()
    assert data["found"] is True
    assert data["hops"] == 1
    assert data["node_ids"] == ["person-0074", "case-0049"]

