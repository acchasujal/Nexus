"""backend/app/services/verification_task_service.py

Authoritative domain service for Persistent Verification Tasks (A7).
Upgrades read-only Network Pulse verification recommendations into an
investigator-usable, persistent task workflow with canonical IDs,
deterministic state machine transitions, evidence linkage, RBAC,
IntelligenceEvent synchronization, and Section 63 BSA audit logging.

Explicit Scope Invariant (A7):
  - Zero graph mutations
  - Zero snapshot diff recomputations
  - Zero automated cross-case routing cascades (deferred to A8/A14)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.db.ingestion.identifiers import make_verification_task_id
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.intelligence_event_service import IntelligenceEventService
from shared.contracts.api import (
    AssignVerificationTaskRequest,
    AttachEvidenceRequest,
    CreateIntelligenceEventRequest,
    CreateVerificationTaskRequest,
    DecideVerificationTaskRequest,
    IntelligenceEventType,
    TaskTransitionHistoryItem,
    TransitionVerificationTaskRequest,
    VerificationTask,
    VerificationTaskDecision,
    VerificationTaskStatus,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Strict deterministic lifecycle transition map
VALID_TRANSITIONS: dict[VerificationTaskStatus, set[VerificationTaskStatus]] = {
    VerificationTaskStatus.CREATED: {
        VerificationTaskStatus.ASSIGNED,
        VerificationTaskStatus.DISMISSED,
    },
    VerificationTaskStatus.ASSIGNED: {
        VerificationTaskStatus.REQUESTED,
        VerificationTaskStatus.UNDER_REVIEW,
        VerificationTaskStatus.DISMISSED,
    },
    VerificationTaskStatus.REQUESTED: {
        VerificationTaskStatus.RECEIVED,
        VerificationTaskStatus.DISMISSED,
    },
    VerificationTaskStatus.RECEIVED: {
        VerificationTaskStatus.UNDER_REVIEW,
        VerificationTaskStatus.DISMISSED,
    },
    VerificationTaskStatus.UNDER_REVIEW: {
        VerificationTaskStatus.VERIFIED,
        VerificationTaskStatus.DISMISSED,
    },
    VerificationTaskStatus.VERIFIED: set(),
    VerificationTaskStatus.DISMISSED: set(),
}

TERMINAL_STATUSES: set[VerificationTaskStatus] = {
    VerificationTaskStatus.VERIFIED,
    VerificationTaskStatus.DISMISSED,
}


class VerificationTaskService:
    """
    Application-layer service managing persistent investigator verification tasks.
    Owns task validation, canonical ID generation, state machine progression,
    authoritative evidence linkage, and audit/intelligence event emission.
    """

    def __init__(
        self,
        repository: Any,
        audit_service: AuditService,
        evidence_service: Any | None = None,
        intelligence_event_service: IntelligenceEventService | None = None,
        auth_policy: EvidenceAuthorizationPolicy | None = None,
        proactive_intelligence_service: Any | None = None,
    ) -> None:
        self._repo = repository
        self._audit = audit_service
        self._evidence_svc = evidence_service
        self._intel_svc = intelligence_event_service
        self._auth = auth_policy
        self._proactive_svc = proactive_intelligence_service

    # ── Task Creation ─────────────────────────────────────────────────────────

    def create_task(
        self,
        request: CreateVerificationTaskRequest,
        principal: Principal | None = None,
    ) -> VerificationTask:
        """
        Validate, deterministically identify, and persist a VerificationTask.
        Idempotent: Re-creating an existing task returns the stored record.
        """
        if not request.case_id or not request.case_id.strip():
            raise ValueError("VerificationTask requires a valid, non-empty case_id.")
        if not request.target_claim or not request.target_claim.strip():
            raise ValueError("VerificationTask requires a valid, non-empty target_claim.")
        if not request.requested_evidence_type or not request.requested_evidence_type.strip():
            raise ValueError("VerificationTask requires a valid, non-empty requested_evidence_type.")
        if not request.verification_action or not request.verification_action.strip():
            raise ValueError("VerificationTask requires a valid, non-empty verification_action.")

        clean_case_id = request.case_id.strip()

        # Enforce case RBAC
        if principal and self._auth:
            allowed, reason = self._auth.can_access_case(principal, clean_case_id)
            if not allowed:
                raise PermissionError(f"Access denied: cannot create verification task for case '{clean_case_id}': {reason}")

        # Generate deterministic canonical task ID (vtask-XXXX)
        discriminator = str(request.originating_pulse_id or "").strip()
        task_id = make_verification_task_id(
            case_id=clean_case_id,
            target_claim=request.target_claim.strip(),
            requested_evidence_type=request.requested_evidence_type.strip(),
            discriminator=discriminator,
        )

        # Idempotency check: if already exists, return existing task
        existing = self._repo.get_verification_task(task_id)
        if existing:
            return VerificationTask(**existing)

        now = _utcnow()
        actor_id = principal.user_id if (principal and not principal.is_anonymous) else "SYSTEM"

        initial_status = (
            VerificationTaskStatus.ASSIGNED
            if request.assigned_officer_id
            else VerificationTaskStatus.CREATED
        )

        history = [
            TaskTransitionHistoryItem(
                from_status=VerificationTaskStatus.CREATED,
                to_status=initial_status,
                actor_id=actor_id,
                timestamp=now,
                rationale="Initial task creation",
            )
        ]

        task = VerificationTask(
            task_id=task_id,
            case_id=clean_case_id,
            created_at=now,
            updated_at=now,
            originating_event_id=request.originating_event_id,
            originating_pulse_id=request.originating_pulse_id,
            target_claim=request.target_claim.strip(),
            reason=request.reason.strip() if request.reason else "Evidence gap identified during intelligence review.",
            requested_evidence_type=request.requested_evidence_type.strip(),
            verification_action=request.verification_action.strip(),
            expected_outcome=request.expected_outcome,
            evidence_gap=request.evidence_gap,
            assigned_officer_id=request.assigned_officer_id,
            assigned_role=request.assigned_role,
            assigned_at=now if request.assigned_officer_id else None,
            status=initial_status,
            history=history,
        )

        # Persist task
        self._repo.save_verification_task(task.model_dump(mode="json"))

        # Emit A3 IntelligenceEvent
        if self._intel_svc:
            try:
                self._intel_svc.record_event(
                    CreateIntelligenceEventRequest(
                        event_type=IntelligenceEventType.VERIFICATION_TASK_CREATED,
                        case_id=clean_case_id,
                        source_id=task_id,
                        source_type="VERIFICATION_TASK",
                        title=f"Verification Task Created: {task.target_claim}",
                        description=task.verification_action,
                        payload={
                            "task_id": task_id,
                            "status": task.status.value,
                            "target_claim": task.target_claim,
                            "requested_evidence_type": task.requested_evidence_type,
                            "assigned_officer_id": task.assigned_officer_id,
                        },
                    ),
                    principal=principal,
                )
            except Exception as e:
                logger.warning("Failed to emit IntelligenceEvent for task creation %s: %s", task_id, e)

        # Emit Section 63 BSA AuditEvent
        self._audit.record(
            event_type=AuditEventType.VERIFICATION_TASK_CREATED,
            actor_id=actor_id,
            case_id=clean_case_id,
            entity_type="VerificationTask",
            entity_id=task_id,
            details={
                "task_id": task_id,
                "case_id": clean_case_id,
                "status": task.status.value,
                "target_claim": task.target_claim,
                "requested_evidence_type": task.requested_evidence_type,
                "assigned_officer_id": task.assigned_officer_id,
            },
        )

        logger.info("Created VerificationTask %s on case %s (status=%s)", task_id, clean_case_id, task.status.value)
        return task

    def create_tasks_from_pulse(
        self,
        pulse_id: str,
        case_id: str | None = None,
        principal: Principal | None = None,
    ) -> list[VerificationTask]:
        """
        Idempotently instantiate persistent VerificationTasks from an active pulse's
        read-only verification recommendations.
        """
        clean_pulse_id = str(pulse_id).strip()
        if not clean_pulse_id:
            raise ValueError("pulse_id must not be empty.")

        pulses: list[Any] = []
        if self._proactive_svc and hasattr(self._proactive_svc, "list_active_pulses"):
            pulses = self._proactive_svc.list_active_pulses(case_id=case_id)

        target_pulse = next((p for p in pulses if p.pulse_id == clean_pulse_id), None)
        if not target_pulse:
            raise KeyError(f"Network pulse '{clean_pulse_id}' not found.")

        target_case_id = case_id
        if not target_case_id and target_pulse.affected_cases:
            target_case_id = target_pulse.affected_cases[0]
        if not target_case_id:
            target_case_id = "case-general"

        created_tasks: list[VerificationTask] = []
        for action_item in getattr(target_pulse, "verification_plan", []):
            task = self.create_task(
                CreateVerificationTaskRequest(
                    case_id=target_case_id,
                    target_claim=action_item.target_claim,
                    reason=f"Derived from proactive intelligence signal {clean_pulse_id}",
                    requested_evidence_type=action_item.missing_evidence_type,
                    verification_action=action_item.recommended_action,
                    originating_pulse_id=clean_pulse_id,
                    assigned_role=getattr(action_item, "responsible_role", None),
                ),
                principal=principal,
            )
            created_tasks.append(task)

        return created_tasks

    # ── Task Retrieval & Listing ──────────────────────────────────────────────

    def get_task(
        self,
        task_id: str,
        principal: Principal | None = None,
    ) -> VerificationTask | None:
        """Retrieve a verification task by canonical ID with case RBAC check."""
        clean_id = str(task_id).strip()
        raw = self._repo.get_verification_task(clean_id)
        if not raw:
            return None

        task = VerificationTask(**raw)

        if principal and self._auth:
            allowed, reason = self._auth.can_access_case(principal, task.case_id)
            if not allowed:
                raise PermissionError(f"Access denied to task '{clean_id}' on case '{task.case_id}': {reason}")

        return task

    def list_tasks(
        self,
        case_id: str | None = None,
        assignee: str | None = None,
        status: VerificationTaskStatus | str | None = None,
        limit: int = 50,
        offset: int = 0,
        principal: Principal | None = None,
    ) -> tuple[list[VerificationTask], int]:
        """List and filter verification tasks with case RBAC authorization."""
        if case_id and principal and self._auth:
            allowed, reason = self._auth.can_access_case(principal, case_id)
            if not allowed:
                raise PermissionError(f"Access denied to verification tasks for case '{case_id}': {reason}")

        st_str = status.value if hasattr(status, "value") else (str(status) if status else None)

        raw_tasks, total_count = self._repo.list_verification_tasks(
            case_id=case_id,
            assignee=assignee,
            status=st_str,
            limit=limit,
            offset=offset,
        )

        tasks: list[VerificationTask] = []
        for r in raw_tasks:
            t = VerificationTask(**r)
            if principal and self._auth and not case_id:
                allowed, _ = self._auth.can_access_case(principal, t.case_id)
                if not allowed:
                    continue
            tasks.append(t)

        return tasks, total_count

    # ── Lifecycle Transitions & Assignment ────────────────────────────────────

    def assign_task(
        self,
        task_id: str,
        request: AssignVerificationTaskRequest,
        principal: Principal | None = None,
    ) -> VerificationTask:
        """Assign or reassign a verification task to an investigator or team."""
        clean_id = str(task_id).strip()
        task = self.get_task(clean_id, principal=principal)
        if not task:
            raise KeyError(f"VerificationTask '{clean_id}' not found.")

        # Reject mutation on terminal states
        if task.status in TERMINAL_STATUSES:
            raise ValueError(f"Cannot reassign task '{clean_id}' in terminal state '{task.status.value}'.")

        now = _utcnow()
        actor_id = principal.user_id if (principal and not principal.is_anonymous) else "SYSTEM"
        prev_status = task.status
        next_status = (
            VerificationTaskStatus.ASSIGNED
            if task.status == VerificationTaskStatus.CREATED
            else task.status
        )

        task.assigned_officer_id = request.assigned_officer_id.strip()
        task.assigned_role = request.assigned_role
        task.assigned_at = now
        task.status = next_status
        task.updated_at = now

        task.history.append(
            TaskTransitionHistoryItem(
                from_status=prev_status,
                to_status=next_status,
                actor_id=actor_id,
                timestamp=now,
                rationale=request.rationale or f"Assigned to {request.assigned_officer_id}",
            )
        )

        self._repo.update_verification_task(task.model_dump(mode="json"))

        self._audit.record(
            event_type=AuditEventType.VERIFICATION_TASK_ASSIGNED,
            actor_id=actor_id,
            case_id=task.case_id,
            entity_type="VerificationTask",
            entity_id=clean_id,
            details={
                "task_id": clean_id,
                "assigned_officer_id": task.assigned_officer_id,
                "previous_status": prev_status.value,
                "new_status": next_status.value,
                "rationale": request.rationale,
            },
        )

        logger.info("Assigned VerificationTask %s to officer %s", clean_id, task.assigned_officer_id)
        return task

    def transition_task(
        self,
        task_id: str,
        request: TransitionVerificationTaskRequest,
        principal: Principal | None = None,
    ) -> VerificationTask:
        """
        Advance a task through the validated lifecycle state machine.
        Rejects invalid transitions and mutations on terminal states.
        """
        clean_id = str(task_id).strip()
        task = self.get_task(clean_id, principal=principal)
        if not task:
            raise KeyError(f"VerificationTask '{clean_id}' not found.")

        # Reject mutation on terminal states
        if task.status in TERMINAL_STATUSES:
            raise ValueError(f"Cannot transition task '{clean_id}' in terminal state '{task.status.value}'.")

        allowed_next = VALID_TRANSITIONS.get(task.status, set())
        if request.target_status not in allowed_next:
            raise ValueError(
                f"Invalid lifecycle transition from '{task.status.value}' to '{request.target_status.value}'. "
                f"Allowed transitions: {[s.value for s in allowed_next]}"
            )

        now = _utcnow()
        actor_id = principal.user_id if (principal and not principal.is_anonymous) else "SYSTEM"
        prev_status = task.status

        task.status = request.target_status
        task.updated_at = now

        task.history.append(
            TaskTransitionHistoryItem(
                from_status=prev_status,
                to_status=request.target_status,
                actor_id=actor_id,
                timestamp=now,
                rationale=request.rationale,
            )
        )

        self._repo.update_verification_task(task.model_dump(mode="json"))

        self._audit.record(
            event_type=AuditEventType.VERIFICATION_TASK_TRANSITIONED,
            actor_id=actor_id,
            case_id=task.case_id,
            entity_type="VerificationTask",
            entity_id=clean_id,
            details={
                "task_id": clean_id,
                "previous_status": prev_status.value,
                "new_status": request.target_status.value,
                "rationale": request.rationale,
            },
        )

        # If transitioning to terminal state, emit IntelligenceEvent
        if request.target_status in TERMINAL_STATUSES and self._intel_svc:
            try:
                self._intel_svc.record_event(
                    CreateIntelligenceEventRequest(
                        event_type=IntelligenceEventType.VERIFICATION_COMPLETED,
                        case_id=task.case_id,
                        source_id=clean_id,
                        source_type="VERIFICATION_TASK",
                        title=f"Verification Task {request.target_status.value}: {task.target_claim}",
                        description=request.rationale or f"Task transitioned to {request.target_status.value}",
                        payload={
                            "task_id": clean_id,
                            "status": request.target_status.value,
                            "target_claim": task.target_claim,
                            "actor_id": actor_id,
                        },
                    ),
                    principal=principal,
                )
            except Exception as e:
                logger.warning("Failed to emit IntelligenceEvent for task transition %s: %s", clean_id, e)

        logger.info("Transitioned VerificationTask %s from %s to %s", clean_id, prev_status.value, task.status.value)
        return task

    # ── Evidence Attachment ───────────────────────────────────────────────────

    def attach_evidence(
        self,
        task_id: str,
        request: AttachEvidenceRequest,
        principal: Principal | None = None,
    ) -> VerificationTask:
        """
        Link an authoritative evidence record to the verification task.
        Validates evidence existence, preserves provenance, and rejects duplicate links.
        """
        clean_id = str(task_id).strip()
        task = self.get_task(clean_id, principal=principal)
        if not task:
            raise KeyError(f"VerificationTask '{clean_id}' not found.")

        # Reject mutation on terminal states
        if task.status in TERMINAL_STATUSES:
            raise ValueError(f"Cannot attach evidence to task '{clean_id}' in terminal state '{task.status.value}'.")

        clean_evidence_id = str(request.evidence_id).strip()
        if not clean_evidence_id:
            raise ValueError("evidence_id must not be empty.")

        # Verify existence of evidence record
        evidence_found = False
        actor_id = principal.user_id if (principal and not principal.is_anonymous) else "SYSTEM"

        if self._evidence_svc and hasattr(self._evidence_svc, "get_evidence_by_id"):
            ev_item = self._evidence_svc.get_evidence_by_id(clean_evidence_id, actor_id=actor_id, suppress_audit=True)
            if ev_item:
                evidence_found = True

        if not evidence_found:
            source_records = getattr(self._repo, "source_records", {})
            if clean_evidence_id in source_records:
                evidence_found = True

        if not evidence_found:
            documents = getattr(self._repo, "documents", {})
            if clean_evidence_id in documents:
                evidence_found = True

        if not evidence_found:
            # Check edge IDs in graph store
            store = self._repo.to_graph_store()
            for edges in store.edge_index.values():
                for e in edges:
                    if getattr(e, "edge_id", None) == clean_evidence_id or f"EV-{getattr(e, 'edge_id', '')}" == clean_evidence_id:
                        evidence_found = True
                        break
                if evidence_found:
                    break

        if not evidence_found:
            raise ValueError(f"Authoritative evidence '{clean_evidence_id}' does not exist in repository.")

        rel = (request.relationship_type or "SUPPORTING").strip().upper()
        now = _utcnow()

        if rel in ("SUPPORTING", "SUPPORTS"):
            if clean_evidence_id not in task.supporting_evidence_ids:
                task.supporting_evidence_ids.append(clean_evidence_id)
        elif rel in ("CONFLICTING", "CONFLICTS"):
            if clean_evidence_id not in task.conflicting_evidence_ids:
                task.conflicting_evidence_ids.append(clean_evidence_id)
        elif rel in ("REQUESTED", "MISSING"):
            if clean_evidence_id not in task.requested_evidence_ids:
                task.requested_evidence_ids.append(clean_evidence_id)
        elif rel in ("RECEIVED", "VERIFIED"):
            if clean_evidence_id not in task.received_evidence_ids:
                task.received_evidence_ids.append(clean_evidence_id)
        else:
            if clean_evidence_id not in task.supporting_evidence_ids:
                task.supporting_evidence_ids.append(clean_evidence_id)

        task.updated_at = now
        task.history.append(
            TaskTransitionHistoryItem(
                from_status=task.status,
                to_status=task.status,
                actor_id=actor_id,
                timestamp=now,
                rationale=f"Attached evidence {clean_evidence_id} ({rel}): {request.notes or 'No notes provided'}",
            )
        )

        self._repo.update_verification_task(task.model_dump(mode="json"))

        self._audit.record(
            event_type=AuditEventType.VERIFICATION_TASK_EVIDENCE_ATTACHED,
            actor_id=actor_id,
            case_id=task.case_id,
            entity_type="VerificationTask",
            entity_id=clean_id,
            details={
                "task_id": clean_id,
                "evidence_id": clean_evidence_id,
                "relationship_type": rel,
                "notes": request.notes,
            },
        )

        logger.info("Attached evidence %s (%s) to VerificationTask %s", clean_evidence_id, rel, clean_id)
        return task

    # ── Final Decision ────────────────────────────────────────────────────────

    def decide_task(
        self,
        task_id: str,
        request: DecideVerificationTaskRequest,
        principal: Principal | None = None,
    ) -> VerificationTask:
        """
        Record a terminal verification decision (VERIFIED or DISMISSED) with rationale.
        Reuses existing NEXUS case authorization policy (can_access_case).
        Emits IntelligenceEvent and Section 63 BSA AuditEvent.
        Explicit Invariant: Zero graph mutations or closed-loop propagation in A7.
        """
        clean_id = str(task_id).strip()
        task = self.get_task(clean_id, principal=principal)
        if not task:
            raise KeyError(f"VerificationTask '{clean_id}' not found.")

        # Reject mutation on terminal states
        if task.status in TERMINAL_STATUSES:
            raise ValueError(f"Cannot record decision on task '{clean_id}' in terminal state '{task.status.value}'.")

        # Validate decision value
        decision_val = request.decision
        target_status = (
            VerificationTaskStatus.VERIFIED
            if decision_val == VerificationTaskDecision.VERIFIED
            else VerificationTaskStatus.DISMISSED
        )

        # Enforce state machine rules: VERIFIED requires task to be UNDER_REVIEW
        if target_status == VerificationTaskStatus.VERIFIED and task.status != VerificationTaskStatus.UNDER_REVIEW:
            raise ValueError(
                f"Task '{clean_id}' cannot be marked VERIFIED from state '{task.status.value}'. "
                f"It must be in '{VerificationTaskStatus.UNDER_REVIEW.value}' state before verification."
            )

        now = _utcnow()
        actor_id = principal.user_id if (principal and not principal.is_anonymous) else "SYSTEM"
        prev_status = task.status

        task.status = target_status
        task.decision = decision_val
        task.decision_rationale = request.rationale.strip()
        task.deciding_actor = actor_id
        task.decided_at = now
        task.updated_at = now

        task.history.append(
            TaskTransitionHistoryItem(
                from_status=prev_status,
                to_status=target_status,
                actor_id=actor_id,
                timestamp=now,
                rationale=f"Decision {decision_val.value}: {request.rationale.strip()}",
            )
        )

        self._repo.update_verification_task(task.model_dump(mode="json"))

        # Emit A3 IntelligenceEvent
        if self._intel_svc:
            try:
                self._intel_svc.record_event(
                    CreateIntelligenceEventRequest(
                        event_type=IntelligenceEventType.VERIFICATION_COMPLETED,
                        case_id=task.case_id,
                        source_id=clean_id,
                        source_type="VERIFICATION_TASK",
                        title=f"Verification Decision: {decision_val.value} on {task.target_claim}",
                        description=request.rationale.strip(),
                        payload={
                            "task_id": clean_id,
                            "decision": decision_val.value,
                            "decision_rationale": request.rationale.strip(),
                            "deciding_actor": actor_id,
                            "supporting_evidence_ids": task.supporting_evidence_ids,
                            "conflicting_evidence_ids": task.conflicting_evidence_ids,
                        },
                    ),
                    principal=principal,
                )
            except Exception as e:
                logger.warning("Failed to emit IntelligenceEvent for verification decision %s: %s", clean_id, e)

        # Emit Section 63 BSA AuditEvent
        self._audit.record(
            event_type=AuditEventType.VERIFICATION_TASK_DECIDED,
            actor_id=actor_id,
            case_id=task.case_id,
            entity_type="VerificationTask",
            entity_id=clean_id,
            details={
                "task_id": clean_id,
                "decision": decision_val.value,
                "rationale": request.rationale.strip(),
                "previous_status": prev_status.value,
                "new_status": target_status.value,
                "supporting_evidence_ids": task.supporting_evidence_ids,
                "conflicting_evidence_ids": task.conflicting_evidence_ids,
            },
        )

        logger.info("Decided VerificationTask %s as %s by actor %s", clean_id, decision_val.value, actor_id)
        return task
