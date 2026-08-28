"""Synthetic FIR CSV parser: CSV rows → validated records and identity claims."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.app.core.graph.entities import SourceRecord
from backend.app.core.graph.enums import GraphRelationshipType

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
    normalize_address,
    normalize_name,
    normalize_phone,
    normalize_vehicle,
    parse_utc_datetime,
)

REQUIRED_COLUMNS = (
    "record_id", "fir_number", "fir_year", "station_name", "district",
    "incident_time", "offence_category", "section", "person_name", "person_role",
)
OPTIONAL_COLUMNS = ("phone_number", "vehicle_number", "address", "national_id")
ROLE_RELATIONSHIPS = {
    "ACCUSED": GraphRelationshipType.ACCUSED_IN,
    "VICTIM": GraphRelationshipType.VICTIM_IN,
    "COMPLAINANT": GraphRelationshipType.COMPLAINANT_IN,
    "WITNESS": GraphRelationshipType.WITNESS_IN,
}


def _semantic_issue(row: Mapping[str, str], row_number: int, field_name: str, code: str, message: str, file_name: str) -> ParseIssue:
    return ParseIssue(
        source_type=SourceType.FIR,
        file_name=file_name,
        row_number=row_number,
        record_id=row.get("record_id", "") or f"row-{row_number}",
        field_name=field_name,
        code=code,
        message=message,
        severity=IssueSeverity.ERROR,
    )


def _row_hash(row: Mapping[str, str]) -> str:
    return hashlib.sha256(canonicalize_csv_row(row).encode("utf-8")).hexdigest()


def _source_record(row: Mapping[str, str], batch_id: str, occurred_at: datetime, file_name: str) -> SourceRecord:
    record_id = make_source_record_id(SourceType.FIR.value, row)
    return SourceRecord(
        id=record_id,
        batch_id=batch_id,
        source_type=SourceType.FIR.value,
        locator=f"{file_name}:{row.get('record_id', '')}",
        raw_excerpt=canonicalize_csv_row(row),
        hash=_row_hash(row),
        occurred_at=occurred_at,
        created_at=occurred_at,
        updated_at=occurred_at,
    )


def _parse_rows(result: CsvParseResult, batch_id: str, file_name: str) -> ParsedSourceBundle:
    """Parse CSV rows into validated records and identity claims."""
    source_records: dict[str, SourceRecord] = {}
    parsed_rows: list[dict[str, Any]] = []
    issues = list(result.issues)

    for row_number, row in enumerate(result.rows, start=2):
        try:
            role = row["person_role"].strip().upper()
            if role not in ROLE_RELATIONSHIPS:
                issues.append(_semantic_issue(row, row_number, "person_role", "UNKNOWN_ROLE", "Unsupported FIR person role", file_name))
                continue
            incident_time = parse_utc_datetime(row["incident_time"])
            name = normalize_name(row["person_name"])
            if not name:
                raise CsvValidationError("person_name must not be empty")
            phone = normalize_phone(row["phone_number"]) if row.get("phone_number", "").strip() else ""
            vehicle = normalize_vehicle(row["vehicle_number"]) if row.get("vehicle_number", "").strip() else ""
            address = normalize_address(row["address"]) if row.get("address", "").strip() else ""
            national_id = row.get("national_id", "").strip()

            source_record = _source_record(row, batch_id, incident_time, file_name)
            source_records[source_record.id] = source_record

            parsed_rows.append({
                "record_id": row["record_id"].strip(),
                "role": role,
                "incident_time": incident_time,
                "name": name,
                "raw_person_name": row["person_name"].strip(),
                "phone": phone,
                "vehicle": vehicle,
                "address": address,
                "raw_address": row.get("address", "").strip(),
                "national_id": national_id,
                "fir_number": row["fir_number"].strip(),
                "fir_year": row["fir_year"].strip(),
                "station_name": row["station_name"].strip(),
                "district": row["district"].strip(),
                "offence_category": row["offence_category"].strip(),
                "section": row["section"].strip(),
                "source_record_id": source_record.id,
                "raw_row": dict(row),
            })
        except (KeyError, CsvValidationError, ValueError) as exc:
            field = "incident_time" if "timestamp" in str(exc) else "row"
            issues.append(_semantic_issue(row, row_number, field, "INVALID_FIR_ROW", str(exc), file_name))

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
        source_record_count=accepted,
    )
    return ParsedSourceBundle(
        batch_id=batch_id,
        source_type=SourceType.FIR,
        file_name=file_name,
        source_records=list(source_records.values()),
        rows=parsed_rows,
        issues=issues,
        summary=summary,
    )


def parse_fir_source(text: str, *, batch_id: str = "batch_fir", file_name: str = "fir_records.csv") -> ParsedSourceBundle:
    """Parse FIR CSV text into validated source records (no graph mapping)."""
    result = parse_csv_text(text, source_type=SourceType.FIR, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)


def parse_fir_source_bytes(data: bytes, *, batch_id: str = "batch_fir", file_name: str = "fir_records.csv") -> ParsedSourceBundle:
    """Parse FIR CSV bytes into validated source records (no graph mapping)."""
    from ..csv_reader import read_csv_bytes
    result = read_csv_bytes(data, source_type=SourceType.FIR, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)


def parse_fir_source_file(path: str | Path, *, batch_id: str = "batch_fir") -> ParsedSourceBundle:
    """Read and parse a FIR CSV file into validated source records (no graph mapping)."""
    result = read_csv_file(path, source_type=SourceType.FIR, file_name=Path(path).name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, Path(path).name)


def parse_fir_text(text: str, *, batch_id: str = "batch_fir", file_name: str = "fir_records.csv") -> IngestionBundle:
    """Parse FIR CSV text into a V2 ingestion bundle (convenience: parser + mapper)."""
    from ..mappers.fir import map_fir_bundle
    parsed = parse_fir_source(text, batch_id=batch_id, file_name=file_name)
    return map_fir_bundle(parsed)


def parse_fir_csv(path: str | Path, *, batch_id: str = "batch_fir") -> IngestionBundle:
    """Read and parse a caller-selected synthetic FIR CSV file."""
    from ..mappers.fir import map_fir_bundle
    parsed = parse_fir_source_file(path, batch_id=batch_id)
    return map_fir_bundle(parsed)


__all__ = ["OPTIONAL_COLUMNS", "REQUIRED_COLUMNS", "parse_fir_csv", "parse_fir_source", "parse_fir_source_bytes", "parse_fir_source_file", "parse_fir_text"]
