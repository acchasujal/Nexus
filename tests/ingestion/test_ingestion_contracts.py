"""Tests for the additive CSV ingestion contracts."""

import json

import pytest
from pydantic import ValidationError

from backend.app.core.graph.edges import GraphEdge
from backend.app.core.graph.entities import Person, SourceRecord
from backend.app.core.graph.enums import GraphRelationshipType, ResolutionStatus
from backend.app.db.ingestion.contracts import (
    EntityReviewCandidate,
    IngestionBundle,
    IngestionSummary,
    IssueSeverity,
    ParseIssue,
    SourceType,
)


def test_valid_bundle_creation() -> None:
    source_record = SourceRecord(
        id="src_fir_001",
        batch_id="batch_test_001",
        source_type="FIR",
        locator="synthetic_fir.csv:1",
        raw_excerpt="Synthetic incident record",
    )
    person = Person(id="person_vikram_001", full_name="Vikram Sharma")
    relationship = GraphEdge(
        id="rel_person_case_001",
        source_id=person.id,
        target_id="case_001",
        edge_type=GraphRelationshipType.INVOLVED_IN,
        source_record_id=source_record.id,
    )

    bundle = IngestionBundle(
        batch_id="batch_test_001",
        source_type=SourceType.FIR,
        file_name="synthetic_fir.csv",
        source_records=[source_record],
        nodes=[person],
        relationships=[relationship],
        summary=IngestionSummary(
            received_count=1,
            accepted_count=1,
            source_record_count=1,
            node_created_count=1,
            relationship_created_count=1,
        ),
    )

    assert bundle.source_records[0].id == "src_fir_001"
    assert bundle.nodes[0].id == "person_vikram_001"
    assert bundle.relationships[0].source_record_id == "src_fir_001"


def test_empty_bundle_creation_uses_safe_defaults() -> None:
    bundle = IngestionBundle(
        batch_id="batch_empty",
        source_type=SourceType.CDR,
        file_name="empty_cdr.csv",
    )

    assert bundle.source_records == []
    assert bundle.nodes == []
    assert bundle.relationships == []
    assert bundle.review_candidates == []
    assert bundle.issues == []
    assert bundle.summary.received_count == 0


def test_confidence_range() -> None:
    with pytest.raises(ValidationError):
        EntityReviewCandidate(
            incoming_record_id="cdr_001",
            candidate_node_id="person_001",
            status=ResolutionStatus.REVIEW_REQUIRED,
            confidence=1.1,
        )

    with pytest.raises(ValidationError):
        EntityReviewCandidate(
            incoming_record_id="cdr_001",
            candidate_node_id="person_001",
            status=ResolutionStatus.REVIEW_REQUIRED,
            confidence=-0.1,
        )


def test_issue_serialization() -> None:
    issue = ParseIssue(
        source_type=SourceType.BANK_TXN,
        file_name="synthetic_bank.csv",
        row_number=4,
        record_id="txn_004",
        field_name="amount",
        code="INVALID_AMOUNT",
        message="Synthetic amount is not numeric",
        severity=IssueSeverity.ERROR,
    )

    serialized = issue.model_dump(mode="json")

    assert serialized["source_type"] == "BANK_TXN"
    assert serialized["severity"] == "ERROR"
    assert json.loads(json.dumps(serialized))["record_id"] == "txn_004"


def test_json_round_trip() -> None:
    bundle = IngestionBundle(
        batch_id="batch_round_trip",
        source_type=SourceType.INTEL_REPORT,
        file_name="synthetic_intel.csv",
        source_records=[SourceRecord(id="src_intel_001", source_type="INTEL_REPORT")],
        nodes=[Person(id="person_001", full_name="Synthetic Analyst")],
        review_candidates=[
            EntityReviewCandidate(
                incoming_record_id="intel_001",
                candidate_node_id="person_001",
                status=ResolutionStatus.MATCHED,
                confidence=0.9,
                matched_fields=["full_name"],
                auto_link_allowed=True,
                requires_human_review=False,
            )
        ],
    )

    recreated = IngestionBundle.model_validate_json(bundle.model_dump_json())

    assert recreated.model_dump(mode="json") == bundle.model_dump(mode="json")
    assert recreated.source_type is SourceType.INTEL_REPORT
    assert recreated.review_candidates[0].status is ResolutionStatus.MATCHED


def test_summary_counts() -> None:
    summary = IngestionSummary(
        received_count=10,
        accepted_count=7,
        duplicate_count=1,
        rejected_count=2,
        warning_count=3,
        source_record_count=7,
        node_created_count=5,
        node_reused_count=2,
        relationship_created_count=6,
        review_required_count=1,
    )

    assert summary.received_count == (
        summary.accepted_count + summary.duplicate_count + summary.rejected_count
    )
    assert summary.source_record_count == summary.accepted_count
    assert summary.review_required_count == 1
