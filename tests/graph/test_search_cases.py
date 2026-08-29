"""tests/graph/test_search_cases.py

Unit tests for GraphService.search_cases and GraphRepository.search_cases.
Verifies single filter, combined filter, case-insensitive normalized matching,
result capping (MAX_RESULTS=50), and empty store handling.
"""

from __future__ import annotations

import pytest

from backend.app.core.graph.algorithms.utils import GraphStore, NodeRecord
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.graph_service import (
    MAX_SEARCH_RESULTS,
    GraphService,
)


@pytest.fixture
def sample_graph_store() -> GraphStore:
    store = GraphStore()
    
    # Node 1: Vehicle Theft in Belagavi, Green risk
    store.nodes["c1"] = NodeRecord(
        node_id="c1",
        entity_type="Case",
        properties={
            "fir_number": "FIR/BEL/0001",
            "case_number": "CC-0001",
            "offence_category": "vehicle_theft",
            "district": "Belagavi",
            "police_station": "Belagavi North",
            "case_stage": "pending",
            "risk_band": "green",
            "reported_at": "2026-01-01T10:00:00Z",
        },
    )

    # Node 2: Cyber Fraud in Bengaluru, Amber risk
    store.nodes["c2"] = NodeRecord(
        node_id="c2",
        entity_type="Case",
        properties={
            "fir_number": "FIR/BEN/0002",
            "case_number": "CC-0002",
            "offence_category": "cyber_fraud",
            "district": "Bengaluru City",
            "police_station": "Jayanagar",
            "case_stage": "further_investigation",
            "risk_band": "amber",
            "reported_at": "2026-01-02T10:00:00Z",
        },
    )

    # Node 3: Murder in Mysuru, Red risk
    store.nodes["c3"] = NodeRecord(
        node_id="c3",
        entity_type="Case",
        properties={
            "fir_number": "FIR/MYS/0003",
            "case_number": "CC-0003",
            "offence_category": "murder",
            "district": "Mysuru",
            "police_station": "Mysuru South",
            "case_stage": "pending",
            "risk_band": "red",
            "reported_at": "2026-01-03T10:00:00Z",
        },
    )

    # Node 4: Simple Theft in Belagavi, Green risk
    store.nodes["c4"] = NodeRecord(
        node_id="c4",
        entity_type="Case",
        properties={
            "fir_number": "FIR/BEL/0004",
            "case_number": "CC-0004",
            "offence_category": "theft",
            "district": "Belagavi",
            "police_station": "Belagavi South",
            "case_stage": "chargesheeted",
            "risk_band": "green",
            "reported_at": "2026-01-04T10:00:00Z",
        },
    )

    # Person Node (should be ignored by search_cases)
    store.nodes["p1"] = NodeRecord(
        node_id="p1",
        entity_type="Person",
        properties={"full_name": "John Doe"},
    )

    return store


@pytest.fixture
def graph_service(sample_graph_store: GraphStore) -> GraphService:
    repo = GraphRepository(store=sample_graph_store)
    return GraphService(repository=repo)


def test_search_cases_by_single_offence_category(graph_service: GraphService) -> None:
    # "theft" should match both "vehicle_theft" (c1) and "theft" (c4) via normalized substring match
    res = graph_service.search_cases(offence_category="theft")
    assert res["count"] == 2
    assert res["returned"] == 2
    case_ids = {c["node_id"] for c in res["cases"]}
    assert case_ids == {"c1", "c4"}


def test_search_cases_by_exact_offence_category(graph_service: GraphService) -> None:
    res = graph_service.search_cases(offence_category="cyber_fraud")
    assert res["count"] == 1
    assert res["cases"][0]["node_id"] == "c2"


def test_search_cases_by_district(graph_service: GraphService) -> None:
    # "Bengaluru" should match "Bengaluru City"
    res = graph_service.search_cases(district="Bengaluru")
    assert res["count"] == 1
    assert res["cases"][0]["node_id"] == "c2"


def test_search_cases_by_district_empty_result(graph_service: GraphService) -> None:
    res = graph_service.search_cases(district="Unknown District")
    assert res["count"] == 0
    assert res["returned"] == 0
    assert res["cases"] == []


def test_search_cases_combined_filters(graph_service: GraphService) -> None:
    # Vehicle theft in Belagavi
    res = graph_service.search_cases(offence_category="vehicle_theft", district="Belagavi")
    assert res["count"] == 1
    assert res["cases"][0]["node_id"] == "c1"


def test_search_cases_by_risk_band(graph_service: GraphService) -> None:
    res = graph_service.search_cases(risk_band="green")
    assert res["count"] == 2
    case_ids = {c["node_id"] for c in res["cases"]}
    assert case_ids == {"c1", "c4"}


def test_search_cases_by_case_stage(graph_service: GraphService) -> None:
    res = graph_service.search_cases(case_stage="further investigation")
    assert res["count"] == 1
    assert res["cases"][0]["node_id"] == "c2"


def test_search_cases_no_filters_returns_all_cases(graph_service: GraphService) -> None:
    res = graph_service.search_cases()
    assert res["count"] == 4
    assert res["returned"] == 4


def test_search_cases_no_match(graph_service: GraphService) -> None:
    res = graph_service.search_cases(offence_category="narcotics")
    assert res["count"] == 0
    assert res["returned"] == 0
    assert res["cases"] == []


def test_search_cases_max_results_capping() -> None:
    store = GraphStore()
    # Create 60 cases
    for i in range(60):
        store.nodes[f"case_{i}"] = NodeRecord(
            node_id=f"case_{i}",
            entity_type="Case",
            properties={"offence_category": "theft", "district": "Bengaluru"},
        )
    repo = GraphRepository(store=store)
    service = GraphService(repository=repo)

    res = service.search_cases(offence_category="theft")
    assert res["count"] == 60
    assert res["returned"] == MAX_SEARCH_RESULTS
    assert len(res["cases"]) == 50
