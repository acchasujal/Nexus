"""tests/test_global_search.py

Unit and integration tests for NEXUS Global Universal Search (/api/v1/nexus/search).
Tests:
  - Text search for Case, Person, Station, Offence
  - Phone normalization (+91 98450 11223, 9845011223, +919845011223)
  - Account normalization (ACC7731, acc-7731)
  - Preservation of original labels in output
  - Subtext generation for entities
  - Resolution state (Before vs After) node search behavior
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


def test_empty_search_returns_empty(client: TestClient) -> None:
    resp = client.get("/api/v1/nexus/search?q=")
    assert resp.status_code == 200
    data = resp.json()
    assert data["query"] == ""
    assert data["cases"] == []
    assert data["entities"] == []


def test_case_text_search(client: TestClient) -> None:
    resp = client.get("/api/v1/nexus/search?q=141/2026")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["cases"]) > 0
    first_case = data["cases"][0]
    assert first_case["fir_number"] == "141/2026"
    assert "Trafficking" in first_case["title"] or "141/2026" in first_case["title"]


def test_person_text_search(client: TestClient) -> None:
    resp = client.get("/api/v1/nexus/search?q=Rafiq")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entities"]) > 0
    labels = [e["label"] for e in data["entities"]]
    assert any("Rafiq" in lbl for lbl in labels)


def test_phone_number_formatting_normalization(client: TestClient) -> None:
    # Stored label: "+91 98450 11223 (CDR: Mysuru)"
    queries = [
        "9845011223",
        "+919845011223",
        "+91 98450 11223",
        "98450 11223",
    ]
    for q in queries:
        resp = client.get(f"/api/v1/nexus/search?q={q}")
        assert resp.status_code == 200
        data = resp.json()
        matching_phones = [e for e in data["entities"] if e["entity_type"] == "Phone"]
        assert len(matching_phones) > 0, f"Query '{q}' failed to match stored phone"
        # Ensure original label is preserved
        assert "+91 98450 11223" in matching_phones[0]["label"]


def test_account_normalization(client: TestClient) -> None:
    # Stored label: "ACC-7731 (Axis)"
    queries = ["ACC-7731", "acc7731", "ACC 7731"]
    for q in queries:
        resp = client.get(f"/api/v1/nexus/search?q={q}")
        assert resp.status_code == 200
        data = resp.json()
        accounts = [e for e in data["entities"] if e["entity_type"] == "Account"]
        assert len(accounts) > 0, f"Query '{q}' failed to match stored account"
        assert "ACC-7731" in accounts[0]["label"]


def test_subtext_generation(client: TestClient) -> None:
    resp = client.get("/api/v1/nexus/search?q=Rafiq")
    assert resp.status_code == 200
    data = resp.json()
    entities = data["entities"]
    assert len(entities) > 0
    for e in entities:
        assert "subtext" in e
        assert e["subtext"] is not None
        assert len(e["subtext"]) > 0


def test_before_after_resolution_search(client: TestClient) -> None:
    # Initial before resolution
    resp_before = client.get("/api/v1/nexus/search?q=Rafiq")
    assert resp_before.status_code == 200
    entities_before = resp_before.json()["entities"]
    labels_before = [e["label"] for e in entities_before]
    assert any("Rafiq Khan" in lbl for lbl in labels_before)

    # Post resolution decision
    req = {
        "decision": "CONFIRM",
        "note": "Verified identical mobile number +91 98450 11223",
    }
    client.post("/api/v1/nexus/resolution/RC-1/decision", json=req)

    # After resolution search
    resp_after = client.get("/api/v1/nexus/search?q=Rafiq")
    assert resp_after.status_code == 200
    entities_after = resp_after.json()["entities"]
    labels_after = [e["label"] for e in entities_after]
    assert any("Rafiq Khan / Rafiq Ahmed" in lbl for lbl in labels_after)


def test_repository_backed_entities_search(client: TestClient) -> None:
    # 1. Search phone 9820298660 -> MUST return person-0120 / Sanjay Patel
    r1 = client.get("/api/v1/nexus/search?q=9820298660")
    assert r1.status_code == 200
    entities_1 = r1.json()["entities"]
    assert any(e["id"] == "person-0120" and "Sanjay Patel" in e["label"] for e in entities_1)

    # 2. Search name "Sanjay Patel" -> MUST return person-0120
    r2 = client.get("/api/v1/nexus/search?q=Sanjay%20Patel")
    assert r2.status_code == 200
    entities_2 = r2.json()["entities"]
    assert any(e["id"] == "person-0120" for e in entities_2)

    # 3. Search FIR "FIR-2026-984" -> MUST return case-0049
    r3 = client.get("/api/v1/nexus/search?q=FIR-2026-984")
    assert r3.status_code == 200
    cases_3 = r3.json()["cases"]
    assert any(c["id"] == "case-0049" for c in cases_3)

    # 4. Verify Entity Fusion demo searches still work alongside repo search
    r_demo = client.get("/api/v1/nexus/search?q=CASE-141")
    assert r_demo.status_code == 200
    assert len(r_demo.json()["cases"]) > 0


def test_search_deduplication(client: TestClient) -> None:
    resp = client.get("/api/v1/nexus/search?q=141")
    assert resp.status_code == 200
    data = resp.json()
    all_case_ids = [c["id"] for c in data["cases"]]
    all_entity_ids = [e["id"] for e in data["entities"]]

    # Assert no duplicate IDs exist in returned lists
    assert len(all_case_ids) == len(set(all_case_ids))
    assert len(all_entity_ids) == len(set(all_entity_ids))


def test_cross_case_resolution_candidates_endpoint(client: TestClient) -> None:
    resp = client.get("/api/v1/nexus/resolution/candidates")
    assert resp.status_code == 200
    candidates = resp.json()
    assert len(candidates) >= 3

    # Candidate 1: Cross-case Rafiq (CASE-141 vs CASE-207)
    c1 = candidates[0]
    assert c1["id"] == "RC-1"
    assert c1["left"]["case_ids"] == ["CASE-141"]
    assert c1["right"]["case_ids"] == ["CASE-207"]
    assert c1["left"]["case_ids"] != c1["right"]["case_ids"]

    # Candidate 2: Cross-case Vikram/Bikram (CASE-305 vs CASE-412)
    c2 = candidates[1]
    assert c2["id"] == "RC-2"
    assert c2["left"]["case_ids"] == ["CASE-305"]
    assert c2["right"]["case_ids"] == ["CASE-412"]

    # Test decision for RC-2
    dec_resp = client.post(
        "/api/v1/nexus/resolution/RC-2/decision",
        json={"decision": "CONFIRM", "decided_by": "IO Test", "note": "Aadhaar verified"},
    )
    assert dec_resp.status_code == 200
    assert dec_resp.json()["status"] == "CONFIRMED"


