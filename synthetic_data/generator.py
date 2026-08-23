"""Synthetic graph generation orchestrator."""

from __future__ import annotations

from collections import OrderedDict
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from synthetic_data.configs import SyntheticDataConfig, SyntheticGraphDataset, SyntheticNodeRecord, build_faker, build_random, utc_now
from synthetic_data.factories.case_factory import CaseBlueprint, ReferenceCatalog, build_case_blueprints, build_reference_catalog
from synthetic_data.factories.clock_factory import ClockRecord, build_clock_records
from synthetic_data.factories.dependency_factory import DependencyRecord, build_dependency_records
from synthetic_data.factories.evidence_factory import EvidenceRecord, build_evidence_records
from synthetic_data.factories.officer_factory import OfficerProfile, build_officer_profiles
from synthetic_data.factories.person_factory import PersonProfile, build_person_profiles
from synthetic_data.relationships import build_relationships


class SyntheticGraphAssembly(BaseModel):
    config: SyntheticDataConfig
    references: ReferenceCatalog
    case_blueprints: list[CaseBlueprint]
    officer_profiles: list[OfficerProfile]
    person_profiles: list[PersonProfile]
    dependency_records: list[DependencyRecord]
    evidence_records: list[EvidenceRecord]
    clock_records: list[ClockRecord]
    dataset: SyntheticGraphDataset

    model_config = ConfigDict(arbitrary_types_allowed=True)


def generate_synthetic_graph(config: SyntheticDataConfig | None = None) -> SyntheticGraphAssembly:
    config = config or SyntheticDataConfig()
    rng = build_random(config.seed)
    build_faker(config.seed)
    references = build_reference_catalog(config, rng)
    case_blueprints = build_case_blueprints(config, rng, references)
    officer_profiles = build_officer_profiles(config, rng, references)
    person_profiles = build_person_profiles(config, rng, case_blueprints)
    dependency_records = build_dependency_records(config, rng, case_blueprints, officer_profiles)
    evidence_records = build_evidence_records(config, rng, case_blueprints, officer_profiles)
    clock_records = build_clock_records(config, rng, case_blueprints)

    nodes = _collect_nodes(
        references=references,
        case_blueprints=case_blueprints,
        officer_profiles=officer_profiles,
        person_profiles=person_profiles,
        dependency_records=dependency_records,
        evidence_records=evidence_records,
        clock_records=clock_records,
    )
    edges = build_relationships(
        case_blueprints=case_blueprints,
        references=references,
        person_profiles=person_profiles,
        officer_profiles=officer_profiles,
        dependency_records=dependency_records,
        evidence_records=evidence_records,
        clock_records=clock_records,
    )
    dataset = SyntheticGraphDataset(
        seed=config.seed,
        generated_at=utc_now(),
        nodes=nodes,
        edges=edges,
        metadata={
            "case_count": len(case_blueprints),
            "person_count": len(person_profiles),
            "officer_count": len(officer_profiles),
            "dependency_count": len(dependency_records),
            "evidence_count": len(evidence_records),
            "clock_count": len(clock_records),
        },
    )
    return SyntheticGraphAssembly(
        config=config,
        references=references,
        case_blueprints=case_blueprints,
        officer_profiles=officer_profiles,
        person_profiles=person_profiles,
        dependency_records=dependency_records,
        evidence_records=evidence_records,
        clock_records=clock_records,
        dataset=dataset,
    )


def _collect_nodes(
    references: ReferenceCatalog,
    case_blueprints: list[CaseBlueprint],
    officer_profiles: list[OfficerProfile],
    person_profiles: list[PersonProfile],
    dependency_records: list[DependencyRecord],
    evidence_records: list[EvidenceRecord],
    clock_records: list[ClockRecord],
) -> list[SyntheticNodeRecord]:
    ordered_nodes: OrderedDict[UUID, SyntheticNodeRecord] = OrderedDict()

    for record in [*references.units, *references.locations, *references.courts, *references.acts, *references.sections, *references.crime_heads, *references.crime_sub_heads]:
        ordered_nodes[record.id] = record
    for blueprint in case_blueprints:
        ordered_nodes[blueprint.case.id] = blueprint.case
    for profile in officer_profiles:
        ordered_nodes[profile.node.id] = profile.node
    for profile in person_profiles:
        ordered_nodes[profile.node.id] = profile.node
    for record in dependency_records:
        ordered_nodes[record.node.id] = record.node
    for record in evidence_records:
        ordered_nodes[record.node.id] = record.node
    for record in clock_records:
        ordered_nodes[record.node.id] = record.node

    return list(ordered_nodes.values())