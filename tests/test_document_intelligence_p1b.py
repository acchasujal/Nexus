"""tests/test_document_intelligence_p1b.py

Comprehensive tests for Phase P1-B: Document Intelligence (Entity & Candidate Relationship Extraction).

Strict Invariants Verified:
  1. Deterministic Extraction: Correct entity mentions, normalized values, source spans, and provenance.
  2. Evidence-Backed Relationships: Candidate relationships extracted ONLY when explicit evidence links them.
  3. Unsupported Inference Guard: Entities in same paragraph without connection produce NO candidate relationship.
  4. Read-Only Resolution: Surfacing candidate matches against graph nodes without automatic fusion or confirmation.
  5. Case RBAC: Unauthorized cases cannot be extracted or retrieved (HTTP 403).
  6. Idempotency: Repeated extraction calls return cached result without duplicating entities or audit spam.
  7. Strict No-Graph-Mutation Invariant: Authoritative graph state before == Authoritative graph state after.
"""

from __future__ import annotations

import copy
import hashlib
import io
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from backend.app.api.dependencies import get_principal
from backend.app.auth.principal import Principal
from backend.app.main import app
from backend.app.services.audit_service import AuditEventType
from shared.contracts.api import (
    CandidateResolutionStatus,
    DocumentSourceType,
    UserRole,
)


def _make_pdf(text: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, text)
    c.save()
    return buf.getvalue()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def ensure_clean_test_repo():
    app_repo = getattr(app.state, "repository", None)
    if app_repo and (not hasattr(app_repo, "nodes") or "person-0001" not in app_repo.nodes):
        app_repo.clear()


@pytest.fixture
def sp_token():
    """Superintendent of Police with divisional oversight across all cases."""
    def override():
        return Principal(
            user_id="OFFICER-DEMO-SP-01",
            email="sp.cyber@ksp.gov.in",
            role=UserRole.SP,
            is_anonymous=False,
        )

    app.dependency_overrides[get_principal] = override
    yield
    app.dependency_overrides.pop(get_principal, None)


@pytest.fixture
def io_assigned_token():
    """Investigating Officer assigned to case-0001."""
    def override():
        return Principal(
            user_id="OFFICER-DEMO-IO-01",
            email="rajesh.kumar@ksp.gov.in",
            role=UserRole.INVESTIGATOR,
            is_anonymous=False,
        )

    app.dependency_overrides[get_principal] = override
    yield
    app.dependency_overrides.pop(get_principal, None)


@pytest.fixture
def io_unassigned_token():
    """Investigating Officer not assigned to case-0001."""
    def override():
        return Principal(
            user_id="OFFICER-UNASSIGNED",
            officer_id="OFFICER-UNASSIGNED",
            email="unassigned@ksp.gov.in",
            role=UserRole.INVESTIGATOR,
            is_anonymous=False,
        )

    app.dependency_overrides[get_principal] = override
    yield
    app.dependency_overrides.pop(get_principal, None)


@pytest.fixture
def anonymous_token():
    """Unauthenticated caller."""
    def override():
        return Principal(
            user_id="anonymous",
            email="",
            role=UserRole.INVESTIGATOR,
            is_anonymous=True,
        )

    app.dependency_overrides[get_principal] = override
    yield
    app.dependency_overrides.pop(get_principal, None)


# ── TEST SUITE ───────────────────────────────────────────────────────────────

def test_document_a_person_phone_date_extraction(client, sp_token):
    """Document A: Inspector report states that Rajesh Kumar contacted 9876543210 on 12 August 2026.

    Expected:
      - Candidates: PERSON (Rajesh Kumar), PHONE (9876543210), DATE_TIME (12 August 2026).
      - Relationship: Rajesh Kumar -> COMMUNICATED_WITH -> 9876543210.
      - Exact source spans and document provenance.
    """
    text = "Inspector report states that Rajesh Kumar contacted 9876543210 on 12 August 2026."
    txt_bytes = text.encode("utf-8")

    # 1. Ingest document via P1A
    up_res = client.post(
        "/api/v1/documents",
        files={"file": ("report_rajesh_comm.txt", txt_bytes, "text/plain")},
        data={"source_type": DocumentSourceType.POLICE_REPORT.value, "case_id": "case-0001"},
    )
    assert up_res.status_code == 200, up_res.text
    doc_id = up_res.json()["document_id"]
    doc_hash = up_res.json()["content_hash"]

    # 2. Run P1B Candidate Extraction
    ext_res = client.post(f"/api/v1/documents/{doc_id}/extract")
    assert ext_res.status_code == 200, ext_res.text
    result = ext_res.json()

    assert result["document_id"] == doc_id
    assert result["content_hash"] == doc_hash
    assert result["status"] == "COMPLETED"

    entities = result["candidate_entities"]
    entity_types = {e["entity_type"]: e for e in entities}

    # Verify Person candidate
    assert "PERSON" in entity_types
    person = entity_types["PERSON"]
    assert person["surface_text"] == "Rajesh Kumar"
    assert person["normalized_value"] == "rajesh kumar"
    assert person["source_span"]["start"] == text.index("Rajesh Kumar")
    assert person["source_span"]["end"] == text.index("Rajesh Kumar") + len("Rajesh Kumar")
    assert person["provenance"]["document_id"] == doc_id
    assert person["provenance"]["document_sha256"] == doc_hash

    # Verify Phone candidate
    assert "PHONE" in entity_types
    phone = entity_types["PHONE"]
    assert phone["surface_text"] == "9876543210"
    assert phone["normalized_value"] == "9876543210"
    assert phone["source_span"]["start"] == text.index("9876543210")

    # Verify Date candidate
    assert "DATE_TIME" in entity_types
    date_ent = entity_types["DATE_TIME"]
    assert "12 August 2026" in date_ent["surface_text"]

    # Verify Candidate Relationship
    relationships = result["candidate_relationships"]
    assert len(relationships) >= 1
    rel = relationships[0]
    assert rel["relationship_type"] == "COMMUNICATED_WITH"
    assert rel["source_text"] == "Rajesh Kumar"
    assert rel["target_text"] == "9876543210"
    assert rel["status"] == "CANDIDATE"
    assert "contacted" in rel["evidence_text"]
    assert rel["provenance"]["document_id"] == doc_id


def test_document_b_account_transfer_extraction(client, sp_token):
    """Document B: Account 123456789 received a transfer of INR 250000 from account 987654321.

    Expected:
      - Candidates: ACCOUNT (123456789), ACCOUNT (987654321).
      - Relationship: 987654321 -> TRANSFERRED_TO -> 123456789.
    """
    text = "Account 123456789 received a transfer of INR 250000 from account 987654321."
    up_res = client.post(
        "/api/v1/documents",
        files={"file": ("bank_transfer_memo.txt", text.encode("utf-8"), "text/plain")},
        data={"source_type": DocumentSourceType.POLICE_REPORT.value},
    )
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    ext_res = client.post(f"/api/v1/documents/{doc_id}/extract")
    assert ext_res.status_code == 200
    result = ext_res.json()

    accounts = [e for e in result["candidate_entities"] if e["entity_type"] == "ACCOUNT"]
    assert len(accounts) == 2
    acc_numbers = {a["normalized_value"] for a in accounts}
    assert "123456789" in acc_numbers
    assert "987654321" in acc_numbers

    # Verify Financial relationship
    relationships = result["candidate_relationships"]
    assert len(relationships) >= 1
    rel = next((r for r in relationships if r["relationship_type"] == "TRANSFERRED_TO"), None)
    assert rel is not None
    assert rel["source_text"] == "987654321"
    assert rel["target_text"] == "123456789"
    assert "received a transfer" in rel["evidence_text"]


def test_document_c_vehicle_location_person_extraction(client, sp_token):
    """Document C: Suspect arrested in Bengaluru while driving vehicle KA01AB1234 named Suresh Gowda.

    Expected:
      - Candidates: PERSON (Suresh Gowda), VEHICLE (KA01AB1234), LOCATION (Bengaluru).
      - Relationship: Suresh Gowda -> USED_VEHICLE -> KA01AB1234.
    """
    text = "Suspect arrested in Bengaluru while driving vehicle KA01AB1234 named Suresh Gowda."
    up_res = client.post(
        "/api/v1/documents",
        files={"file": ("arrest_vehicle_memo.txt", text.encode("utf-8"), "text/plain")},
        data={"source_type": DocumentSourceType.POLICE_REPORT.value},
    )
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    ext_res = client.post(f"/api/v1/documents/{doc_id}/extract")
    assert ext_res.status_code == 200
    result = ext_res.json()

    entities_by_type = {e["entity_type"]: e for e in result["candidate_entities"]}
    assert "PERSON" in entities_by_type
    assert entities_by_type["PERSON"]["surface_text"] == "Suresh Gowda"

    assert "VEHICLE" in entities_by_type
    assert entities_by_type["VEHICLE"]["surface_text"] == "KA01AB1234"
    assert entities_by_type["VEHICLE"]["normalized_value"] == "KA01AB1234"

    assert "LOCATION" in entities_by_type
    assert "Bengaluru" in entities_by_type["LOCATION"]["surface_text"]

    # Verify USED_VEHICLE relationship
    veh_rel = next((r for r in result["candidate_relationships"] if r["relationship_type"] == "USED_VEHICLE"), None)
    assert veh_rel is not None
    assert veh_rel["source_text"] == "Suresh Gowda"
    assert veh_rel["target_text"] == "KA01AB1234"


def test_document_d_ambiguous_identity_resolution_candidate_only(client, sp_token):
    """Document D: Extracted person matches existing graph node.

    Expected:
      - Candidate resolution surfaces matching canonical entity in resolution_candidates.
      - Status is REVIEW_REQUIRED.
      - Absolute Invariant: NO automatic identity fusion, no canonical graph mutation.
    """
    # Use canonical name known to exist in demo graph: "Vikram Sharma" (person-0001)
    text = "Inspector states that Vikram Sharma submitted the preliminary investigation report."
    up_res = client.post(
        "/api/v1/documents",
        files={"file": ("vikram_report.txt", text.encode("utf-8"), "text/plain")},
        data={"source_type": DocumentSourceType.POLICE_REPORT.value, "case_id": "case-0001"},
    )
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    ext_res = client.post(f"/api/v1/documents/{doc_id}/extract")
    assert ext_res.status_code == 200
    result = ext_res.json()

    person_cand = next(e for e in result["candidate_entities"] if e["entity_type"] == "PERSON")
    assert person_cand["surface_text"] == "Vikram Sharma"

    # Status must be REVIEW_REQUIRED (not automatic MATCHED or CONFIRMED)
    assert person_cand["resolution_status"] == CandidateResolutionStatus.REVIEW_REQUIRED.value

    # Must contain candidate matches with scores and reasons
    assert len(person_cand["resolution_candidates"]) > 0
    top_match = person_cand["resolution_candidates"][0]
    assert top_match["canonical_entity_id"] == "person-0001"
    assert top_match["match_score"] >= 0.85
    assert "Exact name match" in top_match["match_reasons"] or "name" in str(top_match["match_reasons"]).lower()

    # Verify dedicated resolution endpoint
    cand_id = person_cand["candidate_id"]
    res_res = client.get(f"/api/v1/candidates/{cand_id}/resolution")
    assert res_res.status_code == 200
    assert len(res_res.json()) == len(person_cand["resolution_candidates"])


def test_document_e_unsupported_inference_guard(client, sp_token):
    """Document E: Entities appear in the same paragraph without relational evidence.

    Expected:
      - Entities (Person, Account) extracted.
      - ZERO unsupported candidate relationships produced.
    """
    text = "Inspector report states that Rajesh Kumar was on leave today. The bank account 987654321012 was audited separately by state revenue officers."
    up_res = client.post(
        "/api/v1/documents",
        files={"file": ("unsupported_inference.txt", text.encode("utf-8"), "text/plain")},
        data={"source_type": DocumentSourceType.POLICE_REPORT.value},
    )
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    ext_res = client.post(f"/api/v1/documents/{doc_id}/extract")
    assert ext_res.status_code == 200
    result = ext_res.json()

    # Entities should be found
    entity_types = {e["entity_type"] for e in result["candidate_entities"]}
    assert "PERSON" in entity_types
    assert "ACCOUNT" in entity_types

    # Relationship must NOT be created between Rajesh Kumar and 987654321012
    rajesh_account_rel = [
        r for r in result["candidate_relationships"]
        if "Rajesh" in r["source_text"] and "987654321012" in r["target_text"]
    ]
    assert len(rajesh_account_rel) == 0, "Unsupported relationship was erroneously generated!"


def test_document_f_case_rbac_enforcement(client):
    """Document F: RBAC boundaries strictly enforced on extraction and retrieval.

    Expected:
      - Anonymous caller receives 401.
      - Unassigned IO receives 403.
      - Assigned IO receives 200.
    """
    text = "Confidential seizure report for case-0001 detailing recovered mobile devices."
    
    # 1. Ingest under case-0001 using assigned IO
    app.dependency_overrides[get_principal] = lambda: Principal(
        user_id="OFFICER-DEMO-IO-01",
        email="rajesh.kumar@ksp.gov.in",
        role=UserRole.INVESTIGATOR,
        is_anonymous=False,
    )
    try:
        up_res = client.post(
            "/api/v1/documents",
            files={"file": ("seizure_case0001.txt", text.encode("utf-8"), "text/plain")},
            data={"case_id": "case-0001"},
        )
        assert up_res.status_code == 200
        doc_id = up_res.json()["document_id"]

        # 2. Anonymous extraction attempt -> 401
        app.dependency_overrides[get_principal] = lambda: Principal(
            user_id="anonymous",
            email="",
            role=UserRole.INVESTIGATOR,
            is_anonymous=True,
        )
        anon_ext = client.post(f"/api/v1/documents/{doc_id}/extract")
        assert anon_ext.status_code == 401

        # 3. Unassigned IO extraction attempt -> 403
        app.dependency_overrides[get_principal] = lambda: Principal(
            user_id="OFFICER-UNASSIGNED",
            officer_id="OFFICER-UNASSIGNED",
            email="unassigned@ksp.gov.in",
            role=UserRole.INVESTIGATOR,
            is_anonymous=False,
        )
        unassigned_ext = client.post(f"/api/v1/documents/{doc_id}/extract")
        assert unassigned_ext.status_code == 403
        assert "Forbidden" in unassigned_ext.json()["detail"]

        # Unassigned IO cannot retrieve candidates -> 403
        unassigned_get = client.get(f"/api/v1/documents/{doc_id}/candidates")
        assert unassigned_get.status_code == 403

        # 4. Assigned IO extraction attempt -> 200
        app.dependency_overrides[get_principal] = lambda: Principal(
            user_id="OFFICER-DEMO-IO-01",
            email="rajesh.kumar@ksp.gov.in",
            role=UserRole.INVESTIGATOR,
            is_anonymous=False,
        )
        assigned_ext = client.post(f"/api/v1/documents/{doc_id}/extract")
        assert assigned_ext.status_code == 200
        result = assigned_ext.json()
        assert result["document_id"] == doc_id

        assigned_get = client.get(f"/api/v1/documents/{doc_id}/candidates")
        assert assigned_get.status_code == 200
        assert assigned_get.json()["document_id"] == doc_id
    finally:
        app.dependency_overrides.pop(get_principal, None)


def test_extraction_idempotency_returns_cached_result(client, sp_token):
    """Verify that repeat calls to extract return the identical extraction run without duplicate work."""
    text = "FIR memo states that suspect Rajesh Kumar called 9876543210 yesterday."
    up_res = client.post(
        "/api/v1/documents",
        files={"file": ("idempotency_memo.txt", text.encode("utf-8"), "text/plain")},
        data={"source_type": DocumentSourceType.FIR_DOCUMENT.value},
    )
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    # First extraction run
    res1 = client.post(f"/api/v1/documents/{doc_id}/extract")
    assert res1.status_code == 200
    run_id1 = res1.json()["extraction_run_id"]
    extracted_at1 = res1.json()["extracted_at"]

    # Second extraction run (idempotent)
    res2 = client.post(f"/api/v1/documents/{doc_id}/extract")
    assert res2.status_code == 200
    data2 = res2.json()

    assert data2["extraction_run_id"] == run_id1
    assert data2["extracted_at"] == extracted_at1


def test_audit_trail_recorded_for_extraction(client, sp_token):
    """Verify DOCUMENT_EXTRACTION_STARTED and DOCUMENT_CANDIDATES_EXTRACTED audit events."""
    app_repo = getattr(app.state, "repository", None)
    text = "Intelligence bulletin states that Rajesh Kumar contacted 9988776655 in Bengaluru."
    up_res = client.post(
        "/api/v1/documents",
        files={"file": ("bulletin_audit.txt", text.encode("utf-8"), "text/plain")},
        data={"source_type": DocumentSourceType.INTELLIGENCE_DOCUMENT.value},
    )
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    ext_res = client.post(f"/api/v1/documents/{doc_id}/extract")
    assert ext_res.status_code == 200

    if hasattr(app_repo, "audit_events"):
        start_events = [
            e for e in app_repo.audit_events
            if e.get("event_type") == AuditEventType.DOCUMENT_EXTRACTION_STARTED.value
            and e.get("entity_id") == doc_id
        ]
        assert len(start_events) >= 1

        completed_events = [
            e for e in app_repo.audit_events
            if e.get("event_type") == AuditEventType.DOCUMENT_CANDIDATES_EXTRACTED.value
            and e.get("entity_id") == doc_id
        ]
        assert len(completed_events) >= 1
        assert completed_events[0]["details"]["entity_count"] > 0


def test_document_extraction_failed_audit_event(client, sp_token, monkeypatch):
    """Verify DOCUMENT_EXTRACTION_FAILED audit event is emitted on unexpected extraction errors."""
    app_repo = getattr(app.state, "repository", None)
    text = "Memo detailing suspect."
    up_res = client.post(
        "/api/v1/documents",
        files={"file": ("fail_audit.txt", text.encode("utf-8"), "text/plain")},
        data={"source_type": DocumentSourceType.POLICE_REPORT.value},
    )
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    from backend.app.services.document_extraction_service import DocumentExtractionService

    def mock_fail(*args, **kwargs):
        raise RuntimeError("Simulated deterministic extraction parser failure")

    monkeypatch.setattr(DocumentExtractionService, "_extract_deterministic_entities", mock_fail)

    ext_res = client.post(f"/api/v1/documents/{doc_id}/extract")
    assert ext_res.status_code == 500

    if hasattr(app_repo, "audit_events"):
        fail_events = [
            e for e in app_repo.audit_events
            if e.get("event_type") == AuditEventType.DOCUMENT_EXTRACTION_FAILED.value
            and e.get("entity_id") == doc_id
        ]
        assert len(fail_events) >= 1
        assert "Simulated deterministic extraction parser failure" in fail_events[0]["details"]["error"]


def test_strict_no_graph_mutation_invariant(client, sp_token):
    """MANDATORY P1B INVARIANT TEST:

    Authoritative Graph Before == Authoritative Graph After.
    Deep snapshot of nodes, node properties, and edges before extraction
    must strictly match after extraction.
    """
    app_repo = getattr(app.state, "repository", None)
    assert app_repo is not None

    # 1. Deep snapshot graph state before extraction
    nodes_before = copy.deepcopy(app_repo.nodes)
    edges_before = copy.deepcopy(app_repo.edges)
    node_count_before = len(nodes_before)
    edge_count_before = len(edges_before)

    # 2. Perform full extraction on multi-entity document
    text = "Inspector report states that Rajesh Kumar contacted 9876543210 while driving vehicle KA01AB1234."
    up_res = client.post(
        "/api/v1/documents",
        files={"file": ("boundary_test_p1b.txt", text.encode("utf-8"), "text/plain")},
        data={"source_type": DocumentSourceType.POLICE_REPORT.value},
    )
    assert up_res.status_code == 200
    doc_id = up_res.json()["document_id"]

    ext_res = client.post(f"/api/v1/documents/{doc_id}/extract")
    assert ext_res.status_code == 200
    cand_data = ext_res.json()
    assert cand_data["entity_count"] > 0
    assert cand_data["relationship_count"] > 0

    # 3. Deep snapshot graph state after extraction
    nodes_after = app_repo.nodes
    edges_after = app_repo.edges

    # Assert counts remain strictly identical
    assert len(nodes_after) == node_count_before, "Graph node count changed during P1B extraction!"
    assert len(edges_after) == edge_count_before, "Graph edge count changed during P1B extraction!"

    # Assert deep content equality (authoritative_graph_before == authoritative_graph_after)
    assert nodes_after == nodes_before, "Graph node properties or identities were mutated!"
    assert edges_after == edges_before, "Graph edges were mutated or appended to!"
