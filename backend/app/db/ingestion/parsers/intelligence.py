"""Synthetic intelligence-report CSV parser: CSV rows → validated records."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.app.core.graph.entities import SourceRecord

from ..contracts import (
    IngestionBundle,
    IngestionSummary,
    IssueSeverity,
    ParsedSourceBundle,
    ParseIssue,
    SourceType,
)
from ..csv_reader import CsvParseResult, parse_csv_text, read_csv_file
from ..identifiers import make_source_record_id
from ..normalization import (
    CsvValidationError,
    canonicalize_csv_row,
    normalize_name,
    normalize_phone,
    parse_utc_datetime,
)

REQUIRED_COLUMNS = (
    "record_id", "report_id", "report_date", "source_agency", "classification", "subject_name", "summary",
)
OPTIONAL_COLUMNS = ("alias", "phone_number", "national_id", "organization", "location")


def _issue(row: Mapping[str, str], row_number: int, field_name: str, code: str, message: str, file_name: str) -> ParseIssue:
    return ParseIssue(source_type=SourceType.INTEL_REPORT, file_name=file_name, row_number=row_number, record_id=row.get("record_id", "") or f"row-{row_number}", field_name=field_name, code=code, message=message, severity=IssueSeverity.ERROR)


def _source_record(row: Mapping[str, str], batch_id: str, occurred_at: datetime, file_name: str) -> SourceRecord:
    canonical = canonicalize_csv_row(row)
    return SourceRecord(id=make_source_record_id(SourceType.INTEL_REPORT.value, row), batch_id=batch_id, source_type=SourceType.INTEL_REPORT.value, locator=f"{file_name}:{row.get('record_id', '')}", raw_excerpt=canonical, hash_algorithm="SHA-256", content_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(), hash_version="v1", hashed_at=occurred_at, occurred_at=occurred_at, created_at=occurred_at, updated_at=occurred_at)


def _parse_rows(result: CsvParseResult, batch_id: str, file_name: str) -> ParsedSourceBundle:
    """Parse intelligence CSV rows into validated records."""
    source_records: dict[str, SourceRecord] = {}
    parsed_rows: list[dict[str, Any]] = []
    issues = list(result.issues)

    for row_number, row in enumerate(result.rows, start=2):
        try:
            report_id_value = row["report_id"].strip()
            subject_name = row["subject_name"].strip()
            if not report_id_value or not subject_name:
                raise CsvValidationError("report_id and subject_name must not be empty")
            report_date = parse_utc_datetime(row["report_date"])
            normalized_name = normalize_name(subject_name)
            alias = normalize_name(row["alias"]) if row.get("alias", "").strip() else ""
            phone = normalize_phone(row["phone_number"]) if row.get("phone_number", "").strip() else ""
            national_id = row.get("national_id", "").strip()
            organization = row.get("organization", "").strip()

            source_record = _source_record(row, batch_id, report_date, file_name)
            source_records[source_record.id] = source_record

            parsed_rows.append({
                "record_id": row["record_id"].strip(),
                "report_id": report_id_value,
                "report_date": report_date,
                "source_agency": row["source_agency"].strip(),
                "classification": row["classification"].strip(),
                "subject_name": subject_name,
                "normalized_name": normalized_name,
                "summary": row["summary"].strip(),
                "alias": alias,
                "raw_alias": row.get("alias", "").strip(),
                "phone": phone,
                "national_id": national_id,
                "organization": organization,
                "location": row.get("location", "").strip(),
                "source_record_id": source_record.id,
                "raw_row": dict(row),
            })
        except (KeyError, CsvValidationError, ValueError) as exc:
            issues.append(_issue(row, row_number, "row", "INVALID_INTELLIGENCE_ROW", str(exc), file_name))

    accepted = len(source_records)
    rejected_rows = {
        (issue.file_name, issue.row_number)
        for issue in issues
        if issue.severity is IssueSeverity.ERROR
        and issue.code not in {"MISSING_HEADER", "MISSING_REQUIRED_COLUMN", "INVALID_HEADER", "DUPLICATE_HEADER"}
        and issue.row_number is not None
    }
    summary = IngestionSummary(
        received_count=len(result.rows) + len(result.quarantined_rows),
        accepted_count=accepted,
        duplicate_count=result.summary.duplicate_count,
        conflict_count=result.summary.conflict_count,
        rejected_count=len(rejected_rows),
        warning_count=sum(1 for issue in issues if issue.severity is IssueSeverity.WARNING),
        source_record_count=accepted
    )
    return ParsedSourceBundle(
        batch_id=batch_id,
        source_type=SourceType.INTEL_REPORT,
        file_name=file_name,
        source_records=list(source_records.values()),
        rows=parsed_rows,
        issues=issues,
        summary=summary,
    )


def parse_intelligence_source(text: str, *, batch_id: str = "batch_intelligence", file_name: str = "intelligence_records.csv") -> ParsedSourceBundle:
    """Parse intelligence CSV text into validated source records (no graph mapping)."""
    result = parse_csv_text(text, source_type=SourceType.INTEL_REPORT, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)


def parse_intelligence_source_bytes(data: bytes, *, batch_id: str = "batch_intelligence", file_name: str = "intelligence_records.csv") -> ParsedSourceBundle:
    """Parse intelligence CSV bytes into validated source records."""
    from ..csv_reader import read_csv_bytes
    result = read_csv_bytes(data, source_type=SourceType.INTEL_REPORT, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)


def parse_intelligence_source_file(path: str | Path, *, batch_id: str = "batch_intelligence") -> ParsedSourceBundle:
    """Read and parse an intelligence CSV file into validated source records."""
    file_name = Path(path).name
    result = read_csv_file(path, source_type=SourceType.INTEL_REPORT, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)


def parse_intelligence_text(text: str, *, batch_id: str = "batch_intelligence", file_name: str = "intelligence_records.csv") -> IngestionBundle:
    """Parse intelligence CSV text into a V2 ingestion bundle (convenience: parser + mapper)."""
    from ..mappers.intelligence import map_intelligence_bundle
    parsed = parse_intelligence_source(text, batch_id=batch_id, file_name=file_name)
    return map_intelligence_bundle(parsed)


def parse_intelligence_csv(path: str | Path, *, batch_id: str = "batch_intelligence") -> IngestionBundle:
    """Read and parse a caller-selected synthetic intelligence CSV file."""
    from ..mappers.intelligence import map_intelligence_bundle
    parsed = parse_intelligence_source_file(path, batch_id=batch_id)
    return map_intelligence_bundle(parsed)


__all__ = ["OPTIONAL_COLUMNS", "REQUIRED_COLUMNS", "parse_intelligence_csv", "parse_intelligence_source", "parse_intelligence_source_bytes", "parse_intelligence_source_file", "parse_intelligence_text"]
