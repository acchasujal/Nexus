"""Tests for deterministic CSV identifiers."""

from backend.app.db.ingestion.identifiers import (
    make_account_id,
    make_batch_id,
    make_case_id,
    make_phone_id,
    make_provisional_person_id,
    make_relationship_id,
    make_source_record_id,
    make_vehicle_id,
)


def test_repeated_id_generation_is_stable() -> None:
    row = {"record_id": "cdr_001", "caller": "+91 98450-12345"}

    factories = [
        lambda: make_batch_id("CDR", "batch_001"),
        lambda: make_source_record_id("CDR", row),
        lambda: make_phone_id("+91 98450-12345"),
        lambda: make_vehicle_id("KA-01 AB-1234"),
        lambda: make_account_id("0012-0007"),
        lambda: make_case_id("FIR/001/2026"),
        lambda: make_provisional_person_id("cdr_001", "CDR"),
        lambda: make_relationship_id("phone_a", "COMMUNICATED_WITH", "phone_b", "src_001"),
    ]

    for factory in factories:
        assert factory() == factory()


def test_source_record_id_changes_for_different_rows() -> None:
    first = make_source_record_id("CDR", {"record_id": "cdr_001", "duration": "30"})
    second = make_source_record_id("CDR", {"record_id": "cdr_002", "duration": "30"})
    assert first != second


def test_provisional_person_id_is_not_name_only() -> None:
    first = make_provisional_person_id("fir_row_001", "FIR")
    second = make_provisional_person_id("cdr_row_001", "CDR")
    assert first != second


def test_relationship_ids_preserve_distinct_source_rows() -> None:
    first = make_relationship_id("phone_a", "COMMUNICATED_WITH", "phone_b", "src_call_001")
    second = make_relationship_id("phone_a", "COMMUNICATED_WITH", "phone_b", "src_call_002")
    assert first != second


def test_ids_are_stable_uuid_strings() -> None:
    value = make_phone_id("9845012345")
    assert len(value) == 36
    assert value.count("-") == 4
