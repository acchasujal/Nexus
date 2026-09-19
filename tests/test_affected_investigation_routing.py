"""tests/test_affected_investigation_routing.py

Comprehensive regression test suite for A14 — Affected Investigation Routing.
Verifies:
  1. Deterministic graph-case intersection for changed entities and relationships.
  2. Originating case exclusion (zero self-routing).
  3. Strict idempotency and duplicate suppression.
  4. Grounded textual explainability citing exact intersecting graph objects.
  5. RBAC and jurisdictional gating on inbox and acknowledgment.
  6. Operational IntelligenceEvents (A3 SIGNAL_GENERATED) and statutory AuditEvents.
  7. End-to-end integration with A8 Closed-Loop Propagation.
  8. Graph mutation isolation (routing failures do not roll back mutations).
  9. REST API endpoints via TestClient.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import create_app
from backend.app.services.affected_investigation_routing_service import (
    AffectedInvestigationRoutingService,
    compute_route_integrity_hash,
    make_route_id,
)
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.closed_loop_propagation_service import ClosedLoopPropagationService
from backend.app.services.intelligence_event_service import IntelligenceEventService
from backend.app.services.proactive_intelligence_service import ProactiveIntelligenceService
from shared.contracts.api import (
    AcknowledgeRouteRequest,
    AffectedInvestigationRoute,
    EvaluateRoutingRequest,
    IntelligenceEventType,
    PulseDeliveryStatus,
    UserRole,
)


@pytest.fixture
def repository() -> InMemoryBackendRepository:
    repo = InMemoryBackendRepository()
    repo.clear()

    # Seed canonical demo cases
    repo.nodes["CASE-141"] = {
        "id": "CASE-141",
        "entity_type": "Case",
        "properties": {
            "fir_number": "FIR-141/2026",
            "title": "Mysuru Extortion Syndicate",
            "district": "Mysuru",
            "station_name": "Devaraja PS",
            "status": "OPEN",
        },
    }
    repo.nodes["CASE-207"] = {
        "id": "CASE-207",
        "entity_type": "Case",
        "properties": {
            "fir_number": "FIR-207/2026",
            "title": "Bengaluru Cyber Financial Fraud",
            "district": "Bengaluru Central",
            "station_name": "Cyber Crime PS",
            "status": "OPEN",
        },
    }
    repo.nodes["CASE-501"] = {
        "id": "CASE-501",
        "entity_type": "Case",
        "properties": {
            "fir_number": "FIR-501/2026",
            "title": "Unrelated Jayanagar Case",
            "district": "Bengaluru Urban",
            "station_name": "Jayanagar PS",
            "status": "OPEN",
        },
    }
    repo.nodes["P-RAFIQ"] = {
        "id": "P-RAFIQ",
        "entity_type": "Person",
        "properties": {
            "full_name": "Rafiq Khan",
            "case_ids": ["CASE-141", "CASE-207"],
        },
    }
    repo.nodes["P-DEEPAK"] = {
        "id": "P-DEEPAK",
        "entity_type": "Person",
        "properties": {
            "full_name": "Deepak Rao",
            "case_ids": ["CASE-207"],
        },
    }
    repo.nodes["PH-UNIFIED"] = {
        "id": "PH-UNIFIED",
        "entity_type": "Phone",
        "properties": {
            "phone_number": "+91 98450 11223",
            "case_ids": ["CASE-141"],
        },
    }

    # Incident edges
    repo.edges.append({
        "id": "edge-acc-141-rafiq",
        "source_id": "P-RAFIQ",
        "target_id": "CASE-141",
        "edge_type": "ACCUSED_IN",
        "properties": {"case_ids": ["CASE-141"]},
    })
    repo.edges.append({
        "id": "edge-acc-207-rafiq",
        "source_id": "P-RAFIQ",
        "target_id": "CASE-207",
        "edge_type": "ACCUSED_IN",
        "properties": {"case_ids": ["CASE-207"]},
    })
    repo.edges.append({
        "id": "edge-acc-207-deepak",
        "source_id": "P-DEEPAK",
        "target_id": "CASE-207",
        "edge_type": "ACCUSED_IN",
        "properties": {"case_ids": ["CASE-207"]},
    })
    repo.edges.append({
        "id": "E-COMM-DK",
        "source_id": "P-RAFIQ",
        "target_id": "P-DEEPAK",
        "edge_type": "COMMUNICATED_WITH",
        "properties": {"case_ids": ["CASE-141", "CASE-207"]},
        "provenance": {"source_type": "CDR", "source_id": "SRC-CDR-B31"},
    })
    repo._rebuild_indexes()
    return repo


@pytest.fixture
def audit_service(repository: InMemoryBackendRepository) -> AuditService:
    return AuditService(repository)


@pytest.fixture
def auth_policy(repository: InMemoryBackendRepository, audit_service: AuditService) -> EvidenceAuthorizationPolicy:
    return EvidenceAuthorizationPolicy(repository, audit_service)


@pytest.fixture
def intel_event_service(
    repository: InMemoryBackendRepository,
    audit_service: AuditService,
    auth_policy: EvidenceAuthorizationPolicy,
) -> IntelligenceEventService:
    return IntelligenceEventService(repository, audit_service, auth_policy)


@pytest.fixture
def routing_service(
    repository: InMemoryBackendRepository,
    audit_service: AuditService,
    auth_policy: EvidenceAuthorizationPolicy,
    intel_event_service: IntelligenceEventService,
) -> AffectedInvestigationRoutingService:
    return AffectedInvestigationRoutingService(
        repository=repository,
        audit_service=audit_service,
        auth_policy=auth_policy,
        intelligence_event_service=intel_event_service,
    )


@pytest.fixture
def admin_principal() -> Principal:
    return Principal(
        user_id="OFFICER-DEMO-ADMIN-01",
        email="admin@nexus.gov.in",
        role=UserRole.ADMIN,
        officer_id="OFFICER-DEMO-ADMIN-01",
    )


@pytest.fixture
def io_assigned_principal() -> Principal:
    """Inspector assigned to CASE-141 and CASE-207."""
    return Principal(
        user_id="OFFICER-DEMO-IO-01",
        email="io@nexus.gov.in",
        role=UserRole.INVESTIGATOR,
        officer_id="OFFICER-DEMO-IO-01",
    )


@pytest.fixture
def io_unassigned_principal() -> Principal:
    """Investigator not assigned to demo cases."""
    return Principal(
        user_id="OFFICER-UNASSIGNED",
        email="unassigned@nexus.gov.in",
        role=UserRole.INVESTIGATOR,
        officer_id="OFFICER-UNASSIGNED",
    )


# ── 1. Unit Tests: Deterministic Intersection & Explainability ───────────────

def test_entity_intersection_creates_route(
    routing_service: AffectedInvestigationRoutingService,
    repository: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """
    Changing an entity accused in CASE-207 (e.g. P-RAFIQ) from origin CASE-141
    must deterministically generate a route to CASE-207.
    """
    resolved = repository.resolve_cases_for_entities_and_edges(["P-RAFIQ"], [])
    assert "CASE-207" in resolved
    assert "CASE-141" in resolved

    routes = routing_service.route_entities_and_edges(
        entity_ids=["P-RAFIQ"],
        edge_ids=[],
        origin_case_id="CASE-141",
        target_snapshot_id="snap-002",
        source_snapshot_id="snap-001",
        principal=admin_principal,
        evidence_refs=["SRC-CDR-B31"],
    )

    assert len(routes) >= 1
    target_route = next((r for r in routes if r.target_case_id == "CASE-207"), None)
    assert target_route is not None
    assert target_route.origin_case_id == "CASE-141"
    assert "P-RAFIQ" in target_route.intersecting_entity_ids
    assert target_route.status == PulseDeliveryStatus.DISPATCHED
    assert "CASE-207" in target_route.routing_reason
    assert "SRC-CDR-B31" in target_route.evidence_refs


def test_originating_case_exclusion(
    routing_service: AffectedInvestigationRoutingService,
    admin_principal: Principal,
) -> None:
    """
    The origin case (CASE-141) must NEVER be routed to as a target case (zero self-routing).
    """
    routes = routing_service.route_entities_and_edges(
        entity_ids=["P-RAFIQ", "PH-UNIFIED"],
        edge_ids=[],
        origin_case_id="CASE-141",
        target_snapshot_id="snap-002",
        source_snapshot_id="snap-001",
        principal=admin_principal,
    )

    # Origin case CASE-141 must be excluded from target routes
    for r in routes:
        assert r.target_case_id != "CASE-141"


def test_edge_intersection_creates_route(
    routing_service: AffectedInvestigationRoutingService,
    admin_principal: Principal,
) -> None:
    """
    A changed relationship connecting entities in CASE-207 must route to CASE-207.
    """
    routes = routing_service.route_entities_and_edges(
        entity_ids=[],
        edge_ids=["E-COMM-DK"],
        origin_case_id="CASE-141",
        target_snapshot_id="snap-002",
        source_snapshot_id="snap-001",
        principal=admin_principal,
    )

    assert any(r.target_case_id == "CASE-207" for r in routes)
    route_207 = next(r for r in routes if r.target_case_id == "CASE-207")
    assert "E-COMM-DK" in route_207.intersecting_edge_ids
    assert "E-COMM-DK" in route_207.routing_reason


def test_unrelated_case_receives_no_route(
    routing_service: AffectedInvestigationRoutingService,
    admin_principal: Principal,
) -> None:
    """
    An unrelated case (e.g. CASE-501 in Jayanagar) must not receive routes for Rafiq/Deepak changes.
    """
    routes = routing_service.route_entities_and_edges(
        entity_ids=["P-RAFIQ"],
        edge_ids=["E-COMM-DK"],
        origin_case_id="CASE-141",
        target_snapshot_id="snap-002",
        source_snapshot_id="snap-001",
        principal=admin_principal,
    )

    routed_case_ids = {r.target_case_id for r in routes}
    assert "CASE-501" not in routed_case_ids


def test_idempotent_duplicate_suppression(
    routing_service: AffectedInvestigationRoutingService,
    repository: InMemoryBackendRepository,
    admin_principal: Principal,
) -> None:
    """
    Evaluating the exact same diff / snapshot pair twice must return the cached route
    without creating duplicate records in repository.affected_routes.
    """
    routes_first = routing_service.route_entities_and_edges(
        entity_ids=["P-RAFIQ"],
        edge_ids=[],
        origin_case_id="CASE-141",
        target_snapshot_id="snap-idem-002",
        source_snapshot_id="snap-idem-001",
        principal=admin_principal,
    )
    assert len(routes_first) > 0
    route_id = routes_first[0].route_id

    count_before = len(repository.affected_routes)

    # Re-evaluate identical diff
    routes_second = routing_service.route_entities_and_edges(
        entity_ids=["P-RAFIQ"],
        edge_ids=[],
        origin_case_id="CASE-141",
        target_snapshot_id="snap-idem-002",
        source_snapshot_id="snap-idem-001",
        principal=admin_principal,
    )

    count_after = len(repository.affected_routes)
    assert count_after == count_before
    assert routes_second[0].route_id == route_id


def test_route_integrity_hash_and_id() -> None:
    """Verify deterministic route hashing and canonical ID formatting."""
    payload = {"route_id": "test", "val": 123}
    h1 = compute_route_integrity_hash(payload)
    h2 = compute_route_integrity_hash(payload)
    assert h1 == h2
    assert len(h1) == 64

    rid = make_route_id("snap-mut-001", "snap-mut-002", "case-0001")
    assert rid.startswith("route-")
    assert "0001" in rid


# ── 2. RBAC & Acknowledgment Tests ───────────────

def test_rbac_inbox_and_detail_gating(
    routing_service: AffectedInvestigationRoutingService,
    io_assigned_principal: Principal,
    io_unassigned_principal: Principal,
    admin_principal: Principal,
) -> None:
    """
    Investigating Officer can only list and view routes for assigned cases.
    Unassigned IO is rejected with PermissionError.
    """
    routes = routing_service.route_entities_and_edges(
        entity_ids=["P-RAFIQ"],
        edge_ids=[],
        origin_case_id="CASE-141",
        target_snapshot_id="snap-rbac-002",
        source_snapshot_id="snap-rbac-001",
        principal=admin_principal,
    )
    route_207 = next(r for r in routes if r.target_case_id == "CASE-207")

    # Assigned IO (assigned to CASE-141 and CASE-207) can view
    r_assigned = routing_service.get_route(route_207.route_id, principal=io_assigned_principal)
    assert r_assigned is not None

    # Unassigned IO cannot view route detail
    with pytest.raises(PermissionError):
        routing_service.get_route(route_207.route_id, principal=io_unassigned_principal)

    # Inbox listing: assigned IO sees CASE-207 route
    inbox_assigned = routing_service.list_inbox_routes(io_assigned_principal, case_id="CASE-207")
    assert any(r.route_id == route_207.route_id for r in inbox_assigned)

    # Inbox listing: unassigned IO sees nothing for CASE-207
    inbox_unassigned = routing_service.list_inbox_routes(io_unassigned_principal, case_id="CASE-207")
    assert len(inbox_unassigned) == 0


def test_authoritative_acknowledgment_lifecycle(
    routing_service: AffectedInvestigationRoutingService,
    audit_service: AuditService,
    io_assigned_principal: Principal,
    io_unassigned_principal: Principal,
    admin_principal: Principal,
) -> None:
    """
    Authoritative acknowledgment transitions route to ACKNOWLEDGED, seals officer badge,
    and logs statutory audit event. Unassigned officer cannot acknowledge.
    """
    routes = routing_service.route_entities_and_edges(
        entity_ids=["P-RAFIQ"],
        edge_ids=[],
        origin_case_id="CASE-141",
        target_snapshot_id="snap-ack-002",
        source_snapshot_id="snap-ack-001",
        principal=admin_principal,
    )
    route_207 = next(r for r in routes if r.target_case_id == "CASE-207")

    # Unassigned IO attempt raises PermissionError
    with pytest.raises(PermissionError):
        routing_service.acknowledge_route(
            route_id=route_207.route_id,
            request=AcknowledgeRouteRequest(decision="ACKNOWLEDGE", note="Unauthorized"),
            principal=io_unassigned_principal,
        )

    # Assigned IO acknowledges
    ack_result = routing_service.acknowledge_route(
        route_id=route_207.route_id,
        request=AcknowledgeRouteRequest(decision="ACKNOWLEDGE", note="Corroborated with Mysuru team"),
        principal=io_assigned_principal,
    )

    assert ack_result.status == PulseDeliveryStatus.ACKNOWLEDGED
    assert ack_result.acknowledged_at is not None
    assert ack_result.acknowledged_by is not None
    assert ack_result.acknowledgment_note == "Corroborated with Mysuru team"

    # Verify audit event
    ack_audits = [e for e in audit_service.list_events() if e.get("event_type") in (AuditEventType.INTELLIGENCE_PULSE_ACKNOWLEDGED, AuditEventType.INTELLIGENCE_PULSE_ACKNOWLEDGED.value)]
    assert len(ack_audits) >= 1
    assert ack_audits[-1].get("entity_id") == route_207.route_id


# ── 3. Integration with A8 Closed-Loop Propagation ───────────────

def test_closed_loop_propagation_with_a14_routing(
    repository: InMemoryBackendRepository,
    audit_service: AuditService,
    auth_policy: EvidenceAuthorizationPolicy,
    intel_event_service: IntelligenceEventService,
    routing_service: AffectedInvestigationRoutingService,
    admin_principal: Principal,
) -> None:
    """
    Verify complete closed loop:
    Investigator Decision -> Mutation -> Snapshot -> NetworkDiff -> Dynamic Pulses -> A14 Routing.
    """
    proactive_svc = ProactiveIntelligenceService(repository)
    # Take baseline snapshot BEFORE mutating repository
    proactive_svc.create_snapshot("snap-baseline-routing")

    prop_svc = ClosedLoopPropagationService(
        repository=repository,
        proactive_service=proactive_svc,
        intel_event_service=intel_event_service,
        audit_service=audit_service,
        auth_policy=auth_policy,
        routing_service=routing_service,
    )

    # Now mutate repository by adding new distinct edge connecting P-RAFIQ to P-DEEPAK
    new_edge_id = "E-TEST-PROP-ROUTING-01"
    repository.edges.append({
        "id": new_edge_id,
        "source_id": "P-RAFIQ",
        "target_id": "P-DEEPAK",
        "edge_type": "TRANSFERRED_FUNDS_TO",
        "weight": 0.95,
        "properties": {"case_ids": ["CASE-141", "CASE-207"]},
        "provenance": {"source_type": "BANK_TXN", "source_id": "SRC-TXN-55"},
    })
    repository._rebuild_indexes()

    result = prop_svc.propagate_decision(
        decision_id="dec-test-a14-prop-01",
        case_id="CASE-141",
        mutation_type="RELATIONSHIP_PROMOTED",
        target_id=new_edge_id,
        principal=admin_principal,
        evidence_refs=["SRC-CDR-B31"],
    )

    assert result.status == "COMPLETED"
    assert len(result.routed_case_ids) >= 1
    assert "CASE-207" in result.routed_case_ids
    assert len(result.route_ids) >= 1

    # Verify A3 SIGNAL_GENERATED event was emitted for the routed case
    events, total = intel_event_service.list_events(case_id="CASE-207")
    routed_events = [e for e in events if e.source_type == "AFFECTED_INVESTIGATION_ROUTE"]
    assert len(routed_events) >= 1
    assert routed_events[0].event_type == IntelligenceEventType.SIGNAL_GENERATED


def test_routing_failure_does_not_break_propagation(
    repository: InMemoryBackendRepository,
    audit_service: AuditService,
    auth_policy: EvidenceAuthorizationPolicy,
    intel_event_service: IntelligenceEventService,
    admin_principal: Principal,
) -> None:
    """
    If the routing service throws an unexpected exception, ClosedLoopPropagationService
    must catch it and finish successfully without rolling back snapshots or mutations.
    """
    faulty_routing_svc = MagicMock()
    faulty_routing_svc.route_network_diff.side_effect = RuntimeError("Simulated routing backend failure")

    proactive_svc = ProactiveIntelligenceService(repository)
    prop_svc = ClosedLoopPropagationService(
        repository=repository,
        proactive_service=proactive_svc,
        intel_event_service=intel_event_service,
        audit_service=audit_service,
        auth_policy=auth_policy,
        routing_service=faulty_routing_svc,
    )

    # Trigger propagation
    result = prop_svc.propagate_decision(
        decision_id="dec-test-fault-routing-01",
        case_id="CASE-141",
        mutation_type="ENTITY_PROMOTED",
        target_id="person-0042",
        principal=admin_principal,
    )

    # Propagation should still succeed; routed_case_ids will be empty
    assert result.status in ("COMPLETED", "SKIPPED_NO_DIFF")
    assert result.routed_case_ids == []
    assert result.route_ids == []


# ── 4. REST API Endpoint Tests via TestClient ───────────────

def test_api_evaluate_and_inbox(repository: InMemoryBackendRepository) -> None:
    """Test POST /nexus/routing/evaluate, GET /nexus/routing/inbox, and POST .../acknowledge."""
    app = create_app()
    # Override app.state.repository to use test repository
    app.state.repository = repository
    client = TestClient(app)

    headers = {"X-Role": "admin"}

    # 1. Evaluate routing
    eval_req = {
        "origin_case_id": "CASE-141",
        "changed_entity_ids": ["P-RAFIQ"],
        "changed_edge_ids": ["E-COMM-DK"],
        "source_snapshot_id": "snap-eval-1",
        "target_snapshot_id": "snap-eval-2",
    }
    resp_eval = client.post("/api/v1/nexus/routing/evaluate", json=eval_req, headers=headers)
    assert resp_eval.status_code == 200
    routes = resp_eval.json()
    assert len(routes) >= 1
    target_route = next(r for r in routes if r["target_case_id"] == "CASE-207")
    route_id = target_route["route_id"]

    # 2. Query inbox
    resp_inbox = client.get("/api/v1/nexus/routing/inbox?case_id=CASE-207", headers=headers)
    assert resp_inbox.status_code == 200
    inbox_items = resp_inbox.json()
    assert any(r["route_id"] == route_id for r in inbox_items)

    # 3. Get single route detail
    resp_detail = client.get(f"/api/v1/nexus/routing/{route_id}", headers=headers)
    assert resp_detail.status_code == 200
    assert resp_detail.json()["route_id"] == route_id

    # 4. Acknowledge route
    ack_headers = {"X-Role": "investigator"}
    resp_ack = client.post(
        f"/api/v1/nexus/routing/{route_id}/acknowledge",
        json={"decision": "ACKNOWLEDGE", "note": "Verified by IO"},
        headers=ack_headers,
    )
    assert resp_ack.status_code == 200
    assert resp_ack.json()["status"] == "ACKNOWLEDGED"
    assert resp_ack.json()["acknowledgment_note"] == "Verified by IO"
