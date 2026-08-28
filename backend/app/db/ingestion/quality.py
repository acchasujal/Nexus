"""Quality accounting for CSV parser results."""

from __future__ import annotations

from typing import Any

from .contracts import IngestionSummary, IssueSeverity


def calculate_ingestion_summary(result: Any) -> IngestionSummary:
    """Calculate ingestion counts from accepted rows, quarantine, and issues."""
    issues = list(getattr(result, "issues", []))
    quarantined = list(getattr(result, "quarantined_rows", []))
    rows = list(getattr(result, "rows", []))
    duplicate_count = sum(1 for issue in issues if issue.code == "DUPLICATE_ROW")
    conflict_count = sum(1 for issue in issues if issue.code == "CONFLICTING_RECORD")
    
    rejected_rows = {
        (issue.file_name, issue.row_number)
        for issue in issues
        if issue.severity is IssueSeverity.ERROR
        and issue.code not in {"MISSING_HEADER", "MISSING_REQUIRED_COLUMN", "INVALID_HEADER", "DUPLICATE_HEADER"}
        and issue.row_number is not None
    }
    rejected_count = len(rejected_rows)
    
    received_count = len(rows) + len(quarantined)
    return IngestionSummary(
        received_count=received_count,
        accepted_count=len(rows),
        duplicate_count=duplicate_count,
        conflict_count=conflict_count,
        rejected_count=rejected_count,
        warning_count=sum(1 for issue in issues if issue.severity is IssueSeverity.WARNING),
        source_record_count=len(rows),
    )


__all__ = ["calculate_ingestion_summary"]
