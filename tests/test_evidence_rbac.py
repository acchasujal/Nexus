"""tests/test_evidence_rbac.py

Comprehensive tests for NEXUS Trust Layer - Phase 2:
Resource-Level RBAC & Digital Evidence Authorization.

Tests cover:
  TEST 1: Authorized investigator requests evidence -> 200 / allowed -> EVIDENCE_VIEWED audit event created.
  TEST 2: Unauthorized officer requests evidence -> 403 / denied -> ACCESS_DENIED audit event created.
  TEST 3: Client attempts to spoof another officer's identity -> authorization still uses authenticated Principal.
  TEST 4: Changing frontend role/header alone cannot bypass backend authorization.
  TEST 5: Supervisor/authorized higher-level role can access appropriate evidence.
  TEST 6: Unknown/nonexistent evidence -> safe 404 response without leaking sensitive information.
  TEST 7: Existing evidence/dossier functionality remains compatible.
"""

from __future__ import annotations

import base64
import json
from fastapi.testclient import TestClient

from backend.app.auth.policy import EvidenceAction, EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import UserRole


def _make_demo_token(user_id: str, role: str) -> str:
    """Helper to generate a valid base64 demo token matching frontend AuthContext session."""
    payload = json.dumps({"sub": user_id, "role": role, "email": f"{user_id}@nexus.internal"})
    return base64.b64encode(payload.encode("utf-8")).decode("utf-8")


# TEST 1: Authorized investigator requests evidence -> 200 / allowed -> EVIDENCE_VIEWED audit event created
def test_authorized_investigator_access_allowed() -> None:
    app = create_app()
    client = TestClient(app)

    token = _make_demo_token("officer_io", "IO")

    # Fetch evidence for case-0001 (assigned to officer_io / Inspector Rajesh Kumar)
    # Target known evidence in case-0001: ev-27dd1b0aa23a1b71
    resp = client.get(
        "/api/v1/evidence/ev-27dd1b0aa23a1b71",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "ev-27dd1b0aa23a1b71"
    assert data["case_id"] == "case-0001"

    # Verify audit event: EVIDENCE_VIEWED recorded with authoritative actor
    audit_resp = client.get("/api/v1/audit?limit=10&role=SP")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    view_event = next(
        (e for e in events if e.get("action") == "evidence_viewed" and e.get("entity_id") == "ev-27dd1b0aa23a1b71"),
        None,
    )
    assert view_event is not None
    assert view_event["user_id"] == "officer_io"
    details = view_event.get("details", {})
    assert details.get("allowed") is True
    assert details.get("officer_id") == "OFFICER-DEMO-IO-01"


# TEST 2: Unauthorized officer requests evidence -> 403 / denied -> ACCESS_DENIED audit event created
def test_unauthorized_investigator_access_denied() -> None:
    app = create_app()
    client = TestClient(app)

    token = _make_demo_token("officer_io", "IO")

    # Fetch evidence for case-0002 (in Mysuru, NOT assigned to officer_io)
    # Target known evidence in case-0002: ev-4406352f2003b9a3
    resp = client.get(
        "/api/v1/evidence/ev-4406352f2003b9a3",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    error_body = resp.json()
    assert "Forbidden" in error_body["detail"]

    # Verify audit event: ACCESS_DENIED recorded with full details
    audit_resp = client.get("/api/v1/audit?limit=10&role=SP")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    denial_event = next(
        (e for e in events if e.get("action") == "access_denied" and e.get("entity_id") == "ev-4406352f2003b9a3"),
        None,
    )
    assert denial_event is not None
    assert denial_event["user_id"] == "officer_io"
    details = denial_event.get("details", {})
    assert details.get("allowed") is False
    assert details.get("officer_id") == "OFFICER-DEMO-IO-01"
    assert "not assigned" in details.get("reason", "").lower()


# TEST 3: Client attempts to spoof another officer's identity -> authorization still uses authenticated Principal
def test_client_spoofed_identity_uses_authenticated_principal() -> None:
    app = create_app()
    client = TestClient(app)

    # Caller token is officer_io (not assigned to case-0002)
    token = _make_demo_token("officer_io", "IO")

    # Request unassigned evidence attempting to send custom headers/query spoofing SP Vikram Hegde
    resp = client.get(
        "/api/v1/evidence/ev-4406352f2003b9a3?officer_id=OFFICER-DEMO-SP-01&role=SP",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Actor-Id": "OFFICER-DEMO-SP-01",
            "X-Officer-Name": "SP Vikram Hegde",
        },
    )
    # Must STILL be denied because authenticated token is officer_io
    assert resp.status_code == 403


# TEST 4: Changing frontend role/header alone cannot bypass backend authorization
def test_dev_role_header_cannot_override_bearer_token() -> None:
    app = create_app()
    client = TestClient(app)

    # Caller token is officer_io, but passes header X-Role: ADMIN or SP
    token = _make_demo_token("officer_io", "IO")

    resp = client.get(
        "/api/v1/evidence/ev-4406352f2003b9a3",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Role": "ADMIN",
            "X-Dev-Role": "SP",
        },
    )
    # TokenVerifier prioritizes verified bearer token over dev fallback headers
    assert resp.status_code == 403


# TEST 5: Supervisor/authorized higher-level role can access appropriate evidence
def test_supervisor_and_sho_access_evidence() -> None:
    app = create_app()
    client = TestClient(app)

    # SP token: state-wide / divisional oversight
    sp_token = _make_demo_token("officer_sp", "SP")
    resp_sp = client.get(
        "/api/v1/evidence/ev-27dd1b0aa23a1b71",
        headers={"Authorization": f"Bearer {sp_token}"},
    )
    assert resp_sp.status_code == 200
    assert resp_sp.json()["id"] == "ev-27dd1b0aa23a1b71"

    # SHO token: supervisory scope covers station/district (Bengaluru & Mangaluru)
    sho_token = _make_demo_token("officer_sho", "SHO")
    resp_sho = client.get(
        "/api/v1/evidence/ev-27dd1b0aa23a1b71",  # Mangaluru / CCB
        headers={"Authorization": f"Bearer {sho_token}"},
    )
    assert resp_sho.status_code == 200
    assert resp_sho.json()["id"] == "ev-27dd1b0aa23a1b71"


# TEST 6: Unknown/nonexistent evidence -> safe 404 response without leaking sensitive information
def test_nonexistent_evidence_returns_safe_404() -> None:
    app = create_app()
    client = TestClient(app)

    token = _make_demo_token("officer_io", "IO")
    resp = client.get(
        "/api/v1/evidence/ev-nonexistent-999999",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Evidence not found"


# TEST 7: Existing evidence/dossier functionality remains compatible
def test_evidence_list_and_verification_compatible() -> None:
    app = create_app()
    client = TestClient(app)

    token = _make_demo_token("officer_io", "IO")

    # List evidence: returns only evidence authorized for this officer
    resp_list = client.get(
        "/api/v1/evidence?limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert isinstance(items, list)
    # Every item returned must be from one of officer_io's assigned cases
    for item in items:
        assert item["case_id"] in ("case-0001", "case-0009", "case-0010")

    # Cryptographic verification endpoint remains functioning
    verify_resp = client.post(
        "/api/v1/evidence/verify",
        json={"evidence_ids": ["ev-27dd1b0aa23a1b71"], "path_node_ids": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["verification_status"] in ("VERIFIED", "INCOMPLETE")
    assert "ev-27dd1b0aa23a1b71" in v_data["evidence_hashes"]
