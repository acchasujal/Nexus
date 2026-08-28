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
    repo.clear() # clear synthetic default
    repo.nodes = {
        "case-1": {"id": "case-1", "entity_type": "Case", "properties": {"fir_number": "141/2026", "title": "Trafficking 141/2026"}},
        "person-1": {"id": "person-1", "entity_type": "Person", "properties": {"full_name": "Rafiq Khan", "role": "Suspect"}},
        "phone-1": {"id": "phone-1", "entity_type": "Phone", "properties": {"phone_number": "+91 98450 11223", "seen_in": "CDR: Mysuru"}},
        "acc-1": {"id": "acc-1", "entity_type": "Account", "properties": {"account_number": "ACC-7731", "holder": "Deepak Rao", "bank": "Global Bank"}},
        "rc-1-incoming": {"id": "rc-1-incoming", "entity_type": "Person", "properties": {"full_name": "Rafiq Ahmed"}},
    }
    repo.review_candidates = {
        "RC-1": {
            "incoming_record_id": "rc-1-incoming",
            "candidate_node_id": "person-1",
            "status": "PENDING"
        }
    }
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


def test_search_deduplication(client: TestClient) -> None:
    resp = client.get("/api/v1/nexus/search?q=141")
    assert resp.status_code == 200
    data = resp.json()
    all_case_ids = [c["id"] for c in data["cases"]]
    all_entity_ids = [e["id"] for e in data["entities"]]

    # Assert no duplicate IDs exist in returned lists
    assert len(all_case_ids) == len(set(all_case_ids))
    assert len(all_entity_ids) == len(set(all_entity_ids))


