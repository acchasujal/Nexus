"""Synthetic and field surveillance-report CSV parser: CSV rows → validated records."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.app.core.graph.entities import SourceRecord

from ..contracts import (
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
    normalize_vehicle,
    parse_utc_datetime,
)

REQUIRED_COLUMNS = (
    "record_id",
    "report_id",
    "case_id",
    "observed_at",
    "subject_name",
    "observation_type",
    "location",
    "summary",
)
OPTIONAL_COLUMNS = (
    "source_agency",
    "officer_badge",
    "vehicle_registration",
    "phone_number",
    "source_reference",
    "national_id",
    "organization",
)


def _issue(
    row: Mapping[str, str],
    row_number: int,
    field_name: str,
    code: str,
    message: str,
    file_name: str,
) -> ParseIssue:
    return ParseIssue(
        source_type=SourceType.SURVEILLANCE_REPORT,
        file_name=file_name,
        row_number=row_number,
        record_id=row.get("record_id", "") or f"row-{row_number}",
        field_name=field_name,
        code=code,
        message=message,
        severity=IssueSeverity.ERROR,
    )


def _source_record(
    row: Mapping[str, str],
    batch_id: str,
    occurred_at: datetime,
    file_name: str,
) -> SourceRecord:
    canonical = canonicalize_csv_row(row)
    return SourceRecord(
        id=make_source_record_id(SourceType.SURVEILLANCE_REPORT.value, row),
        batch_id=batch_id,
        source_type=SourceType.SURVEILLANCE_REPORT.value,
        locator=f"{file_name}:{row.get('record_id', '')}",
        raw_excerpt=canonical,
        hash_algorithm="SHA-256",
        content_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        hash_version="v1",
        hashed_at=occurred_at,
        occurred_at=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
    )


def _parse_rows(
    result: CsvParseResult,
    batch_id: str,
    file_name: str,
) -> ParsedSourceBundle:
    """Parse surveillance CSV rows into validated observations."""
    source_records: dict[str, SourceRecord] = {}
    parsed_rows: list[dict[str, Any]] = []
    issues = list(result.issues)

    for row_number, row in enumerate(result.rows, start=2):
        try:
            record_id = row["record_id"].strip()
            report_id = row["report_id"].strip()
            case_id = row["case_id"].strip()
            subject_name = row["subject_name"].strip()
            observation_type = row["observation_type"].strip().upper()
            location = row["location"].strip()
            summary = row["summary"].strip()

            if not record_id or not report_id or not case_id or not subject_name or not location:
                raise CsvValidationError("record_id, report_id, case_id, subject_name, and location must not be empty")

            try:
                observed_at = parse_utc_datetime(row["observed_at"])
            except CsvValidationError as time_err:
                issues.append(_issue(row, row_number, "observed_at", "INVALID_TIMESTAMP", str(time_err), file_name))
                continue

            normalized_name = normalize_name(subject_name)

            # Optional fields
            phone = ""
            if row.get("phone_number", "").strip():
                try:
                    phone = normalize_phone(row["phone_number"])
                except CsvValidationError as phone_err:
                    issues.append(_issue(row, row_number, "phone_number", "INVALID_PHONE", str(phone_err), file_name))

            vehicle = ""
            if row.get("vehicle_registration", "").strip():
                try:
                    vehicle = normalize_vehicle(row["vehicle_registration"])
                except CsvValidationError as veh_err:
                    issues.append(_issue(row, row_number, "vehicle_registration", "INVALID_VEHICLE", str(veh_err), file_name))

            national_id = row.get("national_id", "").strip()
            source_agency = row.get("source_agency", "").strip() or "Surveillance Unit"
            officer_badge = row.get("officer_badge", "").strip()
            source_reference = row.get("source_reference", "").strip()
            organization = row.get("organization", "").strip()

            source_record = _source_record(row, batch_id, observed_at, file_name)
            source_records[source_record.id] = source_record

            parsed_rows.append({
                "record_id": record_id,
                "report_id": report_id,
                "case_id": case_id,
                "observed_at": observed_at,
                "subject_name": subject_name,
                "normalized_name": normalized_name,
                "observation_type": observation_type,
                "location": location,
                "summary": summary,
                "phone_number": phone,
                "vehicle_registration": vehicle,
                "national_id": national_id,
                "source_agency": source_agency,
                "officer_badge": officer_badge,
                "source_reference": source_reference,
                "organization": organization,
                "source_record_id": source_record.id,
                "raw_row": dict(row),
            })
        except (KeyError, CsvValidationError, ValueError) as exc:
            issues.append(_issue(row, row_number, "row", "INVALID_SURVEILLANCE_ROW", str(exc), file_name))

    accepted = len(source_records)
    summary = IngestionSummary(
        received_count=len(result.rows) + len(result.quarantined_rows),
        accepted_count=accepted,
        duplicate_count=result.summary.duplicate_count,
        conflict_count=result.summary.conflict_count,
        rejected_count=len(result.quarantined_rows) + (len(result.rows) - accepted),
        warning_count=sum(1 for issue in issues if issue.severity is IssueSeverity.WARNING),
        source_record_count=accepted,
    )

    return ParsedSourceBundle(
        batch_id=batch_id,
        source_type=SourceType.SURVEILLANCE_REPORT,
        file_name=file_name,
        source_records=list(source_records.values()),
        rows=parsed_rows,
        issues=issues,
        summary=summary,
    )


def parse_surveillance_source_file(
    path: str | Path,
    batch_id: str | None = None,
    file_name: str | None = None,
) -> ParsedSourceBundle:
    """Parse a surveillance CSV file."""
    path_obj = Path(path)
    effective_name = file_name or path_obj.name
    effective_batch = batch_id or f"batch-surveillance-{path_obj.stem}"
    result = read_csv_file(path_obj, source_type=SourceType.SURVEILLANCE_REPORT, file_name=effective_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, effective_batch, effective_name)


def parse_surveillance_source_bytes(
    data: bytes,
    batch_id: str,
    file_name: str,
) -> ParsedSourceBundle:
    """Parse raw bytes of a surveillance CSV file."""
    from ..csv_reader import read_csv_bytes
    result = read_csv_bytes(data, source_type=SourceType.SURVEILLANCE_REPORT, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)


def parse_surveillance_text(
    text: str,
    *,
    batch_id: str = "batch_surveillance",
    file_name: str = "surveillance_records.csv",
) -> ParsedSourceBundle:
    """Parse raw CSV text of a surveillance report."""
    result = parse_csv_text(text, source_type=SourceType.SURVEILLANCE_REPORT, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)
