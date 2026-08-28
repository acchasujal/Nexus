"""Tests for repository integration of IngestionBundle."""

import pytest
from datetime import datetime, timezone

from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.core.graph.entities import SourceRecord, GraphEntityBase
from backend.app.core.graph.enums import GraphEntityType, GraphRelationshipType, DerivationClass
from backend.app.core.graph.edges import GraphEdge, EvidenceProvenance
from backend.app.db.ingestion.contracts import IngestionBundle, SourceType


def _make_dummy_bundle() -> IngestionBundle:
    sr = SourceRecord(
        id="sr-1",
        batch_id="batch-1",
        source_type=SourceType.FIR.value,
        locator="dummy.csv:1",
        raw_excerpt="foo",
        hash="bar",
        occurred_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    n1 = GraphEntityBase(
        id="node-1",
        entity_type=GraphEntityType.PERSON,
        properties={"full_name": "Test Person 1"},
    )
    n2 = GraphEntityBase(
        id="node-2",
        entity_type=GraphEntityType.CASE,
        properties={"fir_number": "FIR-100"},
    )
    
    e1 = GraphEdge(
        id="edge-1",
        source_id="node-1",
        target_id="node-2",
        edge_type=GraphRelationshipType.ACCUSED_IN,
        start_time=None,
        end_time=None,
        source_record_id="sr-1",
        derivation_class=DerivationClass.FACT,
        confidence=1.0,
        provenance=EvidenceProvenance(source_type="FIR", file_name="dummy.csv", record_id="1"),
        properties={"role": "ACCUSED"},
    )

    return IngestionBundle(
        batch_id="batch-1",
        source_type=SourceType.FIR,
        file_name="dummy.csv",
        source_records=[sr],
        nodes=[n1, n2],
        relationships=[e1],
    )


def test_repository_applies_bundle_without_destroying_static() -> None:
    repo = InMemoryBackendRepository()
    initial_nodes = len(repo.nodes)
    initial_edges = len(repo.edges)
    
    bundle = _make_dummy_bundle()
    created_n, reused_n, created_e, reused_e = repo.apply_bundle(bundle)
    
    assert created_n == 2
    assert reused_n == 0
    assert created_e == 1
    assert reused_e == 0
    
    assert len(repo.nodes) == initial_nodes + 2
    assert len(repo.edges) == initial_edges + 1
    
    # Check that it appears in graph store
    store = repo.to_graph_store()
    assert "node-1" in store.nodes
    assert "node-2" in store.nodes
    assert len(store.adj["node-1"]) > 0


def test_re_ingestion_is_idempotent() -> None:
    repo = InMemoryBackendRepository()
    bundle = _make_dummy_bundle()
    
    # First application
    repo.apply_bundle(bundle)
    
    # Second application
    created_n, reused_n, created_e, reused_e = repo.apply_bundle(bundle)
    assert created_n == 0
    assert reused_n == 2
    assert created_e == 0
    assert reused_e == 1


def test_validation_failure_prevents_partial_writes() -> None:
    repo = InMemoryBackendRepository()
    initial_nodes = len(repo.nodes)
    initial_edges = len(repo.edges)
    
    bundle = _make_dummy_bundle()
    # Break referential integrity
    bundle.relationships[0].source_id = "non-existent-node"
    
    with pytest.raises(ValueError, match="orphan source node"):
        repo.apply_bundle(bundle)
        
    assert len(repo.nodes) == initial_nodes
    assert len(repo.edges) == initial_edges


def test_source_records_are_stored() -> None:
    repo = InMemoryBackendRepository()
    bundle = _make_dummy_bundle()
    repo.apply_bundle(bundle)
    
    assert "sr-1" in repo.source_records
    assert repo.source_records["sr-1"]["hash"] == "bar"
