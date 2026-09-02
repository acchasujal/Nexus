"""backend/app/auth/principal.py

Principal domain model, canonical officer identity, and RBAC authorization policies for NEXUS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from shared.contracts.api import UserRole


@dataclass(frozen=True)
class OfficerIdentity:
    """Canonical officer identity mapped to verified authentications and graph/database Officer entities."""
    officer_id: str
    badge_number: str
    name: str
    rank: str
    role: UserRole
    station_id: str | None = None
    district: str | None = None


# Deterministic canonical officer identities for demo users and role switching
CANONICAL_DEMO_OFFICERS: dict[UserRole, OfficerIdentity] = {
    UserRole.INVESTIGATOR: OfficerIdentity(
        officer_id="OFFICER-DEMO-IO-01",
        badge_number="KA-1001",
        name="Inspector Rajesh Kumar",
        rank="Inspector",
        role=UserRole.INVESTIGATOR,
        station_id="STATION-CYBER-CRIME-BLR",
        district="Bengaluru Central",
    ),
    UserRole.IO: OfficerIdentity(
        officer_id="OFFICER-DEMO-IO-01",
        badge_number="KA-1001",
        name="Inspector Rajesh Kumar",
        rank="Inspector",
        role=UserRole.IO,
        station_id="STATION-CYBER-CRIME-BLR",
        district="Bengaluru Central",
    ),
    UserRole.ANALYST: OfficerIdentity(
        officer_id="OFFICER-DEMO-SHO-01",
        badge_number="KA-1002",
        name="SHO Sunita Sharma",
        rank="Station House Officer",
        role=UserRole.ANALYST,
        station_id="STATION-CYBER-CRIME-BLR",
        district="Bengaluru Central",
    ),
    UserRole.SHO: OfficerIdentity(
        officer_id="OFFICER-DEMO-SHO-01",
        badge_number="KA-1002",
        name="SHO Sunita Sharma",
        rank="Station House Officer",
        role=UserRole.SHO,
        station_id="STATION-CYBER-CRIME-BLR",
        district="Bengaluru Central",
    ),
    UserRole.SUPERVISOR: OfficerIdentity(
        officer_id="OFFICER-DEMO-SP-01",
        badge_number="KA-1003",
        name="SP Vikram Hegde",
        rank="Superintendent of Police",
        role=UserRole.SUPERVISOR,
        station_id="HQ-CID-CYBER-KARNATAKA",
        district="State Cyber Division",
    ),
    UserRole.SP: OfficerIdentity(
        officer_id="OFFICER-DEMO-SP-01",
        badge_number="KA-1003",
        name="SP Vikram Hegde",
        rank="Superintendent of Police",
        role=UserRole.SP,
        station_id="HQ-CID-CYBER-KARNATAKA",
        district="State Cyber Division",
    ),
    UserRole.ADMIN: OfficerIdentity(
        officer_id="OFFICER-DEMO-ADMIN-01",
        badge_number="KA-1000",
        name="System Administrator",
        rank="Director of Cyber Intelligence",
        role=UserRole.ADMIN,
        station_id="HQ-MHA-NCRB-DELHI",
        district="National Cybercrime Operations",
    ),
}


def resolve_officer_identity(
    user_id: str,
    role: UserRole,
    officer_id: str | None = None,
    badge_number: str | None = None,
    name: str | None = None,
) -> OfficerIdentity:
    """Deterministically resolve a canonical OfficerIdentity from authentication credentials."""
    canonical_demo = CANONICAL_DEMO_OFFICERS.get(role)

    # Check if user_id or sub matches a demo username pattern (e.g. officer_io, dev-io, user-001)
    is_demo_user = (
        user_id.startswith("officer_")
        or user_id.startswith("dev-")
        or user_id in ("user-001", "anonymous")
        or (officer_id is None and badge_number is None and name is None)
    )

    if is_demo_user and canonical_demo is not None:
        return OfficerIdentity(
            officer_id=officer_id or canonical_demo.officer_id,
            badge_number=badge_number or canonical_demo.badge_number,
            name=name or canonical_demo.name,
            rank=canonical_demo.rank,
            role=role,
            station_id=canonical_demo.station_id,
            district=canonical_demo.district,
        )

    # Custom / production officer fallback
    resolved_id = officer_id or f"OFFICER-{user_id.upper()}"
    resolved_badge = badge_number or f"BDG-{user_id[-4:].upper()}"
    resolved_name = name or user_id.replace("_", " ").title()

    return OfficerIdentity(
        officer_id=resolved_id,
        badge_number=resolved_badge,
        name=resolved_name,
        rank=canonical_demo.rank if canonical_demo else "Officer",
        role=role,
        station_id=canonical_demo.station_id if canonical_demo else None,
        district=canonical_demo.district if canonical_demo else None,
    )


@dataclass(frozen=True)
class Principal:
    """Verified caller identity carrying authoritative canonical officer details."""
    user_id: str
    email: str
    role: UserRole
    is_anonymous: bool = False
    officer_id: str | None = None
    badge_number: str | None = None
    name: str | None = None

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
            officer_id=None,
            badge_number=None,
            name="Anonymous Caller",
        )

    def get_officer_identity(self) -> OfficerIdentity:
        """Return the authoritative, canonical OfficerIdentity for this Principal."""
        return resolve_officer_identity(
            user_id=self.user_id,
            role=self.role,
            officer_id=self.officer_id,
            badge_number=self.badge_number,
            name=self.name,
        )

    @property
    def display_name(self) -> str:
        """Authoritative officer name or fallback user ID."""
        return self.name or self.user_id

    @property
    def authoritative_actor_id(self) -> str:
        """Authoritative identifier for audit logging and entity attribution."""
        return self.officer_id or self.user_id

    def can_view_investigations(self) -> bool:
        return True

    def can_view_network(self) -> bool:
        return True

    def can_run_resolution(self) -> bool:
        return True

    def can_view_audit_log(self) -> bool:
        # All authenticated roles may view the audit log in demo mode. The audit log contains
        # only the investigator's own actions (no PII beyond what they performed themselves).
        # Production deployments with stricter access requirements would tighten this via
        # environment config or a feature flag rather than hardcoding role lists here.
        return self.role in (
            UserRole.INVESTIGATOR,
            UserRole.IO,
            UserRole.ANALYST,
            UserRole.SUPERVISOR,
            UserRole.ADMIN,
            UserRole.SHO,
            UserRole.SP,
        )

    def can_export_evidence(self) -> bool:
        return self.role in (UserRole.SUPERVISOR, UserRole.ADMIN, UserRole.SP)

    # Legacy permission methods for backwards compatibility
    def can_view_worklist(self) -> bool:
        return True

    def can_view_sho_features(self) -> bool:
        return self.role in (UserRole.SUPERVISOR, UserRole.ADMIN, UserRole.SHO, UserRole.SP)

    def can_view_sp_features(self) -> bool:
        return self.role in (UserRole.SUPERVISOR, UserRole.ADMIN, UserRole.SP)
