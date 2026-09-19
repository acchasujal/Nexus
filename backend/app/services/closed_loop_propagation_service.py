"""backend/app/services/closed_loop_propagation_service.py

Authoritative Closed-Loop Propagation Engine for NEXUS (A8).
Closes the loop deterministically:
  Investigator Decision / Verified Evidence
  -> Graph State Mutation
  -> New Network Snapshot
  -> NetworkDiff (Pure O(N+E))
  -> A3 Operational IntelligenceEvents
  -> Affected Network Intelligence / Dynamic Pulse Refresh

Strict Invariants:
  1. Exact A3 Enum Compatibility: Uses pre-existing IntelligenceEventType members.
  2. Case-Scope Transparency: GraphStore is global; case_scope is investigative
     metadata for attribution/routing, never claimed as graph partitioning.
  3. Zero Fake Intelligence: Under no circumstances is pulse-0082 treated as dynamic.
  4. Decision ID Idempotency: Uses existing decision_id as stable idempotency key.
  5. Retryable & Recoverable: Failed propagation can be retried without re-mutating graph.
  6. Human-Gated Verification: Verification tasks are NOT automatically created from pulses.
  7. Decoupled A14: No cross-jurisdiction packet routing in A8.
  8. Zero Predictive Guilt: Adheres strictly to ReviewPriority and EpistemicState.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.core.graph.algorithms.snapshot_diff import diff_graph_snapshots
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.intelligence_event_service import IntelligenceEventService
from backend.app.services.proactive_intelligence_service import ProactiveIntelligenceService
from shared.contracts.api import (
    CreateIntelligenceEventRequest,
    IntelligenceEventType,
    NetworkPulseItem,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PropagationResult(BaseModel):
    """Authoritative result contract for A8 closed-loop propagation."""
    decision_id: str
    case_id: str
    mutation_type: str
    target_id: str
    snapshot_id: str | None = None
    previous_snapshot_id: str | None = None
    diff_summary: dict[str, int] = Field(default_factory=dict)
    emitted_event_ids: list[str] = Field(default_factory=list)
    generated_pulse_ids: list[str] = Field(default_factory=list)
    routed_case_ids: list[str] = Field(default_factory=list)
    route_ids: list[str] = Field(default_factory=list)
    status: str = "COMPLETED"  # "COMPLETED" | "FAILED" | "SKIPPED_NO_DIFF"
    error_message: str | None = None
    executed_at: datetime = Field(default_factory=_utcnow)


class ClosedLoopPropagationService:
    """Orchestrates deterministic closed-loop propagation post-graph-mutation."""

    def __init__(
        self,
        repository: Any,
        proactive_service: ProactiveIntelligenceService,
        intel_event_service: IntelligenceEventService | None = None,
        audit_service: AuditService | None = None,
        auth_policy: EvidenceAuthorizationPolicy | None = None,
        routing_service: Any | None = None,
    ) -> None:
        self._repo = repository
        self._proactive_svc = proactive_service
        self._intel_svc = intel_event_service
        self._audit = audit_service
        self._auth = auth_policy
        self._routing_svc = routing_service
        self._propagations: dict[str, PropagationResult] = {}

    def get_propagation(self, decision_id: str) -> PropagationResult | None:
        """Retrieve propagation result by decision_id."""
        clean_id = str(decision_id).strip()
        return self._propagations.get(clean_id)

    def propagate_decision(
        self,
        decision_id: str,
        case_id: str,
        mutation_type: str,
        target_id: str,
        principal: Principal | None = None,
        evidence_refs: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> PropagationResult:
        """
        Execute deterministic closed-loop propagation for an authoritative investigator decision.

        Idempotent on decision_id: repeated invocations with the same decision_id
        return the cached completed result without re-snapshotting or re-diffing.
        """
        clean_dec_id = str(decision_id).strip()
        clean_case_id = str(case_id).strip()
        clean_target_id = str(target_id).strip()

        # 1. Idempotency Check
        existing = self._propagations.get(clean_dec_id)
        if existing and existing.status in ("COMPLETED", "SKIPPED_NO_DIFF"):
            logger.info("Returning cached propagation result for decision %s", clean_dec_id)
            return existing

        # 2. RBAC Access Verification
        if principal and self._auth:
            can_access, reason = self._auth.can_access_case(principal, clean_case_id)
            if not can_access:
                raise PermissionError(f"Access denied: cannot propagate changes for case '{clean_case_id}': {reason}")

        actor_id = principal.user_id if (principal and not principal.is_anonymous) else "SYSTEM"
        now = _utcnow()
        now_iso = now.isoformat()
        emitted_event_ids: list[str] = []
        generated_pulse_ids: list[str] = []

        try:
            # 3. Emit Investigator Decision & Observed IntelligenceEvents
            if self._intel_svc:
                # 3a. INVESTIGATOR_DECISION
                try:
                    dec_event = self._intel_svc.record_event(
                        CreateIntelligenceEventRequest(
                            event_type=IntelligenceEventType.INVESTIGATOR_DECISION,
                            case_id=clean_case_id,
                            source_id=clean_dec_id,
                            source_type="INVESTIGATOR_DECISION",
                            title=f"Investigator Decision Committed: {mutation_type}",
                            description=f"Authoritative decision {clean_dec_id} resulted in {mutation_type} for target {clean_target_id}",
                            payload={
                                "decision_id": clean_dec_id,
                                "mutation_type": mutation_type,
                                "target_id": clean_target_id,
                                "actor_id": actor_id,
                                "details": details or {},
                            },
                            actor_id=actor_id,
                        ),
                        principal=principal,
                    )
                    emitted_event_ids.append(dec_event.event_id)
                except Exception as exc:
                    logger.warning("Failed emitting INVESTIGATOR_DECISION event for %s: %s", clean_dec_id, exc)

                # 3b. ENTITY_OBSERVED or RELATIONSHIP_OBSERVED
                obs_event_type = (
                    IntelligenceEventType.RELATIONSHIP_OBSERVED
                    if mutation_type == "RELATIONSHIP_PROMOTED"
                    else IntelligenceEventType.ENTITY_OBSERVED
                )
                try:
                    obs_event = self._intel_svc.record_event(
                        CreateIntelligenceEventRequest(
                            event_type=obs_event_type,
                            case_id=clean_case_id,
                            source_id=clean_target_id,
                            source_type="GRAPH_MUTATION",
                            title=f"Authoritative Graph Mutation: {mutation_type}",
                            description=f"{obs_event_type.value} established in authoritative graph for case {clean_case_id}",
                            payload={
                                "decision_id": clean_dec_id,
                                "target_id": clean_target_id,
                                "mutation_type": mutation_type,
                                "evidence_refs": evidence_refs or [],
                            },
                            actor_id=actor_id,
                        ),
                        principal=principal,
                    )
                    emitted_event_ids.append(obs_event.event_id)
                except Exception as exc:
                    logger.warning("Failed emitting observation event for %s: %s", clean_target_id, exc)

            # 4. Snapshot Boundary
            # Note on case_scope: the underlying repository store is global; case_scope
            # is investigative context metadata for routing/attribution.
            prev_snapshot_id = self._proactive_svc.get_latest_snapshot_id()
            before_store = self._proactive_svc.get_snapshot_store(prev_snapshot_id) or self._repo.to_graph_store()

            # Canonical deterministic snapshot identifier
            clean_token = clean_dec_id.replace("dec-", "")[:8]
            new_snapshot_id = f"snap-mut-{clean_token}"
            snap_summary = self._proactive_svc.create_snapshot(new_snapshot_id, case_scope=clean_case_id)
            after_store = self._proactive_svc.get_snapshot_store(new_snapshot_id) or self._repo.to_graph_store()

            # 5. Emit SNAPSHOT_CREATED IntelligenceEvent
            if self._intel_svc:
                try:
                    snap_event = self._intel_svc.record_event(
                        CreateIntelligenceEventRequest(
                            event_type=IntelligenceEventType.SNAPSHOT_CREATED,
                            case_id=clean_case_id,
                            source_id=new_snapshot_id,
                            source_type="GRAPH_SNAPSHOT",
                            title=f"Network Snapshot Captured: {new_snapshot_id}",
                            description=f"Captured point-in-time graph state post-mutation ({snap_summary.node_count} nodes, {snap_summary.edge_count} edges). Case scope metadata: {clean_case_id}",
                            payload={
                                "snapshot_id": new_snapshot_id,
                                "previous_snapshot_id": prev_snapshot_id,
                                "case_scope_metadata": clean_case_id,
                                "node_count": snap_summary.node_count,
                                "edge_count": snap_summary.edge_count,
                                "decision_id": clean_dec_id,
                            },
                            actor_id=actor_id,
                        ),
                        principal=principal,
                    )
                    emitted_event_ids.append(snap_event.event_id)
                except Exception as exc:
                    logger.warning("Failed emitting SNAPSHOT_CREATED event for %s: %s", new_snapshot_id, exc)

            # 6. Execute Pure O(N+E) Deterministic Diff
            raw_diff = diff_graph_snapshots(before_store, after_store)
            diff_summary = {
                "added_nodes": len(raw_diff.added_nodes),
                "removed_nodes": len(raw_diff.removed_nodes),
                "modified_nodes": len(raw_diff.modified_nodes),
                "added_relationships": len(raw_diff.added_relationships),
                "removed_relationships": len(raw_diff.removed_relationships),
                "modified_relationships": len(raw_diff.modified_relationships),
            }

            has_changes = any(count > 0 for count in diff_summary.values())

            # 7. Emit NETWORK_CHANGE_DETECTED if diff reveals changes
            if has_changes and self._intel_svc:
                try:
                    diff_event = self._intel_svc.record_event(
                        CreateIntelligenceEventRequest(
                            event_type=IntelligenceEventType.NETWORK_CHANGE_DETECTED,
                            case_id=clean_case_id,
                            source_id=f"diff-{prev_snapshot_id}-{new_snapshot_id}",
                            source_type="NETWORK_DIFF",
                            title=f"Network Change Detected ({prev_snapshot_id} -> {new_snapshot_id})",
                            description=f"Structural changes detected: +{diff_summary['added_nodes']} nodes, +{diff_summary['added_relationships']} relationships.",
                            payload={
                                "before_snapshot_id": prev_snapshot_id,
                                "after_snapshot_id": new_snapshot_id,
                                "added_nodes": raw_diff.added_nodes,
                                "removed_nodes": raw_diff.removed_nodes,
                                "added_relationships": raw_diff.added_relationships,
                                "removed_relationships": raw_diff.removed_relationships,
                                "decision_id": clean_dec_id,
                            },
                            actor_id=actor_id,
                        ),
                        principal=principal,
                    )
                    emitted_event_ids.append(diff_event.event_id)
                except Exception as exc:
                    logger.warning("Failed emitting NETWORK_CHANGE_DETECTED event: %s", exc)

            # 8. Dynamic Pulse Generation (Filter on actual diff — NEVER pulse-0082)
            pulses: list[NetworkPulseItem] = []
            if has_changes:
                pulses = self._proactive_svc._filter_network_pulses(raw_diff, before_store, after_store)

            for pulse in pulses:
                # Ensure pulse is registered in dynamic pulse registry
                self._proactive_svc.register_dynamic_pulse(pulse)
                generated_pulse_ids.append(pulse.pulse_id)

                # Emit SIGNAL_GENERATED event
                if self._intel_svc:
                    try:
                        sig_event = self._intel_svc.record_event(
                            CreateIntelligenceEventRequest(
                                event_type=IntelligenceEventType.SIGNAL_GENERATED,
                                case_id=clean_case_id,
                                source_id=pulse.pulse_id,
                                source_type="NETWORK_PULSE",
                                title=pulse.signal_headline,
                                description=f"Intelligence signal generated with review priority {pulse.review_priority.value}",
                                payload={
                                    "pulse_id": pulse.pulse_id,
                                    "signal_headline": pulse.signal_headline,
                                    "review_priority": pulse.review_priority.value,
                                    "affected_entities": pulse.affected_entities,
                                    "affected_cases": pulse.affected_cases,
                                    "decision_id": clean_dec_id,
                                },
                                actor_id=actor_id,
                            ),
                            principal=principal,
                        )
                        emitted_event_ids.append(sig_event.event_id)
                    except Exception as exc:
                        logger.warning("Failed emitting SIGNAL_GENERATED event for %s: %s", pulse.pulse_id, exc)

            # 8b. Affected Investigation Routing (A14)
            routed_case_ids: list[str] = []
            route_ids: list[str] = []
            if has_changes and self._routing_svc:
                try:
                    routes = self._routing_svc.route_network_diff(
                        raw_diff=raw_diff,
                        origin_case_id=clean_case_id,
                        target_snapshot_id=new_snapshot_id,
                        source_snapshot_id=prev_snapshot_id,
                        trigger_event_id=clean_dec_id,
                        principal=principal,
                        evidence_refs=evidence_refs,
                    )
                    routed_case_ids = [r.target_case_id for r in routes]
                    route_ids = [r.route_id for r in routes]
                except Exception as exc:
                    logger.warning("Affected investigation routing failed for %s: %s", clean_dec_id, exc)

            # 9. Audit Trail
            if self._audit:
                self._audit.record(
                    event_type=AuditEventType.NETWORK_EXPLORED,
                    actor_id=actor_id,
                    case_id=clean_case_id,
                    entity_type="ClosedLoopPropagation",
                    entity_id=clean_dec_id,
                    details={
                        "decision_id": clean_dec_id,
                        "snapshot_id": new_snapshot_id,
                        "previous_snapshot_id": prev_snapshot_id,
                        "pulse_count": len(pulses),
                        "diff_summary": diff_summary,
                        "routed_case_count": len(routed_case_ids),
                    },
                )

            result_status = "COMPLETED" if (pulses or has_changes) else "SKIPPED_NO_DIFF"
            res = PropagationResult(
                decision_id=clean_dec_id,
                case_id=clean_case_id,
                mutation_type=mutation_type,
                target_id=clean_target_id,
                snapshot_id=new_snapshot_id,
                previous_snapshot_id=prev_snapshot_id,
                diff_summary=diff_summary,
                emitted_event_ids=emitted_event_ids,
                generated_pulse_ids=generated_pulse_ids,
                routed_case_ids=routed_case_ids,
                route_ids=route_ids,
                status=result_status,
                error_message=None,
                executed_at=now,
            )
            self._propagations[clean_dec_id] = res
            logger.info(
                "Closed-loop propagation completed for decision %s (snapshot=%s, pulses=%d, routed_cases=%d)",
                clean_dec_id,
                new_snapshot_id,
                len(pulses),
                len(routed_case_ids),
            )
            return res

        except Exception as err:
            logger.error("Closed-loop propagation failed for decision %s: %s", clean_dec_id, err, exc_info=True)
            failed_res = PropagationResult(
                decision_id=clean_dec_id,
                case_id=clean_case_id,
                mutation_type=mutation_type,
                target_id=clean_target_id,
                snapshot_id=None,
                previous_snapshot_id=None,
                diff_summary={},
                emitted_event_ids=emitted_event_ids,
                generated_pulse_ids=[],
                status="FAILED",
                error_message=str(err),
                executed_at=now,
            )
            self._propagations[clean_dec_id] = failed_res
            raise

    def retry_propagation(
        self,
        decision_id: str,
        principal: Principal | None = None,
    ) -> PropagationResult:
        """
        Recover and retry closed-loop propagation for a prior decision without re-mutating graph.
        """
        clean_dec_id = str(decision_id).strip()
        existing = self._propagations.get(clean_dec_id)
        if existing and existing.status == "COMPLETED":
            return existing

        # Locate decision details from repository store
        dec_data: dict[str, Any] | None = None
        if hasattr(self._repo, "get_candidate_decisions"):
            # Candidate decisions may be stored across candidates; search repository
            candidates = getattr(self._repo, "candidate_decisions", {})
            if isinstance(candidates, dict) and clean_dec_id in candidates:
                dec_data = candidates[clean_dec_id]
            else:
                # Iterate all candidates
                for dec_list in getattr(self._repo, "candidate_decisions_by_candidate", {}).values():
                    for d in dec_list:
                        if d.get("decision_id") == clean_dec_id:
                            dec_data = d
                            break
                    if dec_data:
                        break

        if not dec_data and existing:
            # Fallback to failed record context
            return self.propagate_decision(
                decision_id=existing.decision_id,
                case_id=existing.case_id,
                mutation_type=existing.mutation_type,
                target_id=existing.target_id,
                principal=principal,
            )

        if not dec_data:
            raise KeyError(f"Decision '{clean_dec_id}' not found in repository for retry.")

        case_id = dec_data.get("case_id") or "GLOBAL"
        action = dec_data.get("action", "MUTATION")
        target_id = dec_data.get("resulting_graph_id") or dec_data.get("target_id", "UNKNOWN")

        return self.propagate_decision(
            decision_id=clean_dec_id,
            case_id=case_id,
            mutation_type=action,
            target_id=target_id,
            principal=principal,
            details=dec_data,
        )
