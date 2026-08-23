"""
graph/services/hotspot_service.py

Unified hotspot detection: combines temporal, spatial, and network anomalies
into dashboard-ready JSON.
"""

from __future__ import annotations

from typing import Any

from backend.app.core.graph.algorithms.pattern_detection import (
    detect_repeat_accused,
    detect_repeat_phone,
    detect_repeat_vehicle,
    detect_repeat_address,
    detect_high_workload_officers,
    detect_dependency_hotspots,
    detect_district_hotspots,
    detect_temporal_hotspots,
)
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.serializers import serialize_dataclass


class HotspotService:
    """
    Combines multiple pattern detectors into unified hotspot reports.
    
    This is what the Dashboard and District Rollup screens call.
    """

    def __init__(self, repository: GraphRepository) -> None:
        self._repo = repository

    # ═══════════════════════════════════════════════════════════════════════
    # MASTER HOTSPOT REPORT
    # ═══════════════════════════════════════════════════════════════════════

    def get_all_hotspots(self) -> dict[str, Any]:
        """
        Complete hotspot report — single API call for the main dashboard.
        
        Returns everything the frontend needs to render alert cards,
        maps, and tables.
        """
        return {
            "generated_at": _now_iso(),
            "summary": self._get_summary_counts(),
            "temporal": self.get_temporal_hotspots(),
            "dependency": self.get_dependency_hotspots(),
            "workload": self.get_workload_hotspots(),
            "network": self.get_network_hotspots(),
            "district": self.get_district_crime_hotspots(),
        }

    # ═══════════════════════════════════════════════════════════════════════
    # INDIVIDUAL HOTSPOT CATEGORIES
    # ═══════════════════════════════════════════════════════════════════════

    def get_district_crime_hotspots(self, min_cases: int = 50) -> dict[str, Any]:
        """
        Districts with a disproportionately high case count.

        Used by: Map layer / District drill-down → "Crime Hotspot" heat overlay
        """
        store = self._repo.store
        hotspots = detect_district_hotspots(store, min_cases=min_cases)

        return {
            "category": "district",
            "alert_level": "red" if len(hotspots) > 5 else "amber" if hotspots else "green",
            "hotspots": [serialize_dataclass(h) for h in hotspots],
            "hotspot_count": len(hotspots),
        }

    def get_temporal_hotspots(self, min_cases: int = 3) -> dict[str, Any]:
        """
        Time-based crime spikes.

        Used by: Dashboard → "Temporal Hotspots"
        """
        store = self._repo.store
        spikes = detect_temporal_hotspots(store, min_cases=min_cases)
        spike_count = len(spikes)

        if spike_count > 10:
            alert_level = "red"
        elif spike_count > 0:
            alert_level = "amber"
        else:
            alert_level = "green"

        return {
            "category": "temporal",
            "alert_level": alert_level,
            "spikes": [serialize_dataclass(s) for s in spikes],
            "spike_count": spike_count,
        }

    def get_dependency_hotspots(self) -> dict[str, Any]:
        """
        Cases with many pending dependencies (investigation blockers).
        
        Used by: Escalation Queue → "Blocked Investigations"
        """
        store = self._repo.store
        hotspots = detect_dependency_hotspots(store, min_pending=3)

        return {
            "category": "dependency",
            "alert_level": "red" if len(hotspots) > 5 else "amber" if hotspots else "green",
            "hotspots": [serialize_dataclass(h) for h in hotspots],
            "hotspot_count": len(hotspots),
            "total_pending_dependencies": sum(h.pending_count for h in hotspots),
        }

    def get_workload_hotspots(self) -> dict[str, Any]:
        """
        Officers with excessive case loads.
        
        Used by: Supervisor Dashboard → Resource deployment
        """
        store = self._repo.store
        officers = detect_high_workload_officers(store, min_cases=5)

        return {
            "category": "workload",
            "alert_level": "red" if len(officers) > 10 else "amber" if officers else "green",
            "officers": [serialize_dataclass(o) for o in officers],
            "officer_count": len(officers),
        }

    def get_network_hotspots(self) -> dict[str, Any]:
        """
        Criminal network anomalies: repeat offenders, shared phones/vehicles/addresses.
        
        Used by: Network Analysis → "Suspicious Clusters"
        """
        store = self._repo.store

        repeat_offenders = detect_repeat_accused(store, min_cases=2)
        phone_clusters = detect_repeat_phone(store, min_persons=2)
        vehicle_clusters = detect_repeat_vehicle(store, min_persons=2)
        address_clusters = detect_repeat_address(store, min_persons=2)

        # Calculate composite alert level
        total_network_flags = (
            len(repeat_offenders) + len(phone_clusters) +
            len(vehicle_clusters) + len(address_clusters)
        )

        return {
            "category": "network",
            "alert_level": "red" if total_network_flags > 10 else "amber" if total_network_flags > 0 else "green",
            "repeat_offenders": {
                "count": len(repeat_offenders),
                "persons": [serialize_dataclass(r) for r in repeat_offenders[:20]],
            },
            "shared_phone_clusters": {
                "count": len(phone_clusters),
                "clusters": [serialize_dataclass(c) for c in phone_clusters[:10]],
            },
            "shared_vehicle_clusters": {
                "count": len(vehicle_clusters),
                "clusters": [serialize_dataclass(c) for c in vehicle_clusters[:10]],
            },
            "shared_address_clusters": {
                "count": len(address_clusters),
                "clusters": [serialize_dataclass(c) for c in address_clusters[:10]],
            },
            "total_network_flags": total_network_flags,
        }

    # ═══════════════════════════════════════════════════════════════════════
    # DISTRICT-SPECIFIC HOTSPOTS (for Map Drill-down)
    # ═══════════════════════════════════════════════════════════════════════

    def get_district_hotspots(self, district: str) -> dict[str, Any]:
        """
        Filter all hotspots to a specific district.
        
        Used by: Map → District click → District detail panel
        """
        # Get base data
        all_temporal = self.get_temporal_hotspots()
        all_deps = self.get_dependency_hotspots()

        # Filter by district (check case node properties)
        store = self._repo.store

        def _case_in_district(case_id: str) -> bool:
            node = store.nodes.get(case_id)
            if not node:
                return False
            return node.properties.get("district") == district

        # Filter temporal spikes to district
        district_spikes = [
            s for s in all_temporal["spikes"]
            if _case_in_district(s.get("case_id", ""))
        ]

        # Filter dependency hotspots to district
        district_deps = [
            h for h in all_deps["hotspots"]
            if _case_in_district(h.get("case_id", ""))
        ]

        return {
            "district": district,
            "temporal_spikes": district_spikes,
            "dependency_hotspots": district_deps,
            "alert_summary": {
                "temporal": len(district_spikes),
                "dependency": len(district_deps),
            },
        }

    # ── Internal helpers ───────────────────────────────────────────────────

    def _get_summary_counts(self) -> dict[str, int]:
        """Quick counts for the dashboard header."""
        store = self._repo.store
        from backend.app.core.graph.algorithms.utils import iter_nodes_by_type

        total_cases = sum(1 for _ in iter_nodes_by_type(store, "Case"))
        total_persons = sum(1 for _ in iter_nodes_by_type(store, "Person"))
        total_officers = sum(1 for _ in iter_nodes_by_type(store, "Officer"))

        return {
            "total_cases": total_cases,
            "total_persons": total_persons,
            "total_officers": total_officers,
        }


def _now_iso() -> str:
    """Current timestamp in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()