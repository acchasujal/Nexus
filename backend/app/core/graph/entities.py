"""backend/app/core/graph/entities.py

Graph node models for the NEXUS unified intelligence graph.
Identifiers are strings or UUIDs. Every entity supports provenance and timestamps.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GraphEntityBase(BaseModel):
    id: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    source_id: Optional[str] = None
    source_type: Optional[str] = None
    confidence: float = 1.0
    properties: dict[str, Any] = Field(default_factory=dict)


class Person(GraphEntityBase):
    full_name: str = ""
    aliases: list[str] = Field(default_factory=list)
    phone_numbers: list[str] = Field(default_factory=list)
    vehicles: list[str] = Field(default_factory=list)
    addresses: list[str] = Field(default_factory=list)
    national_id: Optional[str] = None
    role_in_case: Optional[str] = None
    case_ids: list[str] = Field(default_factory=list)


class Case(GraphEntityBase):
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
    phone_number: str = ""
    imei: Optional[str] = None
    imsi: Optional[str] = None
    carrier: Optional[str] = None
    registered_owner: Optional[str] = None


class Vehicle(GraphEntityBase):
    registration_number: str = ""
    vehicle_type: str = ""  # e.g., "Car", "Motorcycle", "Truck"
    make: Optional[str] = None
    model: Optional[str] = None
    color: Optional[str] = None
    engine_number: Optional[str] = None
    chassis_number: Optional[str] = None
    owner_name: Optional[str] = None


class Location(GraphEntityBase):
    name: str = ""
    address: str = ""
    city: str = ""
    district: str = ""
    state: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_type: Optional[str] = None  # e.g., "CrimeScene", "Residence", "MeetingPoint"


class Organization(GraphEntityBase):
    name: str = ""
    org_type: str = ""  # e.g., "Gang", "Shell Company", "Enterprise", "Club"
    jurisdiction: Optional[str] = None
    registration_number: Optional[str] = None


class Device(GraphEntityBase):
    device_type: str = ""  # e.g., "Laptop", "Mobile", "HardDrive", "GPS Tracker"
    mac_address: Optional[str] = None
    serial_number: Optional[str] = None
    owner_id: Optional[str] = None


class Account(GraphEntityBase):
    account_number: str = ""
    bank_name: str = ""
    branch: Optional[str] = None
    ifsc_code: Optional[str] = None
    account_holder: Optional[str] = None


class Transaction(GraphEntityBase):
    transaction_id: str = ""
    from_account_id: str = ""
    to_account_id: str = ""
    amount: float = 0.0
    currency: str = "INR"
    timestamp: datetime = Field(default_factory=_utcnow)
    transaction_type: str = "TRANSFER"  # "WIRE", "CASH", "UPI", "CRYPTO"
    is_suspicious: bool = False


class Event(GraphEntityBase):
    event_type: str = ""  # "MEETING", "COMMUNICATION_BURST", "INCIDENT", "TRAVEL"
    description: str = ""
    timestamp: datetime = Field(default_factory=_utcnow)
    location_id: Optional[str] = None
    participant_ids: list[str] = Field(default_factory=list)


class IntelligenceReport(GraphEntityBase):
    report_id: str = ""
    title: str = ""
    source_agency: str = ""
    classification_level: str = "RESTRICTED"
    published_date: datetime = Field(default_factory=_utcnow)
    summary: str = ""
    mentioned_person_ids: list[str] = Field(default_factory=list)
    mentioned_org_ids: list[str] = Field(default_factory=list)


class Evidence(GraphEntityBase):
    evidence_number: str = ""
    case_id: str = ""
    evidence_type: str = ""  # "CDR", "CCTV", "BALLISTICS", "DOCUMENT", "FINANCIAL"
    collected_at: datetime = Field(default_factory=_utcnow)
    storage_location: Optional[str] = None
    description: str = ""
    file_path: Optional[str] = None
    hash_sha256: Optional[str] = None