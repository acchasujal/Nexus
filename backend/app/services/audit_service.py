"""backend/app/services/audit_service.py

Durable audit trail service for CaseClock.

Phase 3 implementation of the audit layer:
  - Replaces the list-of-dicts in InMemoryBackendRepository with a proper service
  - Best-effort writes: audit failures never propagate to the caller
  - Correlates events by request_id for cross-service tracing
  - Phase 4 will wire this to AuditRepository (Catalyst Data Store)

## Event taxonomy (from BACKEND_IMPLEMENTATION_PLAN.md §9 Phase 3)

All event_type values must come from the AuditEventType enum.
No free-form strings: this ensures audit reports are queryable.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Exhaustive audit event taxonomy.

    Every event recorded through the audit service must use one of these values.
    Adding new event types: add to this enum first, then the callsite.
    """
    # Worklist / case views
    WORKLIST_VIEWED = "worklist_viewed"
    CASE_VIEWED = "case_viewed"
    CASE_NETWORK_VIEWED = "case_network_viewed"

    # Dependency lifecycle
    DEPENDENCY_UPDATED = "dependency_updated"

    # Escalation lifecycle
    ESCALATIONS_VIEWED = "escalations_viewed"
    MANUAL_ESCALATION_CREATED = "manual_escalation_created"

    # Copilot
    COPILOT_ANSWERED = "copilot_answered"
    COPILOT_REFUSED = "copilot_refused"

    # Auth
    ACCESS_DENIED = "access_denied"
    TOKEN_INVALID = "token_invalid"

    # Admin & Cron
    SEED_STARTED = "seed_started"
    SEED_COMPLETED = "seed_completed"
    SEED_FAILED = "seed_failed"
    DEADLINE_SWEEP_COMPLETED = "deadline_sweep_completed"

    # Document Intelligence
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_OCR_COMPLETED = "document_ocr_completed"
    DOCUMENT_FACTS_CONFIRMED = "document_facts_confirmed"

    # Graph read model
    GRAPH_QUERY_EXECUTED = "graph_query_executed"


class AuditService:
    """Application-layer service for writing audit events.

    In Phase 3 (before Catalyst persistence):
      - Stores events in the in-memory list on InMemoryBackendRepository.
      - All writes are best-effort; exceptions are swallowed and logged.

    In Phase 4 (after AuditRepository wiring):
      - Delegates to AuditRepository.append().
      - Same interface for callers.

    Usage:
        audit = AuditService(repository=repo)
        audit.record(
            AuditEventType.CASE_VIEWED,
            actor_id=principal.user_id,
            case_id=case_id,
            request_id=request_id,
        )
    """

    def __init__(self, repository: Any) -> None:
        """
        Args:
            repository: InMemoryBackendRepository (Phase 1/3) or any object
                        with an `audit_events: list[dict]` attribute.
        """
        self._repository = repository

    def record(
        self,
        event_type: AuditEventType,
        *,
        actor_id: str | None = None,
        case_id: str | None = None,
        request_id: str | None = None,
        **metadata: Any,
    ) -> None:
        """Append one audit event.  Never raises; logs failures.

        Args:
            event_type: Must be an AuditEventType enum member.
            actor_id:   Catalyst ZUID or dev placeholder; None for system events.
            case_id:    Case scoping for queries; None for cross-case events.
            request_id: Correlation ID from RequestIDMiddleware.
            **metadata: Additional key-value pairs stored as event metadata.
        """
        try:
            event: dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "event_type": event_type.value,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "actor_id": actor_id,
                "case_id": case_id,
                "request_id": request_id,
                "metadata": metadata if metadata else None,
            }
            # Phase 1/3: write to in-memory list
            if hasattr(self._repository, "audit_events"):
                self._repository.audit_events.append(event)
            else:
                logger.warning(
                    "AuditService: repository has no audit_events attribute; event not stored "
                    "[event_type=%s, request_id=%s]",
                    event_type.value,
                    request_id,
                )
        except Exception:
            logger.exception(
                "AuditService: failed to record event [event_type=%s, request_id=%s]",
                event_type.value,
                request_id,
            )

    def list_events(
        self,
        limit: int = 100,
        case_id: str | None = None,
        actor_id: str | None = None,
        event_type: AuditEventType | None = None,
    ) -> list[dict[str, Any]]:
        """Read audit events from the in-memory store.

        Phase 4 delegates to AuditRepository.list_events().
        """
        if not hasattr(self._repository, "audit_events"):
            return []

        events: list[dict[str, Any]] = list(self._repository.audit_events)

        if case_id:
            events = [e for e in events if e.get("case_id") == case_id]
        if actor_id:
            events = [e for e in events if e.get("actor_id") == actor_id]
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type.value]

        return events[-limit:]
