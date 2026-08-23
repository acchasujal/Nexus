"""tests/test_auth_verifier.py

Regression test suite for TokenVerifier exception handling, token validation,
and DevelopmentVerifier role parsing.
"""

from __future__ import annotations

import jwt
import pytest
from starlette.requests import Request

from backend.app.api.errors import ForbiddenError
from backend.app.auth.verifier import DevelopmentVerifier
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


@pytest.mark.asyncio
async def test_dev_verifier_default_role() -> None:
    verifier = DevelopmentVerifier(is_production=False)
    req = _make_request()
    principal = await verifier.verify(req)
    assert principal.role == UserRole.INVESTIGATOR
    assert principal.is_anonymous is True


@pytest.mark.asyncio
async def test_dev_verifier_header_role() -> None:
    verifier = DevelopmentVerifier(is_production=False)
    req = _make_request({"X-Role": "SUPERVISOR"})
    principal = await verifier.verify(req)
    assert principal.role == UserRole.SUPERVISOR


@pytest.mark.asyncio
async def test_dev_verifier_valid_jwt() -> None:
    secret = "test-secret-key-123-long-enough-32bytes-for-sha256"
    token = jwt.encode(
        {"sub": "officer-42", "role": "ANALYST", "email": "officer42@nexus.internal"},
        secret,
        algorithm="HS256",
    )
    verifier = DevelopmentVerifier(is_production=True, secret_key=secret)
    req = _make_request({"Authorization": f"Bearer {token}"})
    principal = await verifier.verify(req)
    assert principal.user_id == "officer-42"
    assert principal.role == UserRole.ANALYST
    assert principal.is_anonymous is False


@pytest.mark.asyncio
async def test_dev_verifier_invalid_jwt_in_production() -> None:
    verifier = DevelopmentVerifier(is_production=True, secret_key="test-secret-key-123")
    req = _make_request({"Authorization": "Bearer invalid.malformed.jwt.token"})
    with pytest.raises(ForbiddenError):
        await verifier.verify(req)
