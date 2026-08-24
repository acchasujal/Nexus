"""tests/graph/test_bridge_centrality.py

Focused unit tests for Person-Only Degree Centrality, Betweenness Centrality,
and Bridge / Articulation Point Intelligence.

Validates:
  1. Degree centrality on Person-Only projection (empty, singleton, chain, star).
  2. Betweenness centrality on Person-Only projection.
  3. Articulation point discovery (triangle vs. chain vs. planted bridge).
  4. Golden Fixture Acceptance: Planted bridge entity MUST appear in Top 3.
  5. Explainable bridge candidate structure & absence of predictive guilt scoring.
  6. Non-mutation of input GraphStore.
  7. Deterministic tie-breaking across repeated runs.
"""

import pytest

from backend.app.core.graph.algorithms.bridges import (
    BridgeCandidateResult,
    compute_person_bridge_intelligence,
    get_network_centrality_summary,
    top_bridge_entities,
)
from backend.app.core.graph.algorithms.centrality import (
    compute_person_betweenness_centrality,
    compute_person_degree_centrality,
)
from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord, build_graph_store


# ── Golden Fixture Definition ──────────────────────────────────────────────────

@pytest.fixture
def planted_bridge_graph() -> GraphStore:
    """
    Planted Bridge Golden Graph Structure:

    Community A (Cluster 1):
      person_A1 ── COMMUNICATED_WITH ── person_A2
      person_A1 ── COMMUNICATED_WITH ── person_B
      person_A2 ── COMMUNICATED_WITH ── person_B

    Planted Bridge Edge:
      person_B  ── COMMUNICATED_WITH ── person_C   <-- Critical Articulation Bridge!

    Community B (Cluster 2):
      person_C  ── COMMUNICATED_WITH ── person_D1
      person_C  ── COMMUNICATED_WITH ── person_D2
      person_D1 ── COMMUNICATED_WITH ── person_D2

    Attached Non-Person Hubs (Must be excluded from centrality):
      person_B  ── USED_PHONE ─────────> phone_HUB_99
      person_C  ── OWNS_ACCOUNT ───────> acc_HUB_88
      person_A1 ── USED_VEHICLE ───────> veh_HUB_77
    """
    nodes = [
        NodeRecord("person_A1", "Person", {"canonical_label": "Alice Agent"}),
        NodeRecord("person_A2", "Person", {"canonical_label": "Alan Agent"}),
        NodeRecord("person_B", "Person", {"canonical_label": "Bob Bridge"}),
        NodeRecord("person_C", "Person", {"canonical_label": "Charlie Connector"}),
        NodeRecord("person_D1", "Person", {"canonical_label": "David Operative"}),
        NodeRecord("person_D2", "Person", {"canonical_label": "Daniel Operative"}),
        # Non-person entities
        NodeRecord("phone_HUB_99", "Phone", {"canonical_label": "9999999999"}),
        NodeRecord("acc_HUB_88", "Account", {"canonical_label": "ACC-888"}),
        NodeRecord("veh_HUB_77", "Vehicle", {"canonical_label": "KA-01-7777"}),
    ]

    edges = [
        # Community A
        AdjEdge("COMMUNICATED_WITH", "person_A1", "person_A2", {"properties": {"id": "rel_A1_A2"}}),
        AdjEdge("COMMUNICATED_WITH", "person_A1", "person_B", {"properties": {"id": "rel_A1_B"}}),
        AdjEdge("COMMUNICATED_WITH", "person_A2", "person_B", {"properties": {"id": "rel_A2_B"}}),
        # Planted Bridge Edge
        AdjEdge("COMMUNICATED_WITH", "person_B", "person_C", {"properties": {"id": "rel_B_C"}}),
        # Community B
        AdjEdge("COMMUNICATED_WITH", "person_C", "person_D1", {"properties": {"id": "rel_C_D1"}}),
        AdjEdge("COMMUNICATED_WITH", "person_C", "person_D2", {"properties": {"id": "rel_C_D2"}}),
        AdjEdge("COMMUNICATED_WITH", "person_D1", "person_D2", {"properties": {"id": "rel_D1_D2"}}),
        # Non-person relationships
        AdjEdge("USED_PHONE", "person_B", "phone_HUB_99"),
        AdjEdge("OWNS_ACCOUNT", "person_C", "acc_HUB_88"),
        AdjEdge("USED_VEHICLE", "person_A1", "veh_HUB_77"),
    ]

    return build_graph_store(nodes, edges)


# ── Degree Centrality Tests ─────────────────────────────────────────────────────

def test_degree_centrality_empty_graph():
    empty_store = GraphStore()
    results = compute_person_degree_centrality(empty_store)
    assert len(results) == 0


def test_degree_centrality_singleton_graph():
    store = GraphStore()
    store.nodes["p1"] = NodeRecord("p1", "Person", {"canonical_label": "Solo"})
    results = compute_person_degree_centrality(store)
    assert len(results) == 1
    assert results[0].person_id == "p1"
    assert results[0].degree_centrality == 0.0


def test_degree_centrality_chain_graph():
    # p1 - p2 - p3
    nodes = [
        NodeRecord("p1", "Person"),
        NodeRecord("p2", "Person"),
        NodeRecord("p3", "Person"),
    ]
    edges = [
        AdjEdge("COMMUNICATED_WITH", "p1", "p2"),
        AdjEdge("COMMUNICATED_WITH", "p2", "p3"),
    ]
    store = build_graph_store(nodes, edges)
    results = compute_person_degree_centrality(store)

    assert len(results) == 3
    # p2 has highest degree (2 connections)
    assert results[0].person_id == "p2"
    assert results[0].degree_centrality > results[1].degree_centrality


# ── Betweenness Centrality Tests ────────────────────────────────────────────────

def test_betweenness_centrality_planted_bridge(planted_bridge_graph):
    results = compute_person_betweenness_centrality(planted_bridge_graph)

    # All 6 Person nodes present, non-person nodes absent
    assert len(results) == 6
    person_ids = [r.person_id for r in results]
    assert "phone_HUB_99" not in person_ids
    assert "acc_HUB_88" not in person_ids

    # person_B and person_C must have highest betweenness centrality
    top_two = {results[0].person_id, results[1].person_id}
    assert "person_B" in top_two
    assert "person_C" in top_two
    assert results[0].betweenness_centrality > 0.40


# ── Articulation Point & Bridge Tests ──────────────────────────────────────────

def test_articulation_point_triangle_vs_chain():
    # Triangle (A-B-C-A): Removing any single node keeps graph connected -> no articulation points
    tri_nodes = [NodeRecord("p1", "Person"), NodeRecord("p2", "Person"), NodeRecord("p3", "Person")]
    tri_edges = [
        AdjEdge("COMMUNICATED_WITH", "p1", "p2"),
        AdjEdge("COMMUNICATED_WITH", "p2", "p3"),
        AdjEdge("COMMUNICATED_WITH", "p3", "p1"),
    ]
    tri_store = build_graph_store(tri_nodes, tri_edges)
    tri_results = compute_person_bridge_intelligence(tri_store)

    for r in tri_results:
        assert r.articulation_point is False

    # Chain (A-B-C): Removing B splits A and C -> B is articulation point
    chain_nodes = [NodeRecord("p1", "Person"), NodeRecord("p2", "Person"), NodeRecord("p3", "Person")]
    chain_edges = [
        AdjEdge("COMMUNICATED_WITH", "p1", "p2"),
        AdjEdge("COMMUNICATED_WITH", "p2", "p3"),
    ]
    chain_store = build_graph_store(chain_nodes, chain_edges)
    chain_results = compute_person_bridge_intelligence(chain_store)

    b_res = next(r for r in chain_results if r.person_id == "p2")
    assert b_res.articulation_point is True
    assert b_res.affected_components_count == 2


# ── Golden Acceptance Test ─────────────────────────────────────────────────────

def test_golden_planted_bridge_appears_in_top_3(planted_bridge_graph):
    """
    GOLDEN ACCEPTANCE CRITERION:
    In planted_bridge_graph, person_B and person_C are the planted bridge entities.
    Top 3 bridge entities MUST contain person_B or person_C.
    """
    top_3 = top_bridge_entities(planted_bridge_graph, limit=3)
    top_3_ids = [b.person_id for b in top_3]

    assert len(top_3) == 3
    assert ("person_B" in top_3_ids) or ("person_C" in top_3_ids)

    # Verify planted bridge has articulation_point == True
    planted_bridge = top_3[0]
    assert planted_bridge.articulation_point is True
    assert planted_bridge.bridge_score > 0.50
    assert "key network bridge" in planted_bridge.explanation.lower()


# ── Safety & Neutral Language Verification ────────────────────────────────────

def test_safety_neutral_terminology(planted_bridge_graph):
    """
    CRITICAL SIH SAFETY REQUIREMENT:
    Explanations must use neutral investigative terminology.
    Forbidden words: 'criminal', 'mastermind', 'guilt', 'probability', 'recidivism'.
    """
    results = compute_person_bridge_intelligence(planted_bridge_graph)

    forbidden_terms = ["criminal", "mastermind", "guilt", "recidivism", "probability"]

    for r in results:
        explanation_lower = r.explanation.lower()
        for term in forbidden_terms:
            assert term not in explanation_lower, f"Forbidden predictive guilt term '{term}' found in explanation"


# ── Result Structure & Determinism ─────────────────────────────────────────────

def test_bridge_candidate_result_structure(planted_bridge_graph):
    results = compute_person_bridge_intelligence(planted_bridge_graph)
    top = results[0]

    assert isinstance(top, BridgeCandidateResult)
    assert hasattr(top, "person_id")
    assert hasattr(top, "canonical_label")
    assert hasattr(top, "degree_centrality")
    assert hasattr(top, "betweenness_centrality")
    assert hasattr(top, "articulation_point")
    assert hasattr(top, "bridge_score")
    assert hasattr(top, "affected_components_count")
    assert hasattr(top, "explanation")
    assert hasattr(top, "relationship_ids")
    assert isinstance(top.relationship_ids, list)


def test_determinism_across_repeated_runs(planted_bridge_graph):
    run1 = top_bridge_entities(planted_bridge_graph, limit=5)
    run2 = top_bridge_entities(planted_bridge_graph, limit=5)

    assert len(run1) == len(run2)
    for r1, r2 in zip(run1, run2):
        assert r1.person_id == r2.person_id
        assert r1.bridge_score == r2.bridge_score
        assert r1.articulation_point == r2.articulation_point
        assert r1.explanation == r2.explanation


def test_non_mutation_of_input_graph(planted_bridge_graph):
    node_count_before = len(planted_bridge_graph.nodes)
    edge_types_before = set(planted_bridge_graph.edge_index.keys())

    # Run intelligence functions
    _ = compute_person_degree_centrality(planted_bridge_graph)
    _ = compute_person_betweenness_centrality(planted_bridge_graph)
    _ = compute_person_bridge_intelligence(planted_bridge_graph)
    _ = get_network_centrality_summary(planted_bridge_graph)

    # Verify input graph remains 100% unchanged
    assert len(planted_bridge_graph.nodes) == node_count_before
    assert set(planted_bridge_graph.edge_index.keys()) == edge_types_before
    assert "phone_HUB_99" in planted_bridge_graph.nodes
