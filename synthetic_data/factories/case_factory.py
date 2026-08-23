"""Case and reference graph node factories."""

from __future__ import annotations

from datetime import datetime, timedelta
from random import Random
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.graph.entities import Act, Case, Court, CrimeHead, CrimeSubHead, Location, Section, Unit
from backend.app.core.graph.enums import GraphEntityType

from synthetic_data.configs import (
    SyntheticDataConfig,
    SyntheticNodeRecord,
    build_faker,
    default_case_stages,
    default_offence_categories,
    stable_uuid,
    timestamp_for_index,
    choose_weighted,
    utc_now,
)


class ReferenceCatalog(BaseModel):
    units: list[SyntheticNodeRecord] = Field(default_factory=list)
    locations: list[SyntheticNodeRecord] = Field(default_factory=list)
    courts: list[SyntheticNodeRecord] = Field(default_factory=list)
    acts: list[SyntheticNodeRecord] = Field(default_factory=list)
    sections: list[SyntheticNodeRecord] = Field(default_factory=list)
    crime_heads: list[SyntheticNodeRecord] = Field(default_factory=list)
    crime_sub_heads: list[SyntheticNodeRecord] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class CaseBlueprint(BaseModel):
    case: SyntheticNodeRecord
    district: str
    police_station: str
    case_stage: str
    offence_category: str
    reported_at: datetime
    incident_at: datetime
    unit_id: UUID
    location_id: UUID
    court_id: UUID
    act_id: UUID
    section_ids: list[UUID]
    crime_head_id: UUID
    crime_sub_head_id: UUID
    accused_target: int
    victim_target: int
    complainant_target: int
    witness_target: int
    risk_band: str
    repeat_cluster_id: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


_DISTRICT_STATIONS: dict[str, tuple[str, ...]] = {
    "Bengaluru City": ("Ashok Nagar", "Jayanagar", "Malleshwaram"),
    "Mysuru": ("Mysuru North", "Mysuru South", "Nanjangud"),
    "Mangaluru": ("Mangaluru North", "Mangaluru South", "Bantwal"),
    "Belagavi": ("Belagavi North", "Belagavi South", "Bailhongal"),
    "Hubballi-Dharwad": ("Hubballi Town", "Dharwad Town", "Navalgund"),
    "Kalaburagi": ("Kalaburagi North", "Kalaburagi South", "Sedam"),
}


def build_reference_catalog(config: SyntheticDataConfig, rng: Random) -> ReferenceCatalog:
    fake = build_faker(config.seed)
    base_now = utc_now() - timedelta(days=config.snapshot_days_offset)

    units: list[SyntheticNodeRecord] = []
    for district_index, district in enumerate(config.districts):
        district_unit_id = stable_uuid("unit", district, "district")
        district_unit = SyntheticNodeRecord(
            entity_type=GraphEntityType.UNIT,
            entity=Unit(id=district_unit_id, created_at=timestamp_for_index(base_now, district_index), updated_at=timestamp_for_index(base_now, district_index)),
            properties={
                "unit_name": f"{district} District HQ",
                "unit_type": "district_hq",
                "district": district,
            },
        )
        units.append(district_unit)

        for station_index, station_name in enumerate(_DISTRICT_STATIONS[district]):
            unit_id = stable_uuid("unit", district, station_name)
            units.append(
                SyntheticNodeRecord(
                    entity_type=GraphEntityType.UNIT,
                    entity=Unit(id=unit_id, created_at=timestamp_for_index(base_now, district_index * 4 + station_index + 1), updated_at=timestamp_for_index(base_now, district_index * 4 + station_index + 1)),
                    properties={
                        "unit_name": station_name,
                        "unit_type": "police_station",
                        "district": district,
                        "parent_unit_id": str(district_unit_id),
                    },
                )
            )

    locations: list[SyntheticNodeRecord] = []
    location_pool = max(config.shared_location_clusters, config.case_count // 4)
    for index in range(location_pool):
        district = rng.choice(config.districts)
        station_name = rng.choice(_DISTRICT_STATIONS[district])
        locality = fake.street_name()
        location_id = stable_uuid("location", district, station_name, locality, str(index))
        locations.append(
            SyntheticNodeRecord(
                entity_type=GraphEntityType.LOCATION,
                entity=Location(id=location_id, created_at=timestamp_for_index(base_now, index), updated_at=timestamp_for_index(base_now, index)),
                properties={
                    "locality_name": locality,
                    "district": district,
                    "police_station": station_name,
                    "state": "Karnataka",
                    "address_text": fake.address().replace("\n", ", "),
                    "latitude": float(fake.latitude()),
                    "longitude": float(fake.longitude()),
                    "repeat_cluster_id": f"location-{index // 3}",
                },
            )
        )

    courts: list[SyntheticNodeRecord] = []
    for index, district in enumerate(config.districts):
        court_id = stable_uuid("court", district)
        courts.append(
            SyntheticNodeRecord(
                entity_type=GraphEntityType.COURT,
                entity=Court(id=court_id, created_at=timestamp_for_index(base_now, index), updated_at=timestamp_for_index(base_now, index)),
                properties={
                    "court_name": f"{district} District Court",
                    "court_level": "district",
                    "district": district,
                    "state": "Karnataka",
                },
            )
        )

    acts = [
        _make_reference_node(GraphEntityType.ACT, Act, base_now, "act", name, {"act_name": name, "act_code": code, "jurisdiction": "Karnataka", "short_name": short})
        for name, code, short in (
            ("BNS", "BNS", "bns"),
            ("BNSS", "BNSS", "bnss"),
            ("Evidence Act", "EVIDENCE", "evidence"),
            ("IT Act", "IT", "it"),
        )
    ]

    crime_heads: list[SyntheticNodeRecord] = []
    for index, head_name in enumerate(("Property", "Violence", "Fraud", "Public Order", "Narcotics", "Cyber")):
        head_id = stable_uuid("crime_head", head_name)
        crime_heads.append(
            SyntheticNodeRecord(
                entity_type=GraphEntityType.CRIME_HEAD,
                entity=CrimeHead(id=head_id, created_at=timestamp_for_index(base_now, index), updated_at=timestamp_for_index(base_now, index)),
                properties={
                    "head_code": f"CH-{index + 1:02d}",
                    "head_name": head_name,
                    "category_group": head_name.lower().replace(" ", "_"),
                },
            )
        )

    crime_sub_heads: list[SyntheticNodeRecord] = []
    for index in range(12):
        head = crime_heads[index % len(crime_heads)]
        sub_name = f"{head.properties['head_name']} / Sub-{index + 1:02d}"
        sub_id = stable_uuid("crime_sub_head", sub_name)
        crime_sub_heads.append(
            SyntheticNodeRecord(
                entity_type=GraphEntityType.CRIME_SUB_HEAD,
                entity=CrimeSubHead(id=sub_id, created_at=timestamp_for_index(base_now, index), updated_at=timestamp_for_index(base_now, index)),
                properties={
                    "sub_head_code": f"CSH-{index + 1:02d}",
                    "sub_head_name": sub_name,
                    "head_id": str(head.id),
                },
            )
        )

    sections: list[SyntheticNodeRecord] = []
    section_templates = [
        ("theft", "BNS", "section_theft"),
        ("burglary", "BNS", "section_burglary"),
        ("robbery", "BNS", "section_robbery"),
        ("vehicle_theft", "BNS", "section_vehicle_theft"),
        ("assault", "BNS", "section_assault"),
        ("public_order", "BNSS", "section_public_order"),
        ("fraud", "BNS", "section_fraud"),
        ("forgery", "BNS", "section_forgery"),
        ("harassment", "BNSS", "section_harassment"),
        ("narcotics", "NDPS", "section_narcotics"),
    ]
    for index, (label, act_name, slug) in enumerate(section_templates):
        act = acts[index % len(acts)]
        section_id = stable_uuid("section", slug)
        sections.append(
            SyntheticNodeRecord(
                entity_type=GraphEntityType.SECTION,
                entity=Section(id=section_id, created_at=timestamp_for_index(base_now, index), updated_at=timestamp_for_index(base_now, index)),
                properties={
                    "section_code": f"{slug.upper()}",
                    "section_text": f"Synthetic section for {label}",
                    "severity_band": "serious" if label in {"robbery", "assault", "narcotics"} else "moderate",
                    "act_id": str(act.id),
                    "act_name": act_name,
                },
            )
        )

    return ReferenceCatalog(
        units=units,
        locations=locations,
        courts=courts,
        acts=acts,
        sections=sections,
        crime_heads=crime_heads,
        crime_sub_heads=crime_sub_heads,
    )


def build_case_blueprints(
    config: SyntheticDataConfig,
    rng: Random,
    references: ReferenceCatalog,
) -> list[CaseBlueprint]:
    base_now = utc_now() - timedelta(days=config.snapshot_days_offset)
    case_blueprints: list[CaseBlueprint] = []
    offence_categories = list(default_offence_categories())
    case_stages = list(default_case_stages())

    section_groups = [
        [references.sections[0], references.sections[1]],
        [references.sections[2]],
        [references.sections[3]],
        [references.sections[4], references.sections[5]],
        [references.sections[6]],
        [references.sections[7], references.sections[8]],
        [references.sections[9]],
    ]

    for case_index in range(config.case_count):
        district = config.districts[case_index % len(config.districts)]
        station_name = _DISTRICT_STATIONS[district][case_index % len(_DISTRICT_STATIONS[district])]
        location = references.locations[(case_index * 7) % len(references.locations)]
        court = references.courts[case_index % len(references.courts)]
        unit = next(unit for unit in references.units if unit.properties["unit_name"] == station_name)
        act = references.acts[case_index % len(references.acts)]
        sections = section_groups[case_index % len(section_groups)]
        crime_head = references.crime_heads[case_index % len(references.crime_heads)]
        crime_sub_head = references.crime_sub_heads[case_index % len(references.crime_sub_heads)]
        offence_category = offence_categories[case_index % len(offence_categories)]
        case_stage = case_stages[case_index % len(case_stages)]
        reported_at = timestamp_for_index(base_now, case_index, step_hours=14)
        incident_at = reported_at - timedelta(hours=rng.randint(1, 72))
        case_id = stable_uuid("case", str(case_index), district, station_name)
        risk_band = choose_weighted(
            rng,
            [("green", 0.32), ("amber", 0.28), ("red", 0.22), ("overdue", 0.18)],
        )
        repeat_cluster_id = f"cluster-{case_index // 12}" if case_index % 4 == 0 else None
        accused_target = choose_weighted(
            rng,
            [(1, 0.35), (2, 0.40), (3, 0.20), (4, 0.05)],
        )
        victim_target = choose_weighted(
            rng,
            [(0, 0.45), (1, 0.45), (2, 0.10)],
        )
        complainant_target = choose_weighted(
            rng,
            [(0, 0.30), (1, 0.55), (2, 0.15)],
        )
        witness_target = choose_weighted(
            rng,
            [(0, 0.45), (1, 0.45), (2, 0.10)],
        )

        case_blueprints.append(
            CaseBlueprint(
                case=SyntheticNodeRecord(
                    entity_type=GraphEntityType.CASE,
                    entity=Case(id=case_id, created_at=timestamp_for_index(base_now, case_index, step_hours=12), updated_at=timestamp_for_index(base_now, case_index, step_hours=12)),
                    properties={
                        "fir_number": f"FIR/{district[:3].upper()}/{case_index + 1:04d}",
                        "case_number": f"CC-{case_index + 1:04d}",
                        "district": district,
                        "police_station": station_name,
                        "case_stage": case_stage,
                        "offence_category": offence_category,
                        "reported_at": reported_at,
                        "incident_at": incident_at,
                        "risk_band": risk_band,
                        "repeat_cluster_id": repeat_cluster_id,
                    },
                ),
                district=district,
                police_station=station_name,
                case_stage=case_stage,
                offence_category=offence_category,
                reported_at=reported_at,
                incident_at=incident_at,
                unit_id=unit.id,
                location_id=location.id,
                court_id=court.id,
                act_id=act.id,
                section_ids=[section.id for section in sections],
                crime_head_id=crime_head.id,
                crime_sub_head_id=crime_sub_head.id,
                accused_target=accused_target,
                victim_target=victim_target,
                complainant_target=complainant_target,
                witness_target=witness_target,
                risk_band=risk_band,
                repeat_cluster_id=repeat_cluster_id,
            )
        )

    return case_blueprints


def _make_reference_node(entity_type: GraphEntityType, entity_cls: type, base_now: datetime, key: str, title: str, properties: dict[str, object]) -> SyntheticNodeRecord:
    reference_id = stable_uuid(key, title)
    return SyntheticNodeRecord(
        entity_type=entity_type,
        entity=entity_cls(id=reference_id, created_at=base_now, updated_at=base_now),
        properties=properties,
    )