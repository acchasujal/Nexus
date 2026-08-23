from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.hotspot_service import HotspotService

from helpers import (
    make_case,
    make_dependency,
    make_officer,
    make_person,
    make_store,
    _FakeEdge,
)


def test_summary_counts():
    cases = [make_case(), make_case()]
    persons = [make_person(), make_person(), make_person()]
    officers = [make_officer()]

    store = make_store(
        cases + persons + officers,
        [],
    )

    service = HotspotService(GraphRepository(store))

    summary = service._get_summary_counts()

    assert summary["total_cases"] == 2
    assert summary["total_persons"] == 3
    assert summary["total_officers"] == 1


def test_get_temporal_hotspots():
    cases = [
        make_case(reported_at="2026-07-01"),
        make_case(reported_at="2026-07-01"),
        make_case(reported_at="2026-07-01"),
        make_case(reported_at="2026-07-02"),
    ]

    store = make_store(cases, [])

    service = HotspotService(GraphRepository(store))

    result = service.get_temporal_hotspots()

    assert result["category"] == "temporal"
    assert result["alert_level"] == "amber"
    assert result["spike_count"] == 1

    spike = result["spikes"][0]

    assert spike["date"] == "2026-07-01"
    assert spike["case_count"] == 3


def test_get_dependency_hotspots():
    case = make_case()

    deps = [
        make_dependency("pending"),
        make_dependency("pending"),
        make_dependency("pending"),
        make_dependency("completed"),
    ]

    edges = [
        _FakeEdge("CASE_HAS_DEPENDENCY", case.id, deps[0].id),
        _FakeEdge("CASE_HAS_DEPENDENCY", case.id, deps[1].id),
        _FakeEdge("CASE_HAS_DEPENDENCY", case.id, deps[2].id),
        _FakeEdge("CASE_HAS_DEPENDENCY", case.id, deps[3].id),
    ]

    store = make_store(
        [case] + deps,
        edges,
    )

    service = HotspotService(GraphRepository(store))

    result = service.get_dependency_hotspots()

    assert result["category"] == "dependency"
    assert result["hotspot_count"] == 1
    assert result["total_pending_dependencies"] == 3
    assert result["alert_level"] == "amber"


def test_get_workload_hotspots():
    officer = make_officer()

    cases = [make_case() for _ in range(5)]

    edges = [
        _FakeEdge("INVESTIGATED_BY", c.id, officer.id)
        for c in cases
    ]

    store = make_store(
        cases + [officer],
        edges,
    )

    service = HotspotService(GraphRepository(store))

    result = service.get_workload_hotspots()

    assert result["category"] == "workload"
    assert result["officer_count"] == 1
    assert result["alert_level"] == "amber"


def test_get_network_hotspots():
    case1 = make_case()
    case2 = make_case()

    person1 = make_person(phone_cluster="P1")
    person2 = make_person(phone_cluster="P1")

    edges = [
        _FakeEdge("ACCUSED_IN", person1.id, case1.id),
        _FakeEdge("ACCUSED_IN", person1.id, case2.id),
        _FakeEdge("ACCUSED_IN", person2.id, case1.id),
    ]

    store = make_store(
        [case1, case2, person1, person2],
        edges,
    )

    service = HotspotService(GraphRepository(store))

    result = service.get_network_hotspots()

    assert result["category"] == "network"

    assert "repeat_offenders" in result
    assert "shared_phone_clusters" in result
    assert "shared_vehicle_clusters" in result
    assert "shared_address_clusters" in result

    expected = (
        result["repeat_offenders"]["count"]
        + result["shared_phone_clusters"]["count"]
        + result["shared_vehicle_clusters"]["count"]
        + result["shared_address_clusters"]["count"]
    )

    assert expected == result["total_network_flags"]


def test_get_all_hotspots():
    cases = [
        make_case(reported_at="2026-07-01"),
        make_case(reported_at="2026-07-01"),
        make_case(reported_at="2026-07-01"),
    ]

    store = make_store(cases, [])

    service = HotspotService(GraphRepository(store))

    result = service.get_all_hotspots()

    assert "generated_at" in result
    assert "summary" in result
    assert "temporal" in result
    assert "dependency" in result
    assert "workload" in result
    assert "network" in result


def test_empty_graph():
    store = make_store([], [])

    service = HotspotService(GraphRepository(store))

    result = service.get_all_hotspots()

    assert result["summary"]["total_cases"] == 0
    assert result["summary"]["total_persons"] == 0
    assert result["summary"]["total_officers"] == 0

    assert result["temporal"]["alert_level"] == "green"
    assert result["dependency"]["alert_level"] == "green"
    assert result["workload"]["alert_level"] == "green"
    assert result["network"]["alert_level"] == "green"

def test_get_district_hotspots():
    case1 = make_case(district="Bengaluru")
    case2 = make_case(district="Mysuru")

    store = make_store(
        [case1, case2],
        [],
    )

    service = HotspotService(GraphRepository(store))

    result = service.get_district_hotspots("Bengaluru")

    assert result["district"] == "Bengaluru"

    assert "temporal_spikes" in result
    assert "dependency_hotspots" in result
    assert "alert_summary" in result

    assert isinstance(result["temporal_spikes"], list)
    assert isinstance(result["dependency_hotspots"], list)

    assert result["alert_summary"]["temporal"] == len(result["temporal_spikes"])
    assert result["alert_summary"]["dependency"] == len(
        result["dependency_hotspots"]
    )