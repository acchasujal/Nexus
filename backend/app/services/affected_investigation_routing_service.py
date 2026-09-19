"""backend/app/services/affected_investigation_routing_service.py

Authoritative Affected Investigation Routing Service for NEXUS (A14).
Deterministically routes criminal network change intelligence to existing investigations
following authoritative graph mutations and network diffs.

Strict Invariants:
  1. Zero Predictive Guilt: Strictly structural, evidence-grounded intersection without
     guilt, criminality, or priority ranking scores.
  2. Exact A3 Taxonomy Compatibility: Reuses IntelligenceEventType.SIGNAL_GENERATED
     with source_type="AFFECTED_INVESTIGATION_ROUTE"; zero redundant event enums.
  3. Reused Lifecycle: Reuses PulseDeliveryStatus (DISPATCHED, DELIVERED, ACKNOWLEDGED, ACTIONED, REJECTED).
  4. Originating Case Exclusion: The originating case of a mutation is explicitly excluded
     from target routes to prevent self-routing.
  5. Deterministic Idempotency: Routes are uniquely identified by (source_snapshot, target_snapshot, target_case).
     Repeated diff evaluations return existing routes without duplicate creation or spam.
  6. Graph Mutation Isolation: Routing failures never roll back graph state or snapshots.
  7. Human-in-the-Loop: Verification tasks are NOT automatically created from routes.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.intelligence_event_service import IntelligenceEventService
from shared.contracts.api import (
    AcknowledgeRouteRequest,
    AffectedInvestigationRoute,
    CreateIntelligenceEventRequest,
    IntelligenceEventType,
    PulseDeliveryStatus,
    PulseSecurityClassification,
    UserRole,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def compute_route_integrity_hash(payload: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 digest over normalized route payload."""
    normalized_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized_json.encode("utf-8")).hexdigest()


def make_route_id(source_snapshot_id: str, target_snapshot_id: str, target_case_id: str) -> str:
    """
    Generate deterministic canonical route identifier.
    e.g. route-snap01-snap02-CASE-207
    """
    s_clean = source_snapshot_id.replace("snap-", "").replace("mut-", "")[:6]
    t_clean = target_snapshot_id.replace("snap-", "").replace("mut-", "")[:6]
    c_clean = target_case_id.replace("case-", "").replace("CASE-", "")
    return f"route-{s_clean}-{t_clean}-{c_clean}"


class AffectedInvestigationRoutingService:
    """Application-layer service managing deterministic affected case resolution and routing."""

    def __init__(
        self,
        repository: InMemoryBackendRepository,
        audit_service: AuditService,
        auth_policy: EvidenceAuthorizationPolicy | None = None,
        intelligence_event_service: IntelligenceEventService | None = None,
    ) -> None:
        self.repo = repository
        self.audit = audit_service
        self.auth_policy = auth_policy
        self.intel_svc = intelligence_event_service
        if getattr(self.repo, "affected_routes", None) is None:
            self.repo.affected_routes = {}

    def route_network_diff(
        self,
        raw_diff: Any,
        origin_case_id: str | None,
        target_snapshot_id: str,
        source_snapshot_id: str,
        trigger_event_id: str | None = None,
        principal: Principal | None = None,
        evidence_refs: list[str] | None = None,
    ) -> list[AffectedInvestigationRoute]:
        """
        Deterministically resolve affected existing investigations from a NetworkDiff
        and create/dispatch persistent routing records.
        """
        # 1. Extract changed entity IDs and relationship IDs
        added_nodes = list(getattr(raw_diff, "added_nodes", []))
        modified_nodes = list(getattr(raw_diff, "modified_nodes", []))
        removed_nodes = list(getattr(raw_diff, "removed_nodes", []))
        changed_entity_ids = sorted(list(set(added_nodes + modified_nodes + removed_nodes)))

        added_relationships = list(getattr(raw_diff, "added_relationships", []))
        modified_relationships = list(getattr(raw_diff, "modified_relationships", []))
        removed_relationships = list(getattr(raw_diff, "removed_relationships", []))
        changed_edge_ids = sorted(list(set(added_relationships + modified_relationships + removed_relationships)))

        diff_summary = {
            "added_nodes": len(added_nodes),
            "modified_nodes": len(modified_nodes),
            "removed_nodes": len(removed_nodes),
            "added_relationships": len(added_relationships),
            "modified_relationships": len(modified_relationships),
            "removed_relationships": len(removed_relationships),
        }

        return self.route_entities_and_edges(
            entity_ids=changed_entity_ids,
            edge_ids=changed_edge_ids,
            origin_case_id=origin_case_id,
            target_snapshot_id=target_snapshot_id,
            source_snapshot_id=source_snapshot_id,
            trigger_event_id=trigger_event_id,
            diff_summary=diff_summary,
            principal=principal,
            evidence_refs=evidence_refs,
        )

    def route_entities_and_edges(
        self,
        entity_ids: list[str],
        edge_ids: list[str],
        origin_case_id: str | None,
        target_snapshot_id: str,
        source_snapshot_id: str,
        trigger_event_id: str | None = None,
        diff_summary: dict[str, int] | None = None,
        principal: Principal | None = None,
        evidence_refs: list[str] | None = None,
    ) -> list[AffectedInvestigationRoute]:
        """
        Resolve intersecting existing cases and dispatch routing records idempotently.
        """
        clean_origin = str(origin_case_id).strip() if origin_case_id else None
        origin_district = "Unknown District"
        if clean_origin and clean_origin in self.repo.nodes:
            origin_props = self.repo.nodes[clean_origin].get("properties", {})
            origin_district = origin_props.get("district", "Unknown District")

        # 2. Deterministic Graph-Case Intersection
        resolved_cases = self.repo.resolve_cases_for_entities_and_edges(entity_ids, edge_ids)

        actor_id = principal.user_id if (principal and not principal.is_anonymous) else "SYSTEM"
        routes: list[AffectedInvestigationRoute] = []

        for target_case_id, case_info in resolved_cases.items():
            # 3. Explicit Originating Case Exclusion: Do NOT route to the origin case itself!
            if clean_origin and target_case_id == clean_origin:
                logger.debug("Skipping self-route to origin case '%s'", clean_origin)
                continue

            target_district = case_info.get("district", "Unknown District")
            intersecting_entities = case_info.get("intersecting_entity_ids", [])
            intersecting_edges = case_info.get("intersecting_edge_ids", [])
            reasons = case_info.get("reasons", [])

            if not intersecting_entities and not intersecting_edges:
                continue

            # Grounded explanation string
            reason_text = (
                f"Investigation {target_case_id} affected by network changes from {clean_origin or 'Network Update'}: "
                + " | ".join(reasons)
            )

            # 4. Deterministic Idempotency Key
            route_id = make_route_id(source_snapshot_id, target_snapshot_id, target_case_id)

            # Check if route already exists
            if route_id in self.repo.affected_routes:
                logger.info("Returning existing route %s for target case %s", route_id, target_case_id)
                routes.append(AffectedInvestigationRoute(**self.repo.affected_routes[route_id]))
                continue

            # 5. Payload Integrity Hash
            payload_dict = {
                "route_id": route_id,
                "origin_case_id": clean_origin or "SYSTEM",
                "origin_district": origin_district,
                "target_case_id": target_case_id,
                "target_district": target_district,
                "source_snapshot_id": source_snapshot_id,
                "target_snapshot_id": target_snapshot_id,
                "intersecting_entity_ids": intersecting_entities,
                "intersecting_edge_ids": intersecting_edges,
            }
            route_hash = compute_route_integrity_hash(payload_dict)

            now_iso = _utcnow().isoformat()
            route_data = {
                "route_id": route_id,
                "origin_case_id": clean_origin or "SYSTEM",
                "origin_district": origin_district,
                "target_case_id": target_case_id,
                "target_district": target_district,
                "trigger_event_id": trigger_event_id,
                "source_snapshot_id": source_snapshot_id,
                "target_snapshot_id": target_snapshot_id,
                "diff_summary": diff_summary or {},
                "intersecting_entity_ids": intersecting_entities,
                "intersecting_edge_ids": intersecting_edges,
                "routing_reason": reason_text,
                "evidence_refs": sorted(evidence_refs or []),
                "route_hash": route_hash,
                "status": PulseDeliveryStatus.DISPATCHED.value,
                "dispatched_at": now_iso,
                "acknowledged_at": None,
                "acknowledged_by": None,
                "acknowledgment_note": None,
            }

            self.repo.affected_routes[route_id] = route_data
            route_obj = AffectedInvestigationRoute(**route_data)
            routes.append(route_obj)

            # 6. Backward Compatibility: Sync into repo.intelligence_pulses
            self._sync_into_pulse_packet(route_obj, actor_id)

            # 7. Operational Domain Event (A3): Reusing SIGNAL_GENERATED with source_type="AFFECTED_INVESTIGATION_ROUTE"
            if self.intel_svc:
                try:
                    self.intel_svc.record_event(
                        CreateIntelligenceEventRequest(
                            event_type=IntelligenceEventType.SIGNAL_GENERATED,
                            case_id=target_case_id,
                            source_id=route_id,
                            source_type="AFFECTED_INVESTIGATION_ROUTE",
                            title=f"Intelligence Routed to Investigation {target_case_id}",
                            description=reason_text,
                            payload={
                                "route_id": route_id,
                                "origin_case_id": clean_origin or "SYSTEM",
                                "target_case_id": target_case_id,
                                "target_district": target_district,
                                "source_snapshot_id": source_snapshot_id,
                                "target_snapshot_id": target_snapshot_id,
                                "intersecting_entity_ids": intersecting_entities,
                                "intersecting_edge_ids": intersecting_edges,
                                "route_hash": route_hash,
                            },
                            actor_id=actor_id,
                        ),
                        principal=principal,
                    )
                except Exception as exc:
                    logger.warning("Failed emitting SIGNAL_GENERATED event for route %s: %s", route_id, exc)

            # 8. Statutory Audit Log
            self.audit.record(
                event_type=AuditEventType.INTELLIGENCE_PULSE_DISPATCHED,
                actor_id=actor_id,
                case_id=target_case_id,
                entity_id=route_id,
                entity_type="AffectedInvestigationRoute",
                details={
                    "action": "ROUTE_AFFECTED_INVESTIGATION",
                    "origin_case": clean_origin or "SYSTEM",
                    "target_case": target_case_id,
                    "target_district": target_district,
                    "intersecting_entities": intersecting_entities,
                    "intersecting_edges": intersecting_edges,
                    "route_hash": route_hash,
                },
            )

        logger.info(
            "Affected investigation routing completed for diff (%s -> %s): routed %d investigations",
            source_snapshot_id,
            target_snapshot_id,
            len(routes),
        )
        return routes

    def _sync_into_pulse_packet(self, route: AffectedInvestigationRoute, actor_id: str) -> None:
        """Mirror route into repo.intelligence_pulses for UI and backward compatibility."""
        if getattr(self.repo, "intelligence_pulses", None) is None:
            self.repo.intelligence_pulses = {}

        pkt_id = f"PULSE-ROUTE-{route.route_id.replace('route-', '')}"
        headline = f"Cross-Case Intelligence: Network changes intersecting {route.target_case_id}"
        self.repo.intelligence_pulses[pkt_id] = {
            "packet_id": pkt_id,
            "origin_case_id": route.origin_case_id,
            "origin_district": route.origin_district,
            "origin_officer_id": actor_id,
            "target_case_id": route.target_case_id,
            "target_district": route.target_district,
            "target_role": UserRole.INVESTIGATOR.value,
            "headline": headline,
            "summary": route.routing_reason,
            "shared_entities": route.intersecting_entity_ids,
            "evidence_refs": route.evidence_refs,
            "packet_hash": route.route_hash,
            "security_classification": PulseSecurityClassification.RESTRICTED.value,
            "dispatched_at": route.dispatched_at,
            "delivery_status": route.status.value,
            "acknowledged_at": route.acknowledged_at,
            "acknowledged_by": route.acknowledged_by,
            "acknowledgment_note": route.acknowledgment_note,
        }

    def list_inbox_routes(
        self,
        principal: Principal,
        case_id: str | None = None,
        district: str | None = None,
        status: PulseDeliveryStatus | None = None,
    ) -> list[AffectedInvestigationRoute]:
        """
        List incoming affected investigation routes authorized for the authenticated principal.
        """
        officer = principal.get_officer_identity()
        role = principal.role

        from backend.app.auth.policy import DEMO_OFFICER_CASE_ASSIGNMENTS, DEMO_SHO_DISTRICTS
        assigned_cases = DEMO_OFFICER_CASE_ASSIGNMENTS.get(officer.officer_id, set())
        allowed_districts = DEMO_SHO_DISTRICTS.get(officer.officer_id, set())

        results: list[AffectedInvestigationRoute] = []
        for r_dict in self.repo.affected_routes.values():
            origin_c = r_dict.get("origin_case_id")
            target_c = r_dict.get("target_case_id")
            t_dist = r_dict.get("target_district")
            r_status = r_dict.get("status")

            # Filters
            if case_id and case_id not in (origin_c, target_c):
                continue
            if district and district != t_dist:
                continue
            if status and r_status != status.value:
                continue

            # Role Authorization Gating
            if role in (UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.SP):
                results.append(AffectedInvestigationRoute(**r_dict))
            elif role == UserRole.SHO:
                if t_dist in allowed_districts or origin_c in assigned_cases or target_c in assigned_cases:
                    results.append(AffectedInvestigationRoute(**r_dict))
            else:
                # INVESTIGATOR / IO
                if target_c in assigned_cases or origin_c in assigned_cases:
                    results.append(AffectedInvestigationRoute(**r_dict))

        # Sort descending by dispatched_at
        results.sort(key=lambda r: r.dispatched_at, reverse=True)
        return results

    def get_route(self, route_id: str, principal: Principal | None = None) -> AffectedInvestigationRoute | None:
        """Retrieve single route by ID, enforcing case access checks."""
        r_dict = self.repo.affected_routes.get(route_id)
        if not r_dict:
            return None

        if principal and self.auth_policy:
            target_c = r_dict.get("target_case_id")
            origin_c = r_dict.get("origin_case_id")
            can_t, _ = self.auth_policy.can_access_case(principal, target_c)
            can_o, _ = self.auth_policy.can_access_case(principal, origin_c)
            if not can_t and not can_o:
                raise PermissionError(f"Access denied to route {route_id} for case {target_c}")

        return AffectedInvestigationRoute(**r_dict)

    def acknowledge_route(
        self,
        route_id: str,
        request: AcknowledgeRouteRequest,
        principal: Principal,
    ) -> AffectedInvestigationRoute:
        """
        Record authoritative officer acknowledgment, action, or rejection on an affected investigation route.
        """
        if route_id not in self.repo.affected_routes:
            raise KeyError(f"Affected investigation route '{route_id}' not found.")

        r_dict = self.repo.affected_routes[route_id]
        target_case = r_dict.get("target_case_id")

        # Authorization: Caller must have access to the target investigation
        if self.auth_policy:
            can_access, reason = self.auth_policy.can_access_case(principal, target_case)
            if not can_access:
                raise PermissionError(
                    f"Officer {principal.user_id} is not authorized to acknowledge route for target case '{target_case}': {reason}"
                )

        officer = principal.get_officer_identity()
        dec_upper = request.decision.upper()

        if dec_upper == "ACTION":
            new_status = PulseDeliveryStatus.ACTIONED
        elif dec_upper in ("REJECT", "DISMISS"):
            new_status = PulseDeliveryStatus.REJECTED
        else:
            new_status = PulseDeliveryStatus.ACKNOWLEDGED

        now_iso = _utcnow().isoformat()
        r_dict["status"] = new_status.value
        r_dict["acknowledged_at"] = now_iso
        r_dict["acknowledged_by"] = f"{officer.name} ({officer.rank}, {officer.badge_number})"
        r_dict["acknowledgment_note"] = request.note

        # Sync to intelligence_pulses if present
        pkt_id = f"PULSE-ROUTE-{route_id.replace('route-', '')}"
        if pkt_id in self.repo.intelligence_pulses:
            pkt = self.repo.intelligence_pulses[pkt_id]
            pkt["delivery_status"] = new_status.value
            pkt["acknowledged_at"] = now_iso
            pkt["acknowledged_by"] = r_dict["acknowledged_by"]
            pkt["acknowledgment_note"] = request.note

        # Audit Event
        self.audit.record(
            event_type=AuditEventType.INTELLIGENCE_PULSE_ACKNOWLEDGED,
            actor_id=principal.user_id,
            case_id=target_case,
            entity_id=route_id,
            entity_type="AffectedInvestigationRoute",
            details={
                "action": "ACKNOWLEDGE_AFFECTED_ROUTE",
                "decision": new_status.value,
                "acknowledged_by": r_dict["acknowledged_by"],
                "note": request.note,
            },
        )

        return AffectedInvestigationRoute(**r_dict)
