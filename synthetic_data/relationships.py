"""Relationship assembly for the synthetic investigation graph."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

from backend.app.core.graph.enums import EdgeStorageMode, GraphRelationshipType

from synthetic_data.configs import SyntheticEdgeRecord
from synthetic_data.factories.case_factory import CaseBlueprint, ReferenceCatalog
from synthetic_data.factories.clock_factory import ClockRecord
from synthetic_data.factories.dependency_factory import DependencyRecord
from synthetic_data.factories.evidence_factory import EvidenceRecord
from synthetic_data.factories.officer_factory import OfficerProfile
from synthetic_data.factories.person_factory import PersonProfile


def build_relationships(
    case_blueprints: list[CaseBlueprint],
    references: ReferenceCatalog,
    person_profiles: list[PersonProfile],
    officer_profiles: list[OfficerProfile],
    dependency_records: list[DependencyRecord],
    evidence_records: list[EvidenceRecord],
    clock_records: list[ClockRecord],
) -> list[SyntheticEdgeRecord]:
    edges: list[SyntheticEdgeRecord] = []
    seen: set[tuple[str, str, str, str]] = set()

    def add_edge(edge_type: GraphRelationshipType, source_id, target_id, storage_mode: EdgeStorageMode = EdgeStorageMode.STORED, **properties) -> None:
        key = (edge_type.value, str(source_id), str(target_id), storage_mode.value)
        if key in seen:
            return
        seen.add(key)
        edges.append(
            SyntheticEdgeRecord(
                edge_type=edge_type,
                source_id=source_id,
                target_id=target_id,
                storage_mode=storage_mode,
                properties=properties,
            )
        )

    for blueprint in case_blueprints:
        add_edge(GraphRelationshipType.OCCURRED_IN, blueprint.case.id, blueprint.location_id)
        add_edge(GraphRelationshipType.CASE_HAS_COURT, blueprint.case.id, blueprint.court_id)
        add_edge(GraphRelationshipType.CASE_HAS_CRIME_HEAD, blueprint.case.id, blueprint.crime_head_id)
        add_edge(GraphRelationshipType.CASE_HAS_CRIME_SUB_HEAD, blueprint.case.id, blueprint.crime_sub_head_id)
        for section_id in blueprint.section_ids:
            add_edge(GraphRelationshipType.CHARGED_UNDER, blueprint.case.id, section_id)

    # INVESTIGATED_BY: assign each case to an officer from the same district.
    # Build a district → officer list index once for O(n) total assignment.
    district_officers: dict[str, list] = defaultdict(list)
    for officer in officer_profiles:
        district_officers[officer.district].append(officer)

    for idx, blueprint in enumerate(case_blueprints):
        candidates = district_officers.get(blueprint.district) or officer_profiles
        officer = candidates[idx % len(candidates)]
        add_edge(GraphRelationshipType.INVESTIGATED_BY, blueprint.case.id, officer.node.id)

    for section in references.sections:
        act_id = section.properties["act_id"]
        add_edge(GraphRelationshipType.BELONGS_TO_ACT, section.id, act_id)

    for officer in officer_profiles:
        add_edge(GraphRelationshipType.BELONGS_TO_UNIT, officer.node.id, officer.unit_id)

    for dependency in dependency_records:
        add_edge(GraphRelationshipType.CASE_HAS_DEPENDENCY, dependency.case_id, dependency.node.id)

    for evidence in evidence_records:
        add_edge(GraphRelationshipType.CASE_HAS_EVIDENCE, evidence.case_id, evidence.node.id)

    for clock in clock_records:
        add_edge(GraphRelationshipType.CASE_HAS_CLOCK, clock.case_id, clock.node.id)

    accused_case_map: dict[str, set[str]] = defaultdict(set)
    cluster_case_map: dict[str, set[str]] = defaultdict(set)
    for profile in person_profiles:
        for assignment in profile.assignments:
            if assignment.role == "accused":
                add_edge(GraphRelationshipType.ACCUSED_IN, profile.node.id, assignment.case_id)
                accused_case_map[str(assignment.case_id)].add(str(profile.node.id))
            elif assignment.role == "victim":
                add_edge(GraphRelationshipType.VICTIM_IN, profile.node.id, assignment.case_id)
            elif assignment.role == "complainant":
                add_edge(GraphRelationshipType.COMPLAINANT_IN, profile.node.id, assignment.case_id)
            elif assignment.role == "witness":
                add_edge(GraphRelationshipType.WITNESS_IN, profile.node.id, assignment.case_id)

            if profile.repeat_cluster_id:
                cluster_case_map[profile.repeat_cluster_id].add(str(assignment.case_id))
            if profile.shared_phone_cluster_id:
                cluster_case_map[profile.shared_phone_cluster_id].add(str(assignment.case_id))
            if profile.shared_vehicle_cluster_id:
                cluster_case_map[profile.shared_vehicle_cluster_id].add(str(assignment.case_id))
            if profile.shared_address_cluster_id:
                cluster_case_map[profile.shared_address_cluster_id].add(str(assignment.case_id))

    for case_id, accused_ids in accused_case_map.items():
        for source_id, target_id in combinations(sorted(accused_ids), 2):
            add_edge(
                GraphRelationshipType.CO_ACCUSED_WITH,
                source_id,
                target_id,
                EdgeStorageMode.DERIVED_NOT_STORED,
                case_id=case_id,
            )

    linked_pairs: set[tuple[str, str]] = set()
    for cluster_id, case_ids in cluster_case_map.items():
        if len(case_ids) < 2:
            continue
        sorted_case_ids = sorted(case_ids)[:5]
        for source_id, target_id in combinations(sorted_case_ids, 2):
            pair = (source_id, target_id)
            if pair in linked_pairs:
                continue
            linked_pairs.add(pair)
            add_edge(
                GraphRelationshipType.LINKED_TO,
                source_id,
                target_id,
                EdgeStorageMode.DERIVED_NOT_STORED,
                cluster_id=cluster_id,
            )

    return edges