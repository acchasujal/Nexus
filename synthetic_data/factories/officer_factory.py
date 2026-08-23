"""Officer factory for shared supervisory assignments."""

from __future__ import annotations

from random import Random
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.app.core.graph.entities import Officer
from backend.app.core.graph.enums import GraphEntityType

from synthetic_data.configs import SyntheticDataConfig, SyntheticNodeRecord, build_faker, stable_uuid, timestamp_for_index, utc_now
from synthetic_data.factories.case_factory import ReferenceCatalog


class OfficerProfile(BaseModel):
    node: SyntheticNodeRecord
    full_name: str
    rank: str
    badge_number: str
    district: str
    station_name: str
    unit_id: UUID
    supervisor_rank: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


def build_officer_profiles(
    config: SyntheticDataConfig,
    rng: Random,
    references: ReferenceCatalog,
) -> list[OfficerProfile]:
    fake = build_faker(config.seed + 23)
    station_units = [unit for unit in references.units if unit.properties.get("unit_type") == "police_station"]
    district_units = [unit for unit in references.units if unit.properties.get("unit_type") == "district_hq"]
    profiles: list[OfficerProfile] = []
    ranks = [
        "constable",
        "head_constable",
        "asi",
        "si",
        "inspector",
        "sho",
        "sp",
    ]
    rank_weights = [0.20, 0.20, 0.18, 0.18, 0.12, 0.08, 0.04]

    for index in range(config.officer_count):
        district = config.districts[index % len(config.districts)]
        district_station_units = [unit for unit in station_units if unit.properties.get("district") == district]
        unit = district_station_units[index % len(district_station_units)] if district_station_units else district_units[index % len(district_units)]
        rank = rng.choices(ranks, weights=rank_weights, k=1)[0]
        badge_number = f"KA-{1000 + index:04d}"
        officer_id = stable_uuid("officer", badge_number)
        created_at = timestamp_for_index(utc_now(), index, step_hours=3)
        profiles.append(
            OfficerProfile(
                node=SyntheticNodeRecord(
                    entity_type=GraphEntityType.OFFICER,
                    entity=Officer(id=officer_id, created_at=created_at, updated_at=created_at),
                    properties={
                        "full_name": fake.name(),
                        "rank": rank,
                        "badge_number": badge_number,
                        "district": district,
                        "station_name": unit.properties["unit_name"],
                        "unit_id": str(unit.id),
                        "supervisor_rank": _supervisor_rank(rank),
                    },
                ),
                full_name=fake.name(),
                rank=rank,
                badge_number=badge_number,
                district=district,
                station_name=unit.properties["unit_name"],
                unit_id=unit.id,
                supervisor_rank=_supervisor_rank(rank),
            )
        )
    return profiles


def _supervisor_rank(rank: str) -> str | None:
    hierarchy = {
        "constable": "head_constable",
        "head_constable": "asi",
        "asi": "si",
        "si": "inspector",
        "inspector": "sho",
        "sho": "sp",
        "sp": None,
    }
    return hierarchy.get(rank)