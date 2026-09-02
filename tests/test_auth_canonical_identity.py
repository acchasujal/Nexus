"""tests/test_auth_canonical_identity.py

Tests for NEXUS Trust Layer - Phase 1A: Canonical Authenticated Officer Identity.
Verifies:
  - Authenticated requests resolve to expected canonical officer identity (officer_id, badge_number, name, role).
  - Role remains reliably available and correctly typed.
  - Client-provided actor/decided_by strings cannot override authoritative officer identity.
  - Anonymous / unauthenticated callers are properly flagged as is_anonymous=True.
  - Audit logs record the authoritative actor_id and officer details without trusting client overrides.
"""

from __future__ import annotations

import asyncio
import base64
import json
import jwt
from fastapi.testclient import TestClient
from starlette.requests import Request

from backend.app.auth.principal import (
    CANONICAL_DEMO_OFFICERS,
    Principal,
    resolve_officer_identity,
)
from backend.app.auth.verifier import DevelopmentVerifier
from backend.app.main import create_app
from shared.contracts.api import UserRole


def _make_request(headers: dict[str, str] | None = None) -> Request:
    raw_headers = [
        (k.lower().encode("latin-1"), v.encode("latin-1"))
        for k, v in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw_headers,
    }
    return Request(scope)


def test_resolve_canonical_demo_officer_identities() -> None:
    """Verify deterministic mapping for all demo roles."""
    for role in [
        UserRole.INVESTIGATOR,
        UserRole.IO,
        UserRole.ANALYST,
        UserRole.SHO,
        UserRole.SUPERVISOR,
        UserRole.SP,
        UserRole.ADMIN,
    ]:
        officer = resolve_officer_identity(user_id=f"officer_{role.value.lower()}", role=role)
        expected = CANONICAL_DEMO_OFFICERS[role]
        assert officer.officer_id == expected.officer_id
        assert officer.badge_number == expected.badge_number
        assert officer.name == expected.name
        assert officer.rank == expected.rank
        assert officer.role == role
        assert officer.station_id == expected.station_id


def test_principal_officer_identity_attributes() -> None:
    """Verify Principal exposes authoritative officer properties and get_officer_identity()."""
    principal = Principal(
        user_id="officer_io",
        email="officer_io@nexus.gov.in",
        role=UserRole.IO,
        is_anonymous=False,
        officer_id="OFFICER-DEMO-IO-01",
        badge_number="KA-1001",
        name="Inspector Rajesh Kumar",
    )
    assert principal.officer_id == "OFFICER-DEMO-IO-01"
    assert principal.badge_number == "KA-1001"
    assert principal.name == "Inspector Rajesh Kumar"
    assert principal.display_name == "Inspector Rajesh Kumar"
    assert principal.authoritative_actor_id == "OFFICER-DEMO-IO-01"
    assert principal.is_anonymous is False

    officer = principal.get_officer_identity()
    assert officer.officer_id == "OFFICER-DEMO-IO-01"
    assert officer.badge_number == "KA-1001"
    assert officer.name == "Inspector Rajesh Kumar"
    assert officer.rank == "Inspector"


def test_anonymous_principal_flags() -> None:
    """Verify Principal.anonymous() is cleanly marked and distinguishable."""
    anon = Principal.anonymous()
    assert anon.is_anonymous is True
    assert anon.user_id == "anonymous"
    assert anon.name == "Anonymous Caller"


def test_verifier_resolves_canonical_officer_from_jwt() -> None:
    """Verify TokenVerifier attaches canonical officer identity when parsing JWT."""
    secret = "nexus-test-secret"
    token = jwt.encode(
        {"sub": "officer_sho", "role": "SHO", "email": "officer_sho@nexus.gov.in"},
        secret,
        algorithm="HS256",
    )
    verifier = DevelopmentVerifier(is_production=True, secret_key=secret)
    req = _make_request({"Authorization": f"Bearer {token}"})
    principal = asyncio.run(verifier.verify(req))

    assert principal.is_anonymous is False
    assert principal.user_id == "officer_sho"
    assert principal.role == UserRole.SHO
    assert principal.officer_id == "OFFICER-DEMO-SHO-01"
    assert principal.badge_number == "KA-1002"
    assert principal.name == "SHO Sunita Sharma"


def test_verifier_resolves_canonical_officer_from_base64_session() -> None:
    """Verify rapid demo role session tokens resolve to canonical officer identities."""
    token_data = json.dumps({"sub": "officer_sp", "role": "SP", "email": "officer_sp@nexus.gov.in"})
    b64_token = base64.b64encode(token_data.encode("utf-8")).decode("utf-8")

    verifier = DevelopmentVerifier(is_production=False)
    req = _make_request({"Authorization": f"Bearer {b64_token}"})
    principal = asyncio.run(verifier.verify(req))

    assert principal.is_anonymous is False
    assert principal.user_id == "officer_sp"
    assert principal.role == UserRole.SP
    assert principal.officer_id == "OFFICER-DEMO-SP-01"
    assert principal.badge_number == "KA-1003"
    assert principal.name == "SP Vikram Hegde"


def test_client_spoofed_identity_cannot_override_candidate_decision() -> None:
    """Verify client-provided decided_by string cannot override authenticated officer identity."""
    app = create_app()
    client = TestClient(app)

    # Reset demo state
    client.post("/api/v1/nexus/demo/reset", headers={"X-Role": "INVESTIGATOR"})

    # Submit resolution decision with a spoofed decided_by attempt
    token_data = json.dumps({"sub": "officer_io", "role": "IO", "email": "officer_io@nexus.gov.in"})
    b64_token = base64.b64encode(token_data.encode("utf-8")).decode("utf-8")

    resp = client.post(
        "/api/v1/nexus/resolution/RC-1/decision",
        json={
            "decision": "CONFIRM",
            "decided_by": "ATTACKER_SPOOFED_NAME",  # Untrusted client input
            "note": "Authorized resolution",
        },
        headers={"Authorization": f"Bearer {b64_token}"},
    )
    assert resp.status_code == 200

    # Verify review candidates in state have authoritative officer name, not the spoofed string
    candidates_resp = client.get("/api/v1/nexus/resolution/candidates", headers={"Authorization": f"Bearer {b64_token}"})
    assert candidates_resp.status_code == 200
    candidates = candidates_resp.json()
    rc1 = next((c for c in candidates if c["id"] == "RC-1"), None)
    assert rc1 is not None
    assert rc1["decided_by"] == "Inspector Rajesh Kumar"  # Authoritative name!
    assert rc1["decided_by"] != "ATTACKER_SPOOFED_NAME"

    # Verify audit log recorded authoritative officer information
    audit_resp = client.get("/api/v1/audit?limit=10&role=SP")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    action_event = next((e for e in events if e.get("action") == "entity_resolution_executed"), None)
    assert action_event is not None
    assert action_event["user_id"] == "officer_io"
    details = action_event.get("details", {})
    assert details.get("decided_by") == "Inspector Rajesh Kumar"
    assert details.get("officer_id") == "OFFICER-DEMO-IO-01"
    assert details.get("badge_number") == "KA-1001"
    assert details.get("client_provided_decided_by") == "ATTACKER_SPOOFED_NAME"


def test_client_spoofed_identity_cannot_override_lead_decision() -> None:
    """Verify client-provided decided_by string cannot override lead decision attribution."""
    app = create_app()
    client = TestClient(app)

    client.post("/api/v1/nexus/demo/reset", headers={"X-Role": "INVESTIGATOR"})

    # First confirm RC-1 to ensure lead exists
    client.post(
        "/api/v1/nexus/resolution/RC-1/decision",
        json={"decision": "CONFIRM", "decided_by": "Investigating Officer"},
        headers={"X-Role": "INVESTIGATOR"},
    )

    leads_resp = client.get("/api/v1/nexus/leads", headers={"X-Role": "INVESTIGATOR"})
    assert leads_resp.status_code == 200
    leads = leads_resp.json()
    assert len(leads) >= 1
    lead_id = leads[0]["id"]

    # Submit decision as officer_sho with spoofed decided_by
    token_data = json.dumps({"sub": "officer_sho", "role": "SHO", "email": "officer_sho@nexus.gov.in"})
    b64_token = base64.b64encode(token_data.encode("utf-8")).decode("utf-8")

    dec_resp = client.post(
        f"/api/v1/nexus/leads/{lead_id}/decision",
        json={
            "decision": "ACCEPT",
            "decided_by": "ATTACKER_OVERRIDE_USER",
            "note": "Approved by station head",
        },
        headers={"Authorization": f"Bearer {b64_token}"},
    )
    assert dec_resp.status_code == 200
    decided_lead = dec_resp.json()

    # The returned lead must have authoritative decided_by, not the spoofed string
    assert decided_lead["decided_by"] == "SHO Sunita Sharma"
    assert decided_lead["decided_by"] != "ATTACKER_OVERRIDE_USER"

    # Verify audit log
    audit_resp = client.get("/api/v1/audit?limit=10&role=SP")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    lead_event = next((e for e in events if e.get("action") == "lead_actioned"), None)
    assert lead_event is not None
    assert lead_event["user_id"] == "officer_sho"
    details = lead_event.get("details", {})
    assert details.get("decided_by") == "SHO Sunita Sharma"
    assert details.get("officer_id") == "OFFICER-DEMO-SHO-01"
    assert details.get("badge_number") == "KA-1002"
    assert details.get("client_provided_decided_by") == "ATTACKER_OVERRIDE_USER"
