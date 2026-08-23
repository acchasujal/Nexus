from backend.app.core.graph.repositories.graph_repository import GraphRepository
from helpers import make_case, make_person, make_store


def test_get_case():
    case = make_case()

    store = make_store([case], [])

    repo = GraphRepository(store)

    result = repo.get_case(case.id)

    assert result is not None
    assert result.entity_type == "Case"


def test_get_person():
    person = make_person()

    store = make_store([person], [])

    repo = GraphRepository(store)

    result = repo.get_person(person.id)

    assert result is not None
    assert result.entity_type == "Person"


def test_missing_case_returns_none():
    repo = GraphRepository(make_store([], []))

    assert repo.get_case("missing") is None


def test_missing_person_returns_none():
    repo = GraphRepository(make_store([], []))

    assert repo.get_person("missing") is None