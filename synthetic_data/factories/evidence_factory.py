"""Evidence factory for mixed evidentiary records."""

from __future__ import annotations

from datetime import datetime, timedelta
from random import Random
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.app.core.graph.entities import Evidence
from backend.app.core.graph.enums import GraphEntityType

from synthetic_data.configs import SyntheticDataConfig, SyntheticNodeRecord, build_faker, stable_uuid
from synthetic_data.factories.case_factory import CaseBlueprint
from synthetic_data.factories.officer_factory import OfficerProfile


class EvidenceRecord(BaseModel):
    node: SyntheticNodeRecord
    case_id: UUID
    evidence_type: str
    collected_at: datetime
    collected_by_officer_id: UUID | None = None
    chain_of_custody_status: str = "intact"

    model_config = ConfigDict(arbitrary_types_allowed=True)


def build_evidence_records(
    config: SyntheticDataConfig,
    rng: Random,
    case_blueprints: list[CaseBlueprint],
    officers: list[OfficerProfile],
) -> list[EvidenceRecord]:
    fake = build_faker(config.seed + 43)
    cases = [blueprint.case for blueprint in case_blueprints]
    evidence_types = ["document", "device", "sample", "witness_note", "photo", "call_log"]
    evidence_weights = [0.24, 0.24, 0.12, 0.18, 0.12, 0.10]
    records: list[EvidenceRecord] = []

    for index in range(config.evidence_count):
        case = rng.choice(cases)
        evidence_type = rng.choices(evidence_types, weights=evidence_weights, k=1)[0]
        collected_at = case.entity.created_at + timedelta(hours=rng.randint(1, 240))
        collected_officer = rng.choice(officers)
        evidence_id = stable_uuid("evidence", str(case.id), evidence_type, str(index))
        records.append(
            EvidenceRecord(
                node=SyntheticNodeRecord(
                    entity_type=GraphEntityType.EVIDENCE,
                    entity=Evidence(id=evidence_id, created_at=collected_at, updated_at=collected_at),
                    properties={
                        "case_id": str(case.id),
                        "evidence_type": evidence_type,
                        "description": fake.sentence(nb_words=10),
                        "collected_at": collected_at,
                        "collected_by_officer_id": str(collected_officer.node.id),
                        "chain_of_custody_status": "intact",
                    },
                ),
                case_id=case.id,
                evidence_type=evidence_type,
                collected_at=collected_at,
                collected_by_officer_id=collected_officer.node.id,
            )
        )
    return records