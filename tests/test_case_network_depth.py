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
    """Investigating Officer NOT assigned to FIR-2026-495 (case-0016)."""
    return _make_demo_token("OFFICER-DEMO-IO-02", "IO")


def test_case_network_default_depth_is_1(client: TestClient, sp_token: str) -> None:
    """Verifies that calling /api/v1/network/cases/{case_id} without depth defaults to depth=1."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/case-0016", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["depth"] == 1
    # At depth=1 for FIR-2026-495, there are strictly 5 nodes: case + 3 accused + 1 evidence
    assert data["total_nodes"] == 5
    labels = [n["label"] for n in data["nodes"]]
    assert "FIR-2026-495" in labels
    assert "Karan Gupta" in labels
    assert "Imran Malhotra" in labels
    assert "Anil Kumar" in labels


def test_case_network_depth_0_case_only(client: TestClient, sp_token: str) -> None:
    """Verifies depth=0 returns strictly the case node and 0 edges."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/case-0016?depth=0", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["depth"] == 0
    assert data["total_nodes"] == 1
    assert data["total_edges"] == 0
    node = data["nodes"][0]
    assert node["id"] == "case-0016"
    assert node["context"]["presence_type"] == NodePresenceType.DIRECT_CASE.value
    assert node["context"]["distance_from_case"] == 0


def test_case_network_depth_1_direct_relationships(client: TestClient, sp_token: str) -> None:
    """Verifies depth=1 returns only direct case entities with DIRECT_CASE and EVIDENCE context."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/case-0016?depth=1", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_nodes"] == 5

    # Check node contexts
    nodes_by_label = {n["label"]: n for n in data["nodes"]}

    # Accused persons
    karan = nodes_by_label["Karan Gupta"]
    assert karan["context"]["presence_type"] == NodePresenceType.DIRECT_CASE.value
    assert karan["context"]["distance_from_case"] == 1
    assert "FIR-2026-495" in karan["context"]["source_ids"]
    assert "ACCUSED_IN" in karan["context"]["relationship_types"]
    assert "FIR-2026-495" in karan["context"]["readable_path"]

    # Evidence item
    evidence_nodes = [n for n in data["nodes"] if n["entity_type"] == "Evidence"]
    assert len(evidence_nodes) == 1
    ev = evidence_nodes[0]
    assert ev["context"]["presence_type"] == NodePresenceType.EVIDENCE.value
    assert ev["context"]["distance_from_case"] == 1


def test_case_network_depth_2_expanded_intelligence(client: TestClient, sp_token: str) -> None:
    """Verifies depth=2 pulls in multi-hop intelligence entities (Cyber Hawala Ring & broker)."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/case-0016?depth=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["depth"] == 2
    assert data["total_nodes"] > 5  # Expands to 34 nodes

    nodes_by_label = {n["label"]: n for n in data["nodes"]}

    # Pradeep Iyer is connected via INTEL-BETA-CYBER
    assert "Pradeep Iyer" in nodes_by_label
    pradeep = nodes_by_label["Pradeep Iyer"]
    assert pradeep["context"]["presence_type"] == NodePresenceType.INTELLIGENCE_EXPANSION.value
    assert pradeep["context"]["distance_from_case"] == 2
    assert "INTEL-BETA-CYBER" in pradeep["context"]["source_ids"]
    assert "Cyber Hawala Ring" in pradeep["context"]["reason"]
    assert "FIR-2026-495" in pradeep["context"]["readable_path"]
    assert "Pradeep Iyer" in pradeep["context"]["readable_path"]

    # Ramesh Hegde is connected via CDR-BRIDGE-02 to Karan Gupta
    assert "Ramesh Hegde" in nodes_by_label
    ramesh = nodes_by_label["Ramesh Hegde"]
    assert ramesh["context"]["presence_type"] == NodePresenceType.CDR_CONNECTION.value
    assert ramesh["context"]["distance_from_case"] == 2
    assert "CDR-BRIDGE-02" in ramesh["context"]["source_ids"]


def test_case_network_depth_3_extended(client: TestClient, sp_token: str) -> None:
    """Verifies depth=3 works safely and expands further."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/case-0016?depth=3", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["depth"] == 3
    assert data["total_nodes"] >= 34


def test_case_network_depth_validation_limits(client: TestClient, sp_token: str) -> None:
    """Verifies depths < 0 or > 3 are rejected with 422 Unprocessable Entity."""
    headers = {"Authorization": f"Bearer {sp_token}"}

    res_negative = client.get("/api/v1/network/cases/case-0016?depth=-1", headers=headers)
    assert res_negative.status_code == 422

    res_too_deep = client.get("/api/v1/network/cases/case-0016?depth=4", headers=headers)
    assert res_too_deep.status_code == 422

    res_invalid_type = client.get("/api/v1/network/cases/case-0016?depth=foo", headers=headers)
    assert res_invalid_type.status_code == 422


def test_case_network_rbac_unauthorized_investigator(client: TestClient, unassigned_io_token: str) -> None:
    """Verifies unassigned investigator cannot access case network."""
    headers = {"Authorization": f"Bearer {unassigned_io_token}"}
    res = client.get("/api/v1/network/cases/case-0016?depth=1", headers=headers)
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


def test_case_network_by_fir_number(client: TestClient, sp_token: str) -> None:
    """Verifies case_id parameter accepts either case node ID (case-0016) or FIR number (FIR-2026-495)."""
    headers = {"Authorization": f"Bearer {sp_token}"}
    res = client.get("/api/v1/network/cases/FIR-2026-495?depth=1", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_nodes"] == 5
    assert data["case_id"] == "FIR-2026-495"
