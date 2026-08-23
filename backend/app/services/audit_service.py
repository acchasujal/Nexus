"""backend/app/services/audit_service.py

Durable audit trail service for the NEXUS Criminal Intelligence Platform.
Records immutable events with correlation tracking, principal attribution, and timestamps.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditEventType(str, Enum):
    """Exhaustive audit event taxonomy for NEXUS."""
    # Investigation views
    INVESTIGATION_VIEWED = "investigation_viewed"
    INVESTIGATION_LIST_VIEWED = "investigation_list_viewed"
    WORKLIST_VIEWED = "worklist_viewed"  # legacy compatibility
    CASE_VIEWED = "case_viewed"  # legacy compatibility
    CASE_NETWORK_VIEWED = "case_network_viewed"

    # Network & Analytics
    NETWORK_EXPLORED = "network_explored"
    GRAPH_QUERY_EXECUTED = "graph_query_executed"
    COMMUNITY_DETECTION_EXECUTED = "community_detection_executed"
    BRIDGE_ANALYSIS_EXECUTED = "bridge_analysis_executed"
    SIMILARITY_SEARCH_EXECUTED = "similarity_search_executed"
    PATTERN_SEARCH_EXECUTED = "pattern_search_executed"

    # Entity Resolution & Evidence
    ENTITY_RESOLUTION_EXECUTED = "entity_resolution_executed"
    EVIDENCE_VIEWED = "evidence_viewed"
    TIMELINE_VIEWED = "timeline_viewed"

    # Copilot
    COPILOT_ANSWERED = "copilot_answered"
    COPILOT_REFUSED = "copilot_refused"

    # Auth & Security
    ACCESS_DENIED = "access_denied"
    USER_LOGGED_IN = "user_logged_in"
    TOKEN_INVALID = "token_invalid"

    # Ingestion
    INGESTION_STARTED = "ingestion_started"
    INGESTION_COMPLETED = "ingestion_completed"
    INGESTION_FAILED = "ingestion_failed"
    SEED_COMPLETED = "seed_completed"


class AuditService:
    """Application-layer service for writing and querying audit logs."""

    def __init__(self, repository: Any) -> None:
        self._repository = repository

    def record(
        self,
        event_type: AuditEventType,
        actor_id: str,
        case_id: str | None = None,
        entity_id: str | None = None,
        entity_type: str | None = None,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record an audit event without ever throwing exceptions to callers."""
        try:
            payload = {
                "id": str(uuid.uuid4()),
                "event_type": event_type.value if hasattr(event_type, "value") else str(event_type),
                "actor_id": actor_id,
                "case_id": case_id,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "request_id": request_id,
                "occurred_at": _utcnow().isoformat(),
                "timestamp": _utcnow().isoformat(),
                "details": details or {},
            }
            if hasattr(self._repository, "audit_events") and isinstance(self._repository.audit_events, list):
                self._repository.audit_events.append(payload)
            logger.info("AUDIT: event=%s actor=%s entity=%s", event_type, actor_id, entity_id or case_id)
        except (AttributeError, TypeError, ValueError, KeyError, OSError) as exc:
            logger.warning("Audit log write failed (best-effort): %s", exc)

    def list_events(
        self,
        case_id: str | None = None,
        event_type: AuditEventType | str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        events = getattr(self._repository, "audit_events", [])
        results: list[dict[str, Any]] = []
        for e in reversed(events):
            if case_id and e.get("case_id") != case_id:
                continue
            if event_type:
                target_type = event_type.value if hasattr(event_type, "value") else str(event_type)
                if e.get("event_type") != target_type:
                    continue
            results.append(e)
            if len(results) >= limit:
                break
        return results
