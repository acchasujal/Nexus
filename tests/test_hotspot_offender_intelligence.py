"""tests/test_hotspot_offender_intelligence.py

Automated tests for NEXUS Crime Hotspots, Repeat Offender Radar,
District Drilldown, and Combined Cross-District Bridge Signals.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.hotspot_service import HotspotService
from backend.app.core.graph.services.offender_service import OffenderService
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app


@pytest.fixture
def repo() -> InMemoryBackendRepository:
    return InMemoryBackendRepository()


@pytest.fixture
def graph_repo(repo: InMemoryBackendRepository) -> GraphRepository:
    return GraphRepository(repo.to_graph_store())


@pytest.fixture
def offender_service(graph_repo: GraphRepository) -> OffenderService:
    return OffenderService(graph_repo)


@pytest.fixture
def hotspot_service(graph_repo: GraphRepository, offender_service: OffenderService) -> HotspotService:
    return HotspotService(graph_repo, offender_service=offender_service)


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


# ── Hotspot Intelligence Service Tests ────────────────────────────────────────

def test_hotspot_intelligence_metrics(hotspot_service: HotspotService):
    hotspots = hotspot_service.get_district_intelligence_hotspots()
    assert isinstance(hotspots, list)
    assert len(hotspots) > 0

    top_hotspot = hotspots[0]
    assert "district" in top_hotspot
    assert "case_count" in top_hotspot
    assert top_hotspot["case_count"] > 0
    assert "baseline_cases" in top_hotspot
    assert top_hotspot["baseline_cases"] > 0
    assert "concentration_multiplier" in top_hotspot
    assert top_hotspot["concentration_multiplier"] > 0
    assert "dominant_categories" in top_hotspot
    assert isinstance(top_hotspot["dominant_categories"], list)
    assert "cross_case_links_count" in top_hotspot
    assert "repeat_offender_overlap_count" in top_hotspot
    assert "repeat_offender_ids" in top_hotspot
    assert "evidence_backed" in top_hotspot
    assert top_hotspot["evidence_backed"] is True
    assert top_hotspot["alert_level"] in ("RED", "AMBER", "GREEN")
    assert "summary_reason" in top_hotspot
    assert "baseline" in top_hotspot["summary_reason"].lower() or "cases" in top_hotspot["summary_reason"].lower()


def test_hotspot_drilldown_valid_district(hotspot_service: HotspotService):
    hotspots = hotspot_service.get_district_intelligence_hotspots()
    assert len(hotspots) > 0
    district_name = hotspots[0]["district"]

    drilldown = hotspot_service.get_district_drilldown(district_name)
    assert drilldown["district"] == district_name
    assert drilldown["case_count"] > 0
    assert len(drilldown["cases"]) > 0
    first_case = drilldown["cases"][0]
    assert "case_id" in first_case
    assert "fir_number" in first_case
    assert "crime_head" in first_case
    assert "police_station" in first_case
    assert isinstance(first_case["sections"], list)
    assert isinstance(drilldown["entities"], list)
    assert isinstance(drilldown["repeat_offenders"], list)
    assert isinstance(drilldown["cross_case_links"], list)
    assert isinstance(drilldown["evidence"], list)


# ── Repeat Offender Radar Service Tests ───────────────────────────────────────

def test_repeat_offender_radar_structure(offender_service: OffenderService):
    radar_items = offender_service.get_repeat_offender_radar(min_cases=1)
    assert isinstance(radar_items, list)
    assert len(radar_items) > 0

    item = radar_items[0]
    assert "person_id" in item
    assert "canonical_name" in item
    assert "aliases" in item
    assert isinstance(item["aliases"], list)
    assert "case_count" in item
    assert item["case_count"] >= 1
    assert "case_ids" in item
    assert "fir_numbers" in item
    assert "districts" in item
    assert "district_count" in item
    assert item["district_count"] == len(item["districts"])
    assert "shared_network_entities" in item
    assert "shared_phone_identifiers" in item
    assert "why_surfaced" in item
    assert item["why_surfaced"] == "Deterministic repeat-case + entity-resolution evidence."
    assert "compliance_status" in item
    assert item["compliance_status"] == "Investigative lead — not a finding of guilt."


def test_offender_radar_profile_lookup(offender_service: OffenderService):
    radar_items = offender_service.get_repeat_offender_radar(min_cases=1)
    target_person_id = radar_items[0]["person_id"]

    profile = offender_service.get_offender_radar_profile(target_person_id)
    assert profile is not None
    assert profile["person_id"] == target_person_id
    assert profile["compliance_status"] == "Investigative lead — not a finding of guilt."

    unknown = offender_service.get_offender_radar_profile("non_existent_person_9999")
    assert unknown is None


# ── Combined Cross-District Bridge Tests ──────────────────────────────────────

def test_combined_bridge_signals_structure(hotspot_service: HotspotService):
    signals = hotspot_service.get_combined_bridge_signals()
    assert isinstance(signals, list)

    for s in signals:
        assert "signal_id" in s
        assert "primary_district" in s
        assert "primary_district_cases" in s
        assert "repeat_offender_count" in s
        assert "connected_districts" in s
        assert "cross_district_bridge_detected" in s
        assert s["cross_district_bridge_detected"] is True
        assert "bridging_offender_details" in s
        assert len(s["bridging_offender_details"]) > 0
        assert "alert_title" in s
        assert "RED FLAG" in s["alert_title"]
        assert "explanation" in s
        assert "Cross-case bridge detected" in s["explanation"]


# ── REST API Integration Tests ────────────────────────────────────────────────

def test_api_get_district_hotspots(client: TestClient):
    response = client.get("/api/v1/nexus/intelligence/hotspots")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "concentration_multiplier" in data[0]
    assert data[0]["evidence_backed"] is True


def test_api_get_district_drilldown(client: TestClient):
    # First get a valid district
    hotspots_res = client.get("/api/v1/nexus/intelligence/hotspots")
    assert hotspots_res.status_code == 200
    district = hotspots_res.json()[0]["district"]

    response = client.get(f"/api/v1/nexus/intelligence/hotspots/{district}")
    assert response.status_code == 200
    data = response.json()
    assert data["district"] == district
    assert "cases" in data
    assert "entities" in data
    assert "evidence" in data


def test_api_get_district_drilldown_not_found(client: TestClient):
    response = client.get("/api/v1/nexus/intelligence/hotspots/NonExistentDistrictXYZ123")
    assert response.status_code == 404


def test_api_get_repeat_offenders_radar(client: TestClient):
    response = client.get("/api/v1/nexus/intelligence/offenders?min_cases=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["compliance_status"] == "Investigative lead — not a finding of guilt."


def test_api_get_repeat_offender_radar_profile(client: TestClient):
    offenders_res = client.get("/api/v1/nexus/intelligence/offenders?min_cases=1")
    assert offenders_res.status_code == 200
    person_id = offenders_res.json()[0]["person_id"]

    response = client.get(f"/api/v1/nexus/intelligence/offenders/{person_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["person_id"] == person_id
    assert "canonical_name" in data


def test_api_get_combined_bridge_signals(client: TestClient):
    response = client.get("/api/v1/nexus/intelligence/combined")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
