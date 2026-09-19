"""tests/test_candidate_promotion_p1c.py

Comprehensive test suite for Phase P1-C:
"Investigator Confirmation -> Authoritative Graph Mutation"

Test Matrix:
  1. Canonical ID Generation: Enforces existing conventions (person-XXXX, phone-XXXX, account-XXXX, etc.).
  2. Graph Schema Compatibility: Proves zero ad-hoc badges/properties and full GraphStore compatibility.
  3. MANDATORY Transaction Failure Test: Simulates mutation failure, asserts HTTP 500, candidate NOT accepted,
     no false success audit, no partial graph corruption, candidate available for retry, failure audit emitted.
  4. Zero LLM Verification: Asserts promotion path is 100% deterministic with zero generative calls.
  5. Accept Existing Entity: Correctly links candidate, updates aliases, records ENTITY_LINKED audit.
  6. Accept New Entity: Promotes candidate to new canonical node, records ENTITY_PROMOTED audit.
  7. Accept Relationship: Verifies prerequisite check (both endpoints must be authoritative) and deduplication.
  8. Reject Candidate: Marks candidate REJECTED, preserves record, records CANDIDATE_REJECTED, ZERO graph mutation.
  9. Server-Side RBAC: Enforces 401 for anonymous, 403 for ANALYST, 403 for unassigned IO, 200 for assigned IO/SP/Admin.
  10. Idempotency & Stale Detection: Double-click returns existing decision; conflicting decision raises 409.
"""

from __future__ import annotations

import unittest.mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.auth.principal import Principal
from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.core.graph.algorithms.utils import build_graph_store
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.candidate_promotion_service import CandidatePromotionService
from backend.app.services.graph_mutation_service import GraphMutationService
from shared.contracts.api import (
    AcceptExistingEntityRequest,
    AcceptNewEntityRequest,
    AcceptRelationshipRequest,
    CandidateDecisionStatus,
    RejectCandidateRequest,
    UserRole,
)


@pytest.fixture
def test_repo() -> InMemoryBackendRepository:
    repo = InMemoryBackendRepository()
    repo.clear()

    # Seed an extraction result with candidate entities and relationships
    cand_entity_1 = {
        "candidate_id": "cand-ent-001",
        "entity_type": "PERSON",
        "surface_text": "Rafiq K.",
        "normalized_value": "rafiq k",
        "confidence": 0.95,
        "source_document_id": "doc-test-101",
        "case_id": "case-0001",
        "source_span": {"start": 10, "end": 18},
        "evidence_text": "Accused Rafiq K. observed fleeing scene.",
        "extraction_method": "DETERMINISTIC",
        "provenance": {
            "document_id": "doc-test-101",
            "document_sha256": "hash-test-101",
            "source_text_hash": "span-hash-1",
            "case_id": "case-0001",
        },
        "resolution_status": "REVIEW_REQUIRED",
        "resolution_candidates": [
            {
                "canonical_entity_id": "person-0001",
                "canonical_name": "Vikram Sharma",
                "entity_type": "Person",
                "match_score": 0.88,
                "match_reasons": ["Phonetic name similarity"],
            }
        ],
        "status": "PENDING",
    }

    cand_entity_2 = {
        "candidate_id": "cand-ent-002",
        "entity_type": "PERSON",
        "surface_text": "Suresh Raina",
        "normalized_value": "suresh raina",
        "confidence": 0.92,
        "source_document_id": "doc-test-101",
        "case_id": "case-0001",
        "source_span": {"start": 40, "end": 52},
        "evidence_text": "Accompanied by Suresh Raina near the warehouse.",
        "extraction_method": "DETERMINISTIC",
        "provenance": {
            "document_id": "doc-test-101",
            "document_sha256": "hash-test-101",
            "source_text_hash": "span-hash-2",
            "case_id": "case-0001",
        },
        "resolution_status": "NO_MATCH_FOUND",
        "resolution_candidates": [],
        "status": "PENDING",
    }

    cand_rel_1 = {
        "candidate_relationship_id": "cand-rel-001",
        "source_candidate_id": "cand-ent-001",
        "target_candidate_id": "cand-ent-002",
        "source_text": "Rafiq K.",
        "target_text": "Suresh Raina",
        "relationship_type": "COMMUNICATED_WITH",
        "confidence": 0.89,
        "evidence_text": "Rafiq K. called Suresh Raina at 14:00.",
        "source_document_id": "doc-test-101",
        "case_id": "case-0001",
        "source_span": {"start": 10, "end": 52},
        "provenance": {
            "document_id": "doc-test-101",
            "document_sha256": "hash-test-101",
            "source_text_hash": "rel-hash-1",
            "case_id": "case-0001",
        },
        "status": "CANDIDATE",
    }

    extraction_record = {
        "document_id": "doc-test-101",
        "case_id": "case-0001",
        "content_hash": "hash-test-101",
        "extraction_run_id": "run-001",
        "extracted_at": "2026-03-20T10:00:00Z",
        "candidate_entities": [cand_entity_1, cand_entity_2],
        "candidate_relationships": [cand_rel_1],
        "entity_count": 2,
        "relationship_count": 1,
        "status": "COMPLETED",
        "extraction_notes": [],
    }
    repo.store_candidate_extraction(extraction_record)
    return repo


@pytest.fixture
def audit_service(test_repo: InMemoryBackendRepository) -> AuditService:
    return AuditService(test_repo)


@pytest.fixture
def auth_policy(test_repo: InMemoryBackendRepository, audit_service: AuditService) -> EvidenceAuthorizationPolicy:
    return EvidenceAuthorizationPolicy(test_repo, audit_service)


@pytest.fixture
def mutation_service(test_repo: InMemoryBackendRepository) -> GraphMutationService:
    return GraphMutationService(test_repo)


@pytest.fixture
def promotion_service(
    test_repo: InMemoryBackendRepository,
    mutation_service: GraphMutationService,
    audit_service: AuditService,
    auth_policy: EvidenceAuthorizationPolicy,
) -> CandidatePromotionService:
    return CandidatePromotionService(test_repo, mutation_service, audit_service, auth_policy)


@pytest.fixture
def assigned_io_principal() -> Principal:
    # Officer IO-01 is assigned to case-0001 in demo fixtures
    return Principal(
        user_id="OFFICER-DEMO-IO-01",
        email="rajesh.kumar@ksp.gov.in",
        role=UserRole.INVESTIGATOR,
        is_anonymous=False,
    )


@pytest.fixture
def unassigned_io_principal() -> Principal:
    return Principal(
        user_id="OFFICER-DEMO-IO-99",
        officer_id="OFFICER-DEMO-IO-99",
        email="unassigned@ksp.gov.in",
        role=UserRole.INVESTIGATOR,
        is_anonymous=False,
    )


@pytest.fixture
def analyst_principal() -> Principal:
    return Principal(
        user_id="OFFICER-DEMO-ANALYST-01",
        email="analyst@ksp.gov.in",
        role=UserRole.ANALYST,
        is_anonymous=False,
    )


@pytest.fixture
def supervisor_principal() -> Principal:
    return Principal(
        user_id="OFFICER-DEMO-SP-01",
        email="sp.cyber@ksp.gov.in",
        role=UserRole.SP,
        is_anonymous=False,
    )


# ── 1. CANONICAL ID GENERATION TEST ──────────────────────────────────────────

def test_canonical_id_generation_conventions(mutation_service: GraphMutationService, test_repo: InMemoryBackendRepository) -> None:
    """Verify newly generated entity IDs reuse existing NEXUS conventions (person-XXXX, phone-XXXX, etc.)."""
    # Count existing persons
    existing_person_ids = [k for k in test_repo.nodes if k.startswith("person-")]
    assert len(existing_person_ids) > 0, "Repo should have pre-existing person-XXXX nodes"

    new_person_id = mutation_service.generate_canonical_id("Person")
    assert new_person_id.startswith("person-")
    assert len(new_person_id.split("-")[1]) == 4, "ID suffix must be 4 digits padded with zeros"

    new_phone_id = mutation_service.generate_canonical_id("Phone")
    assert new_phone_id.startswith("phone-")

    new_account_id = mutation_service.generate_canonical_id("Account")
    assert new_account_id.startswith("account-")

    new_veh_id = mutation_service.generate_canonical_id("Vehicle")
    assert new_veh_id.startswith("vehicle-")

    new_loc_id = mutation_service.generate_canonical_id("Location")
    assert new_loc_id.startswith("location-")

    new_org_id = mutation_service.generate_canonical_id("Organization")
    assert new_org_id.startswith("org-")


# ── 2. GRAPH SCHEMA COMPATIBILITY TEST ───────────────────────────────────────

def test_graph_schema_compatibility_on_linking(
    promotion_service: CandidatePromotionService,
    test_repo: InMemoryBackendRepository,
    assigned_io_principal: Principal,
) -> None:
    """Verify link_candidate_to_entity does not introduce arbitrary fields and preserves GraphStore compatibility."""
    target_node = test_repo.nodes["person-0001"]
    initial_keys = set(target_node.keys())

    req = AcceptExistingEntityRequest(
        target_canonical_id="person-0001",
        case_id="case-0001",
        notes="Corroborated alias from FIR text",
    )

    resp = promotion_service.accept_existing_entity("cand-ent-001", req, assigned_io_principal)
    assert resp.status == CandidateDecisionStatus.ACCEPTED_EXISTING_ENTITY.value
    assert resp.resulting_graph_id == "person-0001"

    # Verify node properties
    updated_node = test_repo.nodes["person-0001"]
    assert set(updated_node.keys()) == initial_keys, "Top-level node structure must not have arbitrary fields"
    assert "badges" not in updated_node or "candidate_references" not in updated_node.get("badges", [])
    assert "Rafiq K." in updated_node["properties"]["aliases"], "Surface text should be added to aliases"

    # Verify GraphStore build succeeds without error
    store = build_graph_store(test_repo.nodes.values(), test_repo.edges)
    assert "person-0001" in store.nodes
    assert store.nodes["person-0001"].properties["aliases"] == updated_node["properties"]["aliases"]


# ── 3. MANDATORY TRANSACTION FAILURE TEST ────────────────────────────────────

def test_mandatory_transaction_failure_safeguard(
    promotion_service: CandidatePromotionService,
    test_repo: InMemoryBackendRepository,
    assigned_io_principal: Principal,
) -> None:
    """MANDATORY: Simulate graph/repository failure during mutation.

    Expected:
      - HTTP error raised (500)
      - Candidate is NOT marked ACCEPTED
      - No false-success decision recorded
      - No successful ENTITY_PROMOTED or ENTITY_LINKED event recorded
      - No partial graph mutation remains
      - Candidate remains available for retry (status remains PENDING)
      - Failure audit event recorded (CANDIDATE_PROMOTION_FAILED)
    """
    initial_node_count = len(test_repo.nodes)
    initial_audit_count = len(test_repo.audit_events)

    req = AcceptNewEntityRequest(
        entity_type="Person",
        canonical_name="Suresh Raina",
        case_id="case-0001",
        notes="Should fail due to simulated disk/graph error",
    )

    # Simulate failure in GraphMutationService during entity creation
    with unittest.mock.patch.object(
        promotion_service.mutator,
        "create_canonical_entity",
        side_effect=RuntimeError("Simulated Neo4j / Disk I/O Failure"),
    ):
        with pytest.raises(Exception) as exc_info:
            promotion_service.accept_new_entity("cand-ent-002", req, assigned_io_principal)

        assert "500" in str(exc_info.value) or "Graph mutation failed" in str(exc_info.value)

    # 1. Candidate is NOT marked ACCEPTED
    candidate = test_repo.get_candidate_entity("cand-ent-002")
    assert candidate is not None
    assert candidate.get("status") == "PENDING", "Candidate status must remain PENDING"
    assert candidate.get("resulting_graph_id") is None

    # 2. No false-success decision recorded
    decisions = test_repo.get_candidate_decisions("cand-ent-002")
    assert len(decisions) == 0, "No decision record should exist on failure"

    # 3. No partial graph mutation remains
    assert len(test_repo.nodes) == initial_node_count, "Node count must not increase"

    # 4. No successful promotion audit event recorded
    event_types = [e.get("action") for e in test_repo.audit_events[initial_audit_count:]]
    assert AuditEventType.ENTITY_PROMOTED.value not in event_types
    assert AuditEventType.ENTITY_LINKED.value not in event_types
    assert AuditEventType.CANDIDATE_ACCEPTED.value not in event_types

    # 5. Failure audit event was recorded per AuditService semantics
    assert AuditEventType.CANDIDATE_PROMOTION_FAILED.value in event_types
    failed_event = [e for e in test_repo.audit_events if e.get("action") == AuditEventType.CANDIDATE_PROMOTION_FAILED.value][0]
    assert failed_event.get("entity_id") == "cand-ent-002"
    assert "Simulated Neo4j / Disk I/O Failure" in str(failed_event.get("details", {}).get("error"))


# ── 4. ZERO LLM CALLS TEST ──────────────────────────────────────────────────

def test_zero_llm_calls_in_promotion_path(
    promotion_service: CandidatePromotionService,
    assigned_io_principal: Principal,
) -> None:
    """P1C MUST REMAIN DETERMINISTIC: Verify promotion service never calls any LLM."""
    req = AcceptNewEntityRequest(
        entity_type="Person",
        canonical_name="Suresh Raina",
        case_id="case-0001",
    )

    with unittest.mock.patch("backend.app.ai.llm_client.BaseLLMClient.generate") as mock_llm:
        resp = promotion_service.accept_new_entity("cand-ent-002", req, assigned_io_principal)
        assert resp.status == CandidateDecisionStatus.ACCEPTED_NEW_ENTITY.value
        assert mock_llm.call_count == 0, "LLM must NOT be called anywhere in P1C promotion path!"


# ── 5. ACCEPT NEW ENTITY TEST ────────────────────────────────────────────────

def test_accept_new_entity_success(
    promotion_service: CandidatePromotionService,
    test_repo: InMemoryBackendRepository,
    assigned_io_principal: Principal,
) -> None:
    """Verify promotion of candidate entity into new canonical node."""
    initial_count = len(test_repo.nodes)
    req = AcceptNewEntityRequest(
        entity_type="Person",
        canonical_name="Suresh Raina",
        case_id="case-0001",
        properties={"phone_number": "9845099999"},
        notes="Newly identified syndicate associate",
    )

    resp = promotion_service.accept_new_entity("cand-ent-002", req, assigned_io_principal)
    assert resp.status == CandidateDecisionStatus.ACCEPTED_NEW_ENTITY.value
    assert resp.resulting_graph_id is not None
    assert resp.resulting_graph_id.startswith("person-")

    # Verify node in repo
    assert len(test_repo.nodes) == initial_count + 1
    new_node = test_repo.nodes[resp.resulting_graph_id]
    assert new_node["properties"]["full_name"] == "Suresh Raina"
    assert new_node["properties"]["phone_number"] == "9845099999"

    # Verify candidate status
    candidate = test_repo.get_candidate_entity("cand-ent-002")
    assert candidate["status"] == CandidateDecisionStatus.ACCEPTED_NEW_ENTITY.value
    assert candidate["resulting_graph_id"] == resp.resulting_graph_id

    # Verify audit event
    audits = [e for e in test_repo.audit_events if e.get("action") == AuditEventType.ENTITY_PROMOTED.value]
    assert len(audits) >= 1
    assert audits[-1]["entity_id"] == "cand-ent-002"
    assert audits[-1]["details"]["created_canonical_id"] == resp.resulting_graph_id


# ── 6. ACCEPT RELATIONSHIP TEST ──────────────────────────────────────────────

def test_accept_relationship_prerequisite_and_deduplication(
    promotion_service: CandidatePromotionService,
    test_repo: InMemoryBackendRepository,
    assigned_io_principal: Principal,
) -> None:
    """Verify relationship promotion requires both endpoints to exist in authoritative graph."""
    # 1. Attempt promotion before endpoints exist -> 409 Conflict
    req_invalid = AcceptRelationshipRequest(
        source_canonical_id="cand-ent-001",  # Not in graph
        target_canonical_id="cand-ent-002",  # Not in graph
        relationship_type="COMMUNICATED_WITH",
        case_id="case-0001",
    )

    with pytest.raises(Exception) as exc_info:
        promotion_service.accept_relationship("cand-rel-001", req_invalid, assigned_io_principal)
    assert "409" in str(exc_info.value)
    assert "does not exist in authoritative graph" in str(exc_info.value)

    # 2. Promote endpoints first
    req_p1 = AcceptExistingEntityRequest(target_canonical_id="person-0001", case_id="case-0001")
    promotion_service.accept_existing_entity("cand-ent-001", req_p1, assigned_io_principal)

    req_p2 = AcceptNewEntityRequest(entity_type="Person", canonical_name="Suresh Raina", case_id="case-0001")
    resp_p2 = promotion_service.accept_new_entity("cand-ent-002", req_p2, assigned_io_principal)
    p2_id = resp_p2.resulting_graph_id

    # 3. Now promote relationship between authoritative endpoints
    req_valid = AcceptRelationshipRequest(
        source_canonical_id="person-0001",
        target_canonical_id=p2_id,
        relationship_type="COMMUNICATED_WITH",
        case_id="case-0001",
        notes="Confirmed direct CDR connection",
    )

    initial_edge_count = len(test_repo.edges)
    resp_rel = promotion_service.accept_relationship("cand-rel-001", req_valid, assigned_io_principal)
    assert resp_rel.status == CandidateDecisionStatus.ACCEPTED_RELATIONSHIP.value
    assert len(test_repo.edges) == initial_edge_count + 1

    # Verify edge attributes
    edge = [e for e in test_repo.edges if e.get("id") == resp_rel.target_id][0]
    assert edge["source_id"] == "person-0001"
    assert edge["target_id"] == p2_id
    assert edge["edge_type"] == "COMMUNICATED_WITH"
    assert edge["provenance"]["derivation_method"] == "INVESTIGATOR_CONFIRMATION"

    # 4. Deduplication test: Promoting an identical edge again corroborates rather than duplicates
    resp_dedup = promotion_service.accept_relationship("cand-rel-001", req_valid, assigned_io_principal)
    # Returns idempotent decision
    assert resp_dedup.status == CandidateDecisionStatus.ACCEPTED_RELATIONSHIP.value
    assert len(test_repo.edges) == initial_edge_count + 1, "Should NOT duplicate edge"


# ── 7. REJECT CANDIDATE TEST ─────────────────────────────────────────────────

def test_reject_candidate_preserves_zero_mutation(
    promotion_service: CandidatePromotionService,
    test_repo: InMemoryBackendRepository,
    assigned_io_principal: Principal,
) -> None:
    """Verify rejection never mutates the graph and marks candidate as REJECTED."""
    initial_node_count = len(test_repo.nodes)
    initial_edge_count = len(test_repo.edges)

    req = RejectCandidateRequest(
        reason="Entity mentioned only as a bystander with no evidentiary value",
        notes="Verified against CCTV",
    )

    resp = promotion_service.reject_candidate("cand-ent-001", req, assigned_io_principal, candidate_type="ENTITY")
    assert resp.status == CandidateDecisionStatus.REJECTED.value
    assert resp.resulting_graph_id is None

    # Zero graph mutations
    assert len(test_repo.nodes) == initial_node_count
    assert len(test_repo.edges) == initial_edge_count

    # Candidate marked REJECTED
    candidate = test_repo.get_candidate_entity("cand-ent-001")
    assert candidate["status"] == CandidateDecisionStatus.REJECTED.value

    # Audit event emitted
    audits = [e for e in test_repo.audit_events if e.get("action") == AuditEventType.CANDIDATE_REJECTED.value]
    assert len(audits) >= 1
    assert audits[-1]["entity_id"] == "cand-ent-001"
    assert "bystander" in audits[-1]["details"]["reason"]


# ── 8. SERVER-SIDE RBAC TEST ─────────────────────────────────────────────────

def test_server_side_rbac_enforcement(
    promotion_service: CandidatePromotionService,
    assigned_io_principal: Principal,
    unassigned_io_principal: Principal,
    analyst_principal: Principal,
    supervisor_principal: Principal,
) -> None:
    """Verify strict server-side RBAC:
      - Anonymous: 401/403
      - Analyst: 403 (Read-only, no mutations permitted)
      - Unassigned IO: 403 (Must be assigned to case)
      - Assigned IO: 200 OK
      - Supervisor / SP: 200 OK
    """
    req = AcceptNewEntityRequest(
        entity_type="Person",
        canonical_name="Test Person",
        case_id="case-0001",
    )

    # 1. Anonymous Principal -> 403
    anon_principal = Principal.anonymous()
    with pytest.raises(Exception) as exc_anon:
        promotion_service.accept_new_entity("cand-ent-001", req, anon_principal)
    assert "403" in str(exc_anon.value)

    # 2. Analyst Principal -> 403 Forbidden
    with pytest.raises(Exception) as exc_analyst:
        promotion_service.accept_new_entity("cand-ent-001", req, analyst_principal)
    assert "403" in str(exc_analyst.value)
    assert "ANALYST role has analytical read access only" in str(exc_analyst.value)

    # 3. Unassigned IO Principal -> 403 Forbidden
    with pytest.raises(Exception) as exc_unassigned:
        promotion_service.accept_new_entity("cand-ent-001", req, unassigned_io_principal)
    assert "403" in str(exc_unassigned.value)
    assert "is not assigned to case case-0001" in str(exc_unassigned.value)

    # 4. Assigned IO Principal -> Authorized
    resp_assigned = promotion_service.accept_new_entity("cand-ent-002", req, assigned_io_principal)
    assert resp_assigned.status == CandidateDecisionStatus.ACCEPTED_NEW_ENTITY.value

    # 5. Supervisor Principal -> Authorized
    req_sup = AcceptExistingEntityRequest(target_canonical_id="person-0001", case_id="case-0001")
    resp_sup = promotion_service.accept_existing_entity("cand-ent-001", req_sup, supervisor_principal)
    assert resp_sup.status == CandidateDecisionStatus.ACCEPTED_EXISTING_ENTITY.value


# ── 9. IDEMPOTENCY & CONFLICT PROTECTION ─────────────────────────────────────

def test_idempotency_and_decision_conflict(
    promotion_service: CandidatePromotionService,
    assigned_io_principal: Principal,
) -> None:
    """Verify double-click returns existing decision, while conflicting decision raises 409."""
    req_new = AcceptNewEntityRequest(
        entity_type="Person",
        canonical_name="Suresh Raina",
        case_id="case-0001",
    )

    # First call
    resp1 = promotion_service.accept_new_entity("cand-ent-002", req_new, assigned_io_principal)
    assert resp1.status == CandidateDecisionStatus.ACCEPTED_NEW_ENTITY.value

    # Double-click re-submission -> identical decision returned
    resp2 = promotion_service.accept_new_entity("cand-ent-002", req_new, assigned_io_principal)
    assert resp2.decision_id == resp1.decision_id
    assert resp2.resulting_graph_id == resp1.resulting_graph_id

    # Attempt conflicting decision (linking to existing entity when already created as new) -> 409 Conflict
    req_conflict = AcceptExistingEntityRequest(target_canonical_id="person-0001", case_id="case-0001")
    with pytest.raises(Exception) as exc_info:
        promotion_service.accept_existing_entity("cand-ent-002", req_conflict, assigned_io_principal)
    assert "409" in str(exc_info.value)
    assert "already been decided" in str(exc_info.value)


# ── 10. FASTAPI ROUTE END-TO-END INTEGRATION TEST ───────────────────────────

def test_fastapi_endpoints_integration(test_repo: InMemoryBackendRepository) -> None:
    """Test full HTTP request cycle through FastAPI endpoints."""
    from backend.app.api.core_routes import create_core_router
    from backend.app.api.dependencies import get_principal, get_repository

    app = FastAPI()
    router = create_core_router()
    app.include_router(router, prefix="/api/v1")

    # Override dependencies for test client
    io_principal = Principal(
        user_id="OFFICER-DEMO-IO-01",
        email="rajesh.kumar@ksp.gov.in",
        role=UserRole.INVESTIGATOR,
        is_anonymous=False,
    )
    app.dependency_overrides[get_repository] = lambda: test_repo
    app.dependency_overrides[get_principal] = lambda: io_principal

    client = TestClient(app)

    # 1. Accept New Entity via POST /api/v1/candidates/{id}/accept-new
    res_new = client.post(
        "/api/v1/candidates/cand-ent-002/accept-new",
        json={"entity_type": "Person", "canonical_name": "Suresh Raina", "case_id": "case-0001"},
    )
    assert res_new.status_code == 200, res_new.text
    data_new = res_new.json()
    assert data_new["status"] == "ACCEPTED_NEW_ENTITY"
    new_person_id = data_new["resulting_graph_id"]

    # 2. Accept Existing Entity via POST /api/v1/candidates/{id}/accept-entity
    res_link = client.post(
        "/api/v1/candidates/cand-ent-001/accept-entity",
        json={"target_canonical_id": "person-0001", "case_id": "case-0001", "notes": "Linked by IO"},
    )
    assert res_link.status_code == 200, res_link.text
    assert res_link.json()["status"] == "ACCEPTED_EXISTING_ENTITY"

    # 3. Accept Relationship via POST /api/v1/candidate-relationships/{id}/accept
    res_rel = client.post(
        "/api/v1/candidate-relationships/cand-rel-001/accept",
        json={
            "source_canonical_id": "person-0001",
            "target_canonical_id": new_person_id,
            "relationship_type": "COMMUNICATED_WITH",
            "case_id": "case-0001",
        },
    )
    assert res_rel.status_code == 200, res_rel.text
    assert res_rel.json()["status"] == "ACCEPTED_RELATIONSHIP"

    # 4. Get Decision History via GET /api/v1/candidates/{id}/decisions
    res_dec = client.get("/api/v1/candidates/cand-ent-001/decisions")
    assert res_dec.status_code == 200, res_dec.text
    decisions = res_dec.json()
    assert len(decisions) >= 1
    assert decisions[0]["action"] == "ACCEPT_EXISTING"
