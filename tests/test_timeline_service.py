"""tests/test_timeline_service.py

Comprehensive test suite for A15 — Chronological Timeline Projection.

Validates:
1. Deterministic projection from source records, A3 events, case nodes, tasks, routes.
2. Dual timestamp semantics (occurred_at vs recorded_at) with zero fabricated dates.
3. Stable deterministic canonical IDs.
4. Deterministic chronological sorting (asc & desc) with tiebreakers.
5. Deduplication across different projection paths while keeping distinct milestones.
6. Case-level and entity-level scoping.
7. Date-range filtering and pagination.
8. Statutory RBAC (can_access_case enforcement and 403 on unauthorized case).
9. Traceability to A3, A8 snapshots/diffs, and A14 routing records.
10. Full backward compatibility with existing GET /api/v1/timeline.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import pytest
from fastapi.testclient import TestClient

from backend.app.auth.policy import EvidenceAuthorizationPolicy, Principal
from backend.app.auth.principal import UserRole
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app
from backend.app.services.audit_service import AuditService
from backend.app.services.timeline_service import TimelineService
from shared.contracts.api import (
    AffectedInvestigationRoute,
    EpistemicState,
    EvidenceAssessment,
    IntelligenceEvent,
    IntelligenceEventType,
    PulseDeliveryStatus,
    TimelineEventCategory,
    VerificationTask,
    VerificationTaskDecision,
    VerificationTaskStatus,
)


@pytest.fixture
def repo() -> InMemoryBackendRepository:
    repository = InMemoryBackendRepository()
    repository.clear()
    return repository


@pytest.fixture
def audit_service(repo: InMemoryBackendRepository) -> AuditService:
    return AuditService(repo)


@pytest.fixture
def auth_policy(
    repo: InMemoryBackendRepository, audit_service: AuditService
) -> EvidenceAuthorizationPolicy:
    return EvidenceAuthorizationPolicy(repo, audit_service)



@pytest.fixture
def timeline_service(
    repo: InMemoryBackendRepository,
    auth_policy: EvidenceAuthorizationPolicy,
    audit_service: AuditService,
) -> TimelineService:
    return TimelineService(repository=repo, auth_policy=auth_policy, audit_service=audit_service)


@pytest.fixture
def admin_principal() -> Principal:
    return Principal(
        user_id="admin-01",
        email="admin@ncrb.gov.in",
        role=UserRole.ADMIN,
        officer_id="admin-01",
    )


@pytest.fixture
def io_principal() -> Principal:
    return Principal(
        user_id="officer-104",
        email="io104@mysuru.police.gov.in",
        role=UserRole.INVESTIGATOR,
        officer_id="officer-104",
    )


def test_timeline_projection_from_source_records(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """Verifies CDR, bank wire, and FIR source records project accurately with occurred_at."""
    repo.source_records["SRC-CDR-TEST-01"] = {
        "id": "SRC-CDR-TEST-01",
        "batch_id": "BATCH-2026-08-24",
        "source_type": "CDR",
        "locator": "cdr_log.csv:row10",
        "raw_excerpt": "Suspicious call from 9845011223 to 9845099887 duration 240s",
        "occurred_at": "2026-02-14T22:41:05+00:00",
        "ingested_at": "2026-02-16T10:00:00+00:00",
        "case_ids": ["CASE-141"],
        "content_hash": "hash-cdr-01",
    }
    repo.source_records["SRC-BANK-TEST-01"] = {
        "id": "SRC-BANK-TEST-01",
        "batch_id": "BATCH-2026-08-24",
        "source_type": "BANK_TXN",
        "locator": "bank_stmt.pdf:p2",
        "raw_excerpt": "Transfer of INR 4,80,000 from ACC-9914 to ACC-7731",
        "occurred_at": "2026-02-15T08:12:00+00:00",
        "ingested_at": "2026-02-16T10:00:00+00:00",
        "case_ids": ["CASE-141"],
        "content_hash": "hash-bank-01",
    }

    resp = timeline_service.query_timeline(principal=admin_principal, case_id="CASE-141")
    assert resp.total_count >= 2

    cdr_ev = next(e for e in resp.events if e.id == "tle-src-SRC-CDR-TEST-01")
    assert cdr_ev.category == TimelineEventCategory.COMMUNICATION
    assert cdr_ev.event_type == "CDR"
    assert cdr_ev.occurred_at == datetime(2026, 2, 14, 22, 41, 5, tzinfo=timezone.utc)
    assert cdr_ev.recorded_at == datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc)

    bank_ev = next(e for e in resp.events if e.id == "tle-src-SRC-BANK-TEST-01")
    assert bank_ev.category == TimelineEventCategory.FINANCIAL_TRANSACTION
    assert bank_ev.event_type == "BANK_TXN"
    assert bank_ev.occurred_at == datetime(2026, 2, 15, 8, 12, 0, tzinfo=timezone.utc)


def test_timeline_projection_from_intelligence_events(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """Verifies A3 domain events project accurately with full operational context."""
    repo.intelligence_events["intevt-decision-1"] = {
        "event_id": "intevt-decision-1",
        "event_type": IntelligenceEventType.INVESTIGATOR_DECISION,
        "event_version": "1.0",
        "event_timestamp": datetime(2026, 2, 18, 14, 30, 0, tzinfo=timezone.utc),
        "case_id": "CASE-141",
        "source_id": "cand-001",
        "related_entity_ids": ["person-0001"],
        "related_edge_ids": ["edge-0001"],
        "actor_id": "officer-104",
        "actor_role": UserRole.INVESTIGATOR,
        "observed_at": datetime(2026, 2, 14, 22, 0, 0, tzinfo=timezone.utc),
        "ingested_at": datetime(2026, 2, 16, 10, 0, 0, tzinfo=timezone.utc),
        "title": "Investigator Approved Candidate Promotion",
        "description": "Candidate Rafiq Khan promoted into authoritative graph.",
        "payload": {"decision_id": "dec-101"},
        "integrity_hash": "sha256-hash-101",
    }

    resp = timeline_service.query_timeline(principal=admin_principal, case_id="CASE-141")
    event = next((e for e in resp.events if e.id == "tle-intevt-intevt-decision-1"), None)
    assert event is not None
    assert event.category == TimelineEventCategory.INVESTIGATOR_ACTION
    assert event.event_type == "INVESTIGATOR_DECISION"
    assert event.occurred_at == datetime(2026, 2, 14, 22, 0, 0, tzinfo=timezone.utc)
    assert event.recorded_at == datetime(2026, 2, 18, 14, 30, 0, tzinfo=timezone.utc)
    assert event.actor_id == "officer-104"
    assert "person-0001" in event.participant_ids


def test_timeline_deterministic_ids(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """Verifies that replaying timeline queries generates identical canonical IDs."""
    repo.source_records["SRC-REPLAY-1"] = {
        "id": "SRC-REPLAY-1",
        "source_type": "CDR",
        "occurred_at": "2026-02-10T12:00:00Z",
        "case_ids": ["CASE-141"],
    }
    resp1 = timeline_service.query_timeline(principal=admin_principal, case_id="CASE-141")
    resp2 = timeline_service.query_timeline(principal=admin_principal, case_id="CASE-141")

    ids1 = [e.id for e in resp1.events]
    ids2 = [e.id for e in resp2.events]
    assert ids1 == ids2
    assert "tle-src-SRC-REPLAY-1" in ids1


def test_timeline_chronological_ordering_desc_and_asc(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """Verifies strict deterministic sorting by occurred_at with recorded_at tiebreakers."""
    repo.source_records.clear()
    repo.intelligence_events.clear()

    # Seed 3 events with known times
    repo.source_records["SRC-EARLY"] = {
        "id": "SRC-EARLY",
        "source_type": "FIR",
        "occurred_at": "2026-01-10T10:00:00Z",
        "case_ids": ["CASE-ORDER"],
    }
    repo.source_records["SRC-MID"] = {
        "id": "SRC-MID",
        "source_type": "CDR",
        "occurred_at": "2026-01-15T12:00:00Z",
        "case_ids": ["CASE-ORDER"],
    }
    repo.source_records["SRC-LATE"] = {
        "id": "SRC-LATE",
        "source_type": "BANK_TXN",
        "occurred_at": "2026-01-20T14:00:00Z",
        "case_ids": ["CASE-ORDER"],
    }

    # Query DESC (latest first)
    desc_resp = timeline_service.query_timeline(principal=admin_principal, case_id="CASE-ORDER", order="desc")
    desc_ids = [e.id for e in desc_resp.events]
    assert desc_ids == ["tle-src-SRC-LATE", "tle-src-SRC-MID", "tle-src-SRC-EARLY"]

    # Query ASC (earliest first)
    asc_resp = timeline_service.query_timeline(principal=admin_principal, case_id="CASE-ORDER", order="asc")
    asc_ids = [e.id for e in asc_resp.events]
    assert asc_ids == ["tle-src-SRC-EARLY", "tle-src-SRC-MID", "tle-src-SRC-LATE"]


def test_timeline_occurred_at_vs_recorded_at(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """Verifies that events preserve both when the crime happened and when NEXUS recorded it."""
    crime_time = datetime(2025, 11, 10, 8, 0, 0, tzinfo=timezone.utc)
    ingest_time = datetime(2026, 2, 1, 14, 0, 0, tzinfo=timezone.utc)

    repo.source_records["SRC-HISTORICAL-1"] = {
        "id": "SRC-HISTORICAL-1",
        "source_type": "FIR",
        "raw_excerpt": "Robbery reported on 10 Nov 2025",
        "occurred_at": "2025-11-10T08:00:00Z",
        "ingested_at": "2026-02-01T14:00:00Z",
        "case_ids": ["CASE-TIME-TEST"],
    }

    resp = timeline_service.query_timeline(principal=admin_principal, case_id="CASE-TIME-TEST")
    ev = next(e for e in resp.events if e.id == "tle-src-SRC-HISTORICAL-1")
    assert ev.occurred_at == crime_time
    assert ev.recorded_at == ingest_time
    # Backward compatibility timestamp defaults to occurred_at
    assert ev.timestamp == crime_time


def test_timeline_deduplication(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """Verifies that an event projected via A3 IntelligenceEvent suppresses duplicate source record projection."""
    # 1. Source record
    repo.source_records["SRC-DUAL-01"] = {
        "id": "SRC-DUAL-01",
        "source_type": "CDR",
        "occurred_at": "2026-02-14T20:00:00Z",
        "case_ids": ["CASE-DEDUP"],
    }
    # 2. IntelligenceEvent that specifically references this source record
    repo.intelligence_events["intevt-dual-01"] = {
        "event_id": "intevt-dual-01",
        "event_type": IntelligenceEventType.RELATIONSHIP_OBSERVED,
        "source_id": "SRC-DUAL-01",
        "case_id": "CASE-DEDUP",
        "event_timestamp": datetime(2026, 2, 15, 10, 0, 0, tzinfo=timezone.utc),
        "observed_at": datetime(2026, 2, 14, 20, 0, 0, tzinfo=timezone.utc),
        "title": "Call interaction observed in graph",
    }

    resp = timeline_service.query_timeline(principal=admin_principal, case_id="CASE-DEDUP")
    ids = [e.id for e in resp.events]

    # Must contain the authoritative IntelligenceEvent
    assert "tle-intevt-intevt-dual-01" in ids
    # Must NOT contain a duplicate generic source event for SRC-DUAL-01
    assert "tle-src-SRC-DUAL-01" not in ids


def test_timeline_case_scoping(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """Verifies that case_id filtering strictly isolates events to the requested case."""
    repo.source_records["SRC-CASE-A"] = {
        "id": "SRC-CASE-A",
        "source_type": "FIR",
        "occurred_at": "2026-02-01T10:00:00Z",
        "case_ids": ["CASE-AAA"],
    }
    repo.source_records["SRC-CASE-B"] = {
        "id": "SRC-CASE-B",
        "source_type": "FIR",
        "occurred_at": "2026-02-02T10:00:00Z",
        "case_ids": ["CASE-BBB"],
    }

    resp_a = timeline_service.query_timeline(principal=admin_principal, case_id="CASE-AAA")
    ids_a = [e.id for e in resp_a.events]
    assert "tle-src-SRC-CASE-A" in ids_a
    assert "tle-src-SRC-CASE-B" not in ids_a


def test_timeline_entity_scoping(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """Verifies entity_id filtering isolates events linked to that entity."""
    repo.intelligence_events["intevt-ent-1"] = {
        "event_id": "intevt-ent-1",
        "event_type": IntelligenceEventType.ENTITY_OBSERVED,
        "case_id": "CASE-SCOPE",
        "related_entity_ids": ["person-target-1"],
        "event_timestamp": datetime(2026, 2, 10, 10, 0, 0, tzinfo=timezone.utc),
        "title": "Target suspect observed",
    }
    repo.intelligence_events["intevt-ent-2"] = {
        "event_id": "intevt-ent-2",
        "event_type": IntelligenceEventType.ENTITY_OBSERVED,
        "case_id": "CASE-SCOPE",
        "related_entity_ids": ["person-other-2"],
        "event_timestamp": datetime(2026, 2, 11, 10, 0, 0, tzinfo=timezone.utc),
        "title": "Other person observed",
    }

    resp = timeline_service.query_timeline(
        principal=admin_principal,
        case_id="CASE-SCOPE",
        entity_id="person-target-1",
    )
    ids = [e.id for e in resp.events]
    assert "tle-intevt-intevt-ent-1" in ids
    assert "tle-intevt-intevt-ent-2" not in ids


def test_timeline_date_range_and_pagination(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """Verifies date range boundaries and pagination offsets/limits."""
    repo.source_records.clear()
    for i in range(1, 11):
        day = f"0{i}" if i < 10 else str(i)
        repo.source_records[f"SRC-PAG-{i}"] = {
            "id": f"SRC-PAG-{i}",
            "source_type": "CDR",
            "occurred_at": f"2026-03-{day}T12:00:00Z",
            "case_ids": ["CASE-PAG"],
        }

    # Range filter: March 3 to March 7
    range_resp = timeline_service.query_timeline(
        principal=admin_principal,
        case_id="CASE-PAG",
        from_date="2026-03-03T00:00:00Z",
        to_date="2026-03-07T23:59:59Z",
        order="asc",
    )
    assert range_resp.total_count == 5
    assert range_resp.events[0].id == "tle-src-SRC-PAG-3"
    assert range_resp.events[-1].id == "tle-src-SRC-PAG-7"

    # Pagination: limit 2, offset 1
    paged_resp = timeline_service.query_timeline(
        principal=admin_principal,
        case_id="CASE-PAG",
        from_date="2026-03-03T00:00:00Z",
        to_date="2026-03-07T23:59:59Z",
        order="asc",
        limit=2,
        offset=1,
    )
    assert len(paged_resp.events) == 2
    assert paged_resp.events[0].id == "tle-src-SRC-PAG-4"
    assert paged_resp.events[1].id == "tle-src-SRC-PAG-5"
    assert paged_resp.has_more is True


def test_timeline_rbac_unauthorized_case_forbidden(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    io_principal: Principal,
) -> None:
    """Verifies that an investigator requesting an unauthorized case receives HTTP 403."""
    with pytest.raises(Exception) as exc_info:
        timeline_service.query_timeline(principal=io_principal, case_id="CASE-RESTRICTED-999")
    assert "403" in str(exc_info.value) or "Access denied" in str(exc_info.value)


def test_timeline_a8_and_a14_traceability(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """Verifies closed-loop mutation milestones and A14 routing milestones link properly."""
    # A8 Snapshot diff event
    repo.intelligence_events["intevt-diff-1"] = {
        "event_id": "intevt-diff-1",
        "event_type": IntelligenceEventType.NETWORK_CHANGE_DETECTED,
        "case_id": "CASE-141",
        "snapshot_id": "snap-mut-001",
        "event_timestamp": datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc),
        "observed_at": datetime(2026, 2, 20, 12, 0, 0, tzinfo=timezone.utc),
        "title": "Structural change detected in syndicate network",
        "payload": {"route_id": "route-001"},
    }

    # A14 Affected Route (dispatched + acknowledged)
    route = AffectedInvestigationRoute(
        route_id="route-001",
        origin_case_id="CASE-141",
        origin_district="Mysuru",
        target_case_id="CASE-207",
        target_district="Bengaluru",
        trigger_event_id="intevt-diff-1",
        source_snapshot_id="snap-mut-000",
        target_snapshot_id="snap-mut-001",
        diff_summary={"added_edges": 1},
        intersecting_entity_ids=["person-0001"],
        intersecting_edge_ids=["edge-0001"],
        routing_reason="Shared person across cases",
        evidence_refs=["SRC-CDR-01"],
        route_hash="hash-route-001",
        status=PulseDeliveryStatus.ACKNOWLEDGED,
        dispatched_at="2026-02-20T12:05:00+00:00",
        acknowledged_at="2026-02-20T14:10:00+00:00",
        acknowledged_by="officer-207",
        acknowledgment_note="Acknowledged and opened lead verification",
    )
    repo.affected_routes["route-001"] = route

    # Target case timeline
    target_resp = timeline_service.query_timeline(principal=admin_principal, case_id="CASE-207")
    target_ids = [e.id for e in target_resp.events]
    assert "tle-route-disp-route-001" in target_ids
    assert "tle-route-ack-route-001" in target_ids

    ack_event = next(e for e in target_resp.events if e.id == "tle-route-ack-route-001")
    assert ack_event.category == TimelineEventCategory.CROSS_CASE_ROUTE
    assert ack_event.event_type == "ROUTE_ACKNOWLEDGED"
    assert ack_event.actor_id == "officer-207"


def test_timeline_verification_task_progression(
    timeline_service: TimelineService,
    repo: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """Verifies A7 verification task creation and decision milestones appear as separate timeline entries."""
    task = VerificationTask(
        task_id="vtask-test-01",
        case_id="CASE-141",
        created_at=datetime(2026, 2, 17, 9, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 18, 16, 0, 0, tzinfo=timezone.utc),
        target_claim="Suspect Rafiq Khan owns mobile 9845011223",
        reason="Verify subscriber registration",
        requested_evidence_type="TELECOM_CAF",
        verification_action="Request CAF from operator",
        assigned_officer_id="officer-104",
        assigned_role=UserRole.INVESTIGATOR,
        status=VerificationTaskStatus.VERIFIED,
        history=[],
        requested_evidence_ids=["SRC-CDR-01"],
        received_evidence_ids=["SRC-CAF-01"],
        supporting_evidence_ids=["SRC-CAF-01"],
        conflicting_evidence_ids=[],
        decision=VerificationTaskDecision.VERIFIED,
        decision_rationale="CAF confirmed matches suspect photo and ID",
        deciding_actor="officer-104",
        decided_at=datetime(2026, 2, 18, 16, 0, 0, tzinfo=timezone.utc),
    )
    repo.verification_tasks["vtask-test-01"] = task

    resp = timeline_service.query_timeline(principal=admin_principal, case_id="CASE-141")
    ids = [e.id for e in resp.events]
    assert "tle-vtask-created-vtask-test-01" in ids
    assert "tle-vtask-decided-vtask-test-01" in ids

    decided_ev = next(e for e in resp.events if e.id == "tle-vtask-decided-vtask-test-01")
    assert decided_ev.category == TimelineEventCategory.VERIFICATION_WORKFLOW
    assert decided_ev.event_type == "VERIFICATION_TASK_DECIDED"
    assert decided_ev.occurred_at == datetime(2026, 2, 18, 16, 0, 0, tzinfo=timezone.utc)


def test_timeline_rest_api_endpoints() -> None:
    """Verifies GET /api/v1/timeline and GET /api/v1/nexus/timeline via FastAPI TestClient."""
    app = create_app()
    client = TestClient(app)

    # 1. Existing core endpoint
    resp1 = client.get("/api/v1/timeline", headers={"X-Role": "admin"})
    assert resp1.status_code == 200
    events1 = resp1.json()
    assert isinstance(events1, list)
    if events1:
        assert "id" in events1[0]
        assert "event_type" in events1[0]
        assert "timestamp" in events1[0]
        assert "description" in events1[0]

    # 2. Rich Nexus timeline query endpoint
    resp2 = client.get(
        "/api/v1/nexus/timeline?limit=10&order=desc",
        headers={"X-Role": "admin"},
    )
    assert resp2.status_code == 200
    query_data = resp2.json()
    assert "events" in query_data
    assert "total_count" in query_data
    assert "has_more" in query_data
    assert isinstance(query_data["events"], list)
