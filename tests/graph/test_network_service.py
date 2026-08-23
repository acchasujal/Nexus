from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.network_service import NetworkService

from helpers import (
    make_case,
    make_person,
    make_dependency,
    make_clock,
    make_evidence,
    make_section,
    make_store,
    _FakeEdge,
)


def test_get_case():
    case = make_case()

    store = make_store([case], [])

    service = NetworkService(GraphRepository(store))

    result = service.get_case(case.id)

    assert "case" in result
    assert result["case"]["node_id"] == case.id


def test_get_person():
    person = make_person()

    store = make_store([person], [])

    service = NetworkService(GraphRepository(store))

    result = service.get_person(person.id)

    assert "person" in result
    assert result["person"]["node_id"] == person.id


def test_get_related_cases():
    case1 = make_case()
    case2 = make_case()

    edges = [
        _FakeEdge("LINKED_TO", case1.id, case2.id),
    ]

    store = make_store(
        [case1, case2],
        edges,
    )

    service = NetworkService(GraphRepository(store))

    result = service.get_related_cases(case1.id)

    assert result["case_id"] == case1.id
    assert result["related_case_count"] == 1
    assert result["related_cases"][0]["node_id"] == case2.id


def test_get_cases_for_person():
    case = make_case()
    person = make_person()

    edges = [
        _FakeEdge("ACCUSED_IN", person.id, case.id),
    ]

    store = make_store(
        [case, person],
        edges,
    )

    service = NetworkService(GraphRepository(store))

    result = service.get_cases_for_person(person.id)

    assert result["person_id"] == person.id
    assert result["case_count"] == 1
    assert result["cases"][0]["node_id"] == case.id


def test_get_dependency_chain():
    case = make_case()
    dependency = make_dependency()

    edges = [
        _FakeEdge("CASE_HAS_DEPENDENCY", case.id, dependency.id),
    ]

    store = make_store(
        [case, dependency],
        edges,
    )

    service = NetworkService(GraphRepository(store))

    result = service.get_dependency_chain(case.id)

    assert result["case_id"] == case.id
    assert result["dependency_count"] == 1
    assert result["dependencies"][0]["node_id"] == dependency.id


def test_get_neighbors_and_subgraph():
    case = make_case()
    person = make_person()

    edges = [
        _FakeEdge("ACCUSED_IN", person.id, case.id),
    ]

    store = make_store(
        [case, person],
        edges,
    )

    service = NetworkService(GraphRepository(store))

    neighbors = service.get_neighbors(person.id)

    assert neighbors["node_id"] == person.id
    assert neighbors["neighbor_count"] == 1

    subgraph = service.get_subgraph(person.id)

    assert subgraph["root_id"] == person.id
    assert subgraph["node_count"] >= 2
    assert subgraph["edge_count"] >= 1


def test_case_artifacts():
    case = make_case()

    clock = make_clock()
    evidence = make_evidence()
    section = make_section()

    edges = [
        _FakeEdge("CASE_HAS_CLOCK", case.id, clock.id),
        _FakeEdge("CASE_HAS_EVIDENCE", case.id, evidence.id),
        _FakeEdge("CHARGED_UNDER", case.id, section.id),
    ]

    store = make_store(
        [
            case,
            clock,
            evidence,
            section,
        ],
        edges,
    )

    service = NetworkService(GraphRepository(store))

    clocks = service.get_clock_instances(case.id)
    evidence = service.get_evidence_for_case(case.id)
    sections = service.get_sections_for_case(case.id)

    assert clocks["clock_count"] == 1
    assert evidence["evidence_count"] == 1
    assert sections["section_count"] == 1


def test_missing_nodes():
    store = make_store([], [])

    service = NetworkService(GraphRepository(store))

    assert "error" in service.get_case("missing")
    assert "error" in service.get_person("missing")
    assert "error" in service.get_neighbors("missing")
    assert "error" in service.get_dependency_chain("missing")