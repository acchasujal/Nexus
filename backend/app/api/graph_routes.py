"""
api/graph_routes.py

FastAPI routers for all graph intelligence endpoints.
Dev 1 imports these into main.py.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.graph_service import GraphService
from backend.app.core.graph.services.hotspot_service import HotspotService
from backend.app.core.graph.services.offender_service import OffenderService
from backend.app.api.graph_models import (
    GraphNetworkResponse,
    PersonNetworkResponse,
    CoAccusedResponse,
    PathsBetweenResponse,
    SimilarCasesResponse,
    CaseCompareResponse,
    CrimeSummaryResponse,
    DimensionCountsResponse,
    OfficerWorkloadResponse,
    MasterHotspotsResponse,
    TemporalHotspotsResponse,
    DependencyHotspotsResponse,
    WorkloadHotspotsResponse,
    NetworkHotspotsResponse,
    DistrictHotspotsResponse,
    RepeatOffendersResponse,
    OffenderProfileResponse,
    GraphStatsResponse,
    ConnectedComponentsResponse,
    CentralityResponse,
)


# ── Router factory (Dev 1 calls this with the repo instance) ─────────────

def create_graph_router(repository: GraphRepository) -> APIRouter:
    """
    Factory function — Dev 1 creates the router with the shared repository.
    
    Usage in main.py:
        from backend.app.core.graph.repositories.graph_repository import GraphRepository
        from backend.app.api.graph_routes import create_graph_router
        
        repo = GraphRepository()  # or injected
        app.include_router(create_graph_router(repo), prefix="/api/v1")
    """
    router = APIRouter(prefix="/graph", tags=["graph-intelligence"])

    graph_svc = GraphService(repository)
    hotspot_svc = HotspotService(repository)
    offender_svc = OffenderService(repository)

    # ═════════════════════════════════════════════════
    @router.get("/cases/{case_id}/network", response_model=GraphNetworkResponse)
    def case_network(
        case_id: str,
        depth: int = Query(2, ge=1, le=4, description="BFS depth for neighborhood"),
    ) -> Any:
        """Get the network graph around a specific case."""
        return graph_svc.get_case_network(case_id, depth=depth)

    @router.get("/persons/{person_id}/network", response_model=PersonNetworkResponse)
    def person_network(
        person_id: str,
        depth: int = Query(2, ge=1, le=4),
    ) -> Any:
        """Get the network graph around a specific person."""
        return graph_svc.get_person_network(person_id, depth=depth)

    @router.get("/persons/{person_id}/co-accused", response_model=CoAccusedResponse)
    def co_accused(person_id: str) -> Any:
        """Get all co-accused for a person."""
        return graph_svc.get_co_accused_network(person_id)

    @router.get("/paths", response_model=PathsBetweenResponse)
    def paths_between(
        source_id: str,
        target_id: str,
        max_depth: int = Query(4, ge=1, le=6),
    ) -> Any:
        """Find connection paths between two nodes."""
        return graph_svc.find_paths_between(source_id, target_id, max_depth=max_depth)

    # ═══════════════════════════════════════════════════════════════════════
    # SIMILARITY ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════

    @router.get("/cases/{case_id}/similar", response_model=SimilarCasesResponse)
    def similar_cases(
        case_id: str,
        top_k: int = Query(10, ge=1, le=50),
        min_score: float = Query(0.1, ge=0.0, le=1.0),
    ) -> Any:
        """Find cases similar to the given case."""
        return graph_svc.get_similar_cases(case_id, top_k=top_k, min_score=min_score)

    @router.get("/cases/compare", response_model=CaseCompareResponse)
    def compare_cases(case_a_id: str, case_b_id: str) -> Any:
        """Compare two cases directly."""
        return graph_svc.compare_two_cases(case_a_id, case_b_id)

    # ═══════════════════════════════════════════════════════════════════════
    # AGGREGATION ENDPOINTS (Dashboard Data)
    # ═══════════════════════════════════════════════════════════════════════

    @router.get("/dashboard/summary", response_model=CrimeSummaryResponse)
    def dashboard_summary() -> Any:
        """High-level crime statistics for dashboard cards."""
        return graph_svc.get_crime_summary()

    @router.get("/dashboard/by-district", response_model=DimensionCountsResponse)
    def by_district() -> Any:
        """Crime counts grouped by district."""
        return graph_svc.get_crime_by_district()

    @router.get("/dashboard/by-station", response_model=DimensionCountsResponse)
    def by_station() -> Any:
        """Crime counts grouped by police station."""
        return graph_svc.get_crime_by_station()

    @router.get("/dashboard/by-crime-head", response_model=DimensionCountsResponse)
    def by_crime_head() -> Any:
        """Crime counts grouped by crime head."""
        return graph_svc.get_crime_by_crime_head()

    @router.get("/dashboard/officer-workload", response_model=OfficerWorkloadResponse)
    def officer_workload() -> Any:
        """Case load per investigating officer."""
        return graph_svc.get_officer_workload()

    # ═══════════════════════════════════════════════════════════════════════
    # HOTSPOT ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════

    @router.get("/hotspots", response_model=MasterHotspotsResponse)
    def all_hotspots() -> Any:
        """Complete hotspot report for main dashboard."""
        return hotspot_svc.get_all_hotspots()

    @router.get("/hotspots/temporal", response_model=TemporalHotspotsResponse)
    def temporal_hotspots() -> Any:
        """Time-based crime spikes."""
        return hotspot_svc.get_temporal_hotspots()

    @router.get("/hotspots/dependency", response_model=DependencyHotspotsResponse)
    def dependency_hotspots() -> Any:
        """Cases blocked by pending dependencies."""
        return hotspot_svc.get_dependency_hotspots()

    @router.get("/hotspots/workload", response_model=WorkloadHotspotsResponse)
    def workload_hotspots() -> Any:
        """Officers with excessive case loads."""
        return hotspot_svc.get_workload_hotspots()

    @router.get("/hotspots/network", response_model=NetworkHotspotsResponse)
    def network_hotspots() -> Any:
        """Criminal network anomalies."""
        return hotspot_svc.get_network_hotspots()

    @router.get("/hotspots/district/{district}", response_model=DistrictHotspotsResponse)
    def district_hotspots(district: str) -> Any:
        """Hotspots filtered to a specific district."""
        return hotspot_svc.get_district_hotspots(district)

    # ═══════════════════════════════════════════════════════════════════════
    # OFFENDER ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════

    @router.get("/offenders/repeat", response_model=RepeatOffendersResponse)
    def repeat_offenders(
        min_cases: int = Query(2, ge=2, le=10),
        top_k: int = Query(50, ge=1, le=200),
    ) -> Any:
        """List repeat offenders with case histories."""
        return offender_svc.get_repeat_offenders(min_cases=min_cases, top_k=top_k)

    @router.get("/offenders/{person_id}/profile", response_model=OffenderProfileResponse)
    def offender_profile(person_id: str) -> Any:
        """Detailed factual profile for a person."""
        result = offender_svc.get_offender_profile(person_id)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    # ═══════════════════════════════════════════════════════════════════════
    # GRAPH HEALTH ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════

    @router.get("/stats", response_model=GraphStatsResponse)
    def graph_stats() -> Any:
        """Overall graph statistics."""
        return graph_svc.get_graph_stats()

    @router.get("/components", response_model=ConnectedComponentsResponse)
    def connected_components() -> Any:
        """Disconnected network components."""
        return graph_svc.get_connected_components()

    @router.get("/centrality", response_model=CentralityResponse)
    def centrality(top_k: int = Query(20, ge=1, le=100)) -> Any:
        """Most central figures in the criminal network."""
        return graph_svc.get_central_figures(top_k=top_k)

    return router