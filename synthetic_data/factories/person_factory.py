"""Person factory for repeated identities and role assignments."""

from __future__ import annotations

from collections import defaultdict
from random import Random
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.graph.entities import Person
from backend.app.core.graph.enums import GraphEntityType

from synthetic_data.configs import (
    SyntheticDataConfig,
    SyntheticNodeRecord,
    build_faker,
    choose_weighted,
    stable_uuid,
    timestamp_for_index,
    utc_now,
)
from synthetic_data.factories.case_factory import CaseBlueprint


class CaseRoleAssignment(BaseModel):
    case_id: UUID
    role: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PersonProfile(BaseModel):
    node: SyntheticNodeRecord
    role: str
    assignments: list[CaseRoleAssignment] = Field(default_factory=list)
    district: str
    shared_phone_cluster_id: str | None = None
    shared_vehicle_cluster_id: str | None = None
    shared_address_cluster_id: str | None = None
    repeat_cluster_id: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


def build_person_profiles(
    config: SyntheticDataConfig,
    rng: Random,
    case_blueprints: list[CaseBlueprint],
) -> list[PersonProfile]:
    fake = build_faker(config.seed + 11)
    case_ids_by_district: dict[str, list[UUID]] = defaultdict(list)
    case_ids_by_station: dict[tuple[str, str], list[UUID]] = defaultdict(list)
    for blueprint in case_blueprints:
        case_ids_by_district[blueprint.district].append(blueprint.case.id)
        case_ids_by_station[(blueprint.district, blueprint.police_station)].append(blueprint.case.id)

    shared_phone_numbers = _build_shared_phone_numbers(fake, config.shared_phone_clusters)
    shared_vehicle_numbers = _build_shared_vehicle_numbers(fake, config.shared_vehicle_clusters)
    shared_addresses = _build_shared_addresses(fake, config.shared_address_clusters)

    profiles: list[PersonProfile] = []

    
    accused_case_capacity = [
        choose_weighted(rng, [(4, 0.45), (5, 0.55)]) if index < 60 else choose_weighted(rng, [(2, 0.35), (3, 0.45), (4, 0.20)])
        for index in range(180)
    ]
    accused_case_capacity.extend([1] * 360)
    accused_cluster_counter = 0
    for index, capacity in enumerate(accused_case_capacity):
        district = config.districts[index % len(config.districts)]
        station_key = rng.choice(list(case_ids_by_station.keys())) if index < 180 else None
        case_ids = _pick_case_ids(
            rng,
            case_blueprints,
            capacity,
            preferred_district=district,
            preferred_station=station_key[1] if station_key else None,
        )
        repeat_cluster_id = f"repeat-accused-{accused_cluster_counter // 3}" if index < 180 else None
        accused_cluster_counter += 1
        profiles.append(
            _make_profile(
                fake=fake,
                index=index,
                role="accused",
                district=district,
                assignments=[CaseRoleAssignment(case_id=case_id, role="accused") for case_id in case_ids],
                shared_phone_cluster_id=_pick_shared_cluster(shared_phone_numbers, index, 25),
                shared_vehicle_cluster_id=_pick_shared_cluster(shared_vehicle_numbers, index, 20),
                shared_address_cluster_id=_pick_shared_cluster(shared_addresses, index, 30),
                repeat_cluster_id=repeat_cluster_id,
                assigned_case_ids=case_ids,
                force_vehicle=True,
            )
        )

    victim_caps = [choose_weighted(rng, [(2, 0.55), (3, 0.30), (4, 0.15)]) if index < 50 else 1 for index in range(140)]
    complainant_caps = [choose_weighted(rng, [(2, 0.55), (3, 0.30), (4, 0.15)]) if index < 70 else 1 for index in range(110)]
    witness_caps = [choose_weighted(rng, [(2, 0.50), (3, 0.35), (4, 0.15)]) if index < 60 else 1 for index in range(110)]

    for index, capacity in enumerate(victim_caps):
        district = config.districts[index % len(config.districts)]
        case_ids = _pick_case_ids(rng, case_blueprints, capacity, preferred_district=district)
        profiles.append(
            _make_profile(
                fake=fake,
                index=index + 1000,
                role="victim",
                district=district,
                assignments=[CaseRoleAssignment(case_id=case_id, role="victim") for case_id in case_ids],
                shared_phone_cluster_id=_pick_shared_cluster(shared_phone_numbers, index + 80, 25) if index % 4 == 0 else None,
                shared_vehicle_cluster_id=None,
                shared_address_cluster_id=_pick_shared_cluster(shared_addresses, index + 90, 30),
                repeat_cluster_id=f"repeat-victim-{index // 5}" if index < 50 else None,
                assigned_case_ids=case_ids,
            )
        )

    for index, capacity in enumerate(complainant_caps):
        district = config.districts[index % len(config.districts)]
        case_ids = _pick_case_ids(rng, case_blueprints, capacity, preferred_district=district)
        profiles.append(
            _make_profile(
                fake=fake,
                index=index + 2000,
                role="complainant",
                district=district,
                assignments=[CaseRoleAssignment(case_id=case_id, role="complainant") for case_id in case_ids],
                shared_phone_cluster_id=_pick_shared_cluster(shared_phone_numbers, index + 130, 25) if index % 3 == 0 else None,
                shared_vehicle_cluster_id=None,
                shared_address_cluster_id=_pick_shared_cluster(shared_addresses, index + 140, 30),
                repeat_cluster_id=f"repeat-complainant-{index // 4}" if index < 70 else None,
                assigned_case_ids=case_ids,
            )
        )

    for index, capacity in enumerate(witness_caps):
        district = config.districts[index % len(config.districts)]
        case_ids = _pick_case_ids(rng, case_blueprints, capacity, preferred_district=district)
        profiles.append(
            _make_profile(
                fake=fake,
                index=index + 3000,
                role="witness",
                district=district,
                assignments=[CaseRoleAssignment(case_id=case_id, role="witness") for case_id in case_ids],
                shared_phone_cluster_id=_pick_shared_cluster(shared_phone_numbers, index + 180, 25) if index % 5 == 0 else None,
                shared_vehicle_cluster_id=None,
                shared_address_cluster_id=_pick_shared_cluster(shared_addresses, index + 190, 30),
                repeat_cluster_id=f"repeat-witness-{index // 4}" if index < 60 else None,
                assigned_case_ids=case_ids,
            )
        )

    return profiles


def _pick_case_ids(
    rng: Random,
    case_blueprints: list[CaseBlueprint],
    count: int,
    preferred_district: str | None = None,
    preferred_station: str | None = None,
) -> list[UUID]:
    candidates = [blueprint for blueprint in case_blueprints if preferred_district is None or blueprint.district == preferred_district]
    if preferred_station is not None:
        station_candidates = [blueprint for blueprint in candidates if blueprint.police_station == preferred_station]
        if len(station_candidates) >= count:
            candidates = station_candidates
    if len(candidates) < count:
        candidates = case_blueprints
    chosen = rng.sample(candidates, k=min(count, len(candidates)))
    return [blueprint.case.id for blueprint in chosen]


def _pick_shared_cluster(mapping: dict[str, str], index: int, cluster_count: int) -> str | None:
    if not mapping:
        return None
    cluster_keys = list(mapping.keys())
    return cluster_keys[index % min(cluster_count, len(cluster_keys))]


def _build_shared_phone_numbers(fake, cluster_count: int) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for index in range(cluster_count):
        number = fake.msisdn()
        mapping[f"phone-{index + 1:02d}"] = f"+91-{number[-10:]}"
    return mapping


def _build_shared_vehicle_numbers(fake, cluster_count: int) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for index in range(cluster_count):
        mapping[f"vehicle-{index + 1:02d}"] = f"KA{index % 99 + 1:02d}{fake.bothify(text='??')}{1000 + index:04d}".upper()
    return mapping


def _build_shared_addresses(fake, cluster_count: int) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for index in range(cluster_count):
        mapping[f"address-{index + 1:02d}"] = fake.address().replace("\n", ", ")
    return mapping


def _make_profile(
    fake,
    index: int,
    role: str,
    district: str,
    assignments: list[CaseRoleAssignment],
    shared_phone_cluster_id: str | None,
    shared_vehicle_cluster_id: str | None,
    shared_address_cluster_id: str | None,
    repeat_cluster_id: str | None,
    assigned_case_ids: list[UUID],
    force_vehicle: bool = False,
) -> PersonProfile:
    person_id = stable_uuid("person", role, str(index))
    created_at = timestamp_for_index(utc_now(), index, step_hours=4)
    phone_number = _build_person_phone(index, shared_phone_cluster_id)
    vehicle_number = _build_person_vehicle(index, shared_vehicle_cluster_id) if force_vehicle or shared_vehicle_cluster_id else None
    address_text = _build_person_address(index, shared_address_cluster_id)
    aliases = [fake.first_name(), fake.last_name()]
    full_name = fake.name()
    age = 18 + (index % 42)
    gender = ["male", "female", "other"][index % 3]
    node = SyntheticNodeRecord(
        entity_type=GraphEntityType.PERSON,
        entity=Person(id=person_id, created_at=created_at, updated_at=created_at),
        properties={
            "full_name": full_name,
            "aliases": aliases,
            "role": role,
            "age": age,
            "gender": gender,
            "phone_number": phone_number,
            "vehicle_registration_number": vehicle_number,
            "address_text": address_text,
            "district": district,
            "repeat_cluster_id": repeat_cluster_id,
            "shared_phone_cluster_id": shared_phone_cluster_id,
            "shared_vehicle_cluster_id": shared_vehicle_cluster_id,
            "shared_address_cluster_id": shared_address_cluster_id,
            "assigned_case_ids": [str(case_id) for case_id in assigned_case_ids],
        },
    )
    return PersonProfile(
        node=node,
        role=role,
        assignments=assignments,
        district=district,
        shared_phone_cluster_id=shared_phone_cluster_id,
        shared_vehicle_cluster_id=shared_vehicle_cluster_id,
        shared_address_cluster_id=shared_address_cluster_id,
        repeat_cluster_id=repeat_cluster_id,
    )


def _build_person_phone(index: int, cluster_id: str | None) -> str:
    if cluster_id is None:
        return f"+91-9{index % 10}{(index * 7) % 10}{(index * 11) % 10}{(index * 13) % 10}{(index * 17) % 10}{(index * 19) % 10}{(index * 23) % 10}{(index * 29) % 10}{(index * 31) % 10}"
    suffix = int(cluster_id.split("-")[-1])
    return f"+91-98{suffix:02d}{suffix:02d}{suffix:02d}{suffix:02d}{suffix:02d}"


def _build_person_vehicle(index: int, cluster_id: str | None) -> str | None:
    if cluster_id is None:
        return None
    suffix = int(cluster_id.split("-")[-1])
    return f"KA{(suffix % 99) + 1:02d}{chr(65 + suffix % 26)}{chr(65 + (suffix * 3) % 26)}{1000 + index:04d}"


def _build_person_address(index: int, cluster_id: str | None) -> str:
    suffix = int(cluster_id.split("-")[-1]) if cluster_id is not None else index
    street_no = 10 + (suffix % 80)
    return f"{street_no}, Synthetic Layout, Ward {1 + suffix % 18}, Bengaluru"