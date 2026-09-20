import base64
import json
from fastapi.testclient import TestClient
import pytest

from backend.app.main import create_app
from shared.contracts.api import NodePresenceType


def _make_demo_token(user_id: str, role: str, officer_id: str | None = None) -> str:
    payload = json.dumps({
        "sub": user_id,
        "role": role,
        "email": f"{user_id}@nexus.internal",
        "officer_id": officer_id or user_id,
    })
    return base64.b64encode(payload.encode("utf-8")).decode("utf-8")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def sp_token() -> str:
    """Superintendent of Police token (authorized broadly across jurisdictions)."""
    return _make_demo_token("officer_sp", "SP")


@pytest.fixture
def assigned_io_token() -> str:
    """Investigating Officer assigned to case-0001 / CASE-141."""
    return _make_demo_token("officer_io", "IO")


@pytest.fixture
def unassigned_io_token() -> str:
    """Investigating Officer NOT assigned to FIR-2026-207 (case-0016)."""
    return _make_demo_token("OFFICER-DEMO-IO-02", "IO")


def test_case_network_default_depth_is_1(client: TestClient, sp_token: str) -> None:
    """Verifies that calling /api/v1/network/cases/{case_id} without depth defaults to depth=1."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/case-0016", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["depth"] == 1
    # At depth=1 for case-0016, there are 6 nodes: case + 4 accused + 1 evidence
    assert data["total_nodes"] == 6

    labels = [n["label"] for n in data["nodes"]]
    assert "FIR-2026-207" in labels
    assert "Rafeeq Khan" in labels


def test_case_network_depth_0_case_only(client: TestClient, sp_token: str) -> None:
    """Verifies that depth=0 returns only the case node."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/case-0016?depth=0", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_nodes"] == 1
    assert data["total_edges"] == 0
    assert data["nodes"][0]["id"] == "case-0016"


def test_case_network_depth_1_direct_relationships(client: TestClient, sp_token: str) -> None:
    """Verifies that depth=1 returns the case node and direct relationships (accused, evidence, etc)."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/case-0016?depth=1", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["depth"] == 1
    
    nodes_by_label = {n["label"]: n for n in data["nodes"]}
    # Verify accused person is connected with degree 3
    saleem = nodes_by_label["Rafeeq Khan"]
    assert saleem["degree"] == 3
    assert saleem["context"]["distance_from_case"] == 1
    assert saleem["context"]["presence_type"] == NodePresenceType.DIRECT_CASE.value


def test_case_network_depth_2_expanded_intelligence(client: TestClient, sp_token: str) -> None:
    """Verifies that depth=2 expands the network to secondary entities (phones, co-accused in other cases)."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/case-0016?depth=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["depth"] == 2
    assert data["total_nodes"] > 5  # Should discover more than just depth 1 nodes

    nodes_by_label = {n["label"]: n for n in data["nodes"]}
    
    # Verify that secondary connections have correct distance and presence_type
    found_depth_2 = False
    for n in data["nodes"]:
        if n["context"]["distance_from_case"] == 2:
            found_depth_2 = True
            break
    assert found_depth_2


def test_case_network_depth_3_extended(client: TestClient, sp_token: str) -> None:
    """Verifies that depth=3 pulls in deep connections (e.g. syndicates, deep evidence links)."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/case-0016?depth=3", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["depth"] == 3
    assert data["total_nodes"] > 5


def test_case_network_depth_validation_limits(client: TestClient, sp_token: str) -> None:
    """Verifies that requests for depth > 4 or depth < 0 are rejected by the API."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    
    # Test max limit
    res_high = client.get("/api/v1/network/cases/case-0016?depth=5", headers=headers)
    assert res_high.status_code == 422
    
    # Test min limit
    res_low = client.get("/api/v1/network/cases/case-0016?depth=-1", headers=headers)
    assert res_low.status_code == 422



def test_case_network_rbac_unauthorized_investigator(client: TestClient, unassigned_io_token: str) -> None:
    """Verifies unassigned investigator cannot access case network."""
    headers = {"Authorization": f"Bearer {unassigned_io_token}"}
    res = client.get("/api/v1/network/cases/case-0016?depth=1", headers=headers)
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


def test_case_network_by_fir_number(client: TestClient, sp_token: str) -> None:
    """Verifies case_id parameter accepts either case node ID (case-0016) or FIR number (FIR-2026-207)."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/FIR-2026-207?depth=1", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_nodes"] == 6
    assert data["case_id"] == "FIR-2026-207"
