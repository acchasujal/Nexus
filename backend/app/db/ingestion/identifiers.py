"""Deterministic identifiers for synthetic CSV ingestion records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from synthetic_data.configs import stable_uuid

from .normalization import (
    canonicalize_csv_row,
    normalize_account,
    normalize_phone,
    normalize_vehicle,
)


def _stable_id(*parts: str) -> str:
    return str(stable_uuid(*parts))


def make_batch_id(source_type: str, batch_key: str) -> str:
    """Create a stable batch ID from source type and batch key."""
    return _stable_id("batch", str(source_type).strip().upper(), str(batch_key).strip())


def make_source_record_id(source_type: str, row: Mapping[str, Any]) -> str:
    """Create an ID from source type and canonical row content."""
    return _stable_id("source_record", str(source_type).strip().upper(), canonicalize_csv_row(row))


def make_phone_id(phone: Any) -> str:
    """Create a stable ID from a normalized phone number."""
    return _stable_id("phone", normalize_phone(phone))


def make_vehicle_id(vehicle: Any) -> str:
    """Create a stable ID from a normalized vehicle registration."""
    return _stable_id("vehicle", normalize_vehicle(vehicle))


def make_account_id(account: Any) -> str:
    """Create a stable ID from a normalized account identifier."""
    return _stable_id("account", normalize_account(account))


def make_case_id(fir_number: str) -> str:
    """Create a stable ID from a case's FIR number."""
    key = str(fir_number).strip().upper()
    if not key:
        raise ValueError("fir_number must not be empty")
    return _stable_id("case", key)


def make_provisional_person_id(record_id: str, source_type: str) -> str:
    """Create a provisional ID from source identity, never only a name."""
    if not str(record_id).strip() or not str(source_type).strip():
        raise ValueError("record_id and source_type must not be empty")
    return _stable_id("provisional_person", str(source_type).strip().upper(), str(record_id).strip())


def make_relationship_id(
    source_id: str,
    relationship_type: str,
    target_id: str,
    source_record_id: str,
) -> str:
    """Create a stable relationship ID that preserves source-row uniqueness."""
    parts = (source_id, relationship_type, target_id, source_record_id)
    if any(not str(part).strip() for part in parts):
        raise ValueError("relationship identity parts must not be empty")
    return _stable_id("relationship", *(str(part).strip() for part in parts))


__all__ = [
    "make_account_id",
    "make_batch_id",
    "make_case_id",
    "make_phone_id",
    "make_provisional_person_id",
    "make_relationship_id",
    "make_source_record_id",
    "make_vehicle_id",
]
