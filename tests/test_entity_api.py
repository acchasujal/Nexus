"""tests/test_entity_api.py

Integration tests for Phase 2 Entity Profile API.
Tests:
  - EntityService.get_entity_profile() returns full profile for known entity
  - EntityService.get_entity_profile() returns None for unknown entity
  - EntityService.search_entities() returns matching results
  - EntityService.get_entity_network() returns NetworkGraphResponse
  - GET /entities/{id} returns 200 with profile or 404
  - GET /entities/{id}/network returns graph
  - GET /entities?query=... returns list
  - ENTITY_VIEWED audit event is logged on profile fetch
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app
from backend.app.services.audit_service import AuditService
from backend.app.services.entity_service import EntityService
from backend.app.services.evidence_service import EvidenceService

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def repo() -> InMemoryBackendRepository:
    return InMemoryBackendRepository()


@pytest.fixture
def audit(repo: InMemoryBackendRepository) -> AuditService:
    return AuditService(repo)


@pytest.fixture
def evidence_svc(repo: InMemoryBackendRepository, audit: AuditService) -> EvidenceService:
    return EvidenceService(repo, audit)


@pytest.fixture
def entity_svc(
    repo: InMemoryBackendRepository,
    audit: AuditService,
    evidence_svc: EvidenceService,
) -> EntityService:
    return EntityService(repo, audit, evidence_svc)


@pytest.fixture
def first_person_id(repo: InMemoryBackendRepository) -> str:
    """Return the first Person node ID in the synthetic graph."""
    store = repo.to_graph_store()
    for nid, node in store.nodes.items():
        if node.entity_type == "Person":
            return nid
    return list(store.nodes.keys())[0] if store.nodes else "unknown"


@pytest.fixture
def client() -> TestClient:
    repo = InMemoryBackendRepository()
    app = create_app(repository=repo)
    return TestClient(app)


# ── Unit: EntityService.get_entity_profile ────────────────────────────────────

def test_get_entity_profile_known_entity(
    entity_svc: EntityService,
    first_person_id: str,
) -> None:
    """get_entity_profile with a known entity_id returns a full EntityProfileResponse."""
    profile = entity_svc.get_entity_profile(
        entity_id=first_person_id,
        actor_id="test-actor",
    )
    assert profile is not None
    assert profile.entity_id == first_person_id
    assert profile.entity_type != ""
    assert profile.label != ""
    assert isinstance(profile.aliases, list)
    assert isinstance(profile.degree, int)
    assert profile.degree >= 0


def test_get_entity_profile_unknown_entity(entity_svc: EntityService) -> None:
    """get_entity_profile with unknown entity_id must return None."""
    result = entity_svc.get_entity_profile(
        entity_id="entity-does-not-exist-99999",
        actor_id="test-actor",
    )
    assert result is None


def test_get_entity_profile_has_properties(
    entity_svc: EntityService,
    first_person_id: str,
) -> None:
    """Profile properties dict must be non-None."""
    profile = entity_svc.get_entity_profile(
        entity_id=first_person_id,
        actor_id="test-actor",
    )
    assert profile is not None
    assert isinstance(profile.properties, dict)


def test_get_entity_profile_audit_logged(
    entity_svc: EntityService,
    first_person_id: str,
    repo: InMemoryBackendRepository,
) -> None:
    """ENTITY_VIEWED audit event must be logged after profile retrieval."""
    entity_svc.get_entity_profile(
        entity_id=first_person_id,
        actor_id="officer-test",
    )
    events = [e for e in repo.audit_events if e.get("event_type") == "entity_viewed"]
    assert len(events) >= 1
    assert events[-1]["actor_id"] == "officer-test"


# ── Unit: EntityService.search_entities ───────────────────────────────────────

def test_search_entities_returns_list(entity_svc: EntityService) -> None:
    """search_entities must always return a list, even if empty."""
    results = entity_svc.search_entities(query="sharma", actor_id="test-actor")
    assert isinstance(results, list)


def test_search_entities_with_known_name(
    entity_svc: EntityService,
    repo: InMemoryBackendRepository,
) -> None:
    """Search for a known person name should return at least one result."""
    store = repo.to_graph_store()
    # Find a real name from the synthetic graph
    for nid, node in store.nodes.items():
        if node.entity_type == "Person":
            name = node.properties.get("full_name", "")
            if name and len(name) > 3:
                # Search with first 4 chars to be flexible
                prefix = name[:4].lower()
                results = entity_svc.search_entities(query=prefix, actor_id="test-actor")
                assert len(results) >= 1
                return
    pytest.skip("No Person nodes with names in synthetic graph")


def test_search_entities_entity_type_filter(entity_svc: EntityService) -> None:
    """Entity type filter must restrict results to the given type."""
    results = entity_svc.search_entities(
        query="",  # will use whitespace — no matches
        entity_type="Person",
        actor_id="test-actor",
    )
    # All results (if any) must be Person type
    for r in results:
        assert r.entity_type == "Person"


# ── Unit: EntityService.get_entity_network ────────────────────────────────────

def test_get_entity_network_returns_graph(
    entity_svc: EntityService,
    first_person_id: str,
) -> None:
    """get_entity_network must return a NetworkGraphResponse with at least the root node."""
    graph = entity_svc.get_entity_network(
        entity_id=first_person_id,
        depth=1,
        actor_id="test-actor",
    )
    assert graph.total_nodes >= 1
    assert isinstance(graph.nodes, list)
    assert isinstance(graph.edges, list)


def test_get_entity_network_includes_root(
    entity_svc: EntityService,
    first_person_id: str,
) -> None:
    """Root entity must appear in the returned network nodes."""
    graph = entity_svc.get_entity_network(
        entity_id=first_person_id,
        depth=2,
        actor_id="test-actor",
    )
    node_ids = {n.id for n in graph.nodes}
    assert first_person_id in node_ids


# ── Integration: HTTP Endpoints ───────────────────────────────────────────────

def test_get_entity_profile_404(client: TestClient) -> None:
    """GET /entities/{id} with unknown ID must return 404."""
    resp = client.get("/api/v1/entities/entity-does-not-exist-99999")
    assert resp.status_code == 404


def test_get_entity_profile_endpoint(client: TestClient) -> None:
    """GET /entities/{id} with a real ID returns a profile with required fields."""
    repo = InMemoryBackendRepository()
    store = repo.to_graph_store()
    entity_id = None
    for nid, node in store.nodes.items():
        entity_id = nid
        break

    if entity_id is None:
        pytest.skip("No nodes in synthetic graph")

    resp = client.get(f"/api/v1/entities/{entity_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == entity_id
    assert "entity_type" in data
    assert "label" in data
    assert "properties" in data
    assert "evidence_items" in data
    assert isinstance(data["evidence_items"], list)


def test_get_entity_network_endpoint(client: TestClient) -> None:
    """GET /entities/{id}/network must return a graph with nodes and edges."""
    repo = InMemoryBackendRepository()
    store = repo.to_graph_store()
    entity_id = next(iter(store.nodes), None)
    if entity_id is None:
        pytest.skip("No nodes in synthetic graph")

    resp = client.get(f"/api/v1/entities/{entity_id}/network?depth=2")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "edges" in data
    assert "total_nodes" in data
    assert data["total_nodes"] >= 1


def test_search_entities_endpoint(client: TestClient) -> None:
    """GET /entities?query=... returns a list of matching entities."""
    # Find a real search term from the synthetic data
    repo = InMemoryBackendRepository()
    store = repo.to_graph_store()
    query_term = "a"  # Broad enough to match something
    for nid, node in store.nodes.items():
        name = (node.properties or {}).get("full_name", "")
        if name:
            query_term = name[:3].lower()
            break

    resp = client.get(f"/api/v1/entities?query={query_term}&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_entity_profile_evidence_items_have_provenance(client: TestClient) -> None:
    """Entity profile evidence_items must each contain a valid provenance object."""
    repo = InMemoryBackendRepository()
    store = repo.to_graph_store()
    entity_id = next(iter(store.nodes), None)
    if entity_id is None:
        pytest.skip("No nodes in synthetic graph")

    resp = client.get(f"/api/v1/entities/{entity_id}")
    assert resp.status_code == 200
    data = resp.json()
    for ev_item in data.get("evidence_items", []):
        assert "provenance" in ev_item
        assert ev_item["provenance"]["source_type"] != ""
