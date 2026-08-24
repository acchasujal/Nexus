"""backend/app/core/graph/entities.py

Graph node models for the NEXUS unified intelligence graph (Schema V2).
Every node supports canonical_label, aliases, attributes, confidence, provenance, and timestamps.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import GraphEntityType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GraphEntityBase(BaseModel):
    """
    Canonical Schema V2 Node Base Contract.

    Fields:
      id              : Stable string identifier (non-empty)
      entity_type     : Strongly-typed GraphEntityType enum
      canonical_label : Human-readable display label
      aliases         : Alternative names / aliases list
      attributes      : Structured metadata dictionary
      confidence      : Numeric confidence score (0.0 <= confidence <= 1.0)
      created_at      : Node creation timestamp
      updated_at      : Node update timestamp
      source_id       : Underlying record source ID (if direct)
      source_type     : Underlying record source type (if direct)
      properties      : Legacy property dictionary (kept in sync with attributes)
    """
    id: str
    entity_type: GraphEntityType = GraphEntityType.PERSON
    canonical_label: str = ""
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    source_id: Optional[str] = None
    source_type: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Node id must be a non-empty string")
        return str(v).strip()

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Node confidence must be between 0.0 and 1.0, got {v}")
        return float(v)

    @model_validator(mode="after")
    def sync_canonical_fields(self) -> GraphEntityBase:
        # 1. Collect subclass entity-specific attributes
        subclass_attrs: dict[str, Any] = {}
        for k, v in self.__dict__.items():
            if k not in (
                "id",
                "entity_type",
                "canonical_label",
                "aliases",
                "confidence",
                "created_at",
                "updated_at",
                "source_id",
                "source_type",
                "attributes",
                "properties",
            ):
                if v is not None:
                    subclass_attrs[k] = v

        # 2. Sync properties <-> attributes
        merged = {**subclass_attrs, **self.attributes, **self.properties}
        self.attributes = merged
        self.properties = dict(merged)

        # 3. Extract canonical label if not explicitly provided
        if not self.canonical_label:
            props = self.properties or self.attributes
            self.canonical_label = (
                props.get("canonical_label")
                or getattr(self, "full_name", "")
                or getattr(self, "phone_number", "")
                or getattr(self, "registration_number", "")
                or getattr(self, "account_number", "")
                or getattr(self, "name", "")
                or getattr(self, "title", "")
                or getattr(self, "fir_number", "")
                or getattr(self, "locator", "")
                or getattr(self, "description", "")
                or props.get("full_name")
                or props.get("name")
                or props.get("title")
                or props.get("phone_number")
                or props.get("registration_number")
                or props.get("account_number")
                or self.id
            )

        # 4. Sync aliases if subclass has explicit aliases
        if not self.aliases and hasattr(self, "aliases"):
            subclass_aliases = getattr(self, "aliases", [])
            if isinstance(subclass_aliases, list) and subclass_aliases:
                self.aliases = list(subclass_aliases)
        elif self.aliases and hasattr(self, "aliases"):
            subclass_aliases = getattr(self, "aliases", [])
            if not subclass_aliases:
                setattr(self, "aliases", list(self.aliases))

        return self


class Node(GraphEntityBase):
    """Generic Schema V2 Node representation for arbitrary canonical graph objects."""
    pass


class Person(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.PERSON
    full_name: str = ""
    aliases: list[str] = Field(default_factory=list)
    phone_numbers: list[str] = Field(default_factory=list)
    vehicles: list[str] = Field(default_factory=list)
    addresses: list[str] = Field(default_factory=list)
    national_id: Optional[str] = None
    role_in_case: Optional[str] = None
    case_ids: list[str] = Field(default_factory=list)


class Case(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.CASE
    fir_number: str = ""
    title: str = ""
    station_name: str = ""
    district: str = ""
    state: str = ""
    offence_category: str = ""
    incident_date: Optional[datetime] = None
    status: str = "OPEN"
    summary: str = ""
    sections: list[str] = Field(default_factory=list)
    accused_ids: list[str] = Field(default_factory=list)
    victim_ids: list[str] = Field(default_factory=list)


class Phone(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.PHONE
    phone_number: str = ""
    imei: Optional[str] = None
    imsi: Optional[str] = None
    carrier: Optional[str] = None
    registered_owner: Optional[str] = None


class Vehicle(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.VEHICLE
    registration_number: str = ""
    vehicle_type: str = ""  # e.g., "Car", "Motorcycle", "Truck"
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    engine_number: Optional[str] = None
    chassis_number: Optional[str] = None
    owner_name: Optional[str] = None


class Location(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.LOCATION
    name: str = ""
    address: str = ""
    city: str = ""
    district: str = ""
    state: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_type: Optional[str] = None  # e.g., "CrimeScene", "Residence", "MeetingPoint"


class Organization(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.ORGANIZATION
    name: str = ""
    org_type: str = ""  # e.g., "Gang", "Shell Company", "Enterprise", "Club"
    jurisdiction: Optional[str] = None
    registration_number: Optional[str] = None


class Device(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.DEVICE
    device_type: str = ""  # e.g., "Laptop", "Mobile", "HardDrive", "GPS Tracker"
    mac_address: Optional[str] = None
    serial_number: Optional[str] = None
    owner_id: Optional[str] = None


class Account(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.ACCOUNT
    account_number: str = ""
    bank_name: str = ""
    branch: Optional[str] = None
    ifsc_code: Optional[str] = None
    account_holder: Optional[str] = None


class Transaction(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.TRANSACTION
    transaction_id: str = ""
    from_account_id: str = ""
    to_account_id: str = ""
    amount: float = 0.0
    currency: str = "INR"
    timestamp: datetime = Field(default_factory=_utcnow)
    transaction_type: str = "TRANSFER"  # "WIRE", "CASH", "UPI", "CRYPTO"
    is_suspicious: bool = False


class Event(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.EVENT
    event_type: str = ""  # "MEETING", "COMMUNICATION_BURST", "INCIDENT", "TRAVEL"
    description: str = ""
    timestamp: datetime = Field(default_factory=_utcnow)
    location_id: Optional[str] = None
    participant_ids: list[str] = Field(default_factory=list)


class SourceRecord(GraphEntityBase):
    """
    First-class SourceRecord entity for data lineage and evidence provenance (Schema V2).
    
    Fields:
      id          : Unique record identifier
      batch_id    : Ingestion batch ID
      source_type : Data source category ("CDR", "BANK_TXN", "FIR", "INTEL_REPORT")
      locator     : Record location pointer (file name, line number, UTR, FIR #)
      raw_excerpt : Original raw text/log snippet or JSON payload
      hash        : Cryptographic SHA-256 hash of the raw record
      occurred_at : Timestamp when the underlying record event occurred
    """
    entity_type: GraphEntityType = GraphEntityType.SOURCE_RECORD
    batch_id: str = ""
    source_type: str = "DIRECT_RECORD"
    locator: str = ""
    raw_excerpt: Optional[str] = None
    hash: Optional[str] = None
    occurred_at: datetime = Field(default_factory=_utcnow)


class IntelligenceReport(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.INTELLIGENCE_REPORT
    report_id: str = ""
    title: str = ""
    source_agency: str = ""
    classification_level: str = "RESTRICTED"
    published_date: datetime = Field(default_factory=_utcnow)
    summary: str = ""
    mentioned_person_ids: list[str] = Field(default_factory=list)
    mentioned_org_ids: list[str] = Field(default_factory=list)


class Evidence(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.EVIDENCE
    evidence_number: str = ""
    case_id: str = ""
    evidence_type: str = ""  # "CDR", "CCTV", "BALLISTICS", "DOCUMENT", "FINANCIAL"
    collected_at: datetime = Field(default_factory=_utcnow)
    storage_location: Optional[str] = None
    description: str = ""
    file_path: Optional[str] = None
    hash_sha256: Optional[str] = None


class Officer(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.OFFICER
    badge_number: str = ""
    name: str = ""
    rank: str = ""
    station_id: Optional[str] = None


class Unit(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.UNIT
    name: str = ""
    unit_type: str = ""
    district: str = ""


class Court(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.COURT
    name: str = ""
    jurisdiction: str = ""


class Act(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.ACT
    name: str = ""
    code: str = ""


class Section(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.SECTION
    act_id: str = ""
    section_number: str = ""
    title: str = ""


class CrimeHead(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.CRIME_HEAD
    name: str = ""


class CrimeSubHead(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.CRIME_SUB_HEAD
    crime_head_id: str = ""
    name: str = ""