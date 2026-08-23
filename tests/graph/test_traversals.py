"""
tests/graph/test_traversals.py

Unit tests for backend.app.core.graph.algorithms.traversals.

Coverage
--------
* get_case / get_person — happy path, missing node, wrong entity type
* get_related_cases — bidirectional LINKED_TO, empty, isolated
* get_co_accused — single accused, multiple accused, empty case
* get_cases_for_person — multi-role person, missing person
* get_officer_cases — INVESTIGATED_BY (reverse), zero-case officer
* get_dependency_chain — sorted by nothing (just present), empty
* get_clock_instances — sorted by days_remaining ascending
* get_neighbors — one hop, no edges, unknown node
* get_subgraph — depth=1, depth=2, depth=0 (just root), unknown node
* get_evidence_for_case — happy path, empty
* get_sections_for_case — happy path
* get_cases_for_persons — batch
* Duplicate relationship handling
"""

from __future__ import annotations


from backend.app.core.graph.algorithms.traversals import (
    SubgraphResult,
    get_case,
    get_cases_for_person,
    get_cases_for_persons,
    get_clock_instances,
    get_co_accused,
    get_dependency_chain,
    get_evidence_for_case,
    get_neighbors,
    get_officer_cases,
    get_person,
    get_related_cases,
    get_sections_for_case,
    get_subgraph,
)

from helpers import (
    _FakeEdge,
    make_case,
    make_clock,
    make_dependency,
    make_officer,
    make_person,
    make_section,
    make_store,
)




# ── get_case ──────────────────────────────────────────────────────────────────


def test_get_case_happy(two_case_store):
    store, nodes = two_case_store
    case_a = nodes["case_a"]
    result = get_case(store, case_a.id)
    assert result is not None
    assert result.entity_type == "Case"
    assert result.node_id == case_a.id


def test_get_case_by_fir_number():
    case = make_case()
    case.properties["fir_number"] = "FIR/BEL/0064"
    store = make_store([case], [])
    result = get_case(store, "FIR/BEL/0064")
    assert result is not None
    assert result.node_id == case.id
    assert result.properties["fir_number"] == "FIR/BEL/0064"


def test_get_case_by_case_number():
    case = make_case()
    case.properties["case_number"] = "CC-0064"
    store = make_store([case], [])
    result = get_case(store, "CC-0064")
    assert result is not None
    assert result.node_id == case.id
    assert result.properties["case_number"] == "CC-0064"


def test_get_case_missing(empty_store):
    assert get_case(empty_store, "does-not-exist") is None


def test_get_case_wrong_type(two_case_store):
    store, nodes = two_case_store
    # Passing a Person id to get_case should return None
    assert get_case(store, nodes["person"].id) is None


# ── get_person ────────────────────────────────────────────────────────────────


def test_get_person_happy(two_case_store):
    store, nodes = two_case_store
    result = get_person(store, nodes["person"].id)
    assert result is not None
    assert result.entity_type == "Person"


def test_get_person_missing(empty_store):
    assert get_person(empty_store, "ghost") is None


def test_get_person_wrong_type(two_case_store):
    store, nodes = two_case_store
    assert get_person(store, nodes["case_a"].id) is None


# ── get_related_cases ─────────────────────────────────────────────────────────


def test_get_related_cases_happy(two_case_store):
    store, nodes = two_case_store
    related = get_related_cases(store, nodes["case_a"].id)
    assert any(r.node_id == nodes["case_b"].id for r in related)


def test_get_related_cases_bidirectional(two_case_store):
    """LINKED_TO is stored A→B; querying B should also return A."""
    store, nodes = two_case_store
    from_b = get_related_cases(store, nodes["case_b"].id)
    assert any(r.node_id == nodes["case_a"].id for r in from_b)


def test_get_related_cases_empty(single_case_store):
    """A case with no LINKED_TO edges returns empty list."""
    # Find the single case node
    case_node = next(iter(single_case_store.nodes.values()))
    assert get_related_cases(single_case_store, case_node.node_id) == []


def test_get_related_cases_missing(empty_store):
    assert get_related_cases(empty_store, "ghost") == []


# ── get_co_accused ────────────────────────────────────────────────────────────


def test_get_co_accused_happy(two_case_store):
    store, nodes = two_case_store
    accused = get_co_accused(store, nodes["case_a"].id)
    assert len(accused) == 1
    assert accused[0].entity_type == "Person"


def test_get_co_accused_multiple():
    case = make_case()
    p1 = make_person()
    p2 = make_person()
    store = make_store(
        [case, p1, p2],
        [_FakeEdge("ACCUSED_IN", p1.id, case.id),
         _FakeEdge("ACCUSED_IN", p2.id, case.id)],
    )
    accused = get_co_accused(store, case.id)
    assert len(accused) == 2


def test_get_co_accused_empty():
    case = make_case()
    store = make_store([case], [])
    assert get_co_accused(store, case.id) == []


def test_get_co_accused_missing(empty_store):
    assert get_co_accused(empty_store, "ghost") == []


# ── get_cases_for_person ──────────────────────────────────────────────────────


def test_get_cases_for_person_accused(two_case_store):
    store, nodes = two_case_store
    cases = get_cases_for_person(store, nodes["person"].id)
    case_ids = {c.node_id for c in cases}
    assert nodes["case_a"].id in case_ids
    assert nodes["case_b"].id in case_ids


def test_get_cases_for_person_multi_role():
    """A person who is accused in one case and victim in another."""
    case_a = make_case()
    case_b = make_case()
    person = make_person()
    store = make_store(
        [case_a, case_b, person],
        [_FakeEdge("ACCUSED_IN", person.id, case_a.id),
         _FakeEdge("VICTIM_IN", person.id, case_b.id)],
    )
    cases = get_cases_for_person(store, person.id)
    ids = {c.node_id for c in cases}
    assert case_a.id in ids and case_b.id in ids


def test_get_cases_for_person_missing(empty_store):
    assert get_cases_for_person(empty_store, "ghost") == []


def test_get_cases_for_person_isolated():
    """Person node with no outgoing edges."""
    person = make_person()
    store = make_store([person], [])
    assert get_cases_for_person(store, person.id) == []


# ── get_officer_cases ─────────────────────────────────────────────────────────


def test_get_officer_cases_happy(two_case_store):
    store, nodes = two_case_store
    cases = get_officer_cases(store, nodes["officer"].id)
    ids = {c.node_id for c in cases}
    assert nodes["case_a"].id in ids
    assert nodes["case_b"].id in ids


def test_get_officer_cases_zero_cases():
    officer = make_officer()
    store = make_store([officer], [])
    assert get_officer_cases(store, officer.id) == []


def test_get_officer_cases_missing(empty_store):
    assert get_officer_cases(empty_store, "ghost") == []


# ── get_dependency_chain ──────────────────────────────────────────────────────


def test_get_dependency_chain_happy(two_case_store):
    store, nodes = two_case_store
    deps = get_dependency_chain(store, nodes["case_a"].id)
    assert len(deps) == 1
    assert deps[0].entity_type == "Dependency"


def test_get_dependency_chain_multiple():
    case = make_case()
    d1 = make_dependency("pending")
    d2 = make_dependency("resolved")
    store = make_store(
        [case, d1, d2],
        [_FakeEdge("CASE_HAS_DEPENDENCY", case.id, d1.id),
         _FakeEdge("CASE_HAS_DEPENDENCY", case.id, d2.id)],
    )
    assert len(get_dependency_chain(store, case.id)) == 2


def test_get_dependency_chain_empty(single_case_store):
    case_node = next(iter(single_case_store.nodes.values()))
    assert get_dependency_chain(single_case_store, case_node.node_id) == []


def test_get_dependency_chain_missing(empty_store):
    assert get_dependency_chain(empty_store, "ghost") == []


# ── get_clock_instances ───────────────────────────────────────────────────────


def test_get_clock_instances_sorted_by_urgency(two_case_store):
    """Clocks should be sorted by days_remaining ascending (most urgent first)."""
    store, nodes = two_case_store
    # case_a has clock_a (3 days), case_b has clock_b (20 days)
    clocks_a = get_clock_instances(store, nodes["case_a"].id)
    assert len(clocks_a) == 1
    assert clocks_a[0].properties["days_remaining"] == 3


def test_get_clock_instances_multiple():
    case = make_case()
    c1 = make_clock(status="amber", days_remaining=10)
    c2 = make_clock(status="red", days_remaining=2)
    c3 = make_clock(status="green", days_remaining=25)
    store = make_store(
        [case, c1, c2, c3],
        [_FakeEdge("CASE_HAS_CLOCK", case.id, c1.id),
         _FakeEdge("CASE_HAS_CLOCK", case.id, c2.id),
         _FakeEdge("CASE_HAS_CLOCK", case.id, c3.id)],
    )
    clocks = get_clock_instances(store, case.id)
    days = [c.properties["days_remaining"] for c in clocks]
    assert days == sorted(days), "Clocks must be sorted by days_remaining ascending"


def test_get_clock_instances_empty(single_case_store):
    case_node = next(iter(single_case_store.nodes.values()))
    assert get_clock_instances(single_case_store, case_node.node_id) == []


def test_get_clock_instances_missing(empty_store):
    assert get_clock_instances(empty_store, "ghost") == []


# ── get_neighbors ─────────────────────────────────────────────────────────────


def test_get_neighbors_happy(two_case_store):
    store, nodes = two_case_store
    # case_a → dep, clock_a, evidence, officer, case_b (LINKED_TO)
    nbrs = get_neighbors(store, nodes["case_a"].id)
    assert len(nbrs) > 0


def test_get_neighbors_isolated(single_case_store):
    case_node = next(iter(single_case_store.nodes.values()))
    assert get_neighbors(single_case_store, case_node.node_id) == []


def test_get_neighbors_missing(empty_store):
    assert get_neighbors(empty_store, "ghost") == []


# ── get_subgraph ──────────────────────────────────────────────────────────────


def test_get_subgraph_depth1(two_case_store):
    store, nodes = two_case_store
    sg = get_subgraph(store, nodes["case_a"].id, depth=1)
    assert isinstance(sg, SubgraphResult)
    assert len(sg.nodes) >= 1  # at least root
    node_ids = {n.node_id for n in sg.nodes}
    assert nodes["case_a"].id in node_ids


def test_get_subgraph_depth2_reaches_deeper(two_case_store):
    store, nodes = two_case_store
    sg_d1 = get_subgraph(store, nodes["case_a"].id, depth=1)
    sg_d2 = get_subgraph(store, nodes["case_a"].id, depth=2)
    assert len(sg_d2.nodes) >= len(sg_d1.nodes)


def test_get_subgraph_edges_internal_only(two_case_store):
    store, nodes = two_case_store
    sg = get_subgraph(store, nodes["case_a"].id, depth=2)
    node_ids = {n.node_id for n in sg.nodes}
    for edge in sg.edges:
        assert edge.source_id in node_ids
        assert edge.target_id in node_ids


def test_get_subgraph_missing(empty_store):
    sg = get_subgraph(empty_store, "ghost", depth=2)
    assert sg.nodes == []
    assert sg.edges == []


def test_get_subgraph_depth_cap():
    """depth > 8 should be capped at 8."""
    case = make_case()
    store = make_store([case], [])
    sg = get_subgraph(store, case.id, depth=100)
    assert sg.depth == 8


# ── get_evidence_for_case ─────────────────────────────────────────────────────


def test_get_evidence_for_case_happy(two_case_store):
    store, nodes = two_case_store
    ev = get_evidence_for_case(store, nodes["case_a"].id)
    assert len(ev) == 1
    assert ev[0].entity_type == "Evidence"


def test_get_evidence_for_case_empty(single_case_store):
    case_node = next(iter(single_case_store.nodes.values()))
    assert get_evidence_for_case(single_case_store, case_node.node_id) == []


# ── get_sections_for_case ─────────────────────────────────────────────────────


def test_get_sections_for_case_happy():
    case = make_case()
    s1 = make_section("BNS_302")
    s2 = make_section("BNS_379")
    store = make_store(
        [case, s1, s2],
        [_FakeEdge("CHARGED_UNDER", case.id, s1.id),
         _FakeEdge("CHARGED_UNDER", case.id, s2.id)],
    )
    sections = get_sections_for_case(store, case.id)
    assert len(sections) == 2


def test_get_sections_for_case_empty(single_case_store):
    case_node = next(iter(single_case_store.nodes.values()))
    assert get_sections_for_case(single_case_store, case_node.node_id) == []


# ── get_cases_for_persons (batch) ─────────────────────────────────────────────


def test_get_cases_for_persons_batch(two_case_store):
    store, nodes = two_case_store
    result = get_cases_for_persons(store, [nodes["person"].id, "ghost"])
    assert len(result[nodes["person"].id]) == 2
    assert result["ghost"] == []


# ── Duplicate relationship handling ───────────────────────────────────────────


def test_duplicate_edges_deduplicated():
    """build_graph_store deduplicates same-type same-source same-target edges."""
    case = make_case()
    person = make_person()
    edges = [
        _FakeEdge("ACCUSED_IN", person.id, case.id),
        _FakeEdge("ACCUSED_IN", person.id, case.id),  # duplicate
    ]
    store = make_store([case, person], edges)
    # Should only appear once in accused list
    accused = get_co_accused(store, case.id)
    assert len(accused) == 1
