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
from backend.app.core.graph.algorithms.traversals import get_co_accused
from backend.app.core.graph.algorithms.utils import prop_str, get_edges_of_type
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