"""
graph/services/hotspot_service.py

Unified hotspot detection: combines temporal, spatial, and network anomalies
into dashboard-ready JSON.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.core.graph.algorithms.pattern_detection import (
    detect_dependency_hotspots,
    detect_district_hotspots,
    detect_high_workload_officers,
    detect_repeat_accused,
    detect_repeat_address,
    detect_repeat_phone,
    detect_repeat_vehicle,
    detect_temporal_hotspots,
)
from backend.app.core.graph.algorithms.pattern_rules import (
    _extract_edge_evidence_ids,
    _extract_node_evidence_ids,
)
from backend.app.core.graph.algorithms.utils import iter_nodes_by_type, prop_str
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.offender_service import OffenderService
from backend.app.core.graph.services.serializers import serialize_dataclass



class HotspotService:
    """
    Combines multiple pattern detectors into unified hotspot reports.
    
    This is what the Dashboard and District Rollup screens call.
    """

    def __init__(self, repository: GraphRepository, offender_service: OffenderService | None = None) -> None:
        self._repo = repository
        self._offender_service = offender_service

    # ═══════════════════════════════════════════════════════════════════════
    # ADVANCED HOTSPOT INTELLIGENCE & COMBINED SIGNALS
    # ═══════════════════════════════════════════════════════════════════════

    def get_district_intelligence_hotspots(self) -> list[dict[str, Any]]:
        """
        Compute high-signal District Crime Hotspots with dynamic baseline multiplier,
        dominant categories, cross-case network links, repeat offender overlap,
        and evidence provenance citations.
        """
        store = self._repo.store
        district_cases: dict[str, list[Any]] = {}
        total_cases = 0
        for node in iter_nodes_by_type(store, "Case"):
            total_cases += 1
            district = prop_str(node, "district", default="Unknown District")
            district_cases.setdefault(district, []).append(node)

        num_districts = max(1, len(district_cases))
        baseline_cases = round(total_cases / num_districts, 1) if num_districts > 0 else 1.0

        offender_svc = self._offender_service or OffenderService(self._repo)
        repeat_offenders_data = offender_svc.get_repeat_offender_radar(min_cases=2)

        hotspots: list[dict[str, Any]] = []
        for district, cases in district_cases.items():
            case_count = len(cases)
            concentration_multiplier = round(case_count / baseline_cases, 1) if baseline_cases > 0 else 1.0

            # Dominant categories
            category_counts: dict[str, int] = {}
            for c in cases:
                cat = prop_str(c, "crime_head") or prop_str(c, "crime_category") or prop_str(c, "category") or "General"
                category_counts[cat] = category_counts.get(cat, 0) + 1

            dominant_categories = [
                {
                    "category": cat,
                    "count": count,
                    "percentage": round((count / case_count) * 100.0, 1) if case_count > 0 else 0.0,
                }
                for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ]

            dist_case_ids = {c.node_id for c in cases}

            # Repeat offender overlap
            overlap_offender_ids: list[str] = []
            overlap_offender_names: list[str] = []
            for off in repeat_offenders_data:
                off_cases = set(off.get("case_ids", []))
                if off_cases & dist_case_ids:
                    overlap_offender_ids.append(off.get("person_id", ""))
                    overlap_offender_names.append(off.get("canonical_name", ""))

            # Cross-case network links
            dist_entities = set(dist_case_ids)
            for cid in dist_case_ids:
                for edge in store.adj.get(cid, []):
                    dist_entities.add(edge.target_id)
                for edge in store.radj.get(cid, []):
                    dist_entities.add(edge.source_id)

            cross_case_edges: set[tuple[str, str, str]] = set()
            for ent in dist_entities:
                for edge in store.adj.get(ent, []):
                    if edge.target_id not in dist_entities or (edge.edge_type in ("ACCUSED_IN", "TRANSFERRED_TO", "COMMUNICATED_WITH") and edge.target_id not in dist_case_ids):
                        cross_case_edges.add((edge.source_id, edge.edge_type, edge.target_id))

            cross_links_count = len(cross_case_edges)

            # Evidence IDs
            evidence_ids: set[str] = set()
            for cid in dist_case_ids:
                cnode = store.nodes.get(cid)
                if cnode:
                    evidence_ids.update(_extract_node_evidence_ids(cnode, store))
                for edge in store.adj.get(cid, []):
                    evidence_ids.update(_extract_edge_evidence_ids(edge, store))
            for ent_id in dist_entities:
                enode = store.nodes.get(ent_id)
                if enode:
                    evidence_ids.update(_extract_node_evidence_ids(enode, store))

            alert_level = "RED" if (concentration_multiplier >= 1.5 or len(overlap_offender_ids) >= 2) else "AMBER" if concentration_multiplier >= 1.0 else "GREEN"

            summary_reason = (
                f"District '{district}' has {case_count} cases ({concentration_multiplier}x baseline of {baseline_cases}) "
                f"with {len(overlap_offender_ids)} repeat offenders and {cross_links_count} cross-case network links."
            )

            hotspots.append({
                "district": district,
                "case_count": case_count,
                "baseline_cases": baseline_cases,
                "concentration_multiplier": concentration_multiplier,
                "dominant_categories": dominant_categories,
                "cross_case_links_count": cross_links_count,
                "repeat_offender_overlap_count": len(overlap_offender_ids),
                "repeat_offender_ids": overlap_offender_ids,
                "repeat_offender_names": overlap_offender_names,
                "evidence_backed": True,
                "evidence_ids": sorted(list(evidence_ids)),
                "alert_level": alert_level,
                "summary_reason": summary_reason,
            })

        hotspots.sort(key=lambda h: (-h["concentration_multiplier"], -h["case_count"], h["district"]))
        return hotspots

    def get_district_drilldown(self, district: str) -> dict[str, Any]:
        """
        Deep-dive inspection payload for a single district: cases, accused entities,
        repeat offenders, cross-case links, and backing forensic evidence.
        """
        store = self._repo.store
        district_cases: list[Any] = []
        all_districts: set[str] = set()
        total_cases = 0

        for node in iter_nodes_by_type(store, "Case"):
            total_cases += 1
            d = prop_str(node, "district", default="Unknown District")
            all_districts.add(d)
            if d.lower() == district.lower() or d == district:
                district_cases.append(node)

        baseline = round(total_cases / max(1, len(all_districts)), 1) if all_districts else 1.0
        case_count = len(district_cases)
        multiplier = round(case_count / baseline, 1) if baseline > 0 else 1.0

        case_items: list[dict[str, Any]] = []
        case_ids: set[str] = set()

        for c in district_cases:
            cid = c.node_id
            case_ids.add(cid)
            sections: list[str] = []
            for edge in store.adj.get(cid, []):
                if edge.edge_type == "CHARGED_UNDER":
                    sec_node = store.nodes.get(edge.target_id)
                    sections.append(prop_str(sec_node, "section_number", default=edge.target_id))

            accused_count = sum(1 for e in store.radj.get(cid, []) if e.edge_type == "ACCUSED_IN")

            case_items.append({
                "case_id": cid,
                "fir_number": prop_str(c, "fir_number", default=cid),
                "title": prop_str(c, "title") or prop_str(c, "case_name") or f"Case {cid}",
                "date": prop_str(c, "reported_at") or prop_str(c, "incident_date") or "",
                "crime_head": prop_str(c, "crime_head") or prop_str(c, "crime_category") or "General",
                "police_station": prop_str(c, "police_station", default="Station HQ"),
                "sections": sorted(sections),
                "accused_count": accused_count,
            })

        entity_items: list[dict[str, Any]] = []
        seen_entities: set[str] = set()
        for cid in case_ids:
            for edge in store.radj.get(cid, []):
                src_node = store.nodes.get(edge.source_id)
                if src_node and src_node.node_id not in seen_entities:
                    seen_entities.add(src_node.node_id)
                    ent_case_count = sum(1 for e in store.adj.get(src_node.node_id, []) if e.edge_type == "ACCUSED_IN")
                    entity_items.append({
                        "entity_id": src_node.node_id,
                        "name": prop_str(src_node, "full_name") or prop_str(src_node, "label") or src_node.node_id,
                        "entity_type": src_node.entity_type,
                        "case_count": ent_case_count,
                        "role": edge.edge_type if edge.edge_type else "Accused",
                    })

        offender_svc = self._offender_service or OffenderService(self._repo)
        repeat_offenders_data = offender_svc.get_repeat_offender_radar(min_cases=2)
        district_repeat_offenders = [
            off for off in repeat_offenders_data
            if any(cid in case_ids for cid in off.get("case_ids", []))
        ]

        cross_links: list[dict[str, Any]] = []
        seen_edge_keys: set[tuple[str, str, str]] = set()
        for cid in case_ids:
            for edge in store.adj.get(cid, []):
                edge_key = (edge.source_id, edge.edge_type, edge.target_id)
                if edge_key not in seen_edge_keys:
                    seen_edge_keys.add(edge_key)
                    cross_links.append({
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "edge_type": edge.edge_type,
                        "case_ids": [cid],
                    })

        evidence_items: list[dict[str, Any]] = []
        evidence_ids: set[str] = set()
        for c in district_cases:
            cid = c.node_id
            for eid in _extract_node_evidence_ids(c, store):
                evidence_ids.add(eid)
                evidence_items.append({
                    "evidence_id": eid,
                    "source_type": "FIR_RECORD",
                    "description": f"Source document for FIR {prop_str(c, 'fir_number', default=cid)}",
                    "case_id": cid,
                })
            for edge in store.adj.get(cid, []):
                for eid in _extract_edge_evidence_ids(edge, store):
                    evidence_ids.add(eid)
                    evidence_items.append({
                        "evidence_id": eid,
                        "source_type": "RELATIONSHIP_RECORD",
                        "description": f"Forensic record backing edge {edge.edge_type}",
                        "case_id": cid,
                    })

        return {
            "district": district,
            "case_count": case_count,
            "baseline_cases": baseline,
            "concentration_multiplier": multiplier,
            "cases": case_items,
            "entities": entity_items,
            "repeat_offenders": district_repeat_offenders,
            "cross_case_links": cross_links,
            "evidence_ids": sorted(list(evidence_ids)),
            "evidence": evidence_items,
        }

    def get_combined_bridge_signals(self) -> list[dict[str, Any]]:
        """
        Detect combined Hotspot ↔ Repeat Offender Overlap and Cross-District Syndicate Bridges.
        Surfaces network signals connecting District X ↔ District Y via mobile repeat offenders.
        """
        hotspots = self.get_district_intelligence_hotspots()
        offender_svc = self._offender_service or OffenderService(self._repo)
        repeat_offenders_data = offender_svc.get_repeat_offender_radar(min_cases=2)
        store = self._repo.store

        signals: list[dict[str, Any]] = []
        for h in hotspots:
            dist = h["district"]
            dist_cases = h["case_count"]

            bridging_details: list[dict[str, Any]] = []
            connected_districts_map: dict[str, list[str]] = {}
            all_bridge_evidence = set(h.get("evidence_ids", []))

            for off in repeat_offenders_data:
                off_districts = off.get("districts", [])
                if dist in off_districts:
                    other_districts = [d for d in off_districts if d != dist]
                    if other_districts:
                        bridging_details.append({
                            "person_id": off["person_id"],
                            "name": off["canonical_name"],
                            "home_district": dist,
                            "external_districts": other_districts,
                            "case_ids": off["case_ids"],
                            "case_count": off["case_count"],
                        })
                        for od in other_districts:
                            connected_districts_map.setdefault(od, []).append(off["canonical_name"])
                        all_bridge_evidence.update(off.get("evidence_ids", []))

            if bridging_details:
                connected_districts_info = [
                    {
                        "district": od,
                        "bridging_offenders": sorted(list(set(suspects))),
                        "case_count": sum(1 for c in store.nodes.values() if c.entity_type == "Case" and prop_str(c, "district") == od),
                    }
                    for od, suspects in sorted(connected_districts_map.items())
                ]

                ext_dists_str = ", ".join(sorted(connected_districts_map.keys()))
                explanation = (
                    f"Crime hotspot: District '{dist}' ({dist_cases} cases). "
                    f"{len(h['repeat_offender_ids'])} resolved repeat offenders are associated with this area. "
                    f"{len(bridging_details)} of those offenders also connect to cases in {ext_dists_str}. "
                    f"Cross-case bridge detected."
                )

                clean_slug = re.sub(r'[^a-zA-Z0-9]', '-', dist.lower()).strip('-')
                sig_id = f"sig-bridge-{clean_slug}"
                signals.append({
                    "signal_id": sig_id,
                    "primary_district": dist,
                    "primary_district_cases": dist_cases,
                    "repeat_offender_count": len(h["repeat_offender_ids"]),
                    "connected_districts": connected_districts_info,
                    "cross_district_bridge_detected": True,
                    "bridging_offender_details": bridging_details,
                    "evidence_ids": sorted(list(all_bridge_evidence)),
                    "alert_title": "RED FLAG — Cross-District Criminal Network Bridge",
                    "explanation": explanation,
                })

        return signals


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