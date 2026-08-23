"""backend/app/auth/principal.py

Principal domain model for CaseClock.

A Principal is the verified identity of the caller attached to every
authenticated request.  Phase 1 routes carry no real auth; Phase 3 builds
this from a verified Catalyst Auth JWT.

Design:
  - Principal is immutable (frozen dataclass).
  - Role is validated against the shared UserRole enum.
  - Principal.anonymous() returns a sentinel for Phase 1 / public routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from shared.contracts.api import UserRole


@dataclass(frozen=True)
class Principal:
    """Verified caller identity.

    Attributes:
        user_id:     Catalyst user ID (ZUID), e.g. "1234567890"
        email:       Verified email from the Catalyst JWT.
        role:        Enforced role from the Catalyst user-defined role claim.
        is_anonymous: True for Phase 1 stopgap and public health endpoints.
    """

    user_id: str
    email: str
    role: UserRole
    is_anonymous: bool = False

    # Sentinel anonymous principal for Phase 1 routes that have no auth yet.
    _ANONYMOUS_ID: ClassVar[str] = "anonymous"
    _ANONYMOUS_EMAIL: ClassVar[str] = "anonymous@caseclock.internal"
    _ANONYMOUS_ROLE: ClassVar[UserRole] = UserRole.IO

    @classmethod
    def anonymous(cls) -> "Principal":
        """Return the anonymous principal for Phase 1 stopgap routes.

        Phase 3 removes this from route usage; it is still valid for
        health-check and metrics endpoints.
        """
        return cls(
            user_id=cls._ANONYMOUS_ID,
            email=cls._ANONYMOUS_EMAIL,
            role=cls._ANONYMOUS_ROLE,
            is_anonymous=True,
        )

    def can_view_worklist(self) -> bool:
        """All authenticated roles can view the worklist."""
        return not self.is_anonymous or True  # Phase 1: always allowed

    def can_access_sho_features(self) -> bool:
        """SHO and SP can access station-level oversight features."""
        return self.role in (UserRole.SHO, UserRole.SP)

    def can_access_sp_features(self) -> bool:
        """SP can access district-level aggregation and full escalation routing."""
        return self.role == UserRole.SP

    def can_view_audit_log(self) -> bool:
        """Audit log is restricted to SHO and above."""
        return self.role in (UserRole.SHO, UserRole.SP)

    def __str__(self) -> str:
        if self.is_anonymous:
            return "Principal(anonymous)"
        return f"Principal(user_id={self.user_id!r}, role={self.role.value!r})"
