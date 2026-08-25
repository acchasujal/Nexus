"""Tests for CSV normalization helpers."""

from datetime import timezone
from decimal import Decimal

import pytest

from backend.app.db.ingestion.normalization import (
    CsvValidationError,
    canonicalize_csv_row,
    normalize_account,
    normalize_address,
    normalize_currency,
    normalize_ifsc,
    normalize_name,
    normalize_phone,
    normalize_vehicle,
    parse_non_negative_decimal,
    parse_utc_datetime,
)


def test_normalize_phone_formats_consistently() -> None:
    assert normalize_phone("+91 98450-12345") == "9845012345"
    assert normalize_phone("9845012345") == "9845012345"
    assert normalize_phone("+919845012345") == "9845012345"


def test_normalize_vehicle_formats() -> None:
    assert normalize_vehicle("ka-01 ab-1234") == "KA01AB1234"
    assert normalize_vehicle("KA 01 AB 1234") == "KA01AB1234"


def test_normalize_account_preserves_leading_zeroes() -> None:
    assert normalize_account("  0012-0007  ") == "00120007"


def test_normalize_ifsc_case() -> None:
    assert normalize_ifsc("sbin0001234") == "SBIN0001234"
    assert normalize_ifsc(" SBIN 0001234 ") == "SBIN0001234"


def test_text_and_currency_normalization() -> None:
    assert normalize_name("  Vikram   Sharma! ") == "vikram sharma"
    assert normalize_address("#4, MG Road, Bengaluru") == "4 mg road bengaluru"
    assert normalize_currency(" inr ") == "INR"


def test_utc_and_offset_timestamps() -> None:
    utc_value = parse_utc_datetime("2026-08-24T14:00:00Z")
    offset_value = parse_utc_datetime("2026-08-24T19:30:00+05:30")

    assert utc_value.tzinfo is not None
    assert utc_value.tzinfo == timezone.utc
    assert offset_value == utc_value


def test_invalid_dates_and_negative_amounts_raise() -> None:
    with pytest.raises(CsvValidationError):
        parse_utc_datetime("2026-02-30T14:00:00Z")
    with pytest.raises(CsvValidationError):
        parse_non_negative_decimal("-0.01")

    assert parse_non_negative_decimal("00012.50") == Decimal("12.50")


def test_canonicalize_csv_row_is_order_independent() -> None:
    first = canonicalize_csv_row({"b": "two", "a": "one"})
    second = canonicalize_csv_row({"a": "one", "b": "two"})
    assert first == second
