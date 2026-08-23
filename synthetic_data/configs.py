"""Shared configuration and record models for synthetic graph generation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from random import Random
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.graph.entities import GraphEntityBase
from backend.app.core.graph.enums import EdgeStorageMode, GraphEntityType, GraphRelationshipType

try:
    from faker import Faker
except ImportError:  # pragma: no cover - deterministic fallback for local environments without Faker
    class Faker:  # type: ignore[no-redef]
        """Small deterministic fallback matching the tiny subset of Faker we use."""

        _FIRST_NAMES = (
            "Aarav",
            "Ananya",
            "Dev",
            "Diya",
            "Ishaan",
            "Kavya",
            "Meera",
            "Nikhil",
            "Priya",
            "Rohan",
            "Sana",
            "Vivaan",
        )
        _LAST_NAMES = (
            "Iyer",
            "Nair",
            "Rao",
            "Sharma",
            "Gupta",
            "Kulkarni",
            "Patel",
            "Shetty",
            "Reddy",
            "Menon",
        )
        _STREETS = (
            "MG Road",
            "Brigade Road",
            "Church Street",
            "Jayanagar 4th Block",
            "Indiranagar 12th Main",
            "Hebbal Ring Road",
        )

        def __init__(self, locale: str = "en_IN") -> None:
            self._rng = Random(0)
            self.locale = locale

        @classmethod
        def seed(cls, seed: int) -> None:
            cls._class_seed = seed

        def seed_instance(self, seed: int) -> None:
            self._rng.seed(seed)

        def name(self) -> str:
            return f"{self.first_name()} {self.last_name()}"

        def first_name(self) -> str:
            return self._rng.choice(self._FIRST_NAMES)

        def last_name(self) -> str:
            return self._rng.choice(self._LAST_NAMES)

        def msisdn(self) -> str:
            return "".join(str(self._rng.randint(0, 9)) for _ in range(12))

        def bothify(self, text: str) -> str:
            result: list[str] = []
            for character in text:
                if character == "#":
                    result.append(str(self._rng.randint(0, 9)))
                elif character == "?":
                    result.append(chr(ord("A") + self._rng.randint(0, 25)))
                else:
                    result.append(character)
            return "".join(result)

        def address(self) -> str:
            return f"{self._rng.randint(1, 250)}, {self.street_name()}, Bengaluru"

        def street_name(self) -> str:
            return self._rng.choice(self._STREETS)

        def latitude(self) -> str:
            return f"{12 + self._rng.random() * 10:.6f}"

        def longitude(self) -> str:
            return f"{76 + self._rng.random() * 8:.6f}"

        def sentence(self, nb_words: int = 6) -> str:
            words = [self._rng.choice(("pending", "review", "contact", "report", "verify", "collect", "follow", "update", "scan", "confirm")) for _ in range(nb_words)]
            return " ".join(words).capitalize() + "."

from shared.constants.clock_types import ClockType


class SyntheticDataConfig(BaseModel):
    seed: int = 42
    case_count: int = 500
    person_count: int = 900
    officer_count: int = 150
    evidence_count: int = 1000
    dependency_count: int = 150
    districts: tuple[str, ...] = (
        "Bengaluru City",
        "Mysuru",
        "Mangaluru",
        "Belagavi",
        "Hubballi-Dharwad",
        "Kalaburagi",
    )
    stations_per_district: int = 3
    repeat_accused_min_cases: int = 2
    repeat_accused_max_cases: int = 5
    shared_phone_clusters: int = 25
    shared_vehicle_clusters: int = 20
    shared_address_clusters: int = 30
    shared_location_clusters: int = 80
    output_dir: Path = Field(default_factory=lambda: Path("artifacts/synthetic_graph"))
    json_filename: str = "synthetic_graph.json"
    nodes_csv_filename: str = "nodes.csv"
    edges_csv_filename: str = "edges.csv"
    snapshot_days_offset: int = 0

    model_config = ConfigDict(arbitrary_types_allowed=True)


class SyntheticNodeRecord(BaseModel):
    entity_type: GraphEntityType
    entity: GraphEntityBase
    properties: dict[str, Any] = Field(default_factory=dict)
    labels: tuple[str, ...] = ()

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def id(self) -> UUID:
        return self.entity.id

    def to_flat_row(self) -> dict[str, Any]:
        row = {
            "entity_type": self.entity_type.value,
            "id": str(self.entity.id),
            "created_at": self.entity.created_at.isoformat(),
            "updated_at": self.entity.updated_at.isoformat(),
        }
        for key, value in self.properties.items():
            row[key] = _serialize_value(value)
        if self.labels:
            row["labels"] = "|".join(self.labels)
        return row


class SyntheticEdgeRecord(BaseModel):
    edge_type: GraphRelationshipType
    source_id: UUID
    target_id: UUID
    storage_mode: EdgeStorageMode = EdgeStorageMode.STORED
    properties: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_flat_row(self) -> dict[str, Any]:
        row = {
            "edge_type": self.edge_type.value,
            "source_id": str(self.source_id),
            "target_id": str(self.target_id),
            "storage_mode": self.storage_mode.value,
        }
        for key, value in self.properties.items():
            row[key] = _serialize_value(value)
        return row


class SyntheticGraphDataset(BaseModel):
    seed: int
    generated_at: datetime
    nodes: list[SyntheticNodeRecord] = Field(default_factory=list)
    edges: list[SyntheticEdgeRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def counts_by_type(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for node in self.nodes:
            counts[node.entity_type.value] = counts.get(node.entity_type.value, 0) + 1
        return counts


def build_faker(seed: int) -> Faker:
    faker = Faker("en_IN")
    Faker.seed(seed)
    faker.seed_instance(seed)
    return faker


def build_random(seed: int) -> Random:
    return Random(seed)


def stable_uuid(*parts: str) -> UUID:
    token = "::".join(parts)
    return uuid5(NAMESPACE_URL, f"caseclock::{token}")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp_for_index(base: datetime, index: int, step_hours: int = 6) -> datetime:
    return base - timedelta(hours=index * step_hours)


def choose_weighted(rng: Random, weighted_choices: list[tuple[Any, float]]) -> Any:
    threshold = rng.random() * sum(weight for _, weight in weighted_choices)
    running = 0.0
    for choice, weight in weighted_choices:
        running += weight
        if threshold <= running:
            return choice
    return weighted_choices[-1][0]


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    return value


def default_case_stages() -> tuple[str, ...]:
    return (
        "investigation",
        "charge_sheet_draft",
        "charge_sheet_filed",
        "further_investigation",
    )


def default_offence_categories() -> tuple[str, ...]:
    return (
        "theft",
        "burglary",
        "robbery",
        "vehicle_theft",
        "assault",
        "public_order",
        "fraud",
        "forgery",
        "harassment",
        "narcotics",
    )


def clock_type_choices() -> tuple[ClockType, ...]:
    return (
        ClockType.INVESTIGATION_60_DAY,
        ClockType.INVESTIGATION_90_DAY,
        ClockType.DOCUMENT_SUPPLY,
        ClockType.FURTHER_INVESTIGATION,
    )