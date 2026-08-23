"""
tests/graph/test_aggregation.py

Unit tests for backend.app.core.graph.algorithms.aggregation.

Coverage
--------
* crime_count_by_district — empty, single, multiple districts
* crime_count_by_station — station grouping
* crime_count_by_crime_head — edge-based (CASE_HAS_CRIME_HEAD)
* crime_count_by_offence_category — category grouping
* case_counts — total, by_stage, by_risk_band, by_offence_category
* dependency_status_counts — pending / resolved / escalated
* average_dependencies_per_case — zero cases, exact value
* clock_status_counts — green / amber / red / overdue
* average_evidence_per_case — zero cases, exact value
* officer_workload — id-keyed counts
* officer_workload_named — badge-keyed counts, fallback
* Statistics module: compute_graph_statistics — empty, single node, populated
"""

from __future__ import annotations

import pytest

from backend.app.core.graph.algorithms.aggregation import (
    CaseCounts,
    average_dependencies_per_case,
    average_evidence_per_case,
    case_counts,
    clock_status_counts,
    crime_count_by_crime_head,
    crime_count_by_district,
    crime_count_by_offence_category,
    crime_count_by_station,
    dependency_status_counts,
    officer_workload,
    officer_workload_named,
)
from backend.app.core.graph.algorithms.statistics import GraphStatistics, compute_graph_statistics

from helpers import (
    _FakeEdge,
    make_case,
    make_clock,
    make_crime_head,
    make_dependency,
    make_evidence,
    make_officer,
    make_store,
    _FakeNode,
    make_person
    
)




# ── crime_count_by_district ───────────────────────────────────────────────────


def test_crime_count_by_district_empty(empty_store):
    assert crime_count_by_district(empty_store) == {}


def test_crime_count_by_district_single():
    case = make_case(district="Bengaluru City")
    store = make_store([case], [])
    result = crime_count_by_district(store)
    assert result["Bengaluru City"] == 1


def test_crime_count_by_district_multiple():
    cases = [
        make_case(district="Bengaluru City"),
        make_case(district="Bengaluru City"),
        make_case(district="Mysuru"),
    ]
    store = make_store(cases, [])
    result = crime_count_by_district(store)
    assert result["Bengaluru City"] == 2
    assert result["Mysuru"] == 1
    assert sum(result.values()) == 3


def test_crime_count_by_district_unknown_fallback():
    """Cases with no district property fall into 'unknown'."""

    node = _FakeNode("Case", {})  # no "district" key
    store = make_store([node], [])
    result = crime_count_by_district(store)
    assert result.get("unknown", 0) == 1


# ── crime_count_by_station ────────────────────────────────────────────────────


def test_crime_count_by_station_empty(empty_store):
    assert crime_count_by_station(empty_store) == {}


def test_crime_count_by_station_grouped():
    cases = [
        make_case(station="Ashok Nagar"),
        make_case(station="Ashok Nagar"),
        make_case(station="Malleshwaram"),
    ]
    store = make_store(cases, [])
    result = crime_count_by_station(store)
    assert result["Ashok Nagar"] == 2
    assert result["Malleshwaram"] == 1


# ── crime_count_by_crime_head ─────────────────────────────────────────────────


def test_crime_count_by_crime_head_empty(empty_store):
    assert crime_count_by_crime_head(empty_store) == {}


def test_crime_count_by_crime_head_uses_edge():
    case_a = make_case()
    case_b = make_case()
    head = make_crime_head("Property")
    store = make_store(
        [case_a, case_b, head],
        [_FakeEdge("CASE_HAS_CRIME_HEAD", case_a.id, head.id),
         _FakeEdge("CASE_HAS_CRIME_HEAD", case_b.id, head.id)],
    )
    result = crime_count_by_crime_head(store)
    assert result.get("Property", 0) == 2


def test_crime_count_by_crime_head_fallback_to_id():
    """If crime head node is missing, key falls back to the node id."""
    case = make_case()
    
    # Edge to a non-existent node
    edge = _FakeEdge("CASE_HAS_CRIME_HEAD", case.id, "dangling-id")
    store = make_store([case], [edge])
    result = crime_count_by_crime_head(store)
    # "dangling-id" is not in store.nodes so the key is "dangling-id"
    assert "dangling-id" in result


# ── crime_count_by_offence_category ──────────────────────────────────────────


def test_crime_count_by_offence_category_empty(empty_store):
    assert crime_count_by_offence_category(empty_store) == {}


def test_crime_count_by_offence_category_grouped():
    cases = [
        make_case(offence_category="theft"),
        make_case(offence_category="theft"),
        make_case(offence_category="fraud"),
    ]
    store = make_store(cases, [])
    result = crime_count_by_offence_category(store)
    assert result["theft"] == 2
    assert result["fraud"] == 1


# ── case_counts ───────────────────────────────────────────────────────────────


def test_case_counts_empty(empty_store):
    cc = case_counts(empty_store)
    assert cc.total == 0
    assert cc.by_stage == {}
    assert cc.by_risk_band == {}
    assert cc.by_offence_category == {}


def test_case_counts_totals():
    cases = [
        make_case(case_stage="investigation", risk_band="green", offence_category="theft"),
        make_case(case_stage="investigation", risk_band="red", offence_category="fraud"),
        make_case(case_stage="charge_sheet_filed", risk_band="green", offence_category="theft"),
    ]
    store = make_store(cases, [])
    cc = case_counts(store)
    assert cc.total == 3
    assert cc.by_stage["investigation"] == 2
    assert cc.by_stage["charge_sheet_filed"] == 1
    assert cc.by_risk_band["green"] == 2
    assert cc.by_risk_band["red"] == 1
    assert cc.by_offence_category["theft"] == 2


def test_case_counts_returns_dataclass(empty_store):
    assert isinstance(case_counts(empty_store), CaseCounts)


# ── dependency_status_counts ──────────────────────────────────────────────────


def test_dependency_status_counts_empty(empty_store):
    assert dependency_status_counts(empty_store) == {}


def test_dependency_status_counts_grouped():
    deps = [
        make_dependency("pending"),
        make_dependency("pending"),
        make_dependency("resolved"),
        make_dependency("escalated"),
    ]
    store = make_store(deps, [])
    result = dependency_status_counts(store)
    assert result["pending"] == 2
    assert result["resolved"] == 1
    assert result["escalated"] == 1


# ── average_dependencies_per_case ────────────────────────────────────────────


def test_average_dependencies_per_case_no_cases(empty_store):
    assert average_dependencies_per_case(empty_store) == 0.0


def test_average_dependencies_per_case_exact():
    case_a = make_case()
    case_b = make_case()
    d1 = make_dependency()
    d2 = make_dependency()
    d3 = make_dependency()
    store = make_store(
        [case_a, case_b, d1, d2, d3],
        [_FakeEdge("CASE_HAS_DEPENDENCY", case_a.id, d1.id),
         _FakeEdge("CASE_HAS_DEPENDENCY", case_a.id, d2.id),
         _FakeEdge("CASE_HAS_DEPENDENCY", case_b.id, d3.id)],
    )
    avg = average_dependencies_per_case(store)
    assert avg == pytest.approx(1.5, abs=1e-4)


# ── clock_status_counts ───────────────────────────────────────────────────────


def test_clock_status_counts_empty(empty_store):
    assert clock_status_counts(empty_store) == {}


def test_clock_status_counts_grouped():
    clocks = [
        make_clock("green"),
        make_clock("green"),
        make_clock("amber"),
        make_clock("red"),
        make_clock("overdue"),
    ]
    store = make_store(clocks, [])
    result = clock_status_counts(store)
    assert result["green"] == 2
    assert result["amber"] == 1
    assert result["red"] == 1
    assert result["overdue"] == 1


# ── average_evidence_per_case ─────────────────────────────────────────────────


def test_average_evidence_per_case_no_cases(empty_store):
    assert average_evidence_per_case(empty_store) == 0.0


def test_average_evidence_per_case_exact():
    case = make_case()
    e1 = make_evidence()
    e2 = make_evidence()
    store = make_store(
        [case, e1, e2],
        [_FakeEdge("CASE_HAS_EVIDENCE", case.id, e1.id),
         _FakeEdge("CASE_HAS_EVIDENCE", case.id, e2.id)],
    )
    avg = average_evidence_per_case(store)
    assert avg == pytest.approx(2.0, abs=1e-4)


# ── officer_workload ──────────────────────────────────────────────────────────


def test_officer_workload_empty(empty_store):
    assert officer_workload(empty_store) == {}


def test_officer_workload_counts():
    case_a = make_case()
    case_b = make_case()
    officer = make_officer()
    store = make_store(
        [case_a, case_b, officer],
        [_FakeEdge("INVESTIGATED_BY", case_a.id, officer.id),
         _FakeEdge("INVESTIGATED_BY", case_b.id, officer.id)],
    )
    result = officer_workload(store)
    assert result[officer.id] == 2


def test_officer_workload_zero_case_officer_omitted():
    """Officer with no cases should not appear in the result."""
    officer = make_officer()
    store = make_store([officer], [])
    result = officer_workload(store)
    assert officer.id not in result


# ── officer_workload_named ────────────────────────────────────────────────────


def test_officer_workload_named_uses_badge():
    case = make_case()
    officer = make_officer(badge="KA-0042")
    store = make_store(
        [case, officer],
        [_FakeEdge("INVESTIGATED_BY", case.id, officer.id)],
    )
    result = officer_workload_named(store)
    assert "KA-0042" in result
    assert result["KA-0042"] == 1


# ── compute_graph_statistics ──────────────────────────────────────────────────


def test_graph_statistics_empty(empty_store):
    stats = compute_graph_statistics(empty_store)
    assert isinstance(stats, GraphStatistics)
    assert stats.num_nodes == 0
    assert stats.num_edges == 0
    assert stats.density == 0.0
    assert stats.average_degree == 0.0
    assert stats.largest_component_size == 0
    assert stats.isolated_node_count == 0


def test_graph_statistics_single_node():
    case = make_case()
    store = make_store([case], [])
    stats = compute_graph_statistics(store)
    assert stats.num_nodes == 1
    assert stats.num_edges == 0
    assert stats.isolated_node_count == 1
    assert stats.largest_component_size == 1


def test_graph_statistics_populated(two_case_store):
    store, nodes = two_case_store
    stats = compute_graph_statistics(store)
    assert stats.num_nodes == len(store.nodes)
    assert stats.num_edges > 0
    assert stats.entity_distribution.get("Case", 0) == 2
    assert stats.largest_component_size >= 1
    assert stats.density >= 0.0
    assert stats.average_degree >= 0.0


def test_graph_statistics_entity_distribution():
    case = make_case()
    person = make_person()
    dep = make_dependency()
    store = make_store([case, person, dep], [])
    stats = compute_graph_statistics(store)
    assert stats.entity_distribution["Case"] == 1
    assert stats.entity_distribution["Person"] == 1
    assert stats.entity_distribution["Dependency"] == 1


def test_graph_statistics_isolated_count():
    """Nodes with no edges are counted as isolated."""
    case_a = make_case()
    case_b = make_case()
    # No edges — both are isolated
    store = make_store([case_a, case_b], [])
    stats = compute_graph_statistics(store)
    assert stats.isolated_node_count == 2


def test_graph_statistics_largest_component_connected(two_case_store):
    store, _ = two_case_store
    stats = compute_graph_statistics(store)
    # All nodes are connected (via the LINKED_TO or ACCUSED_IN chain)
    assert stats.largest_component_size == stats.num_nodes


def test_graph_statistics_two_components(multi_component_store):
    store, case_a, case_b = multi_component_store
    stats = compute_graph_statistics(store)
    assert stats.largest_component_size == 1  # each node is its own component
