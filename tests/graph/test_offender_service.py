from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.offender_service import OffenderService
from helpers import make_case, make_person, make_store, _FakeEdge, make_section, make_crime_head


def test_get_repeat_offenders():
    person = make_person()
    case1 = make_case()
    case2 = make_case()

    edges = [
        _FakeEdge("ACCUSED_IN", person.id, case1.id),
        _FakeEdge("ACCUSED_IN", person.id, case2.id),
    ]

    store = make_store(
        [person, case1, case2],
        edges,
    )

    service = OffenderService(GraphRepository(store))
    result = service.get_repeat_offenders(min_cases=2)

    assert result["min_cases_threshold"] == 2
    assert result["offender_count"] == 1
    assert result["offenders"][0]["person_id"] == person.id
    assert result["offenders"][0]["case_count"] == 2


def test_get_offender_profile_not_found():
    store = make_store([], [])
    service = OffenderService(GraphRepository(store))
    result = service.get_offender_profile("nonexistent")

    assert "error" in result
    assert result["person_id"] == "nonexistent"


def test_get_offender_profile_success():
    # Setup:
    # person1 (target) is accused in case1 and case2
    # person2 is accused in case1 (co-accused, 1 shared case)
    # person3 is accused in case1 and case2 (co-accused, 2 shared cases)
    # person4 is accused in case3 (not co-accused, no shared cases with person1)
    
    person1 = make_person()
    person2 = make_person()
    person3 = make_person()
    person4 = make_person()

    case1 = make_case(district="District A", station="Station A")
    case2 = make_case(district="District B", station="Station B")
    case3 = make_case()

    section1 = make_section("SEC_302")
    crime_head1 = make_crime_head("Violent")

    edges = [
        # person1 relations
        _FakeEdge("ACCUSED_IN", person1.id, case1.id),
        _FakeEdge("ACCUSED_IN", person1.id, case2.id),

        # person2 relations (shares case1)
        _FakeEdge("ACCUSED_IN", person2.id, case1.id),

        # person3 relations (shares case1 and case2)
        _FakeEdge("ACCUSED_IN", person3.id, case1.id),
        _FakeEdge("ACCUSED_IN", person3.id, case2.id),

        # person4 relations (shares case3, no overlap)
        _FakeEdge("ACCUSED_IN", person4.id, case3.id),

        # case details for case1
        _FakeEdge("CHARGED_UNDER", case1.id, section1.id),
        _FakeEdge("CASE_HAS_CRIME_HEAD", case1.id, crime_head1.id),
    ]

    store = make_store(
        [person1, person2, person3, person4, case1, case2, case3, section1, crime_head1],
        edges,
    )

    service = OffenderService(GraphRepository(store))
    result = service.get_offender_profile(person1.id)

    assert result["person_id"] == person1.id
    assert result["accused_in_count"] == 2
    assert set(result["case_ids"]) == {case1.id, case2.id}
    assert result["jurisdiction_spread"]["station_count"] == 2
    assert result["jurisdiction_spread"]["district_count"] == 2
    assert result["section_diversity"]["count"] == 1
    assert result["crime_head_diversity"]["count"] == 1

    # Check co-accused logic
    # Unique co-accused should be person2 and person3 (person1 excluded, person4 excluded)
    assert result["co_accused_count"] == 2
    
    co_accused_list = result["co_accused"]
    co_accused_by_id = {c["person_id"]: c for c in co_accused_list}

    assert person2.id in co_accused_by_id
    assert person3.id in co_accused_by_id
    assert person1.id not in co_accused_by_id
    assert person4.id not in co_accused_by_id

    assert co_accused_by_id[person2.id]["shared_case_count"] == 1
    assert co_accused_by_id[person3.id]["shared_case_count"] == 2

    # Check factual summary template
    summary = result["summary"]
    assert f"Person {person1.id} appears as accused in 2 case(s)." in summary
    assert "Linked to 2 co-accused individual(s)." in summary

def test_get_repeat_offenders_resolved():
    case1 = make_case()
    case2 = make_case()

    person = make_person()

    edges = [
        _FakeEdge("ACCUSED_IN", person.id, case1.id),
        _FakeEdge("ACCUSED_IN", person.id, case2.id),
    ]

    store = make_store(
        [case1, case2, person],
        edges,
    )

    service = OffenderService(GraphRepository(store))

    result = service.get_repeat_offenders_resolved(
        min_cases=2,
        confidence_threshold=0.70,
    )

    assert result["min_cases_threshold"] == 2
    assert result["confidence_threshold"] == 0.70

    assert "offender_count" in result
    assert "offenders" in result

    if result["offender_count"] > 0:
        offender = result["offenders"][0]

        assert "canonical_person_name" in offender
        assert "person_ids" in offender
        assert "case_count" in offender
        assert "case_ids" in offender
        assert "reason" in offender