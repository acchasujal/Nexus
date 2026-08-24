"""Synthetic CDR CSV parser: CSV rows → validated records and identity claims."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from backend.app.core.graph.entities import SourceRecord

from ..contracts import (
    IngestionBundle,
    IngestionSummary,
    IssueSeverity,
    ParseIssue,
    ParsedSourceBundle,
    SourceType,
)
from ..csv_reader import CsvParseResult, parse_csv_text, read_csv_file
from ..identifiers import make_source_record_id
from ..normalization import CsvValidationError, canonicalize_csv_row, normalize_name, normalize_phone, parse_utc_datetime

REQUIRED_COLUMNS = (
    "record_id", "caller_number", "callee_number", "start_time", "duration_seconds", "call_type",
)
OPTIONAL_COLUMNS = (
    "end_time", "caller_imei", "callee_imei", "caller_subscriber_name", "caller_national_id",
    "callee_subscriber_name", "callee_national_id", "cell_location",
)


def _issue(row: Mapping[str, str], row_number: int, field_name: str, code: str, message: str, file_name: str) -> ParseIssue:
    return ParseIssue(
        source_type=SourceType.CDR,
        file_name=file_name,
        row_number=row_number,
        record_id=row.get("record_id", "") or f"row-{row_number}",
        field_name=field_name,
        code=code,
        message=message,
        severity=IssueSeverity.ERROR,
    )


def _source_record(row: Mapping[str, str], batch_id: str, occurred_at: datetime) -> SourceRecord:
    return SourceRecord(
        id=make_source_record_id(SourceType.CDR.value, row),
        batch_id=batch_id,
        source_type=SourceType.CDR.value,
        locator=f"cdr_records.csv:{row.get('record_id', '')}",
        raw_excerpt=canonicalize_csv_row(row),
        hash=hashlib.sha256(canonicalize_csv_row(row).encode("utf-8")).hexdigest(),
        occurred_at=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
    )


def _parse_rows(result: CsvParseResult, batch_id: str, file_name: str) -> ParsedSourceBundle:
    """Parse CDR CSV rows into validated records."""
    source_records: dict[str, SourceRecord] = {}
    parsed_rows: list[dict[str, Any]] = []
    issues = list(result.issues)

    for row_number, row in enumerate(result.rows, start=2):
        try:
            caller = normalize_phone(row["caller_number"])
            callee = normalize_phone(row["callee_number"])
            start_time = parse_utc_datetime(row["start_time"])
            end_time = parse_utc_datetime(row["end_time"]) if row.get("end_time", "").strip() else None
            if end_time is not None and end_time < start_time:
                raise CsvValidationError("end_time cannot be before start_time")
            duration_text = row["duration_seconds"].strip()
            duration = int(duration_text)
            if duration < 0:
                raise CsvValidationError("duration_seconds must be non-negative")
            if not row["call_type"].strip():
                raise CsvValidationError("call_type must not be empty")

            source_record = _source_record(row, batch_id, start_time)
            source_records[source_record.id] = source_record

            parsed_rows.append({
                "record_id": row["record_id"].strip(),
                "caller": caller,
                "callee": callee,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "call_type": row["call_type"].strip(),
                "caller_imei": row.get("caller_imei", "").strip(),
                "callee_imei": row.get("callee_imei", "").strip(),
                "cell_location": row.get("cell_location", "").strip(),
                "caller_subscriber_name": row.get("caller_subscriber_name", "").strip(),
                "caller_national_id": row.get("caller_national_id", "").strip(),
                "callee_subscriber_name": row.get("callee_subscriber_name", "").strip(),
                "callee_national_id": row.get("callee_national_id", "").strip(),
                "source_record_id": source_record.id,
                "raw_row": dict(row),
            })
        except (KeyError, CsvValidationError, ValueError) as exc:
            field_name = "start_time" if "timestamp" in str(exc) or "time" in str(exc) else "row"
            issues.append(_issue(row, row_number, field_name, "INVALID_CDR_ROW", str(exc), file_name))

    accepted = len(source_records)
    summary = IngestionSummary(
        received_count=len(result.rows) + len(result.quarantined_rows),
        accepted_count=accepted,
        duplicate_count=result.summary.duplicate_count,
        rejected_count=sum(1 for issue in issues if issue.severity is IssueSeverity.ERROR),
        warning_count=sum(1 for issue in issues if issue.severity is IssueSeverity.WARNING),
        source_record_count=accepted,
    )
    return ParsedSourceBundle(
        batch_id=batch_id,
        source_type=SourceType.CDR,
        file_name=file_name,
        source_records=list(source_records.values()),
        rows=parsed_rows,
        issues=issues,
        summary=summary,
    )


def parse_cdr_source(text: str, *, batch_id: str = "batch_cdr", file_name: str = "cdr_records.csv") -> ParsedSourceBundle:
    """Parse CDR CSV text into validated source records (no graph mapping)."""
    result = parse_csv_text(text, source_type=SourceType.CDR, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)


def parse_cdr_source_file(path: str | Path, *, batch_id: str = "batch_cdr") -> ParsedSourceBundle:
    """Read and parse a CDR CSV file into validated source records."""
    file_name = Path(path).name
    result = read_csv_file(path, source_type=SourceType.CDR, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)


def parse_cdr_text(text: str, *, batch_id: str = "batch_cdr", file_name: str = "cdr_records.csv") -> IngestionBundle:
    """Parse CDR CSV text into a V2 ingestion bundle (convenience: parser + mapper)."""
    from ..mappers.cdr import map_cdr_bundle
    parsed = parse_cdr_source(text, batch_id=batch_id, file_name=file_name)
    return map_cdr_bundle(parsed)


def parse_cdr_csv(path: str | Path, *, batch_id: str = "batch_cdr") -> IngestionBundle:
    """Read and parse a caller-selected synthetic CDR CSV file."""
    from ..mappers.cdr import map_cdr_bundle
    parsed = parse_cdr_source_file(path, batch_id=batch_id)
    return map_cdr_bundle(parsed)


__all__ = ["OPTIONAL_COLUMNS", "REQUIRED_COLUMNS", "parse_cdr_csv", "parse_cdr_source", "parse_cdr_source_file", "parse_cdr_text"]
