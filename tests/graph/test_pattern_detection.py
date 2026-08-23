"""
tests/graph/test_pattern_detection.py

Unit tests for backend.app.core.graph.algorithms.pattern_detection.

Coverage
--------
* detect_repeat_accused — happy path, below threshold, empty graph, exact count
* detect_repeat_phone — cluster detected, below threshold, no cluster ids
* detect_repeat_vehicle — happy path, below threshold
* detect_repeat_address — happy path, empty
* detect_high_workload_officers — above/below threshold, zero-case officer
* detect_dependency_hotspots — pending count threshold, resolved not counted
* detect_district_hotspots — above/below threshold, empty graph
* All result types carry a non-empty reason field
* All result lists are sorted descending by primary metric
"""

from __future__ import annotations


from backend.app.core.graph.algorithms.pattern_detection import (
    ClusterResult,
    DependencyHotspotResult,
    DistrictHotspotResult,
    OfficerWorkloadResult,
    RepeatAccusedResult,
    detect_dependency_hotspots,
    detect_district_hotspots,
    detect_high_workload_officers,
    detect_repeat_accused,
    detect_repeat_address,
    detect_repeat_phone,
    detect_repeat_vehicle,
)

from helpers import (
    _FakeEdge,
    make_case,
    make_dependency,
    make_officer,
    make_person,
    make_store,
)


# ── detect_repeat_accused ─────────────────────────────────────────────────────


def test_repeat_accused_happy():
    case_a = make_case()
    case_b = make_case()
    person = make_person()
    store = make_store(
        [case_a, case_b, person],
        [_FakeEdge("ACCUSED_IN", person.id, case_a.id),
         _FakeEdge("ACCUSED_IN", person.id, case_b.id)],
    )
    results = detect_repeat_accused(store, min_cases=2)
    assert len(results) == 1
    assert results[0].person_id == person.id
    assert results[0].case_count == 2
    assert isinstance(results[0], RepeatAccusedResult)


def test_repeat_accused_below_threshold():
    """Person accused in only 1 case should not be flagged."""
    case = make_case()
    person = make_person()
    store = make_store(
        [case, person],
        [_FakeEdge("ACCUSED_IN", person.id, case.id)],
    )
    assert detect_repeat_accused(store, min_cases=2) == []


def test_repeat_accused_empty(empty_store):
    assert detect_repeat_accused(empty_store) == []


def test_repeat_accused_multiple_sorted():
    """Result must be sorted by case_count descending."""
    case_a = make_case()
    case_b = make_case()
    case_c = make_case()
    p1 = make_person()  # accused in 3 cases
    p2 = make_person()  # accused in 2 cases
    store = make_store(
        [case_a, case_b, case_c, p1, p2],
        [_FakeEdge("ACCUSED_IN", p1.id, case_a.id),
         _FakeEdge("ACCUSED_IN", p1.id, case_b.id),
         _FakeEdge("ACCUSED_IN", p1.id, case_c.id),
         _FakeEdge("ACCUSED_IN", p2.id, case_a.id),
         _FakeEdge("ACCUSED_IN", p2.id, case_b.id)],
    )
    results = detect_repeat_accused(store, min_cases=2)
    assert results[0].case_count >= results[-1].case_count
    assert results[0].person_id == p1.id


def test_repeat_accused_reason_nonempty():
    case_a = make_case()
    case_b = make_case()
    person = make_person()
    store = make_store(
        [case_a, case_b, person],
        [_FakeEdge("ACCUSED_IN", person.id, case_a.id),
         _FakeEdge("ACCUSED_IN", person.id, case_b.id)],
    )
    results = detect_repeat_accused(store, min_cases=2)
    assert results[0].reason != ""


def test_repeat_accused_deduplicates_case_ids():
    """Duplicate ACCUSED_IN edges for the same case should count once."""
    case = make_case()
    person = make_person()
    store = make_store(
        [case, person],
        [_FakeEdge("ACCUSED_IN", person.id, case.id),
         _FakeEdge("ACCUSED_IN", person.id, case.id)],  # duplicate
    )
    results = detect_repeat_accused(store, min_cases=1)
    # case_count should be 1, not 2
    assert results[0].case_count == 1


# ── detect_repeat_phone ───────────────────────────────────────────────────────


def test_repeat_phone_happy():
    case = make_case()
    p1 = make_person(phone_cluster="phone-01")
    p2 = make_person(phone_cluster="phone-01")
    store = make_store(
        [case, p1, p2],
        [_FakeEdge("ACCUSED_IN", p1.id, case.id),
         _FakeEdge("ACCUSED_IN", p2.id, case.id)],
    )
    results = detect_repeat_phone(store, min_persons=2)
    assert len(results) == 1
    assert isinstance(results[0], ClusterResult)
    assert results[0].cluster_type == "phone"
    assert len(results[0].person_ids) == 2


def test_repeat_phone_below_threshold():
    case = make_case()
    person = make_person(phone_cluster="phone-01")
    store = make_store([case, person], [_FakeEdge("ACCUSED_IN", person.id, case.id)])
    assert detect_repeat_phone(store, min_persons=2) == []


def test_repeat_phone_empty(empty_store):
    assert detect_repeat_phone(empty_store) == []


def test_repeat_phone_no_cluster_id():
    """Persons with empty phone_cluster_id should not be grouped."""
    person = make_person(phone_cluster=None)
    store = make_store([person], [])
    assert detect_repeat_phone(store, min_persons=2) == []


def test_repeat_phone_reason_nonempty():
    case = make_case()
    p1 = make_person(phone_cluster="phone-01")
    p2 = make_person(phone_cluster="phone-01")
    store = make_store(
        [case, p1, p2],
        [_FakeEdge("ACCUSED_IN", p1.id, case.id),
         _FakeEdge("ACCUSED_IN", p2.id, case.id)],
    )
    results = detect_repeat_phone(store, min_persons=2)
    assert results[0].reason != ""


def test_repeat_phone_case_ids_collected():
    """Each cluster result should list the cases associated with its persons."""
    case_a = make_case()
    case_b = make_case()
    p1 = make_person(phone_cluster="phone-05")
    p2 = make_person(phone_cluster="phone-05")
    store = make_store(
        [case_a, case_b, p1, p2],
        [_FakeEdge("ACCUSED_IN", p1.id, case_a.id),
         _FakeEdge("VICTIM_IN", p2.id, case_b.id)],
    )
    results = detect_repeat_phone(store, min_persons=2)
    assert case_a.id in results[0].case_ids
    assert case_b.id in results[0].case_ids


# ── detect_repeat_vehicle ─────────────────────────────────────────────────────


def test_repeat_vehicle_happy():
    case = make_case()
    p1 = make_person(vehicle_cluster="vehicle-03")
    p2 = make_person(vehicle_cluster="vehicle-03")
    store = make_store(
        [case, p1, p2],
        [_FakeEdge("ACCUSED_IN", p1.id, case.id),
         _FakeEdge("ACCUSED_IN", p2.id, case.id)],
    )
    results = detect_repeat_vehicle(store, min_persons=2)
    assert len(results) == 1
    assert results[0].cluster_type == "vehicle"


def test_repeat_vehicle_empty(empty_store):
    assert detect_repeat_vehicle(empty_store) == []


def test_repeat_vehicle_below_threshold():
    case = make_case()
    person = make_person(vehicle_cluster="vehicle-03")
    store = make_store([case, person], [_FakeEdge("ACCUSED_IN", person.id, case.id)])
    assert detect_repeat_vehicle(store, min_persons=2) == []


# ── detect_repeat_address ─────────────────────────────────────────────────────


def test_repeat_address_happy():
    case = make_case()
    p1 = make_person(address_cluster="address-07")
    p2 = make_person(address_cluster="address-07")
    store = make_store(
        [case, p1, p2],
        [_FakeEdge("ACCUSED_IN", p1.id, case.id),
         _FakeEdge("ACCUSED_IN", p2.id, case.id)],
    )
    results = detect_repeat_address(store, min_persons=2)
    assert len(results) == 1
    assert results[0].cluster_type == "address"


def test_repeat_address_empty(empty_store):
    assert detect_repeat_address(empty_store) == []


# ── detect_high_workload_officers ─────────────────────────────────────────────


def test_high_workload_officers_happy():
    cases = [make_case() for _ in range(5)]
    officer = make_officer(badge="KA-0010")
    edges = [_FakeEdge("INVESTIGATED_BY", c.id, officer.id) for c in cases]
    store = make_store(cases + [officer], edges)
    results = detect_high_workload_officers(store, min_cases=5)
    assert len(results) == 1
    assert isinstance(results[0], OfficerWorkloadResult)
    assert results[0].case_count == 5
    assert "KA-0010" in results[0].badge_number


def test_high_workload_officers_below_threshold():
    case = make_case()
    officer = make_officer()
    store = make_store(
        [case, officer],
        [_FakeEdge("INVESTIGATED_BY", case.id, officer.id)],
    )
    assert detect_high_workload_officers(store, min_cases=5) == []


def test_high_workload_officers_empty(empty_store):
    assert detect_high_workload_officers(empty_store) == []


def test_high_workload_officers_sorted():
    case_a = make_case()
    case_b = make_case()
    o1 = make_officer(badge="KA-0001")
    o2 = make_officer(badge="KA-0002")
    edges = [
        _FakeEdge("INVESTIGATED_BY", case_a.id, o1.id),
        _FakeEdge("INVESTIGATED_BY", case_b.id, o1.id),
        _FakeEdge("INVESTIGATED_BY", case_a.id, o2.id),
    ]
    store = make_store([case_a, case_b, o1, o2], edges)
    results = detect_high_workload_officers(store, min_cases=1)
    counts = [r.case_count for r in results]
    assert counts == sorted(counts, reverse=True)


def test_high_workload_officers_reason_nonempty():
    cases = [make_case() for _ in range(5)]
    officer = make_officer()
    store = make_store(cases + [officer],
                       [_FakeEdge("INVESTIGATED_BY", c.id, officer.id) for c in cases])
    results = detect_high_workload_officers(store, min_cases=3)
    assert all(r.reason != "" for r in results)


# ── detect_dependency_hotspots ────────────────────────────────────────────────


def test_dependency_hotspots_happy():
    case = make_case()
    deps = [make_dependency("pending") for _ in range(4)]
    edges = [_FakeEdge("CASE_HAS_DEPENDENCY", case.id, d.id) for d in deps]
    store = make_store([case] + deps, edges)
    results = detect_dependency_hotspots(store, min_pending=3)
    assert len(results) == 1
    assert isinstance(results[0], DependencyHotspotResult)
    assert results[0].pending_count == 4


def test_dependency_hotspots_resolved_not_counted():
    """Resolved dependencies must not push a case over the threshold."""
    case = make_case()
    pending = make_dependency("pending")
    resolved = [make_dependency("resolved") for _ in range(5)]
    edges = (
        [_FakeEdge("CASE_HAS_DEPENDENCY", case.id, pending.id)]
        + [_FakeEdge("CASE_HAS_DEPENDENCY", case.id, d.id) for d in resolved]
    )
    store = make_store([case, pending] + resolved, edges)
    # Only 1 pending, threshold is 3 → should not flag
    results = detect_dependency_hotspots(store, min_pending=3)
    assert results == []


def test_dependency_hotspots_below_threshold():
    case = make_case()
    dep = make_dependency("pending")
    store = make_store([case, dep], [_FakeEdge("CASE_HAS_DEPENDENCY", case.id, dep.id)])
    assert detect_dependency_hotspots(store, min_pending=3) == []


def test_dependency_hotspots_empty(empty_store):
    assert detect_dependency_hotspots(empty_store) == []


def test_dependency_hotspots_sorted():
    case_a = make_case()
    case_b = make_case()
    deps_a = [make_dependency("pending") for _ in range(5)]
    deps_b = [make_dependency("pending") for _ in range(3)]
    edges = (
        [_FakeEdge("CASE_HAS_DEPENDENCY", case_a.id, d.id) for d in deps_a]
        + [_FakeEdge("CASE_HAS_DEPENDENCY", case_b.id, d.id) for d in deps_b]
    )
    store = make_store([case_a, case_b] + deps_a + deps_b, edges)
    results = detect_dependency_hotspots(store, min_pending=3)
    pending_counts = [r.pending_count for r in results]
    assert pending_counts == sorted(pending_counts, reverse=True)


def test_dependency_hotspots_reason_nonempty():
    case = make_case()
    deps = [make_dependency("pending") for _ in range(3)]
    store = make_store([case] + deps,
                       [_FakeEdge("CASE_HAS_DEPENDENCY", case.id, d.id) for d in deps])
    results = detect_dependency_hotspots(store, min_pending=3)
    assert all(r.reason != "" for r in results)


# ── detect_district_hotspots ──────────────────────────────────────────────────


def test_district_hotspots_happy():
    cases = [make_case(district="Bengaluru City") for _ in range(3)]
    store = make_store(cases, [])
    results = detect_district_hotspots(store, min_cases=3)
    assert len(results) == 1
    assert isinstance(results[0], DistrictHotspotResult)
    assert results[0].district == "Bengaluru City"
    assert results[0].case_count == 3


def test_district_hotspots_below_threshold():
    cases = [make_case(district="Mysuru") for _ in range(2)]
    store = make_store(cases, [])
    assert detect_district_hotspots(store, min_cases=5) == []


def test_district_hotspots_empty(empty_store):
    assert detect_district_hotspots(empty_store) == []


def test_district_hotspots_sorted():
    blr = [make_case(district="Bengaluru City") for _ in range(5)]
    mys = [make_case(district="Mysuru") for _ in range(3)]
    store = make_store(blr + mys, [])
    results = detect_district_hotspots(store, min_cases=3)
    counts = [r.case_count for r in results]
    assert counts == sorted(counts, reverse=True)
    assert results[0].district == "Bengaluru City"


def test_district_hotspots_reason_nonempty():
    cases = [make_case(district="Kalaburagi") for _ in range(5)]
    store = make_store(cases, [])
    results = detect_district_hotspots(store, min_cases=3)
    assert all(r.reason != "" for r in results)
