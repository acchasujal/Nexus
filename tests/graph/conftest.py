"""tests/graph/conftest.py — shared fixtures for all graph algorithm tests."""
import pathlib
import sys

import pytest
from helpers import (
    _FakeEdge,
    make_case,
    make_clock,
    make_dependency,
    make_evidence,
    make_officer,
    make_person,
    make_store,
)

from backend.app.core.graph.algorithms.utils import (
    GraphStore,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
print("ROOT =", ROOT)

sys.path.insert(0, str(ROOT))






# ─────────────────────────────────────────────────────────────────────────────
# Lightweight fake record objects that mirror the SyntheticNodeRecord /
# SyntheticEdgeRecord interface used by build_graph_store, without importing
# anything from synthetic_data.
# ─────────────────────────────────────────────────────────────────────────────



# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def empty_store() -> GraphStore:
    """A store with no nodes or edges."""
    return GraphStore()


@pytest.fixture()
def single_case_store() -> GraphStore:
    """Store with exactly one Case node and no edges."""
    case = make_case()
    return make_store([case], [])


@pytest.fixture()
def two_case_store():
    """Two cases, one person accused in both, linked by LINKED_TO."""
    case_a = make_case(district="Bengaluru City", station="Ashok Nagar", offence_category="theft")
    case_b = make_case(district="Bengaluru City", station="Ashok Nagar", offence_category="theft",
                       reported_at="2026-01-10T00:00:00+00:00")
    person = make_person(role="accused")
    officer = make_officer()
    dep = make_dependency(status="pending")
    clock_a = make_clock(status="red", days_remaining=3)
    clock_b = make_clock(status="green", days_remaining=20)
    evidence = make_evidence()

    nodes = [case_a, case_b, person, officer, dep, clock_a, clock_b, evidence]
    edges = [
        _FakeEdge("ACCUSED_IN", person.id, case_a.id),
        _FakeEdge("ACCUSED_IN", person.id, case_b.id),
        _FakeEdge("INVESTIGATED_BY", case_a.id, officer.id),
        _FakeEdge("INVESTIGATED_BY", case_b.id, officer.id),
        _FakeEdge("CASE_HAS_DEPENDENCY", case_a.id, dep.id),
        _FakeEdge("CASE_HAS_CLOCK", case_a.id, clock_a.id),
        _FakeEdge("CASE_HAS_CLOCK", case_b.id, clock_b.id),
        _FakeEdge("CASE_HAS_EVIDENCE", case_a.id, evidence.id),
        _FakeEdge("LINKED_TO", case_a.id, case_b.id),
    ]
    store = make_store(nodes, edges)
    return store, {
        "case_a": case_a, "case_b": case_b, "person": person,
        "officer": officer, "dep": dep, "clock_a": clock_a,
        "clock_b": clock_b, "evidence": evidence,
    }


@pytest.fixture()
def multi_component_store():
    """Two completely disconnected case nodes — two components."""
    case_a = make_case(district="Mysuru")
    case_b = make_case(district="Mangaluru")
    store = make_store([case_a, case_b], [])
    return store, case_a, case_b
