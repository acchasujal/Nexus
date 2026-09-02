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

from backend.app.core.crypto.audit_integrity import (
    AuditIntegrityVerificationResult,
    compute_audit_event_hash,
    verify_audit_event_integrity,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str) and val:
        try:
            cleaned = val.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return _utcnow()


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
    LEAD_ACTIONED = "lead_actioned"
    ENTITY_VIEWED = "entity_viewed"
    EVIDENCE_VIEWED = "evidence_viewed"
    EVIDENCE_HASH_COMPUTED = "evidence_hash_computed"
    EVIDENCE_VERIFIED = "evidence_verified"
    EVIDENCE_INTEGRITY_VERIFIED = "evidence_integrity_verified"
    EVIDENCE_INTEGRITY_MISMATCH = "evidence_integrity_mismatch"
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

    # Export (BE-05)
    EXPORT_INITIATED = "export_initiated"
    EXPORT_COMPLETED = "export_completed"


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
            # Determine previous_hash safely from the existing repository audit log
            previous_hash: str | None = None
            events = getattr(self._repository, "audit_events", None)
            if isinstance(events, list) and len(events) > 0:
                last_event = events[-1]
                previous_hash = last_event.get("integrity_hash")

            now_iso = _utcnow().isoformat()
            payload = {
                "id": str(uuid.uuid4()),
                "event_type": event_type.value if hasattr(event_type, "value") else str(event_type),
                "actor_id": actor_id,
                "case_id": case_id,
                "entity_id": entity_id,
                "entity_type": entity_type,
                "request_id": request_id,
                "occurred_at": now_iso,
                "timestamp": now_iso,
                "previous_hash": previous_hash,
                "details": details or {},
            }

            # Cryptographic canonical serialization & SHA-256 computation
            integrity_hash = compute_audit_event_hash(payload)
            payload["integrity_hash"] = integrity_hash

            if hasattr(self._repository, "audit_events") and isinstance(self._repository.audit_events, list):
                self._repository.audit_events.append(payload)

            # Persist to PostgreSQL if repository supports it
            if hasattr(self._repository, "_get_connection"):
                try:
                    from psycopg.types.json import Jsonb
                    with self._repository._get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO audit_events (id, user_id, user_role, action, entity_type, entity_id, details, timestamp)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                                """,
                                (
                                    payload["id"],
                                    payload["actor_id"],
                                    (payload["details"] or {}).get("role", "INVESTIGATOR"),
                                    payload["event_type"],
                                    payload["entity_type"],
                                    payload["entity_id"] or payload["case_id"],
                                    Jsonb(payload["details"] or {}),
                                    _parse_datetime(payload["timestamp"]),
                                ),
                            )
                        conn.commit()
                except Exception as db_exc:
                    logger.debug("Optional direct PostgreSQL audit write: %s", db_exc)

            logger.info("AUDIT: event=%s actor=%s entity=%s", event_type, actor_id, entity_id or case_id)
        except Exception as exc:
            logger.error("AuditService.record failed: %s", exc)

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Retrieve a single audit event by ID from the repository."""
        events = getattr(self._repository, "audit_events", [])
        for e in events:
            if e.get("id") == event_id:
                return e
        return None

    def verify_event_integrity(self, event_id: str) -> AuditIntegrityVerificationResult | None:
        """Verify the cryptographic integrity of a specific audit event.

        Returns AuditIntegrityVerificationResult or None if event does not exist.
        """
        event = self.get_event(event_id)
        if event is None:
            return None
        return verify_audit_event_integrity(event)

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
