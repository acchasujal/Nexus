from types import SimpleNamespace

import pytest

from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services import graph_service as graph_service_module
from backend.app.core.graph.services.graph_service import GraphService

from helpers import make_case, make_store


def test_similar_cases_maps_internal_result_to_public_contract(monkeypatch: pytest.MonkeyPatch):
    anchor = make_case()
    other = make_case()
    service = GraphService(GraphRepository(make_store([anchor, other], [])))
    raw = SimpleNamespace(
        case_a_id=other.id,
        case_b_id=anchor.id,
        score=0.75,
        matched_features=["shared_district"],
        feature_contributions={"shared_district": 0.05},
    )
    monkeypatch.setattr(graph_service_module, "find_similar_cases", lambda *args, **kwargs: [raw])

    response = service.get_similar_cases(anchor.id)

    assert response["matches"] == [{
        "case_id": other.id,
        "score": 0.75,
        "reasons": ["shared_district"],
        "properties": {"shared_district": 0.05},
    }]


def test_similar_cases_rejects_result_unrelated_to_requested_case(monkeypatch: pytest.MonkeyPatch):
    anchor, unrelated_a, unrelated_b = make_case(), make_case(), make_case()
    service = GraphService(GraphRepository(make_store([anchor, unrelated_a, unrelated_b], [])))
    raw = SimpleNamespace(
        case_a_id=unrelated_a.id,
        case_b_id=unrelated_b.id,
        score=0.75,
        matched_features=[],
        feature_contributions={},
    )
    monkeypatch.setattr(graph_service_module, "find_similar_cases", lambda *args, **kwargs: [raw])

    with pytest.raises(ValueError, match="exactly one endpoint"):
        service.get_similar_cases(anchor.id)
