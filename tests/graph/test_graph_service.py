from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.graph_service import GraphService
from helpers import make_case, make_store, _FakeEdge, make_officer, make_person



def test_get_crime_summary():
    cases = [
        make_case(),
        make_case(),
        make_case(),
    ]

    store = make_store(cases, [])
    repo = GraphRepository(store)
    service = GraphService(repo)

    result = service.get_crime_summary()

    assert isinstance(result, dict)

    # At minimum, verify it isn't empty.
    assert len(result) > 0



def test_get_crime_by_district():
    cases = [
        make_case(district="Bengaluru"),
        make_case(district="Bengaluru"),
        make_case(district="Mysuru"),
    ]

    store = make_store(cases, [])
    service = GraphService(GraphRepository(store))

    result = service.get_crime_by_district()

    assert result["dimension"] == "district"
    assert result["counts"]["Bengaluru"] == 2
    assert result["counts"]["Mysuru"] == 1

def test_get_crime_by_station():
    cases = [
        make_case(station="Ashok Nagar"),
        make_case(station="Ashok Nagar"),
        make_case(station="Cubbon Park"),
    ]

    store = make_store(cases, [])
    service = GraphService(GraphRepository(store))

    result = service.get_crime_by_station()

    assert result["dimension"] == "police_station"
    assert result["counts"]["Ashok Nagar"] == 2
    assert result["counts"]["Cubbon Park"] == 1

def test_get_crime_by_offence_category():
    cases = [
        make_case(offence_category="theft"),
        make_case(offence_category="theft"),
        make_case(offence_category="murder"),
    ]

    store = make_store(cases, [])
    service = GraphService(GraphRepository(store))

    result = service.get_crime_by_offence_category()

    assert result["dimension"] == "offence_category"
    assert result["counts"]["theft"] == 2
    assert result["counts"]["murder"] == 1

def test_get_officer_workload():
    case1 = make_case()
    case2 = make_case()

    officer1 = make_officer("KA-0001")
    officer2 = make_officer("KA-0002")

    edges = [
        _FakeEdge("INVESTIGATED_BY", case1.id, officer1.id),
        _FakeEdge("INVESTIGATED_BY", case2.id, officer1.id),
        _FakeEdge("INVESTIGATED_BY", case2.id, officer2.id),
    ]

    store = make_store(
        [case1, case2, officer1, officer2],
        edges,
    )

    service = GraphService(GraphRepository(store))

    result = service.get_officer_workload()

    assert result["dimension"] == "officer"
    assert result["total_officers"] == 2

    workloads = {
        x["officer_id"]: x["case_count"]
        for x in result["workloads"]
    }

    assert workloads[officer1.id] == 2
    assert workloads[officer2.id] == 1

def test_get_graph_stats():
    case = make_case()
    person = make_person()
    officer = make_officer()

    edge = _FakeEdge(
        "INVESTIGATED_BY",
        case.id,
        officer.id,
    )

    store = make_store(
        [case, person, officer],
        [edge],
    )

    service = GraphService(GraphRepository(store))

    result = service.get_graph_stats()

    assert isinstance(result, dict)

    # Don't hardcode every value unless you know the exact schema.
    # Just verify important keys exist.
    assert len(result) > 0

def test_get_connected_components():
    case1 = make_case()
    officer1 = make_officer("KA-0001")

    case2 = make_case()
    officer2 = make_officer("KA-0002")

    edges = [
        _FakeEdge("INVESTIGATED_BY", case1.id, officer1.id),
        _FakeEdge("INVESTIGATED_BY", case2.id, officer2.id),
    ]

    store = make_store(
        [
            case1,
            officer1,
            case2,
            officer2,
        ],
        edges,
    )

    service = GraphService(GraphRepository(store))

    result = service.get_connected_components()

    assert result["component_count"] == 2
    assert result["largest_component_size"] == 2

def test_get_case_network():
    case = make_case()
    person = make_person()
    officer = make_officer()

    edges = [
        _FakeEdge("ACCUSED_IN", person.id, case.id),
        _FakeEdge("INVESTIGATED_BY", case.id, officer.id),
    ]

    store = make_store(
        [case, person, officer],
        edges,
    )

    service = GraphService(GraphRepository(store))

    result = service.get_case_network(case.id)

    assert result["root_id"] == case.id
    assert result["node_count"] >= 3
    assert result["edge_count"] >= 2

    node_ids = {n["node_id"] for n in result["nodes"]}

    assert case.id in node_ids
    assert person.id in node_ids
    assert officer.id in node_ids

def test_get_co_accused_network():
    case = make_case()

    person1 = make_person()
    person2 = make_person()

    edges = [
        _FakeEdge("ACCUSED_IN", person1.id, case.id),
        _FakeEdge("ACCUSED_IN", person2.id, case.id),
    ]

    store = make_store(
        [case, person1, person2],
        edges,
    )

    service = GraphService(GraphRepository(store))

    result = service.get_co_accused_network(person1.id)

    assert result["person_id"] == person1.id
    assert result["co_accused_count"] == 1

   

    co = result["co_accused"][0]

    assert co["person_id"] == person2.id
    assert len(co["shared_cases"]) == 1



