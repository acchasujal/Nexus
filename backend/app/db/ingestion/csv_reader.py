"""Safe, standard-library CSV parsing primitives."""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import IngestionSummary, IssueSeverity, ParseIssue, SourceType
from .normalization import CsvValidationError, canonicalize_csv_row
from .quality import calculate_ingestion_summary


@dataclass
class CsvParseResult:
    """Rows and quality information produced by one CSV parse."""

    rows: list[dict[str, str]] = field(default_factory=list)
    quarantined_rows: list[dict[str, Any]] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)
    duplicate_hashes: set[str] = field(default_factory=set)
    summary: IngestionSummary = field(default_factory=IngestionSummary)


def _issue(
    source_type: SourceType,
    file_name: str,
    row_number: int,
    code: str,
    message: str,
    severity: IssueSeverity,
    field_name: str = "",
    record_id: str | None = None,
) -> ParseIssue:
    return ParseIssue(
        source_type=source_type,
        file_name=file_name,
        row_number=max(row_number, 1),
        record_id=record_id or f"row-{max(row_number, 1)}",
        field_name=field_name,
        code=code,
        message=message,
        severity=severity,
    )


def _record_id(row: Mapping[str, str], row_number: int) -> str:
    """Use only an explicit row identifier, never a sensitive field as an ID."""
    value = row.get("record_id", "").strip()
    return value or f"row-{row_number}"


def _validate_header(
    header: list[str],
    required_columns: Iterable[str],
    source_type: SourceType,
    file_name: str,
) -> list[ParseIssue]:
    issues: list[ParseIssue] = []
    if not header:
        return [_issue(source_type, file_name, 1, "MISSING_HEADER", "CSV header is missing", IssueSeverity.ERROR)]
    normalized = [column.strip() for column in header]
    if any(not column for column in normalized):
        issues.append(_issue(source_type, file_name, 1, "INVALID_HEADER", "CSV header contains an empty column", IssueSeverity.ERROR))
    seen: set[str] = set()
    if len(normalized) != len(set(normalized)):
        issues.append(_issue(source_type, file_name, 1, "DUPLICATE_HEADER", "CSV header contains duplicate columns", IssueSeverity.ERROR))
    for column in required_columns:
        if column not in normalized:
            issues.append(_issue(source_type, file_name, 1, "MISSING_REQUIRED_COLUMN", f"Required column '{column}' is missing", IssueSeverity.ERROR, column))
    seen.update(normalized)
    return issues


def parse_csv_text(
    text: str,
    *,
    source_type: SourceType,
    file_name: str,
    required_columns: Iterable[str] = (),
    max_rows: int = 10_000,
    max_field_length: int = 10_000,
) -> CsvParseResult:
    """Parse CSV text without executing or interpreting cell contents."""
    result = CsvParseResult()
    if not isinstance(text, str):
        result.issues.append(_issue(source_type, file_name, 1, "INVALID_TEXT", "CSV input must be text", IssueSeverity.ERROR))
        result.summary = calculate_ingestion_summary(result)
        return result

    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader, [])
        header_issues = _validate_header(header, required_columns, source_type, file_name)
        result.issues.extend(header_issues)
        if any(issue.severity is IssueSeverity.ERROR for issue in header_issues):
            result.summary = calculate_ingestion_summary(result)
            return result

        canonical_hashes: set[str] = set()
        seen_record_ids: dict[str, str] = {}
        for row_number, values in enumerate(reader, start=2):
            if row_number > max_rows + 1:
                result.quarantined_rows.append({"row_number": row_number, "raw": values})
                result.issues.append(_issue(source_type, file_name, row_number, "ROW_LIMIT_EXCEEDED", "CSV row limit exceeded", IssueSeverity.ERROR))
                continue
            if not values or all(not value.strip() for value in values):
                result.quarantined_rows.append({"row_number": row_number, "raw": values})
                result.issues.append(_issue(source_type, file_name, row_number, "BLANK_ROW", "Blank CSV row ignored", IssueSeverity.WARNING))
                continue
            if len(values) != len(header):
                result.quarantined_rows.append({"row_number": row_number, "raw": values})
                result.issues.append(_issue(source_type, file_name, row_number, "COLUMN_COUNT_MISMATCH", "CSV row does not match the header", IssueSeverity.ERROR))
                continue
            row = {header[index].strip(): values[index] for index in range(len(header))}
            oversized = next(((key, value) for key, value in row.items() if len(value) > max_field_length), None)
            if oversized:
                result.quarantined_rows.append({"row_number": row_number, "raw": values})
                result.issues.append(_issue(source_type, file_name, row_number, "FIELD_TOO_LARGE", "CSV field exceeds the configured length limit", IssueSeverity.ERROR, oversized[0], _record_id(row, row_number)))
                continue
            row_hash = hashlib.sha256(canonicalize_csv_row(row).encode("utf-8")).hexdigest()
            explicit_id = row.get("record_id", "").strip()
            
            if row_hash in canonical_hashes:
                result.duplicate_hashes.add(row_hash)
                result.quarantined_rows.append({"row_number": row_number, "raw": values})
                result.issues.append(_issue(source_type, file_name, row_number, "DUPLICATE_ROW", "Duplicate CSV row ignored", IssueSeverity.WARNING, record_id=_record_id(row, row_number)))
                continue
                
            if explicit_id:
                if explicit_id in seen_record_ids and seen_record_ids[explicit_id] != row_hash:
                    result.quarantined_rows.append({"row_number": row_number, "raw": values})
                    result.issues.append(_issue(source_type, file_name, row_number, "CONFLICTING_RECORD", "Record ID already exists with different content", IssueSeverity.ERROR, record_id=explicit_id))
                    continue
                seen_record_ids[explicit_id] = row_hash
                
            canonical_hashes.add(row_hash)
            result.rows.append(row)
    except csv.Error:
        result.issues.append(_issue(source_type, file_name, 1, "MALFORMED_CSV", "Malformed CSV structure", IssueSeverity.ERROR))
    except (UnicodeError, CsvValidationError):
        result.issues.append(_issue(source_type, file_name, 1, "INVALID_ENCODING", "CSV contains invalid UTF-8 or row data", IssueSeverity.ERROR))

    result.summary = calculate_ingestion_summary(result)
    return result


def read_csv_bytes(
    data: bytes,
    *,
    source_type: SourceType,
    file_name: str,
    required_columns: Iterable[str] = (),
    max_rows: int = 10_000,
    max_field_length: int = 10_000,
) -> CsvParseResult:
    """Decode UTF-8 bytes strictly, then delegate parsing to pure text logic."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        result = CsvParseResult()
        result.issues.append(_issue(source_type, file_name, 1, "INVALID_UTF8", "CSV is not valid UTF-8", IssueSeverity.ERROR))
        result.summary = calculate_ingestion_summary(result)
        return result
    return parse_csv_text(text, source_type=source_type, file_name=file_name, required_columns=required_columns, max_rows=max_rows, max_field_length=max_field_length)


def read_csv_file(
    path: str | Path,
    *,
    source_type: SourceType,
    file_name: str | None = None,
    required_columns: Iterable[str] = (),
    max_rows: int = 10_000,
    max_field_length: int = 10_000,
) -> CsvParseResult:
    """Read a caller-selected UTF-8 file; CSV fields never control this path."""
    display_name = file_name or Path(path).name
    try:
        data = Path(path).read_bytes()
    except OSError:
        result = CsvParseResult()
        result.issues.append(_issue(source_type, display_name, 1, "FILE_READ_ERROR", "CSV file could not be read", IssueSeverity.ERROR))
        result.summary = calculate_ingestion_summary(result)
        return result
    return read_csv_bytes(data, source_type=source_type, file_name=display_name, required_columns=required_columns, max_rows=max_rows, max_field_length=max_field_length)


__all__ = ["CsvParseResult", "parse_csv_text", "read_csv_bytes", "read_csv_file"]
