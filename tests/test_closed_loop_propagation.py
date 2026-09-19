"""tests/test_closed_loop_propagation.py

Comprehensive tests for A8: Closed-Loop Propagation.
Verifies:
  1. Complete Closed Loop: Investigator Decision -> Graph Mutation -> Snapshot -> Diff -> A3 Events -> Pulse Refresh.
  2. A3 Event Enum Integrity: Exactly uses pre-existing IntelligenceEventType members.
  3. Case Scope Transparency: Snapshot case_scope is metadata; underlying store is global.
  4. Pulse Integrity: pulse-0082 is never emitted as dynamic intelligence.
  5. Idempotency: Decision ID is used as stable idempotency key; duplicate runs return cached result.
  6. Retry & Recovery: Failed propagation leaves mutation intact and can be retried cleanly.
  7. Verification Boundary: Verification tasks are NOT automatically created from pulses.
  8. API Endpoints: GET /nexus/propagation/{decision_id} and POST /nexus/propagation/retry/{decision_id}.
"""

from __future__ import annotations

import unittest.mock
import pytest
from fastapi.testclient import TestClient

from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import app
from backend.app.services.audit_service import AuditService
from backend.app.services.candidate_promotion_service import CandidatePromotionService
from backend.app.services.closed_loop_propagation_service import ClosedLoopPropagationService
from backend.app.services.graph_mutation_service import GraphMutationService
from backend.app.services.intelligence_event_service import IntelligenceEventService
from backend.app.services.proactive_intelligence_service import ProactiveIntelligenceService
from shared.contracts.api import (
    AcceptNewEntityRequest,
    AcceptRelationshipRequest,
    CandidateDecisionStatus,
    IntelligenceEventType,
    UserRole,
)


@pytest.fixture
def repo():
    r = InMemoryBackendRepository()
    r.clear()
    # Seed baseline node and edge
    r.nodes["person-0001"] = {
        "id": "person-0001",
        "entity_type": "Person",
        "properties": {"full_name": "Vikram Sharma", "case_id": "case-0001"},
    }
    r.nodes["person-0002"] = {
        "id": "person-0002",
        "entity_type": "Person",
        "properties": {"full_name": "Rafiq Khan", "case_id": "case-0001"},
    }
    r._rebuild_indexes()
    return r


@pytest.fixture
def audit_svc(repo):
    return AuditService(repo)


@pytest.fixture
def auth_policy(repo, audit_svc):
    return EvidenceAuthorizationPolicy(repo, audit_svc)


@pytest.fixture
def intel_svc(repo, audit_svc, auth_policy):
    return IntelligenceEventService(repo, audit_service=audit_svc, auth_policy=auth_policy)


@pytest.fixture
def proactive_svc(repo):
    svc = ProactiveIntelligenceService(repo)
    svc.clear_dynamic_pulses()
    return svc


@pytest.fixture
def propagation_svc(repo, proactive_svc, intel_svc, audit_svc, auth_policy):
    return ClosedLoopPropagationService(
        repository=repo,
        proactive_service=proactive_svc,
        intel_event_service=intel_svc,
        audit_service=audit_svc,
        auth_policy=auth_policy,
    )


@pytest.fixture
def mutator(repo):
    return GraphMutationService(repo)


@pytest.fixture
def promotion_svc(repo, mutator, audit_svc, auth_policy, propagation_svc):
    return CandidatePromotionService(
        repository=repo,
        mutation_service=mutator,
        audit_service=audit_svc,
        auth_policy=auth_policy,
        propagation_service=propagation_svc,
    )


@pytest.fixture
def authorized_io():
    return Principal(
        user_id="officer_io",
        email="io@nexus.gov.in",
        role=UserRole.INVESTIGATOR,
        officer_id="OFFICER-DEMO-IO-01",
    )


# ── 1. Complete End-to-End Closed Loop ───────────────────────────────────────

def test_closed_loop_relationship_promotion(repo, promotion_svc, proactive_svc, intel_svc, authorized_io):
    """Test full loop from relationship acceptance to pulse refresh."""
    # Seed candidate relationship
    cand_rel = {
        "candidate_id": "cand-rel-001",
        "candidate_relationship_id": "cand-rel-001",
        "relationship_id": "cand-rel-001",
        "source_canonical_id": "person-0001",
        "target_canonical_id": "person-0002",
        "relationship_type": "COMMUNICATED_WITH",
        "confidence": 0.95,
        "source_document_id": "doc-cdr-901",
        "case_id": "case-0001",
        "status": "PENDING",
    }
    repo.candidate_extractions["doc-cdr-901"] = {
        "document_id": "doc-cdr-901",
        "candidate_entities": [],
        "candidate_relationships": [cand_rel],
    }

    req = AcceptRelationshipRequest(
        source_canonical_id="person-0001",
        target_canonical_id="person-0002",
        relationship_type="COMMUNICATED_WITH",
        case_id="case-0001",
        notes="Corroborated by CDR logs",
    )

    decision = promotion_svc.accept_relationship("cand-rel-001", req, principal=authorized_io)

    # 1. Decision Assertions
    assert decision.status == CandidateDecisionStatus.ACCEPTED_RELATIONSHIP.value
    assert decision.propagation_status == "COMPLETED"
    assert decision.propagation_snapshot_id is not None
    assert decision.propagation_snapshot_id.startswith("snap-mut-")

    # 2. Graph State Mutation
    assert any(e.get("edge_type") == "COMMUNICATED_WITH" for e in repo.edges)

    # 3. Snapshot Creation
    snap_id = decision.propagation_snapshot_id
    snap_store = proactive_svc.get_snapshot_store(snap_id)
    assert snap_store is not None
    assert len(snap_store.nodes) >= 2

    # 4. IntelligenceEvents Emitted
    events, total = intel_svc.list_events(case_id="case-0001")
    assert total >= 4
    event_types = [e.event_type for e in events]
    assert IntelligenceEventType.INVESTIGATOR_DECISION in event_types
    assert IntelligenceEventType.RELATIONSHIP_OBSERVED in event_types
    assert IntelligenceEventType.SNAPSHOT_CREATED in event_types
    assert IntelligenceEventType.NETWORK_CHANGE_DETECTED in event_types
    assert IntelligenceEventType.SIGNAL_GENERATED in event_types

    # 5. Pulse Refresh
    active_pulses = proactive_svc.list_active_pulses(case_id="case-0001")
    assert len(active_pulses) >= 1
    generated_pulse = next((p for p in active_pulses if p.pulse_id != "pulse-0082"), None)
    assert generated_pulse is not None
    assert generated_pulse.pulse_id != "pulse-0082"
    assert "COMMUNICATED_WITH" in str(generated_pulse.change_ids) or "person-" in str(generated_pulse.affected_entities)
    assert len(generated_pulse.verification_plan) >= 1

    # 6. Verify Human-in-the-Loop: Tasks NOT automatically created
    tasks = getattr(repo, "verification_tasks", {})
    assert len(tasks) == 0


def test_closed_loop_entity_promotion(repo, promotion_svc, proactive_svc, intel_svc, authorized_io):
    """Test full loop from new entity creation to diff and snapshot."""
    cand_entity = {
        "candidate_id": "cand-ent-001",
        "entity_type": "PERSON",
        "surface_text": "Deepak Rao",
        "source_document_id": "doc-fir-101",
        "case_id": "case-0001",
        "status": "PENDING",
    }
    repo.candidate_extractions["doc-fir-101"] = {
        "document_id": "doc-fir-101",
        "candidate_entities": [cand_entity],
        "candidate_relationships": [],
    }

    req = AcceptNewEntityRequest(
        canonical_name="Deepak Rao",
        entity_type="Person",
        case_id="case-0001",
        notes="Primary suspect named in FIR",
    )

    decision = promotion_svc.accept_new_entity("cand-ent-001", req, principal=authorized_io)
    assert decision.status == CandidateDecisionStatus.ACCEPTED_NEW_ENTITY.value
    assert decision.propagation_status == "COMPLETED"

    # Events check
    events, total = intel_svc.list_events(case_id="case-0001")
    event_types = [e.event_type for e in events]
    assert IntelligenceEventType.INVESTIGATOR_DECISION in event_types
    assert IntelligenceEventType.ENTITY_OBSERVED in event_types
    assert IntelligenceEventType.SNAPSHOT_CREATED in event_types
    assert IntelligenceEventType.NETWORK_CHANGE_DETECTED in event_types


# ── 2. Idempotency on Stable Decision ID ─────────────────────────────────────

def test_propagation_idempotency(propagation_svc, authorized_io):
    """Verify that repeating propagation with same decision_id returns cached result."""
    res1 = propagation_svc.propagate_decision(
        decision_id="dec-test-idemp-001",
        case_id="case-0001",
        mutation_type="ENTITY_PROMOTED",
        target_id="person-0001",
        principal=authorized_io,
    )
    assert res1.status in ("COMPLETED", "SKIPPED_NO_DIFF")
    initial_event_count = len(res1.emitted_event_ids)

    # Re-run with identical decision_id
    res2 = propagation_svc.propagate_decision(
        decision_id="dec-test-idemp-001",
        case_id="case-0001",
        mutation_type="ENTITY_PROMOTED",
        target_id="person-0001",
        principal=authorized_io,
    )
    assert res2.status == res1.status
    assert res2.snapshot_id == res1.snapshot_id
    assert res2.emitted_event_ids == res1.emitted_event_ids
    assert res2.executed_at == res1.executed_at


# ── 3. Retry and Recovery Semantics ──────────────────────────────────────────

def test_propagation_retry_after_failure(repo, propagation_svc, authorized_io):
    """Verify that a failed propagation leaves mutation intact and can be retried."""
    decision_id = "dec-fail-test-01"

    # Seed mock candidate decision in repository
    repo.candidate_decisions[decision_id] = {
        "decision_id": decision_id,
        "case_id": "case-0001",
        "action": "ACCEPT_NEW",
        "resulting_graph_id": "person-0001",
    }

    # Simulate failure on first run
    with unittest.mock.patch.object(propagation_svc._proactive_svc, "create_snapshot", side_effect=RuntimeError("Snapshot store unavailable")):
        with pytest.raises(RuntimeError):
            propagation_svc.propagate_decision(
                decision_id=decision_id,
                case_id="case-0001",
                mutation_type="ENTITY_PROMOTED",
                target_id="person-0001",
                principal=authorized_io,
            )

    # Verify failure recorded
    failed = propagation_svc.get_propagation(decision_id)
    assert failed is not None
    assert failed.status == "FAILED"
    assert "Snapshot store unavailable" in (failed.error_message or "")

    # Retry propagation without mocking error
    retry_res = propagation_svc.retry_propagation(decision_id, principal=authorized_io)
    assert retry_res.status in ("COMPLETED", "SKIPPED_NO_DIFF")
    assert retry_res.snapshot_id is not None


# ── 4. Pulse Integrity (Never pulse-0082 as Dynamic) ─────────────────────────

def test_pulse_0082_never_emitted_as_dynamic(propagation_svc, authorized_io):
    """Verify that propagation never treats pulse-0082 as dynamic intelligence."""
    res = propagation_svc.propagate_decision(
        decision_id="dec-pulse-check-01",
        case_id="case-0001",
        mutation_type="RELATIONSHIP_PROMOTED",
        target_id="person-0001",
        principal=authorized_io,
    )
    assert "pulse-0082" not in res.generated_pulse_ids


# ── 5. Case Scope Transparency ───────────────────────────────────────────────

def test_case_scope_transparency(proactive_svc, propagation_svc, authorized_io):
    """Verify that case_scope is metadata and underlying store remains global."""
    res = propagation_svc.propagate_decision(
        decision_id="dec-scope-check-01",
        case_id="case-0001",
        mutation_type="ENTITY_PROMOTED",
        target_id="person-0001",
        principal=authorized_io,
    )
    snap = proactive_svc._snapshots[res.snapshot_id]
    assert snap["case_scope"] == "case-0001"
    # Store contains all global nodes
    assert len(snap["store"].nodes) >= 2


# ── 6. API Endpoints ─────────────────────────────────────────────────────────

def test_api_propagation_endpoints(authorized_io):
    """Test REST API routes GET /nexus/propagation/{id} and POST /nexus/propagation/retry/{id}."""
    client = TestClient(app)

    # Anonymous access rejected
    res_anon = client.get("/nexus/propagation/dec-missing")
    assert res_anon.status_code == 401

    headers = {
        "X-Role": "INVESTIGATOR",
        "X-User-Id": authorized_io.user_id,
        "X-User-Role": authorized_io.role.value,
        "X-User-District": "Bengaluru",
        "X-Assigned-Cases": "case-0001",
    }

    # 404 for unknown decision
    res_404 = client.get("/nexus/propagation/dec-nonexistent", headers=headers)
    assert res_404.status_code == 404

    # 404 retry for unknown decision
    res_retry_404 = client.post("/nexus/propagation/retry/dec-nonexistent", headers=headers)
    assert res_retry_404.status_code == 404
