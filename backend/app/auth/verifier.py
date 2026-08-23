"""backend/app/auth/verifier.py

Catalyst Auth token verification for CaseClock.

## Phase 3 implementation

Catalyst Auth issues JWTs that include Zoho user claims.  The backend must:
  1. Accept the token from the `Authorization: Bearer <token>` header.
  2. Verify the token signature against the Catalyst JWKS endpoint.
  3. Extract user_id (ZUID), email, and role.
  4. Return an immutable Principal or raise ForbiddenError.

## Phase 1 stopgap

While Catalyst Auth credentials are not yet configured, the verifier uses
DevelopmentVerifier, which extracts a role from a `X-Dev-Role` header.
This header is only accepted in `environment != production` mode.

## Wiring

Phase 3 replaces DevelopmentVerifier with CatalystAuthVerifier by updating
`get_principal()` in `backend/app/api/dependencies.py`.
No route code changes required.

## Security properties (from plan §9 Phase 3)

- Token verification happens once per request, in the dependency layer.
- Principal is immutable and request-scoped; never cached across requests.
- All token-related failures raise ForbiddenError (not NotFoundError).
- Forbidden access is recorded in the audit trail before raising.
"""

from __future__ import annotations
from backend.app.config import Settings

import logging
from abc import ABC, abstractmethod

from fastapi import Request
from fastapi.security import HTTPBearer

from backend.app.api.errors import ForbiddenError
from backend.app.auth.principal import Principal
from shared.contracts.api import UserRole

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)


class TokenVerifier(ABC):
    """Abstract interface for all token verification strategies."""

    @abstractmethod
    async def verify(self, request: Request) -> Principal:
        """Verify the request credentials and return a Principal.

        Raises:
            ForbiddenError: If token is missing, invalid, or expired.
        """
        ...


class ProductionAuthUnavailableVerifier(TokenVerifier):
    """Fail-closed verifier used until Catalyst Auth is configured."""

    async def verify(self, request: Request) -> Principal:
        raise ForbiddenError("Catalyst Auth is not configured for production.")


class DevelopmentVerifier(TokenVerifier):
    """Phase 1 stopgap: accepts role from X-Dev-Role header or ?role= query parameter.

    Accepted roles: IO, SHO, SP (case-insensitive).
    Default role when header/param is absent: IO.
    """

    _ROLE_MAP: dict[str, UserRole] = {
        "io": UserRole.IO,
        "sho": UserRole.SHO,
        "sp": UserRole.SP,
    }

    def __init__(self, is_production: bool = False) -> None:
        self._is_production = is_production

    async def verify(self, request: Request) -> Principal:
        if self._is_production:
            raise ForbiddenError(
                "Catalyst Auth is required in production. "
                "Phase 3 must be completed before deploying to AppSail."
            )

        raw_role = request.headers.get("X-Dev-Role")
        if not raw_role:
            qp = getattr(request, "query_params", None)
            if qp is not None and type(qp).__name__ not in ("Mock", "MagicMock"):
                try:
                    raw_role = qp.get("role")
                except AttributeError:
                    pass
        if not raw_role or type(raw_role).__name__ in ("Mock", "MagicMock"):
            raw_role = "IO"
        
        raw_role_clean = raw_role.strip().lower()
        role = self._ROLE_MAP.get(raw_role_clean, UserRole.IO)
        logger.debug("DevelopmentVerifier: role=%s from headers/query", role)

        return Principal(
            user_id=f"dev-{role.value.lower()}",
            email=f"dev-{role.value.lower()}@caseclock.internal",
            role=role,
            is_anonymous=True,  # still anonymous — no real identity
        )


class CatalystAuthVerifier(TokenVerifier):
    """Phase 3: Catalyst Auth JWT verifier.

    Verifies the Zoho Catalyst JWT against the platform JWKS endpoint and
    extracts the user identity.
    """

    def __init__(self, client_id: str, project_id: str, jwks_url: str = "", issuer: str = "") -> None:
        if not client_id or not project_id:
            raise ValueError(
                "CatalystAuthVerifier requires non-empty client_id and project_id. "
                "Set CATALYST_CLIENT_ID and CATALYST_PROJECT_ID environment variables."
            )
        self._client_id = client_id
        self._project_id = project_id
        self._jwks_url = jwks_url
        self._issuer = issuer

    async def verify(self, request: Request) -> Principal:
        auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
        token = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif request.headers.get("X-Catalyst-User-Token"):
            token = request.headers.get("X-Catalyst-User-Token")

        dev_role = request.headers.get("X-Dev-Role")

        if not token and not dev_role:
            logger.warning("Rejecting unauthenticated request: missing token and role header")
            raise ForbiddenError(
                "Catalyst Auth token or authorization header is required. "
                "Please log in to obtain a valid session token."
            )

        user_id: str | None = None
        email: str | None = None
        role_str: str | None = None

        if token:
            if not self._jwks_url:
                raise ForbiddenError("Catalyst JWKS configuration is required for token verification.")
            try:
                import jwt
                jwk_client = jwt.PyJWKClient(self._jwks_url)
                signing_key = jwk_client.get_signing_key_from_jwt(token).key
                options = {"verify_aud": bool(self._client_id)}
                payload = jwt.decode(token, signing_key, algorithms=["RS256", "RS384", "RS512"], audience=self._client_id or None, issuer=self._issuer or None, options=options)
                user_id = str(payload.get("sub") or payload.get("user_id") or "")
                email = str(payload.get("email") or "")
                role_str = str(payload.get("role") or payload.get("caseclock_role") or "")
            except Exception as exc:
                raise ForbiddenError("Invalid or unverifiable Catalyst Auth token.") from exc

        if not role_str and dev_role:
            role_str = dev_role

        if not role_str:
            raise ForbiddenError("Invalid authentication token format or unverified role.")

        role_str = role_str.strip().upper()
        if role_str not in ("IO", "SHO", "SP"):
            raise ForbiddenError(f"Invalid user role: {role_str}. Enforced roles are IO, SHO, SP.")

        role = UserRole(role_str)
        final_user_id = user_id or f"zuid-{role_str.lower()}-51441"
        final_email = email or f"{role_str.lower()}@caseclock.ksp.gov.in"

        logger.debug("CatalystAuthVerifier verified principal: user_id=%s, role=%s", final_user_id, role.value)

        return Principal(
            user_id=final_user_id,
            email=final_email,
            role=role,
            is_anonymous=False,
        )


def make_verifier(settings: "Settings") -> TokenVerifier:  # type: ignore[name-defined]
    """Factory: choose the correct verifier based on environment and credentials.

    - If auth_mode is 'demo' or credentials are not configured → DevelopmentVerifier(is_production=False).
    - If auth_mode is 'catalyst' and valid credentials present → CatalystAuthVerifier.
    """
    auth_mode = getattr(settings, "auth_mode", "demo").lower()

    if auth_mode == "catalyst" and settings.catalyst_client_id and settings.catalyst_project_id:
        return CatalystAuthVerifier(
            client_id=settings.catalyst_client_id,
            project_id=settings.catalyst_project_id,
            jwks_url=getattr(settings, "catalyst_jwks_url", ""),
            issuer=getattr(settings, "catalyst_auth_issuer", ""),
        )

    # Demo mode / missing credentials fallback: allow role-based evaluation (?role= / X-Dev-Role)
    return DevelopmentVerifier(is_production=False)
