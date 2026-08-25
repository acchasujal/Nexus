"""tests/graph/test_louvain_communities.py

Focused unit tests for Person-Only Louvain Community Detection (Schema V2).

Validates:
  1. Empty graph (0 communities).
  2. Singleton graph (1 community, 1 member).
  3. Two disconnected people (2 communities, 1 member each).
  4. Fully connected dense cluster (1 natural community).
  5. Two clearly separated clusters with bridge edge (Golden Fixture).
  6. Membership contains ONLY Person IDs (non-person entities excluded).
  7. Deterministic, stable community IDs (comm_<hash>).
  8. Deterministic member and community ordering.
  9. Non-mutation of input GraphStore.
 10. Reproducible partition across repeated runs with fixed seed.
 11. Safety verification: zero predictive guilt scoring / neutral terminology.
"""

import pytest

from backend.app.core.graph.algorithms.communities import (
    NetworkCommunitiesSummary,
    detect_louvain_communities,
    generate_stable_community_id,
)
from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord, build_graph_store


@pytest.fixture
def two_cluster_golden_fixture() -> GraphStore:
    """
    Golden Fixture: Two dense 4-person cliques connected by a single bridge edge,
    plus attached non-person hub entities.

    Cluster A: {person_A1, person_A2, person_A3, person_A4}
    Cluster B: {person_B1, person_B2, person_B3, person_B4}
    Bridge Edge: person_A4 -- COMMUNICATED_WITH -- person_B1

    Non-Person Hubs:
      person_A1 -- USED_PHONE --> phone_101
      person_B1 -- OWNS_ACCOUNT --> account_202
      person_A4 -- ACCUSED_IN --> case_303
    """
    nodes = [
        # Cluster A
        NodeRecord("person_A1", "Person", {"canonical_label": "Alice"}),
        NodeRecord("person_A2", "Person", {"canonical_label": "Arthur"}),
        NodeRecord("person_A3", "Person", {"canonical_label": "Andrew"}),
        NodeRecord("person_A4", "Person", {"canonical_label": "Amelia"}),
        # Cluster B
        NodeRecord("person_B1", "Person", {"canonical_label": "Bob"}),
        NodeRecord("person_B2", "Person", {"canonical_label": "Brian"}),
        NodeRecord("person_B3", "Person", {"canonical_label": "Bella"}),
        NodeRecord("person_B4", "Person", {"canonical_label": "Blake"}),
        # Non-person hubs
        NodeRecord("phone_101", "Phone", {"canonical_label": "9876543210"}),
        NodeRecord("account_202", "Account", {"canonical_label": "ACC-202"}),
        NodeRecord("case_303", "Case", {"canonical_label": "FIR 303"}),
    ]

    edges = []
    # Cluster A dense edges
    cluster_a = ["person_A1", "person_A2", "person_A3", "person_A4"]
    for i in range(len(cluster_a)):
        for j in range(i + 1, len(cluster_a)):
            edges.append(AdjEdge("COMMUNICATED_WITH", cluster_a[i], cluster_a[j]))

    # Cluster B dense edges
    cluster_b = ["person_B1", "person_B2", "person_B3", "person_B4"]
    for i in range(len(cluster_b)):
        for j in range(i + 1, len(cluster_b)):
            edges.append(AdjEdge("COMMUNICATED_WITH", cluster_b[i], cluster_b[j]))

    # Bridge edge between Cluster A and Cluster B
    edges.append(AdjEdge("COMMUNICATED_WITH", "person_A4", "person_B1"))

    # Non-person edges
    edges.append(AdjEdge("USED_PHONE", "person_A1", "phone_101"))
    edges.append(AdjEdge("OWNS_ACCOUNT", "person_B1", "account_202"))
    edges.append(AdjEdge("ACCUSED_IN", "person_A4", "case_303"))

    return build_graph_store(nodes, edges)


def test_empty_graph_louvain():
    empty_store = GraphStore()
    summary = detect_louvain_communities(empty_store)
    assert summary.community_count == 0
    assert summary.modularity == 0.0
    assert len(summary.communities) == 0


def test_singleton_graph_louvain():
    store = GraphStore()
    store.nodes["p1"] = NodeRecord("p1", "Person", {"canonical_label": "Solo Person"})
    summary = detect_louvain_communities(store)

    assert summary.community_count == 1
    assert len(summary.communities) == 1
    assert summary.communities[0].member_ids == ["p1"]
    assert summary.communities[0].size == 1


def test_two_disconnected_persons_louvain():
    store = GraphStore()
    store.nodes["p1"] = NodeRecord("p1", "Person")
    store.nodes["p2"] = NodeRecord("p2", "Person")

    summary = detect_louvain_communities(store)
    assert summary.community_count == 2
    assert len(summary.communities) == 2
    assert summary.communities[0].size == 1
    assert summary.communities[1].size == 1
    assert {summary.communities[0].member_ids[0], summary.communities[1].member_ids[0]} == {"p1", "p2"}


def test_dense_single_community_louvain():
    nodes = [NodeRecord(f"p{i}", "Person") for i in range(1, 5)]
    edges = [AdjEdge("COMMUNICATED_WITH", f"p{i}", f"p{j}") for i in range(1, 5) for j in range(i + 1, 5)]
    store = build_graph_store(nodes, edges)

    summary = detect_louvain_communities(store)
    assert summary.community_count == 1
    assert len(summary.communities[0].member_ids) == 4


def test_golden_fixture_louvain(two_cluster_golden_fixture):
    """
    GOLDEN FIXTURE ACCEPTANCE TEST:
    Verifies that Louvain community detection correctly partitions the two 4-person cliques
    and completely excludes non-person nodes.
    """
    summary = detect_louvain_communities(two_cluster_golden_fixture)

    assert isinstance(summary, NetworkCommunitiesSummary)
    assert summary.community_count == 2
    assert summary.modularity > 0.30

    comm_a = summary.communities[0]
    comm_b = summary.communities[1]

    assert comm_a.size == 4
    assert comm_b.size == 4

    members_a = set(comm_a.member_ids)
    members_b = set(comm_b.member_ids)

    # Verify members match expected clusters
    expected_a = {"person_A1", "person_A2", "person_A3", "person_A4"}
    expected_b = {"person_B1", "person_B2", "person_B3", "person_B4"}

    assert (members_a == expected_a and members_b == expected_b) or (members_a == expected_b and members_b == expected_a)

    # Verify non-person entities are 100% excluded
    all_members = members_a.union(members_b)
    assert "phone_101" not in all_members
    assert "account_202" not in all_members
    assert "case_303" not in all_members


def test_only_person_ids_in_communities(two_cluster_golden_fixture):
    summary = detect_louvain_communities(two_cluster_golden_fixture)

    for comm in summary.communities:
        assert comm.dominant_entity_type == "Person"
        for mid in comm.member_ids:
            assert mid.startswith("person_")


def test_stable_community_id_generation():
    members1 = ["person_B", "person_A", "person_C"]
    members2 = ["person_A", "person_C", "person_B"]

    # Order of inputs should not affect generated ID
    cid1 = generate_stable_community_id(members1)
    cid2 = generate_stable_community_id(members2)

    assert cid1 == cid2
    assert cid1.startswith("comm_")
    assert len(cid1) == 17  # "comm_" + 12 hex chars


def test_deterministic_member_and_community_ordering(two_cluster_golden_fixture):
    summary = detect_louvain_communities(two_cluster_golden_fixture)

    # Member IDs within each community MUST be sorted ascending
    for comm in summary.communities:
        assert comm.member_ids == sorted(comm.member_ids)

    # Communities MUST be sorted by size descending, then smallest member ID ascending
    if len(summary.communities) > 1:
        c0, c1 = summary.communities[0], summary.communities[1]
        assert c0.size >= c1.size
        if c0.size == c1.size:
            assert c0.member_ids[0] < c1.member_ids[0]


def test_reproducible_partition_across_repeated_runs(two_cluster_golden_fixture):
    run1 = detect_louvain_communities(two_cluster_golden_fixture, seed=42)
    run2 = detect_louvain_communities(two_cluster_golden_fixture, seed=42)

    assert run1.community_count == run2.community_count
    assert run1.modularity == run2.modularity

    for c1, c2 in zip(run1.communities, run2.communities):
        assert c1.community_id == c2.community_id
        assert c1.member_ids == c2.member_ids
        assert c1.size == c2.size


def test_non_mutation_of_input_graph(two_cluster_golden_fixture):
    node_count_before = len(two_cluster_golden_fixture.nodes)
    edge_types_before = set(two_cluster_golden_fixture.edge_index.keys())

    _ = detect_louvain_communities(two_cluster_golden_fixture)

    assert len(two_cluster_golden_fixture.nodes) == node_count_before
    assert set(two_cluster_golden_fixture.edge_index.keys()) == edge_types_before
    assert "phone_101" in two_cluster_golden_fixture.nodes


def test_neutral_explanations(two_cluster_golden_fixture):
    summary = detect_louvain_communities(two_cluster_golden_fixture)
    forbidden_terms = ["criminal", "gang", "mastermind", "guilt", "mafia"]

    for comm in summary.communities:
        reason_lower = comm.reason.lower()
        for term in forbidden_terms:
            assert term not in reason_lower
