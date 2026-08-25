"""backend/app/auth/principal.py

Principal domain model and RBAC authorization policies for NEXUS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from shared.contracts.api import UserRole


@dataclass(frozen=True)
class Principal:
    """Verified caller identity."""
    user_id: str
    email: str
    role: UserRole
    is_anonymous: bool = False

    _ANONYMOUS_ID: ClassVar[str] = "anonymous"
    _ANONYMOUS_EMAIL: ClassVar[str] = "anonymous@nexus.internal"
    _ANONYMOUS_ROLE: ClassVar[UserRole] = UserRole.INVESTIGATOR

    @classmethod
    def anonymous(cls) -> Principal:
        return cls(
            user_id=cls._ANONYMOUS_ID,
            email=cls._ANONYMOUS_EMAIL,
            role=cls._ANONYMOUS_ROLE,
            is_anonymous=True,
        )

    def can_view_investigations(self) -> bool:
        return True

    def can_view_network(self) -> bool:
        return True

    def can_run_resolution(self) -> bool:
        return True

    def can_view_audit_log(self) -> bool:
        return self.role in (UserRole.SUPERVISOR, UserRole.ADMIN, UserRole.SHO, UserRole.SP)

    def can_export_evidence(self) -> bool:
        return self.role in (UserRole.SUPERVISOR, UserRole.ADMIN, UserRole.SP)

    # Legacy permission methods for backwards compatibility
    def can_view_worklist(self) -> bool:
        return True

    def can_view_sho_features(self) -> bool:
        return self.role in (UserRole.SUPERVISOR, UserRole.ADMIN, UserRole.SHO, UserRole.SP)

    def can_view_sp_features(self) -> bool:
        return self.role in (UserRole.SUPERVISOR, UserRole.ADMIN, UserRole.SP)
