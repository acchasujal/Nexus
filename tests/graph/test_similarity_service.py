from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.similarity_service import SimilarityService

from helpers import make_case, make_store


def test_get_similar_cases_unknown_case():
    store = make_store([], [])

    service = SimilarityService(GraphRepository(store))

    result = service.get_similar_cases("missing-case")

    assert result["error"] == "Case not found"
    assert result["case_id"] == "missing-case"


def test_get_similar_cases_empty_result():
    case = make_case()

    store = make_store([case], [])

    service = SimilarityService(GraphRepository(store))

    result = service.get_similar_cases(case.id)

    assert result["case_id"] == case.id
    assert result["similar_case_count"] == 0
    assert result["similar_cases"] == []


def test_compare_cases_missing_case_a():
    case = make_case()

    store = make_store([case], [])

    service = SimilarityService(GraphRepository(store))

    result = service.compare_cases("missing", case.id)

    assert result["error"] == "Case not found"
    assert result["case_id"] == "missing"


def test_compare_cases_missing_case_b():
    case = make_case()

    store = make_store([case], [])

    service = SimilarityService(GraphRepository(store))

    result = service.compare_cases(case.id, "missing")

    assert result["error"] == "Case not found"
    assert result["case_id"] == "missing"


def test_compare_same_case():
    case = make_case()

    store = make_store([case], [])

    service = SimilarityService(GraphRepository(store))

    result = service.compare_cases(case.id, case.id)

    assert result["case_a"] == case.id
    assert result["case_b"] == case.id

    assert result["similarity_score"] == 1.0

    assert isinstance(result["shared_features"], list)

    assert len(result["shared_features"]) > 0


def test_compare_two_cases():
    case1 = make_case(
        district="Bengaluru",
        station="Ashok Nagar",
        offence_category="theft",
    )

    case2 = make_case(
        district="Bengaluru",
        station="Ashok Nagar",
        offence_category="theft",
    )

    store = make_store(
        [case1, case2],
        [],
    )

    service = SimilarityService(GraphRepository(store))

    result = service.compare_cases(case1.id, case2.id)

    assert result["case_a"] == case1.id
    assert result["case_b"] == case2.id

    assert 0.0 <= result["similarity_score"] <= 1.0

    assert isinstance(result["shared_features"], list)


def test_batch_similarity_matrix_empty():
    store = make_store([], [])

    service = SimilarityService(GraphRepository(store))

    result = service.batch_similarity_matrix([])

    assert result["case_ids"] == []
    assert result["pair_count"] == 0
    assert result["pairs"] == []


def test_batch_similarity_matrix():
    case1 = make_case(
        district="Bengaluru",
        offence_category="theft",
    )

    case2 = make_case(
        district="Bengaluru",
        offence_category="theft",
    )

    case3 = make_case(
        district="Mysuru",
        offence_category="murder",
    )

    store = make_store(
        [case1, case2, case3],
        [],
    )

    service = SimilarityService(GraphRepository(store))

    result = service.batch_similarity_matrix(
        [
            case1.id,
            case2.id,
            case3.id,
        ]
    )

    assert result["case_ids"] == [
        case1.id,
        case2.id,
        case3.id,
    ]

    assert result["pair_count"] == len(result["pairs"])

    assert isinstance(result["pairs"], list)