"""Synthetic bank transaction CSV parser: CSV rows → validated records."""

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
    normalize_account,
    normalize_currency,
    normalize_ifsc,
    parse_non_negative_decimal,
    parse_utc_datetime,
)

REQUIRED_COLUMNS = (
    "record_id", "utr", "from_account", "from_bank", "to_account", "to_bank", "amount", "currency", "timestamp",
)
OPTIONAL_COLUMNS = (
    "from_ifsc", "from_holder_name", "from_holder_national_id", "to_ifsc", "to_holder_name", "to_holder_national_id",
)


def _issue(row: Mapping[str, str], row_number: int, field_name: str, code: str, message: str, file_name: str) -> ParseIssue:
    return ParseIssue(
        source_type=SourceType.BANK_TXN,
        file_name=file_name,
        row_number=row_number,
        record_id=row.get("record_id", "") or f"row-{row_number}",
        field_name=field_name,
        code=code,
        message=message,
        severity=IssueSeverity.ERROR,
    )


def _source_record(row: Mapping[str, str], batch_id: str, occurred_at: datetime, file_name: str) -> SourceRecord:
    canonical = canonicalize_csv_row(row)
    return SourceRecord(
        id=make_source_record_id(SourceType.BANK_TXN.value, row),
        batch_id=batch_id,
        source_type=SourceType.BANK_TXN.value,
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


def _parse_rows(result: CsvParseResult, batch_id: str, file_name: str) -> ParsedSourceBundle:
    """Parse bank CSV rows into validated records."""
    source_records: dict[str, SourceRecord] = {}
    parsed_rows: list[dict[str, Any]] = []
    issues = list(result.issues)
    seen_utrs: set[str] = set()

    for row_number, row in enumerate(result.rows, start=2):
        try:
            utr = row["utr"].strip()
            if not utr:
                raise CsvValidationError("utr must not be empty")
            if utr in seen_utrs:
                issues.append(_issue(row, row_number, "utr", "DUPLICATE_UTR", "UTR already appeared in this batch", file_name))
                continue
            from_account = normalize_account(row["from_account"])
            to_account = normalize_account(row["to_account"])
            amount = parse_non_negative_decimal(row["amount"])
            currency = normalize_currency(row["currency"])
            timestamp = parse_utc_datetime(row["timestamp"])
            from_ifsc = normalize_ifsc(row["from_ifsc"]) if row.get("from_ifsc", "").strip() else ""
            to_ifsc = normalize_ifsc(row["to_ifsc"]) if row.get("to_ifsc", "").strip() else ""

            source_record = _source_record(row, batch_id, timestamp, file_name)
            source_records[source_record.id] = source_record
            seen_utrs.add(utr)

            parsed_rows.append({
                "record_id": row["record_id"].strip(),
                "utr": utr,
                "from_account": from_account,
                "to_account": to_account,
                "from_bank": row["from_bank"].strip(),
                "to_bank": row["to_bank"].strip(),
                "amount": amount,
                "currency": currency,
                "timestamp": timestamp,
                "from_ifsc": from_ifsc,
                "to_ifsc": to_ifsc,
                "from_holder_name": row.get("from_holder_name", "").strip(),
                "from_holder_national_id": row.get("from_holder_national_id", "").strip(),
                "to_holder_name": row.get("to_holder_name", "").strip(),
                "to_holder_national_id": row.get("to_holder_national_id", "").strip(),
                "source_record_id": source_record.id,
                "raw_row": dict(row),
            })
        except (KeyError, CsvValidationError, ValueError) as exc:
            issues.append(_issue(row, row_number, "row", "INVALID_BANK_ROW", str(exc), file_name))

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
        source_type=SourceType.BANK_TXN,
        file_name=file_name,
        source_records=list(source_records.values()),
        rows=parsed_rows,
        issues=issues,
        summary=summary,
    )


def parse_bank_source(text: str, *, batch_id: str = "batch_bank", file_name: str = "bank_transactions.csv") -> ParsedSourceBundle:
    """Parse bank CSV text into validated source records (no graph mapping)."""
    result = parse_csv_text(text, source_type=SourceType.BANK_TXN, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)


def parse_bank_source_bytes(data: bytes, *, batch_id: str = "batch_bank", file_name: str = "bank_transactions.csv") -> ParsedSourceBundle:
    """Parse bank CSV bytes into validated source records."""
    from ..csv_reader import read_csv_bytes
    result = read_csv_bytes(data, source_type=SourceType.BANK_TXN, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)


def parse_bank_source_file(path: str | Path, *, batch_id: str = "batch_bank") -> ParsedSourceBundle:
    """Read and parse a bank CSV file into validated source records."""
    file_name = Path(path).name
    result = read_csv_file(path, source_type=SourceType.BANK_TXN, file_name=file_name, required_columns=REQUIRED_COLUMNS)
    return _parse_rows(result, batch_id, file_name)


def parse_bank_text(text: str, *, batch_id: str = "batch_bank", file_name: str = "bank_transactions.csv") -> IngestionBundle:
    """Parse bank CSV text into a V2 ingestion bundle (convenience: parser + mapper)."""
    from ..mappers.bank import map_bank_bundle
    parsed = parse_bank_source(text, batch_id=batch_id, file_name=file_name)
    return map_bank_bundle(parsed)


def parse_bank_csv(path: str | Path, *, batch_id: str = "batch_bank") -> IngestionBundle:
    """Read and parse a caller-selected synthetic bank CSV file."""
    from ..mappers.bank import map_bank_bundle
    parsed = parse_bank_source_file(path, batch_id=batch_id)
    return map_bank_bundle(parsed)


__all__ = ["OPTIONAL_COLUMNS", "REQUIRED_COLUMNS", "parse_bank_csv", "parse_bank_source", "parse_bank_source_bytes", "parse_bank_source_file", "parse_bank_text"]
