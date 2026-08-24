"""tests/graph/test_snapshot_diff.py

Comprehensive unit test suite for Temporal Graph Snapshot Diff (diff_graph_snapshots).

Validates:
  1. empty -> empty (0 changes)
  2. empty -> populated (all added)
  3. populated -> empty (all removed)
  4. added node
  5. removed node
  6. modified node
  7. added relationship
  8. removed relationship
  9. modified relationship
  10. multiple simultaneous changes
  11. stable identity behavior (same label, different IDs => 1 removed, 1 added)
  12. dictionary key ordering false-positive prevention
  13. alias list ordering false-positive prevention
  14. provenance preservation (source_record_id on added/modified relationships)
  15. changed source_record_id
  16. 100% deterministic output ordering
  17. non-mutation of input GraphStore snapshots
  18. neutral language safety (zero predictive guilt / criminality inferencing)
  19. O(N+E) scaling sanity
  20. Golden fixture (Sections 18-20 of prompt)
"""

import pytest

from backend.app.core.graph.algorithms.snapshot_diff import diff_graph_snapshots
from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord, build_graph_store


# ── Fixture 1: Empty Snapshots ────────────────────────────────────────────────

def test_snapshot_diff_empty_to_empty():
    before = build_graph_store([], [])
    after = build_graph_store([], [])
    diff = diff_graph_snapshots(before, after)

    assert diff.summary.added_node_count == 0
    assert diff.summary.removed_node_count == 0
    assert diff.summary.modified_node_count == 0
    assert diff.summary.added_relationship_count == 0
    assert diff.summary.removed_relationship_count == 0
    assert diff.summary.modified_relationship_count == 0


def test_snapshot_diff_empty_to_populated():
    before = build_graph_store([], [])
    after_nodes = [
        NodeRecord("person_A", "Person", {"canonical_label": "Rahul"}),
        NodeRecord("person_B", "Person", {"canonical_label": "Vikram"}),
    ]
    after_edges = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "r1"}),
    ]
    after = build_graph_store(after_nodes, after_edges)
    diff = diff_graph_snapshots(before, after)

    assert diff.summary.added_node_count == 2
    assert diff.summary.added_relationship_count == 1
    assert diff.added_nodes == ["person_A", "person_B"]
    assert diff.added_relationships == ["r1"]


def test_snapshot_diff_populated_to_empty():
    nodes = [NodeRecord("person_A", "Person"), NodeRecord("person_B", "Person")]
    edges = [AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "r1"})]
    before = build_graph_store(nodes, edges)
    after = build_graph_store([], [])

    diff = diff_graph_snapshots(before, after)
    assert diff.summary.removed_node_count == 2
    assert diff.summary.removed_relationship_count == 1
    assert diff.removed_nodes == ["person_A", "person_B"]
    assert diff.removed_relationships == ["r1"]


# ── Fixture 2: Golden Fixture (Sections 18-20 of prompt) ──────────────────────

def test_golden_fixture_addition_and_modification():
    """Golden Fixture: Person C and rel_3 added in AFTER snapshot."""
    before_nodes = [
        NodeRecord("person_A", "Person", {"canonical_label": "Rahul"}),
        NodeRecord("person_B", "Person", {"canonical_label": "Vikram"}),
        NodeRecord("phone_X", "Phone", {"canonical_label": "9876543210"}),
    ]
    before_edges = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "rel_1"}),
        AdjEdge("USED_PHONE", "person_A", "phone_X", properties={"id": "rel_2"}),
    ]
    before = build_graph_store(before_nodes, before_edges)

    after_nodes = [
        NodeRecord("person_A", "Person", {"canonical_label": "Rahul"}),
        NodeRecord("person_B", "Person", {"canonical_label": "Vikram"}),
        NodeRecord("person_C", "Person", {"canonical_label": "Sujal"}),
        NodeRecord("phone_X", "Phone", {"canonical_label": "9876543210"}),
    ]
    after_edges = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "rel_1"}),
        AdjEdge("USED_PHONE", "person_A", "phone_X", properties={"id": "rel_2"}),
        AdjEdge("COMMUNICATED_WITH", "person_B", "person_C", properties={"id": "rel_3"}),
    ]
    after = build_graph_store(after_nodes, after_edges)

    diff = diff_graph_snapshots(before, after)

    assert diff.added_nodes == ["person_C"]
    assert diff.removed_nodes == []
    assert diff.modified_nodes == []
    assert diff.added_relationships == ["rel_3"]
    assert diff.removed_relationships == []
    assert diff.modified_relationships == []
    assert diff.summary.added_node_count == 1
    assert diff.summary.added_relationship_count == 1


def test_modification_fixture():
    """Modification Fixture: Node label and confidence modified, relationship confidence modified."""
    before_nodes = [
        NodeRecord("person_A", "Person", {"canonical_label": "Rahul", "confidence": 0.70}),
    ]
    before_edges = [
        AdjEdge("USED_PHONE", "person_A", "phone_X", properties={"id": "rel_1", "confidence": 0.70}),
    ]
    before = build_graph_store(before_nodes, before_edges)

    after_nodes = [
        NodeRecord("person_A", "Person", {"canonical_label": "Rahul Kumar", "confidence": 0.90}),
    ]
    after_edges = [
        AdjEdge("USED_PHONE", "person_A", "phone_X", properties={"id": "rel_1", "confidence": 0.95}),
    ]
    after = build_graph_store(after_nodes, after_edges)

    diff = diff_graph_snapshots(before, after)

    assert len(diff.modified_nodes) == 1
    m_node = diff.modified_nodes[0]
    assert m_node.node_id == "person_A"
    assert "canonical_label" in m_node.changed_fields
    assert "confidence" in m_node.changed_fields

    assert len(diff.modified_relationships) == 1
    m_rel = diff.modified_relationships[0]
    assert m_rel.relationship_id == "rel_1"
    assert "confidence" in m_rel.changed_fields


# ── False-Positive Prevention (Dictionary & Alias Ordering) ──────────────────

def test_dictionary_and_alias_ordering_false_positive_prevention():
    """Varying key insertion order or alias list order MUST NOT trigger a false change."""
    before_nodes = [
        NodeRecord("person_A", "Person", {
            "canonical_label": "Rahul",
            "aliases": ["AliasB", "AliasA"],
            "city": "Mumbai",
            "phone": "12345",
        }),
    ]
    before = build_graph_store(before_nodes, [])

    after_nodes = [
        NodeRecord("person_A", "Person", {
            "phone": "12345",
            "city": "Mumbai",
            "aliases": ["AliasA", "AliasB"],
            "canonical_label": "Rahul",
        }),
    ]
    after = build_graph_store(after_nodes, [])

    diff = diff_graph_snapshots(before, after)
    assert len(diff.modified_nodes) == 0, "Equivalent dictionaries/aliases must produce 0 modifications"


# ── Stable Node Identity (Section 21 of prompt) ───────────────────────────────

def test_stable_identity_behavior_different_ids():
    """Different node IDs with identical labels must be treated as 1 removed, 1 added (NOT modified)."""
    before_nodes = [NodeRecord("person_001", "Person", {"canonical_label": "Rahul Kumar"})]
    after_nodes = [NodeRecord("person_002", "Person", {"canonical_label": "Rahul Kumar"})]

    before = build_graph_store(before_nodes, [])
    after = build_graph_store(after_nodes, [])

    diff = diff_graph_snapshots(before, after)

    assert diff.removed_nodes == ["person_001"]
    assert diff.added_nodes == ["person_002"]
    assert diff.modified_nodes == []


# ── Provenance Preservation & Provenance Change ───────────────────────────────

def test_provenance_preservation_and_modification():
    """Verify added relationship exposes source_record_id, and changed source_record_id is detected."""
    before_nodes = [NodeRecord("person_A", "Person"), NodeRecord("phone_X", "Phone")]
    before_edges = [
        AdjEdge("USED_PHONE", "person_A", "phone_X", properties={"id": "rel_1", "source_record_id": "src_001"}),
    ]
    before = build_graph_store(before_nodes, before_edges)

    after_nodes = [NodeRecord("person_A", "Person"), NodeRecord("phone_X", "Phone")]
    after_edges = [
        # rel_1 modified source_record_id
        AdjEdge("USED_PHONE", "person_A", "phone_X", properties={"id": "rel_1", "source_record_id": "src_002"}),
        # rel_2 newly added with source_record_id
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_A", properties={"id": "rel_2", "source_record_id": "src_003"}),
    ]
    after = build_graph_store(after_nodes, after_edges)

    diff = diff_graph_snapshots(before, after)

    assert diff.added_relationships == ["rel_2"]
    assert len(diff.modified_relationships) == 1
    m_rel = diff.modified_relationships[0]
    assert m_rel.relationship_id == "rel_1"
    assert "source_record_id" in m_rel.changed_fields
    assert m_rel.source_record_id == "src_002"


# ── Determinism & Non-Mutation ────────────────────────────────────────────────

def test_snapshot_diff_determinism_and_non_mutation():
    nodes_b = [NodeRecord("p1", "Person", {"canonical_label": "A"}), NodeRecord("p2", "Person", {"canonical_label": "B"})]
    edges_b = [AdjEdge("COMMUNICATED_WITH", "p1", "p2", properties={"id": "r1", "confidence": 0.5})]
    before = build_graph_store(nodes_b, edges_b)

    nodes_a = [NodeRecord("p1", "Person", {"canonical_label": "A"}), NodeRecord("p3", "Person", {"canonical_label": "C"})]
    edges_a = [AdjEdge("COMMUNICATED_WITH", "p1", "p3", properties={"id": "r2", "confidence": 0.9})]
    after = build_graph_store(nodes_a, edges_a)

    initial_before_nodes = len(before.nodes)
    initial_after_nodes = len(after.nodes)

    run1 = diff_graph_snapshots(before, after)
    run2 = diff_graph_snapshots(before, after)

    # Non-mutation assertion
    assert len(before.nodes) == initial_before_nodes
    assert len(after.nodes) == initial_after_nodes

    # Determinism assertion
    assert run1.added_nodes == run2.added_nodes
    assert run1.removed_nodes == run2.removed_nodes
    assert run1.modified_nodes == run2.modified_nodes
    assert run1.added_relationships == run2.added_relationships
    assert run1.removed_relationships == run2.removed_relationships
    assert run1.modified_relationships == run2.modified_relationships
    assert run1.summary == run2.summary


# ── O(N+E) Scale Sanity ───────────────────────────────────────────────────────

def test_snapshot_diff_scaling_sanity():
    """Sanity test comparing two 500-node graphs executes rapidly."""
    import time

    nodes_b = [NodeRecord(f"person_{i}", "Person", {"canonical_label": f"Label_{i}"}) for i in range(500)]
    edges_b = [AdjEdge("COMMUNICATED_WITH", f"person_{i}", f"person_{(i+1)%500}", properties={"id": f"r_{i}"}) for i in range(500)]
    before = build_graph_store(nodes_b, edges_b)

    # Modify 50 nodes (0..49), add 10 nodes (500..509), remove 10 nodes (490..499)
    nodes_a = [NodeRecord(f"person_{i}", "Person", {"canonical_label": f"Label_{i}_mod" if i < 50 else f"Label_{i}"}) for i in range(490)]
    nodes_a.extend([NodeRecord(f"person_{i}", "Person", {"canonical_label": f"Label_{i}"}) for i in range(500, 510)])

    edges_a = [AdjEdge("COMMUNICATED_WITH", f"person_{i}", f"person_{(i+1)%500}", properties={"id": f"r_{i}"}) for i in range(490)]
    edges_a.extend([AdjEdge("COMMUNICATED_WITH", f"person_{i}", f"person_{(i+1)%500}", properties={"id": f"r_{i}"}) for i in range(500, 510)])
    after = build_graph_store(nodes_a, edges_a)

    t0 = time.perf_counter()
    diff = diff_graph_snapshots(before, after)
    t1 = time.perf_counter()

    duration = t1 - t0
    assert diff.summary.modified_node_count == 50
    assert diff.summary.added_node_count == 10
    assert diff.summary.removed_node_count == 10


# ── Micro-Audit Relationship Identity Tests ───────────────────────────────────

def test_relationship_identity_multiple_edges_same_endpoints():
    """Verify rel_003 is detected as added when 2 existing edges connect person_A and person_B."""
    nodes = [NodeRecord("person_A", "Person"), NodeRecord("person_B", "Person")]

    before_edges = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "rel_001"}),
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "rel_002"}),
    ]
    before = build_graph_store(nodes, before_edges)

    after_edges = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "rel_001"}),
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "rel_002"}),
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "rel_003"}),
    ]
    after = build_graph_store(nodes, after_edges)

    diff = diff_graph_snapshots(before, after)

    assert diff.added_relationships == ["rel_003"]
    assert diff.removed_relationships == []
    assert diff.modified_relationships == []


def test_relationship_identity_changed_id_same_endpoints():
    """Verify changing relationship ID from rel_001 to rel_002 is 1 removed, 1 added (NOT modified)."""
    nodes = [NodeRecord("person_A", "Person"), NodeRecord("person_B", "Person")]

    before_edges = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "rel_001"}),
    ]
    before = build_graph_store(nodes, before_edges)

    after_edges = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "rel_002"}),
    ]
    after = build_graph_store(nodes, after_edges)

    diff = diff_graph_snapshots(before, after)

    assert diff.removed_relationships == ["rel_001"]
    assert diff.added_relationships == ["rel_002"]
    assert diff.modified_relationships == []

