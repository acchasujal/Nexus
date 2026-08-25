"""Pure normalization and CSV value-validation helpers."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from backend.app.core.graph.algorithms.entity_resolution import (
    clean_phone,
    clean_vehicle,
    normalize_text,
)

from .exceptions import CsvValidationError


def _require_text(value: Any, field_name: str) -> str:
    if value is None or not str(value).strip():
        raise CsvValidationError(f"{field_name} must not be empty")
    return str(value).strip()


def normalize_phone(value: Any) -> str:
    """Return an Indian phone number as ten digits."""
    raw = _require_text(value, "phone")
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) != 10 or digits[0] not in "6789":
        raise CsvValidationError("phone must be a valid ten-digit Indian number")
    return clean_phone(digits)


def normalize_vehicle(value: Any) -> str:
    """Return a vehicle registration without separators, in uppercase."""
    normalized = clean_vehicle(_require_text(value, "vehicle"))
    if not re.fullmatch(r"[A-Z0-9]+", normalized):
        raise CsvValidationError("vehicle contains invalid characters")
    return normalized


def normalize_account(value: Any) -> str:
    """Return an account identifier as text, preserving leading zeroes."""
    normalized = re.sub(r"[\s-]", "", _require_text(value, "account"))
    if not re.fullmatch(r"[A-Za-z0-9]+", normalized):
        raise CsvValidationError("account contains invalid characters")
    return normalized.upper()


def normalize_ifsc(value: Any) -> str:
    """Return an uppercase, separator-free IFSC code."""
    normalized = re.sub(r"\s+", "", _require_text(value, "IFSC")).upper()
    if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", normalized):
        raise CsvValidationError("IFSC must match the Indian eleven-character format")
    return normalized


def normalize_name(value: Any) -> str:
    """Return a lowercase, whitespace-normalized name."""
    return normalize_text(_require_text(value, "name"))


def normalize_address(value: Any) -> str:
    """Return a lowercase, punctuation-normalized address."""
    return normalize_text(_require_text(value, "address"))


def normalize_currency(value: Any) -> str:
    """Return a three-letter uppercase currency code."""
    normalized = _require_text(value, "currency").upper()
    if not re.fullmatch(r"[A-Z]{3}", normalized):
        raise CsvValidationError("currency must be a three-letter code")
    return normalized


def parse_utc_datetime(value: Any) -> datetime:
    """Parse an ISO-8601 timestamp and return an aware UTC datetime."""
    raw = _require_text(value, "timestamp")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CsvValidationError("timestamp must be valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CsvValidationError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def parse_non_negative_decimal(value: Any) -> Decimal:
    """Parse a decimal amount and reject negative or invalid values."""
    raw = _require_text(value, "amount")
    try:
        amount = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise CsvValidationError("amount must be a valid decimal") from exc
    if not amount.is_finite() or amount < 0:
        raise CsvValidationError("amount must be finite and non-negative")
    return amount


def canonicalize_csv_row(row: Mapping[str, Any]) -> str:
    """Serialize a row deterministically for hashing and stable identifiers."""
    if not isinstance(row, Mapping):
        raise CsvValidationError("row must be a mapping")
    try:
        return json.dumps(
            {str(key): row[key] for key in sorted(row, key=lambda item: str(item))},
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    except (TypeError, ValueError) as exc:
        raise CsvValidationError("row contains a value that cannot be canonicalized") from exc
