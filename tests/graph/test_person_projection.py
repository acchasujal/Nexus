"""tests/graph/test_person_projection.py

Unit tests for Person-Only Graph Projection (Schema V2).
Validates:
  1. Projected graph contains ONLY Person nodes.
  2. All original Person IDs, canonical labels, and aliases are preserved.
  3. Valid Person -> Person relationships (COMMUNICATED_WITH, CONNECTED_TO, etc.) are retained.
  4. Non-person nodes (Phone, Vehicle, Account, Case, Event, SourceRecord, etc.) are excluded.
  5. Unsupported indirect relationships do NOT invent false direct edges.
  6. Edge metadata, confidence, derivation_class, and properties are preserved.
  7. Original GraphStore input is NOT mutated (non-destructive derived graph view).
  8. Empty graph, singleton graph, no-Person graph edge cases.
  9. Self-loop filtering behavior.
 10. Deterministic, reproducible output across repeated executions.
 11. Multiple relationships between the same two people are preserved.
"""

import pytest

from backend.app.core.graph.algorithms.projection import (
    project_person_graph,
    project_person_nodes_and_edges,
)
from backend.app.core.graph.algorithms.utils import (
    AdjEdge,
    GraphStore,
    NodeRecord,
    build_graph_store,
)
from backend.app.core.graph.edges import (
    Relationship,
)
from backend.app.core.graph.entities import (
    Person,
    Phone,
    Vehicle,
)
from backend.app.core.graph.enums import (
    GraphRelationshipType,
)


@pytest.fixture
def sample_investigation_graph() -> GraphStore:
    """
    Sample heterogeneous investigation graph containing:
      - 3 Person nodes (person_001, person_002, person_003)
      - 1 Phone node (phone_001)
      - 1 Vehicle node (veh_001)
      - 1 Account node (acc_001)
      - 1 Case node (case_101)
      - Direct Person -> Person edge (person_001 -> person_002 COMMUNICATED_WITH)
      - Person -> Non-Person edges (OWNS_ACCOUNT, USED_PHONE, USED_VEHICLE, ACCUSED_IN)
    """
    nodes = [
        NodeRecord(
            node_id="person_001",
            entity_type="Person",
            properties={"canonical_label": "Rahul Kumar", "aliases": ["R. Kumar"], "role": "Accused"},
        ),
        NodeRecord(
            node_id="person_002",
            entity_type="Person",
            properties={"canonical_label": "Vikram Sharma", "aliases": ["Vicky"], "role": "Suspect"},
        ),
        NodeRecord(
            node_id="person_003",
            entity_type="Person",
            properties={"canonical_label": "Suresh Patel", "aliases": [], "role": "Witness"},
        ),
        NodeRecord(
            node_id="phone_001",
            entity_type="Phone",
            properties={"canonical_label": "9876543210", "imei": "864201041234567"},
        ),
        NodeRecord(
            node_id="veh_001",
            entity_type="Vehicle",
            properties={"canonical_label": "KA-01-MJ-9999", "make": "Mahindra"},
        ),
        NodeRecord(
            node_id="acc_001",
            entity_type="Account",
            properties={"canonical_label": "ACC-100200300", "bank_name": "HDFC"},
        ),
        NodeRecord(
            node_id="case_101",
            entity_type="Case",
            properties={"canonical_label": "FIR 101/2026", "district": "Bengaluru"},
        ),
    ]

    edges = [
        # Direct Person -> Person relationship
        AdjEdge(
            edge_type="COMMUNICATED_WITH",
            source_id="person_001",
            target_id="person_002",
            properties={"call_count": 15, "confidence": 1.0, "derivation_class": "FACT"},
        ),
        # Direct Person -> Person relationship (CO_ACCUSED_WITH)
        AdjEdge(
            edge_type="CO_ACCUSED_WITH",
            source_id="person_001",
            target_id="person_002",
            properties={"confidence": 0.9, "derivation_class": "DERIVED"},
        ),
        # Person -> Non-Person relationships
        AdjEdge(edge_type="USED_PHONE", source_id="person_001", target_id="phone_001"),
        AdjEdge(edge_type="USED_PHONE", source_id="person_002", target_id="phone_001"),
        AdjEdge(edge_type="USED_VEHICLE", source_id="person_001", target_id="veh_001"),
        AdjEdge(edge_type="USED_VEHICLE", source_id="person_003", target_id="veh_001"),
        AdjEdge(edge_type="OWNS_ACCOUNT", source_id="person_001", target_id="acc_001"),
        AdjEdge(edge_type="ACCUSED_IN", source_id="person_001", target_id="case_101"),
    ]

    return build_graph_store(nodes, edges)


def test_projection_contains_only_person_nodes(sample_investigation_graph):
    projected = project_person_graph(sample_investigation_graph)
    assert len(projected.nodes) == 3
    for nid, node in projected.nodes.items():
        assert node.entity_type in ("Person", "PERSON")
        assert nid in ("person_001", "person_002", "person_003")

    # Verify non-person entities are completely absent from nodes dict
    assert "phone_001" not in projected.nodes
    assert "veh_001" not in projected.nodes
    assert "acc_001" not in projected.nodes
    assert "case_101" not in projected.nodes


def test_original_person_ids_labels_aliases_preserved(sample_investigation_graph):
    projected = project_person_graph(sample_investigation_graph)
    p1 = projected.nodes["person_001"]
    p2 = projected.nodes["person_002"]

    assert p1.node_id == "person_001"
    assert p1.properties["canonical_label"] == "Rahul Kumar"
    assert p1.properties["aliases"] == ["R. Kumar"]

    assert p2.node_id == "person_002"
    assert p2.properties["canonical_label"] == "Vikram Sharma"
    assert p2.properties["aliases"] == ["Vicky"]


def test_valid_person_to_person_relationships_retained(sample_investigation_graph):
    projected = project_person_graph(sample_investigation_graph)
    out_p1 = projected.adj.get("person_001", [])

    # person_001 has 2 outgoing Person->Person edges (COMMUNICATED_WITH, CO_ACCUSED_WITH)
    assert len(out_p1) == 2
    edge_types = {e.edge_type for e in out_p1}
    assert "COMMUNICATED_WITH" in edge_types
    assert "CO_ACCUSED_WITH" in edge_types

    for e in out_p1:
        assert e.source_id == "person_001"
        assert e.target_id == "person_002"


def test_non_person_nodes_and_relationships_excluded(sample_investigation_graph):
    projected = project_person_graph(sample_investigation_graph)

    # Verify edge index contains only Person->Person edges
    for etype, edges in projected.edge_index.items():
        for e in edges:
            assert e.source_id in projected.nodes
            assert e.target_id in projected.nodes
            assert projected.nodes[e.source_id].entity_type in ("Person", "PERSON")
            assert projected.nodes[e.target_id].entity_type in ("Person", "PERSON")

    # Excluded relationship types MUST NOT be present in edge_index
    assert "USED_PHONE" not in projected.edge_index
    assert "USED_VEHICLE" not in projected.edge_index
    assert "OWNS_ACCOUNT" not in projected.edge_index
    assert "ACCUSED_IN" not in projected.edge_index


def test_no_false_direct_relationships_invented(sample_investigation_graph):
    """
    In sample_investigation_graph:
      person_001 and person_003 both use veh_001, but there is NO direct edge
      between person_001 and person_003.
    Verify that projection DOES NOT invent a false edge between person_001 and person_003.
    """
    projected = project_person_graph(sample_investigation_graph)

    # person_003 has no direct Person->Person edges
    out_p3 = projected.adj.get("person_003", [])
    in_p3 = projected.radj.get("person_003", [])
    assert len(out_p3) == 0
    assert len(in_p3) == 0


def test_edge_metadata_and_provenance_preserved(sample_investigation_graph):
    projected = project_person_graph(sample_investigation_graph)
    comm_edges = projected.edge_index.get("COMMUNICATED_WITH", [])
    assert len(comm_edges) == 1
    edge = comm_edges[0]

    assert edge.properties["call_count"] == 15
    assert edge.properties["confidence"] == 1.0
    assert edge.properties["derivation_class"] == "FACT"


def test_original_graph_is_not_mutated(sample_investigation_graph):
    node_count_before = len(sample_investigation_graph.nodes)
    edge_types_before = set(sample_investigation_graph.edge_index.keys())

    # Perform projection
    projected = project_person_graph(sample_investigation_graph)

    # Verify original graph state is unmodified
    assert len(sample_investigation_graph.nodes) == node_count_before
    assert set(sample_investigation_graph.edge_index.keys()) == edge_types_before
    assert "phone_001" in sample_investigation_graph.nodes
    assert "USED_PHONE" in sample_investigation_graph.edge_index
    assert len(projected.nodes) < len(sample_investigation_graph.nodes)


def test_empty_graph_projection():
    empty_store = GraphStore()
    projected = project_person_graph(empty_store)
    assert len(projected.nodes) == 0
    assert len(projected.adj) == 0
    assert len(projected.edge_index) == 0


def test_singleton_person_projection():
    store = GraphStore()
    store.nodes["p1"] = NodeRecord(node_id="p1", entity_type="Person", properties={"full_name": "Solo Person"})
    store.adj["p1"] = []
    store.radj["p1"] = []

    projected = project_person_graph(store)
    assert len(projected.nodes) == 1
    assert "p1" in projected.nodes
    assert len(projected.adj["p1"]) == 0


def test_no_person_graph_projection():
    store = GraphStore()
    store.nodes["phone1"] = NodeRecord(node_id="phone1", entity_type="Phone")
    store.nodes["veh1"] = NodeRecord(node_id="veh1", entity_type="Vehicle")

    projected = project_person_graph(store)
    assert len(projected.nodes) == 0
    assert len(projected.edge_index) == 0


def test_self_loop_filtering():
    store = GraphStore()
    store.nodes["p1"] = NodeRecord(node_id="p1", entity_type="Person")
    store.nodes["p2"] = NodeRecord(node_id="p2", entity_type="Person")

    # Self-loop edge
    edge_self = AdjEdge(edge_type="COMMUNICATED_WITH", source_id="p1", target_id="p1")
    # Normal edge
    edge_normal = AdjEdge(edge_type="COMMUNICATED_WITH", source_id="p1", target_id="p2")

    store.adj["p1"] = [edge_self, edge_normal]
    store.radj["p1"] = [edge_self]
    store.radj["p2"] = [edge_normal]
    store.edge_index["COMMUNICATED_WITH"] = [edge_self, edge_normal]

    # Default (include_self_loops=False)
    projected_no_loops = project_person_graph(store, include_self_loops=False)
    assert len(projected_no_loops.edge_index["COMMUNICATED_WITH"]) == 1
    assert projected_no_loops.edge_index["COMMUNICATED_WITH"][0].target_id == "p2"

    # With self-loops
    projected_with_loops = project_person_graph(store, include_self_loops=True)
    assert len(projected_with_loops.edge_index["COMMUNICATED_WITH"]) == 2


def test_repeated_execution_is_deterministic(sample_investigation_graph):
    proj1 = project_person_graph(sample_investigation_graph)
    proj2 = project_person_graph(sample_investigation_graph)

    assert list(proj1.nodes.keys()) == list(proj2.nodes.keys())
    assert list(proj1.edge_index.keys()) == list(proj2.edge_index.keys())

    for etype in proj1.edge_index:
        edges1 = [(e.edge_type, e.source_id, e.target_id) for e in proj1.edge_index[etype]]
        edges2 = [(e.edge_type, e.source_id, e.target_id) for e in proj2.edge_index[etype]]
        assert edges1 == edges2


def test_project_person_nodes_and_edges_raw_models():
    p1 = Person(id="person_001", full_name="Rahul Kumar")
    p2 = Person(id="person_002", full_name="Vikram Sharma")
    phone = Phone(id="phone_001", phone_number="9876543210")
    veh = Vehicle(id="veh_001", registration_number="KA-01-MJ-9999")

    nodes = [p1, p2, phone, veh]

    rel_comm = Relationship(
        id="rel_01",
        source_id="person_001",
        target_id="person_002",
        type=GraphRelationshipType.COMMUNICATED_WITH,
    )
    rel_phone = Relationship(
        id="rel_02",
        source_id="person_001",
        target_id="phone_001",
        type=GraphRelationshipType.USED_PHONE,
    )

    edges = [rel_comm, rel_phone]

    projected_nodes, projected_edges = project_person_nodes_and_edges(nodes, edges)

    assert len(projected_nodes) == 2
    assert {n.id for n in projected_nodes} == {"person_001", "person_002"}

    assert len(projected_edges) == 1
    assert projected_edges[0].source_id == "person_001"
    assert projected_edges[0].target_id == "person_002"
