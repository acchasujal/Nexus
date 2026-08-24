"""Tests for ingestion quality summaries."""

from backend.app.db.ingestion.contracts import SourceType
from backend.app.db.ingestion.csv_reader import parse_csv_text
from backend.app.db.ingestion.quality import calculate_ingestion_summary


def test_summary_counts_valid_duplicate_blank_and_rejected_rows() -> None:
    result = parse_csv_text(
        "record_id,name\n"
        "1,Vikram\n"
        "1,Vikram\n"
        "\n"
        "2,Bikram\n"
        "3\n",
        source_type=SourceType.FIR,
        file_name="fir.csv",
    )

    summary = calculate_ingestion_summary(result)
    assert summary.received_count == 5
    assert summary.accepted_count == 2
    assert summary.duplicate_count == 1
    assert summary.rejected_count == 1
    assert summary.warning_count == 2
    assert summary.source_record_count == 2


def test_quality_summary_is_safe_for_empty_result() -> None:
    result = parse_csv_text("", source_type=SourceType.CDR, file_name="empty.csv")
    summary = calculate_ingestion_summary(result)
    assert summary.received_count == 0
    assert summary.accepted_count == 0
    assert summary.rejected_count == 0
    assert summary.warning_count == 0
