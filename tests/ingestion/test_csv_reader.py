"""Tests for safe common CSV parsing."""

from backend.app.db.ingestion.contracts import SourceType
from backend.app.db.ingestion.csv_reader import parse_csv_text, read_csv_bytes


def test_valid_utf8_and_row_tracking() -> None:
    result = parse_csv_text(
        "record_id,name\n1,किरण\n2,Andre\n",
        source_type=SourceType.FIR,
        file_name="fir.csv",
        required_columns=("record_id", "name"),
    )

    assert result.rows[0]["name"] == "किरण"
    assert result.summary.received_count == 2
    assert result.summary.accepted_count == 2


def test_missing_header() -> None:
    result = parse_csv_text("", source_type=SourceType.CDR, file_name="cdr.csv")
    assert result.issues[0].code == "MISSING_HEADER"
    assert result.issues[0].row_number == 1


def test_missing_required_column() -> None:
    result = parse_csv_text(
        "record_id,name\n1,Vikram\n",
        source_type=SourceType.FIR,
        file_name="fir.csv",
        required_columns=("record_id", "incident_time"),
    )
    assert any(issue.code == "MISSING_REQUIRED_COLUMN" for issue in result.issues)
    assert result.rows == []


def test_blank_row_is_quarantined_with_warning() -> None:
    result = parse_csv_text(
        "record_id,name\n1,Vikram\n\n2,Bikram\n",
        source_type=SourceType.FIR,
        file_name="fir.csv",
    )
    assert len(result.rows) == 2
    assert result.quarantined_rows[0]["row_number"] == 3
    assert result.issues[0].code == "BLANK_ROW"
    assert result.summary.warning_count == 1


def test_duplicate_raw_row_is_not_accepted_twice() -> None:
    result = parse_csv_text(
        "record_id,name\n1,Vikram\n1,Vikram\n2,Bikram\n",
        source_type=SourceType.CDR,
        file_name="cdr.csv",
    )
    assert len(result.rows) == 2
    assert result.summary.duplicate_count == 1
    assert any(issue.code == "DUPLICATE_ROW" and issue.row_number == 3 for issue in result.issues)


def test_oversized_field_is_quarantined() -> None:
    result = parse_csv_text(
        "record_id,name\n1,too-long\n",
        source_type=SourceType.FIR,
        file_name="fir.csv",
        max_field_length=3,
    )
    assert result.rows == []
    assert result.issues[0].code == "FIELD_TOO_LARGE"
    assert result.issues[0].row_number == 2


def test_malformed_unicode_is_reported() -> None:
    result = read_csv_bytes(
        b"record_id,name\n1,\xff\n",
        source_type=SourceType.FIR,
        file_name="fir.csv",
    )
    assert result.rows == []
    assert result.issues[0].code == "INVALID_UTF8"


def test_row_limit_is_reported_and_quarantined() -> None:
    result = parse_csv_text(
        "record_id\n1\n2\n3\n",
        source_type=SourceType.BANK_TXN,
        file_name="bank.csv",
        max_rows=2,
    )
    assert len(result.rows) == 2
    assert result.issues[-1].code == "ROW_LIMIT_EXCEEDED"
    assert result.summary.rejected_count == 1
