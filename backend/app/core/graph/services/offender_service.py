"""
graph/services/offender_service.py

Repeat offender detection and profiling.
"""

from __future__ import annotations

from typing import Any

from backend.app.core.graph.algorithms.pattern_detection import (
    detect_repeat_accused,
    detect_repeat_accused_resolved,
)
from backend.app.core.graph.algorithms.pattern_rules import (
    _extract_edge_evidence_ids,
    _extract_node_evidence_ids,
)
from backend.app.core.graph.algorithms.traversals import get_co_accused
from backend.app.core.graph.algorithms.utils import get_edges_of_type, prop_str
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.serializers import serialize_node



class OffenderService:
    """
    Investigative lead generation: repeat offender signals.
    
    All outputs are templated from graph facts only — no generated prose
    about guilt or risk (per EXECUTION_RULES.md anti-hallucination rules).
    """

    def __init__(self, repository: GraphRepository) -> None:
        self._repo = repository

    def get_repeat_offenders(self, min_cases: int = 2, top_k: int = 50) -> dict[str, Any]:
        """
        List repeat offenders with their case histories.
        
        Used by: Intelligence → Repeat Offender Tracking
        """
        store = self._repo.store
        results = detect_repeat_accused(store, min_cases=min_cases)

        return {
            "min_cases_threshold": min_cases,
            "offender_count": len(results),
            "offenders": [
                {
                    "person_id": r.person_id,
                    "case_count": r.case_count,
                    "case_ids": r.case_ids,
                    "reason": r.reason,
                    "person": serialize_node(store.nodes.get(r.person_id)),
                }
                for r in results[:top_k]
            ],
        }

    def get_repeat_offenders_resolved(
        self,
        min_cases: int = 2,
        confidence_threshold: float = 0.70,
        top_k: int = 50,
    ) -> dict[str, Any]:
        """
        List repeat offenders using entity-resolution clustering.

        Groups Person nodes that represent the same individual across spelling
        variations and alias usage, then flags clusters with min_cases or more
        unique cases.

        Used by: Intelligence → Resolved Repeat Offender Tracking
        """
        store = self._repo.store
        results = detect_repeat_accused_resolved(
            store,
            min_cases=min_cases,
            confidence_threshold=confidence_threshold,
        )

        return {
            "min_cases_threshold": min_cases,
            "confidence_threshold": confidence_threshold,
            "offender_count": len(results),
            "offenders": [
                {
                    "canonical_person_name": r.canonical_person_name,
                    "person_ids": r.person_ids,
                    "case_count": r.case_count,
                    "case_ids": r.case_ids,
                    "reason": r.reason,
                }
                for r in results[:top_k]
            ],
        }

    def get_offender_profile(self, person_id: str) -> dict[str, Any]:
        """
        Detailed profile for a single person: cases, sections, MO signals.
        
        Output is strictly factual — "3 prior FIRs, sections 302, 304"
        never "high risk of reoffending."
        """
        store = self._repo.store
        person = store.nodes.get(person_id)

        if not person or person.entity_type != "Person":
            return {"error": "Person not found", "person_id": person_id}

        # Gather all cases this person is accused in
        case_ids: list[str] = []
        sections: set[str] = set()
        crime_heads: set[str] = set()
        police_stations: set[str] = set()
        districts: set[str] = set()
        fir_numbers: list[str] = []

        for edge in store.adj.get(person_id, []):
            if edge.edge_type != "ACCUSED_IN":
                continue
            case_id = edge.target_id
            case_ids.append(case_id)

            case = store.nodes.get(case_id)
            if not case:
                continue

            # Collect FIR number
            fir = prop_str(case, "fir_number")
            if fir:
                fir_numbers.append(fir)

            # Collect location
            ps = prop_str(case, "police_station")
            if ps:
                police_stations.add(ps)
            dist = prop_str(case, "district")
            if dist:
                districts.add(dist)

            # Collect sections via CHARGED_UNDER edges
            for e in store.adj.get(case_id, []):
                if e.edge_type == "CHARGED_UNDER":
                    sec = store.nodes.get(e.target_id)
                    if sec:
                        sections.add(prop_str(sec, "section_number") or e.target_id)

            # Collect crime heads via CASE_HAS_CRIME_HEAD edges
            for e in get_edges_of_type(store, "CASE_HAS_CRIME_HEAD"):
                if e.source_id == case_id:
                    head = store.nodes.get(e.target_id)
                    if head:
                        crime_heads.add(prop_str(head, "head_name") or e.target_id)

        # Get co-accused network
        co_accused_map: dict[str, list[str]] = {}
        for case_id in case_ids:
            accused = get_co_accused(store, case_id)
            for p in accused:
                if p.node_id == person_id:
                    continue
                co_accused_map.setdefault(p.node_id, []).append(case_id)

        return {
            "person_id": person_id,
            "person": serialize_node(person),
            "accused_in_count": len(case_ids),
            "case_ids": case_ids,
            "fir_numbers": fir_numbers,
            "section_diversity": {
                "unique_sections": sorted(list(sections)),
                "count": len(sections),
            },
            "crime_head_diversity": {
                "unique_crime_heads": sorted(list(crime_heads)),
                "count": len(crime_heads),
            },
            "jurisdiction_spread": {
                "police_stations": sorted(list(police_stations)),
                "districts": sorted(list(districts)),
                "station_count": len(police_stations),
                "district_count": len(districts),
            },
            "co_accused_count": len(co_accused_map),
            "co_accused": [
                {
                    "person_id": pid,
                    "shared_case_count": len(cases),
                }
                for pid, cases in co_accused_map.items()
            ],
            # Templated summary — no AI-generated prose
            "summary": self._generate_factual_summary(
                person_id=person_id,
                case_count=len(case_ids),
                sections=sections,
                stations=police_stations,
                co_accused_count=len(co_accused_map),
            ),
        }

    def _generate_factual_summary(self, person_id: str, case_count: int,
                                   sections: set[str], stations: set[str],
                                   co_accused_count: int) -> str:
        """
        Generate strictly factual summary string.
        Never implies guilt, risk, or prediction.
        """
        parts = [f"Person {person_id} appears as accused in {case_count} case(s)."]

        if sections:
            parts.append(f"Sections involved: {', '.join(sorted(sections))}.")

        if len(stations) > 1:
            parts.append(f"Cases span {len(stations)} police stations.")

        if co_accused_count > 0:
            parts.append(f"Linked to {co_accused_count} co-accused individual(s).")

        return " ".join(parts)

    def get_repeat_offender_radar(self, min_cases: int = 2, top_k: int = 50) -> list[dict[str, Any]]:
        """
        Produce high-signal Repeat Offender Radar records with resolved aliases,
        case history, district spread, shared phone/network entities, and evidence citations.
        Strictly factual and compliant with non-guilt constraints.
        """
        store = self._repo.store
        resolved_results = detect_repeat_accused_resolved(store, min_cases=min_cases)
        raw_repeat = detect_repeat_accused(store, min_cases=min_cases)

        seen_person_ids: set[str] = set()
        radar_items: list[dict[str, Any]] = []

        # 1. Process entity-resolved repeat accused clusters
        for r in resolved_results:
            cluster_pids = set(r.person_ids)
            seen_person_ids.update(cluster_pids)

            aliases: set[str] = set()
            phones: set[str] = set()
            evidence_ids: set[str] = set()

            for pid in cluster_pids:
                pnode = store.nodes.get(pid)
                if not pnode:
                    continue
                name = prop_str(pnode, "full_name") or prop_str(pnode, "label")
                if name and name != r.canonical_person_name:
                    aliases.add(name)
                node_aliases = pnode.properties.get("aliases", [])
                if isinstance(node_aliases, list):
                    for a in node_aliases:
                        if a and str(a) != r.canonical_person_name:
                            aliases.add(str(a))
                phone = prop_str(pnode, "phone_number")
                if phone:
                    phones.add(phone)
                for edge in store.adj.get(pid, []):
                    if edge.edge_type in ("USED_PHONE", "USES_PHONE", "HAS_PHONE"):
                        phone_node = store.nodes.get(edge.target_id)
                        p_num = prop_str(phone_node, "phone_number") or prop_str(phone_node, "label") or edge.target_id
                        phones.add(p_num)
                    evidence_ids.update(_extract_edge_evidence_ids(edge, store))
                evidence_ids.update(_extract_node_evidence_ids(pnode, store))

            case_ids = r.case_ids
            fir_numbers: list[str] = []
            districts: set[str] = set()
            recent_case: dict[str, Any] | None = None
            latest_date_str = ""

            for cid in case_ids:
                cnode = store.nodes.get(cid)
                if not cnode:
                    continue
                fir = prop_str(cnode, "fir_number") or cid
                fir_numbers.append(fir)
                dist = prop_str(cnode, "district", default="Unknown District")
                districts.add(dist)
                date_str = prop_str(cnode, "reported_at") or prop_str(cnode, "incident_date") or ""
                if not recent_case or date_str > latest_date_str:
                    latest_date_str = date_str
                    recent_case = {
                        "case_id": cid,
                        "fir_number": fir,
                        "date": date_str,
                        "district": dist,
                        "crime_head": prop_str(cnode, "crime_head", default="General"),
                    }
                evidence_ids.update(_extract_node_evidence_ids(cnode, store))
                for edge in store.adj.get(cid, []):
                    evidence_ids.update(_extract_edge_evidence_ids(edge, store))

            shared_entities: list[dict[str, Any]] = []
            seen_shared: set[str] = set()
            for cid in case_ids:
                co_accused_list = get_co_accused(store, cid)
                for ca in co_accused_list:
                    if ca.node_id not in cluster_pids and ca.node_id not in seen_shared:
                        seen_shared.add(ca.node_id)
                        shared_entities.append({
                            "entity_id": ca.node_id,
                            "label": prop_str(ca, "full_name", default=ca.node_id),
                            "entity_type": "Person",
                            "shared_reason": f"Co-accused in case {cid}",
                        })
            for pid in cluster_pids:
                for edge in store.adj.get(pid, []):
                    if edge.edge_type in ("USED_PHONE", "ASSOCIATED_VEHICLE", "OWNS_ACCOUNT", "TRANSFERRED_TO"):
                        tgt = store.nodes.get(edge.target_id)
                        if tgt and tgt.node_id not in seen_shared:
                            seen_shared.add(tgt.node_id)
                            shared_entities.append({
                                "entity_id": tgt.node_id,
                                "label": prop_str(tgt, "label") or prop_str(tgt, "phone_number") or prop_str(tgt, "account_number") or tgt.node_id,
                                "entity_type": tgt.entity_type,
                                "shared_reason": f"Linked via {edge.edge_type}",
                            })

            radar_items.append({
                "person_id": r.person_ids[0] if r.person_ids else "unknown",
                "canonical_name": r.canonical_person_name,
                "aliases": sorted(list(aliases)),
                "resolved_person_ids": r.person_ids,
                "case_count": r.case_count,
                "case_ids": r.case_ids,
                "fir_numbers": sorted(list(set(fir_numbers))),
                "districts": sorted(list(districts)),
                "district_count": len(districts),
                "shared_network_entities_count": len(shared_entities),
                "shared_network_entities": shared_entities[:10],
                "shared_phone_identifiers": sorted(list(phones)),
                "most_recent_case": recent_case,
                "evidence_ids": sorted(list(evidence_ids)),
                "why_surfaced": "Deterministic repeat-case + entity-resolution evidence.",
                "compliance_status": "Investigative lead — not a finding of guilt.",
            })

        # 2. Process unmerged repeat accused
        for r in raw_repeat:
            if r.person_id in seen_person_ids:
                continue
            pnode = store.nodes.get(r.person_id)
            if not pnode:
                continue
            name = prop_str(pnode, "full_name") or prop_str(pnode, "label") or r.person_id
            aliases_raw = pnode.properties.get("aliases", [])
            aliases_list = [str(a) for a in aliases_raw if str(a) != name] if isinstance(aliases_raw, list) else []
            phones_raw: set[str] = set()
            phone = prop_str(pnode, "phone_number")
            if phone:
                phones_raw.add(phone)
            evidence_ids_raw: set[str] = set()
            evidence_ids_raw.update(_extract_node_evidence_ids(pnode, store))
            for edge in store.adj.get(r.person_id, []):
                if edge.edge_type in ("USED_PHONE", "USES_PHONE", "HAS_PHONE"):
                    phone_node = store.nodes.get(edge.target_id)
                    p_num = prop_str(phone_node, "phone_number") or prop_str(phone_node, "label") or edge.target_id
                    phones_raw.add(p_num)
                evidence_ids_raw.update(_extract_edge_evidence_ids(edge, store))

            case_ids = r.case_ids
            fir_numbers_raw: list[str] = []
            districts_raw: set[str] = set()
            recent_case = None
            latest_date_str = ""
            for cid in case_ids:
                cnode = store.nodes.get(cid)
                if not cnode:
                    continue
                fir = prop_str(cnode, "fir_number") or cid
                fir_numbers_raw.append(fir)
                dist = prop_str(cnode, "district", default="Unknown District")
                districts_raw.add(dist)
                date_str = prop_str(cnode, "reported_at") or prop_str(cnode, "incident_date") or ""
                if not recent_case or date_str > latest_date_str:
                    latest_date_str = date_str
                    recent_case = {
                        "case_id": cid,
                        "fir_number": fir,
                        "date": date_str,
                        "district": dist,
                        "crime_head": prop_str(cnode, "crime_head", default="General"),
                    }
                evidence_ids_raw.update(_extract_node_evidence_ids(cnode, store))
                for edge in store.adj.get(cid, []):
                    evidence_ids_raw.update(_extract_edge_evidence_ids(edge, store))

            shared_entities_raw: list[dict[str, Any]] = []
            seen_shared_raw: set[str] = set()
            for cid in case_ids:
                co_accused_list = get_co_accused(store, cid)
                for ca in co_accused_list:
                    if ca.node_id != r.person_id and ca.node_id not in seen_shared_raw:
                        seen_shared_raw.add(ca.node_id)
                        shared_entities_raw.append({
                            "entity_id": ca.node_id,
                            "label": prop_str(ca, "full_name", default=ca.node_id),
                            "entity_type": "Person",
                            "shared_reason": f"Co-accused in case {cid}",
                        })
            for edge in store.adj.get(r.person_id, []):
                if edge.edge_type in ("USED_PHONE", "ASSOCIATED_VEHICLE", "OWNS_ACCOUNT", "TRANSFERRED_TO"):
                    tgt = store.nodes.get(edge.target_id)
                    if tgt and tgt.node_id not in seen_shared_raw:
                        seen_shared_raw.add(tgt.node_id)
                        shared_entities_raw.append({
                            "entity_id": tgt.node_id,
                            "label": prop_str(tgt, "label") or prop_str(tgt, "phone_number") or prop_str(tgt, "account_number") or tgt.node_id,
                            "entity_type": tgt.entity_type,
                            "shared_reason": f"Linked via {edge.edge_type}",
                        })

            radar_items.append({
                "person_id": r.person_id,
                "canonical_name": name,
                "aliases": sorted(aliases_list),
                "resolved_person_ids": [r.person_id],
                "case_count": r.case_count,
                "case_ids": r.case_ids,
                "fir_numbers": sorted(list(set(fir_numbers_raw))),
                "districts": sorted(list(districts_raw)),
                "district_count": len(districts_raw),
                "shared_network_entities_count": len(shared_entities_raw),
                "shared_network_entities": shared_entities_raw[:10],
                "shared_phone_identifiers": sorted(list(phones_raw)),
                "most_recent_case": recent_case,
                "evidence_ids": sorted(list(evidence_ids_raw)),
                "why_surfaced": "Deterministic repeat-case + entity-resolution evidence.",
                "compliance_status": "Investigative lead — not a finding of guilt.",
            })

        radar_items.sort(key=lambda x: (-x["case_count"], -x["district_count"], x["canonical_name"]))
        return radar_items[:top_k]

    def get_offender_radar_profile(self, person_id: str) -> dict[str, Any] | None:
        """Fetch radar profile for a specific person or cluster member."""
        radar_items = self.get_repeat_offender_radar(min_cases=1, top_k=500)
        for item in radar_items:
            if item["person_id"] == person_id or person_id in item.get("resolved_person_ids", []):
                return item
        # Fallback to single person profile wrapped in radar format
        store = self._repo.store
        pnode = store.nodes.get(person_id)
        if not pnode or pnode.entity_type != "Person":
            return None
        prof = self.get_offender_profile(person_id)
        return {
            "person_id": person_id,
            "canonical_name": prop_str(pnode, "full_name") or prop_str(pnode, "label") or person_id,
            "aliases": pnode.properties.get("aliases", []),
            "resolved_person_ids": [person_id],
            "case_count": prof.get("accused_in_count", 0),
            "case_ids": prof.get("case_ids", []),
            "fir_numbers": prof.get("fir_numbers", []),
            "districts": prof.get("jurisdiction_spread", {}).get("districts", []),
            "district_count": prof.get("jurisdiction_spread", {}).get("district_count", 0),
            "shared_network_entities_count": prof.get("co_accused_count", 0),
            "shared_network_entities": [
                {"entity_id": ca["person_id"], "label": ca["person_id"], "entity_type": "Person", "shared_reason": f"Co-accused in {ca['shared_case_count']} case(s)"}
                for ca in prof.get("co_accused", [])[:10]
            ],
            "shared_phone_identifiers": [prop_str(pnode, "phone_number")] if prop_str(pnode, "phone_number") else [],
            "most_recent_case": None,
            "evidence_ids": [],
            "why_surfaced": "Deterministic repeat-case + entity-resolution evidence.",
            "compliance_status": "Investigative lead — not a finding of guilt.",
        }