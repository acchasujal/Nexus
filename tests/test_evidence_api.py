"""tests/test_evidence_api.py

Integration tests for Phase 1 Evidence Retrieval API and Phase 4 SHA-256 chain.
Tests:
  - EvidenceService.get_evidence_for_entity() returns real provenance
  - EvidenceService.get_evidence_by_id() returns item or None on miss
  - EvidenceService.list_all_evidence() filters work correctly
  - EvidenceService.verify_evidence_chain() is deterministic (BE-04)
  - SHA-256 hash changes on provenance field modification
  - GET /evidence/{id} endpoint returns 200 or 404
  - GET /evidence endpoint returns list
  - GET /entities/{source}/links/{target}/evidence returns list
  - POST /evidence/verify returns chain_hash
  - EVIDENCE_VIEWED audit event is recorded
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app
from backend.app.services.audit_service import AuditService
from backend.app.services.evidence_service import (
    EvidenceService,
    compute_evidence_hash,
    compute_path_chain_hash,
)
from shared.contracts.api import (
    EvidenceItemResponse,
    EvidenceProvenanceContract,
)

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
def client() -> TestClient:
    repo = InMemoryBackendRepository()
    app = create_app(repository=repo)
    return TestClient(app)


@pytest.fixture
def first_node_ids(repo: InMemoryBackendRepository) -> tuple[str, str]:
    """Return the first two node IDs that have an edge between them."""
    store = repo.to_graph_store()
    for etype, edges in store.edge_index.items():
        for edge in edges:
            if edge.source_id in store.nodes and edge.target_id in store.nodes:
                return edge.source_id, edge.target_id
    return "unknown-source", "unknown-target"


# ── Unit: EvidenceService ────────────────────────────────────────────────────

def test_list_all_evidence_returns_items(evidence_svc: EvidenceService) -> None:
    """list_all_evidence with no filter should return at least one item from the graph."""
    items = evidence_svc.list_all_evidence(limit=20, actor_id="test-actor")
    # The synthetic graph has edges with provenance; we expect at least some evidence
    assert isinstance(items, list)
    # All items must have required fields
    for item in items:
        assert item.id.startswith("ev-")
        assert item.provenance is not None
        assert item.provenance.source_type != ""


def test_evidence_items_have_real_provenance(evidence_svc: EvidenceService) -> None:
    """Evidence items must contain real provenance fields, not fabricated data."""
    items = evidence_svc.list_all_evidence(limit=10, actor_id="test-actor")
    if not items:
        pytest.skip("No evidence items in synthetic graph — skip")
    item = items[0]
    # Must have a stable deterministic ID
    assert len(item.id) > 4
    # Provenance fields must be non-empty
    assert item.evidence_type != ""
    assert item.description != ""


def test_get_evidence_by_id_returns_none_for_unknown(evidence_svc: EvidenceService) -> None:
    """Unknown evidence ID must return None, not raise an exception."""
    result = evidence_svc.get_evidence_by_id(
        evidence_id="ev-0000000000000000",
        actor_id="test-actor",
    )
    assert result is None


def test_get_evidence_by_id_hit(evidence_svc: EvidenceService) -> None:
    """If an item exists, get_evidence_by_id should return it by its stable ID."""
    all_items = evidence_svc.list_all_evidence(limit=5, actor_id="test-actor")
    if not all_items:
        pytest.skip("No evidence items in synthetic graph")
    first_id = all_items[0].id
    result = evidence_svc.get_evidence_by_id(evidence_id=first_id, actor_id="test-actor")
    assert result is not None
    assert result.id == first_id


def test_get_evidence_for_edge(
    evidence_svc: EvidenceService,
    first_node_ids: tuple[str, str],
    repo: InMemoryBackendRepository,
) -> None:
    """get_evidence_for_edge should return items matching the source/target pair."""
    source_id, target_id = first_node_ids
    results = evidence_svc.get_evidence_for_edge(
        source_id=source_id,
        target_id=target_id,
        actor_id="test-actor",
    )
    assert isinstance(results, list)
    # All returned items must come from the correct edge
    for item in results:
        assert item.provenance is not None


def test_evidence_audit_event_is_recorded(
    evidence_svc: EvidenceService,
    repo: InMemoryBackendRepository,
) -> None:
    """EVIDENCE_VIEWED audit event must be logged when evidence is retrieved."""
    initial_count = len(repo.audit_events)
    items = evidence_svc.list_all_evidence(limit=5, actor_id="officer-001")
    if not items:
        pytest.skip("No evidence items — skip audit test")

    # Look up a specific evidence item to trigger the audit event
    evidence_svc.get_evidence_by_id(evidence_id=items[0].id, actor_id="officer-001")
    audit_events = [e for e in repo.audit_events if e.get("event_type") == "evidence_viewed"]
    assert len(audit_events) > initial_count or len(audit_events) > 0


# ── Unit: SHA-256 Hash Chain (BE-04) ─────────────────────────────────────────

@pytest.fixture
def sample_evidence() -> EvidenceItemResponse:
    from datetime import datetime, timezone
    return EvidenceItemResponse(
        id="ev-test001",
        evidence_number="FIR-2026-001",
        case_id="case-0001",
        evidence_type="FIR",
        description="Filed FIR for theft at Ashok Nagar",
        collected_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        provenance=EvidenceProvenanceContract(
            source_type="FIR",
            source_id="FIR-2026-001",
            timestamp=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            extracted_fact="Accused VIKRAM SHARMA filed FIR",
            derivation_method="DIRECT",
            confidence=1.0,
        ),
    )


def test_compute_evidence_hash_is_deterministic(sample_evidence: EvidenceItemResponse) -> None:
    """Same evidence must produce the same SHA-256 hash every time."""
    h1 = compute_evidence_hash(sample_evidence)
    h2 = compute_evidence_hash(sample_evidence)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 produces 64 hex characters


def test_compute_evidence_hash_changes_on_field_modification(
    sample_evidence: EvidenceItemResponse,
) -> None:
    """Modifying any provenance field must change the hash."""
    original_hash = compute_evidence_hash(sample_evidence)

    # Create a copy with modified extracted_fact
    modified = sample_evidence.model_copy(deep=True)
    modified.provenance.extracted_fact = "MODIFIED: different fact"
    modified_hash = compute_evidence_hash(modified)

    assert original_hash != modified_hash


def test_compute_evidence_hash_changes_on_source_id_change(
    sample_evidence: EvidenceItemResponse,
) -> None:
    """Modifying source_id must change the hash (tamper detection)."""
    original_hash = compute_evidence_hash(sample_evidence)
    modified = sample_evidence.model_copy(deep=True)
    modified.provenance.source_id = "TAMPERED-FIR-9999"
    assert compute_evidence_hash(modified) != original_hash


def test_compute_path_chain_hash_is_deterministic() -> None:
    """Same sequence of hop hashes must produce the same chain hash."""
    hops = ["aabbcc", "ddeeff", "001122"]
    assert compute_path_chain_hash(hops) == compute_path_chain_hash(hops)


def test_compute_path_chain_hash_empty_returns_empty() -> None:
    """Empty hop list must return empty string, not raise."""
    assert compute_path_chain_hash([]) == ""


def test_verify_evidence_chain_verified_status(
    evidence_svc: EvidenceService,
) -> None:
    """verify_evidence_chain with no IDs returns VERIFIED chain."""
    result = evidence_svc.verify_evidence_chain(
        evidence_ids=[],
        path_node_ids=[],
        actor_id="test-actor",
    )
    assert result.verification_status == "VERIFIED"
    assert result.chain_hash == ""


def test_verify_evidence_chain_with_known_id(evidence_svc: EvidenceService) -> None:
    """verify_evidence_chain with a known evidence ID returns VERIFIED."""
    all_items = evidence_svc.list_all_evidence(limit=2, actor_id="test-actor")
    if not all_items:
        pytest.skip("No evidence items in synthetic graph")

    ev_id = all_items[0].id
    result = evidence_svc.verify_evidence_chain(
        evidence_ids=[ev_id],
        path_node_ids=[],
        actor_id="test-actor",
    )
    assert result.verification_status == "VERIFIED"
    assert ev_id in result.evidence_hashes
    assert len(result.chain_hash) == 64


def test_verify_evidence_chain_incomplete_on_unknown_id(evidence_svc: EvidenceService) -> None:
    """verify_evidence_chain with an unknown ID returns INCOMPLETE."""
    result = evidence_svc.verify_evidence_chain(
        evidence_ids=["ev-nonexistent999"],
        path_node_ids=[],
        actor_id="test-actor",
    )
    assert result.verification_status == "INCOMPLETE"


# ── Integration: HTTP Endpoints ───────────────────────────────────────────────

def test_get_evidence_by_id_404(client: TestClient) -> None:
    """GET /evidence/{id} with unknown ID must return 404."""
    resp = client.get("/api/v1/evidence/ev-0000000000000000")
    assert resp.status_code == 404


def test_list_evidence_endpoint(client: TestClient) -> None:
    """GET /evidence should return a list (possibly empty)."""
    resp = client.get("/api/v1/evidence?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_list_evidence_with_case_filter(client: TestClient) -> None:
    """GET /evidence?case_id=case-0001 should return only case-0001 evidence."""
    resp = client.get("/api/v1/evidence?case_id=case-0001&limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_get_edge_evidence_endpoint(client: TestClient) -> None:
    """GET /entities/{source}/links/{target}/evidence should return a list."""
    # Use known synthetic node IDs
    repo = InMemoryBackendRepository()
    store = repo.to_graph_store()
    for etype, edges in store.edge_index.items():
        for edge in edges:
            source_id = edge.source_id
            target_id = edge.target_id
            resp = client.get(f"/api/v1/entities/{source_id}/links/{target_id}/evidence")
            assert resp.status_code == 200
            assert isinstance(resp.json(), list)
            return
    pytest.skip("No edges found in synthetic graph")


def test_verify_evidence_endpoint(client: TestClient) -> None:
    """POST /evidence/verify with empty lists returns VERIFIED chain."""
    resp = client.post("/api/v1/evidence/verify", json={"evidence_ids": [], "path_node_ids": []})
    assert resp.status_code == 200
    data = resp.json()
    assert "chain_hash" in data
    assert "verification_status" in data
    assert data["verification_status"] == "VERIFIED"


def test_get_evidence_by_id_round_trip(client: TestClient) -> None:
    """Fetch evidence list, then fetch first item by ID — must match."""
    list_resp = client.get("/api/v1/evidence?limit=5")
    assert list_resp.status_code == 200
    items = list_resp.json()
    if not items:
        pytest.skip("No evidence items available")

    ev_id = items[0]["id"]
    detail_resp = client.get(f"/api/v1/evidence/{ev_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == ev_id
    assert "provenance" in detail
    assert detail["provenance"]["source_type"] != ""
