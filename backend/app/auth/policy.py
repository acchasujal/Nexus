"""backend/app/auth/policy.py

Central Resource-Level Authorization Policy Engine for NEXUS.
Phase 2: RBAC & Digital Evidence Authorization.

Defines deterministic authorization decisions for sensitive resources,
specifically digital evidence, according to officer role, jurisdiction,
station assignment, and case-level authorizations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.app.auth.principal import OfficerIdentity, Principal
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import UserRole


class EvidenceAction(str, Enum):
    VIEW = "VIEW"
    DOWNLOAD = "DOWNLOAD"
    EXPORT = "EXPORT"


@dataclass(frozen=True)
class AuthorizationDecision:
    """Structured deterministic decision returned by the authorization policy engine."""
    allowed: bool
    reason: str
    officer_id: str
    badge_number: str | None
    role: UserRole
    resource_id: str
    action: EvidenceAction
    case_id: str | None = None
    district: str | None = None


# Deterministic assignments for demo officers to mirror realistic police jurisdictional hierarchy.
# Clearly isolated configuration for synthetic and demo datasets.
DEMO_OFFICER_CASE_ASSIGNMENTS: dict[str, set[str]] = {
    # Inspector Rajesh Kumar (IO / INVESTIGATOR) is directly assigned to specific cases:
    # case-0001 (Mangaluru), case-0009 (Bengaluru Rural), and case-0010 (Bengaluru Rural)
    "OFFICER-DEMO-IO-01": {"case-0001", "case-0009", "case-0010"},
}

# Stations supervised by SHO (Station House Officer) in demo mode
DEMO_SHO_STATIONS: dict[str, set[str]] = {
    "OFFICER-DEMO-SHO-01": {"Central Crime Branch", "Cyber Crime PS", "STATION-CYBER-CRIME-BLR"},
}

# Districts supervised by SHO (Station House Officer) in demo mode
DEMO_SHO_DISTRICTS: dict[str, set[str]] = {
    "OFFICER-DEMO-SHO-01": {"Bengaluru Central", "Bengaluru Rural", "Bengaluru Urban", "Mangaluru"},
}


class EvidenceAuthorizationPolicy:
    """Centralized resource-level authorization engine for digital evidence in NEXUS.

    Authorization Rules:
      1. ADMIN: Full system oversight, authorized to access digital evidence for audit and compliance.
      2. SUPERVISOR / SP: Superintendent / State Cyber Division oversight; broad jurisdiction across cases.
      3. SHO / STATION HOUSE OFFICER: Supervisory oversight across cases registered in their station or district jurisdiction.
      4. INVESTIGATOR / IO: Restricted to evidence belonging to cases they are explicitly assigned to.
      5. ANALYST: Intelligence analysis within assigned jurisdiction/cases. Unassigned cross-jurisdictional evidence is restricted.
      6. ANONYMOUS: Denied unconditionally.
    """

    def __init__(self, repository: Any, audit_service: AuditService) -> None:
        self._repo = repository
        self._audit = audit_service

    def resolve_evidence_context(self, evidence_id: str) -> dict[str, Any] | None:
        """Resolve the case and jurisdictional context for a given evidence item.

        Checks direct edge links in the graph store, repository source records, and incident edges.
        Returns a dict with 'case_id', 'district', 'station_name' or None if evidence doesn't exist.
        """
        nodes = getattr(self._repo, "nodes", {})
        edges = getattr(self._repo, "edges", [])

        # 1. Check in repo.source_records if present
        source_records = getattr(self._repo, "source_records", {})
        if evidence_id in source_records:
            s_rec = source_records[evidence_id]
            c_ids = s_rec.get("case_ids") or []
            case_id = c_ids[0] if c_ids else None
            district = None
            station_name = None
            if case_id and case_id in nodes:
                c_props = nodes[case_id].get("properties", {})
                district = c_props.get("district")
                station_name = c_props.get("station_name")
            return {
                "case_id": case_id,
                "district": district,
                "station_name": station_name,
                "record": s_rec,
            }

        # 2. Check edges for evidence ID match or provenance source_id match
        for edge in edges:
            prov = edge.get("provenance", {})
            src_id = prov.get("source_id")
            s_node = edge.get("source_id", "")
            t_node = edge.get("target_id", "")
            e_type = edge.get("edge_type", "")

            # Match on deterministic evidence id or raw source id
            # Construct candidate evidence IDs
            from backend.app.services.evidence_service import _make_evidence_id
            computed_ev_id = _make_evidence_id(src_id or "", s_node, t_node, e_type) if src_id else None

            if evidence_id == computed_ev_id or (src_id and evidence_id == src_id) or evidence_id in (s_node, t_node):
                # Infer case_id
                case_id = None
                for nid in (s_node, t_node):
                    node = nodes.get(nid, {})
                    if node.get("entity_type") in ("Case", "CASE"):
                        case_id = nid
                        break

                district = None
                station_name = None
                if case_id and case_id in nodes:
                    c_props = nodes[case_id].get("properties", {})
                    district = c_props.get("district")
                    station_name = c_props.get("station_name")

                return {
                    "case_id": case_id,
                    "district": district,
                    "station_name": station_name,
                    "edge": edge,
                }

        return None

    def authorize_evidence_access(
        self,
        principal: Principal,
        evidence_id: str,
        action: EvidenceAction = EvidenceAction.VIEW,
        context: dict[str, Any] | None = None,
        request_id: str | None = None,
        suppress_audit: bool = False,
    ) -> AuthorizationDecision:
        """Deterministically decide if the authenticated principal can perform the requested action on evidence."""
        officer: OfficerIdentity = principal.get_officer_identity()
        role = principal.role

        # Reject anonymous callers immediately
        if principal.is_anonymous:
            decision = AuthorizationDecision(
                allowed=False,
                reason="Unauthenticated anonymous callers cannot access evidence.",
                officer_id=principal.user_id,
                badge_number=None,
                role=role,
                resource_id=evidence_id,
                action=action,
            )
            if not suppress_audit:
                self._record_decision_audit(decision, principal, request_id)
            return decision

        # Resolve evidence metadata if not passed
        ev_ctx = context if context is not None else self.resolve_evidence_context(evidence_id)
        if ev_ctx is None:
            # Evidence doesn't exist
            decision = AuthorizationDecision(
                allowed=False,
                reason="Evidence record not found.",
                officer_id=officer.officer_id,
                badge_number=officer.badge_number,
                role=role,
                resource_id=evidence_id,
                action=action,
            )
            return decision

        case_id = ev_ctx.get("case_id")
        district = ev_ctx.get("district")
        station_name = ev_ctx.get("station_name")

        # 1. ADMIN
        if role == UserRole.ADMIN:
            decision = AuthorizationDecision(
                allowed=True,
                reason="System administrator granted oversight access.",
                officer_id=officer.officer_id,
                badge_number=officer.badge_number,
                role=role,
                resource_id=evidence_id,
                action=action,
                case_id=case_id,
                district=district,
            )
            if not suppress_audit:
                self._record_decision_audit(decision, principal, request_id)
            return decision

        # 2. SUPERVISOR / SP
        if role in (UserRole.SUPERVISOR, UserRole.SP):
            # SP / Supervisor has state-wide / divisional supervisory oversight across all cases
            decision = AuthorizationDecision(
                allowed=True,
                reason=f"{officer.rank} supervisory authority covers evidence across jurisdictional division.",
                officer_id=officer.officer_id,
                badge_number=officer.badge_number,
                role=role,
                resource_id=evidence_id,
                action=action,
                case_id=case_id,
                district=district,
            )
            if not suppress_audit:
                self._record_decision_audit(decision, principal, request_id)
            return decision

        # 3. SHO / STATION HOUSE OFFICER
        if role == UserRole.SHO:
            allowed_stations = DEMO_SHO_STATIONS.get(officer.officer_id, set())
            allowed_districts = DEMO_SHO_DISTRICTS.get(officer.officer_id, set())

            station_match = bool(station_name and station_name in allowed_stations)
            district_match = bool(district and district in allowed_districts)

            if station_match or district_match or not case_id:
                decision = AuthorizationDecision(
                    allowed=True,
                    reason="SHO supervisory scope covers police station or district jurisdiction.",
                    officer_id=officer.officer_id,
                    badge_number=officer.badge_number,
                    role=role,
                    resource_id=evidence_id,
                    action=action,
                    case_id=case_id,
                    district=district,
                )
            else:
                decision = AuthorizationDecision(
                    allowed=False,
                    reason=f"Evidence belonging to case outside SHO station/district jurisdiction ({district or 'Unknown'}).",
                    officer_id=officer.officer_id,
                    badge_number=officer.badge_number,
                    role=role,
                    resource_id=evidence_id,
                    action=action,
                    case_id=case_id,
                    district=district,
                )
            if not suppress_audit:
                self._record_decision_audit(decision, principal, request_id)
            return decision

        # 4. INVESTIGATOR / IO
        if role in (UserRole.INVESTIGATOR, UserRole.IO):
            assigned_cases = DEMO_OFFICER_CASE_ASSIGNMENTS.get(officer.officer_id, set())
            if case_id and case_id in assigned_cases:
                decision = AuthorizationDecision(
                    allowed=True,
                    reason=f"Investigating Officer assigned directly to case {case_id}.",
                    officer_id=officer.officer_id,
                    badge_number=officer.badge_number,
                    role=role,
                    resource_id=evidence_id,
                    action=action,
                    case_id=case_id,
                    district=district,
                )
            else:
                target_case = case_id or "unassigned case"
                decision = AuthorizationDecision(
                    allowed=False,
                    reason=f"Investigator is not assigned to {target_case}.",
                    officer_id=officer.officer_id,
                    badge_number=officer.badge_number,
                    role=role,
                    resource_id=evidence_id,
                    action=action,
                    case_id=case_id,
                    district=district,
                )
            if not suppress_audit:
                self._record_decision_audit(decision, principal, request_id)
            return decision

        # 5. ANALYST
        if role == UserRole.ANALYST:
            # Analysts have access within their assigned district/jurisdiction
            analyst_districts = DEMO_SHO_DISTRICTS.get(officer.officer_id, {"Bengaluru Central", "Bengaluru Rural", "Bengaluru Urban"})
            if district and district in analyst_districts:
                decision = AuthorizationDecision(
                    allowed=True,
                    reason=f"Analyst assigned to intelligence scope for district {district}.",
                    officer_id=officer.officer_id,
                    badge_number=officer.badge_number,
                    role=role,
                    resource_id=evidence_id,
                    action=action,
                    case_id=case_id,
                    district=district,
                )
            else:
                decision = AuthorizationDecision(
                    allowed=False,
                    reason=f"Analyst not assigned to intelligence jurisdiction for {district or 'target case'}.",
                    officer_id=officer.officer_id,
                    badge_number=officer.badge_number,
                    role=role,
                    resource_id=evidence_id,
                    action=action,
                    case_id=case_id,
                    district=district,
                )
            if not suppress_audit:
                self._record_decision_audit(decision, principal, request_id)
            return decision

        # Fallback denial
        decision = AuthorizationDecision(
            allowed=False,
            reason=f"Role {role.value} does not have access permissions for digital evidence.",
            officer_id=officer.officer_id,
            badge_number=officer.badge_number,
            role=role,
            resource_id=evidence_id,
            action=action,
            case_id=case_id,
            district=district,
        )
        if not suppress_audit:
            self._record_decision_audit(decision, principal, request_id)
        return decision

    def _record_decision_audit(
        self,
        decision: AuthorizationDecision,
        principal: Principal,
        request_id: str | None = None,
    ) -> None:
        """Record immutable audit events using the authoritative Principal and decision outcome."""
        event_type = AuditEventType.EVIDENCE_VIEWED if decision.allowed else AuditEventType.ACCESS_DENIED
        self._audit.record(
            event_type=event_type,
            actor_id=principal.user_id,
            case_id=decision.case_id,
            entity_id=decision.resource_id,
            entity_type="Evidence",
            request_id=request_id,
            details={
                "allowed": decision.allowed,
                "action": decision.action.value,
                "reason": decision.reason,
                "officer_id": decision.officer_id,
                "badge_number": decision.badge_number,
                "role": decision.role.value if hasattr(decision.role, "value") else str(decision.role),
                "resource_id": decision.resource_id,
                "case_id": decision.case_id,
                "district": decision.district,
            },
        )
