"""backend/app/services/intelligence_event_service.py

Authoritative domain service for the NEXUS Operational Intelligence Event plane (A3).
Manages strongly-typed, immutable IntelligenceEvents with canonical ID generation,
deterministic SHA-256 payload integrity hashing, evidence provenance tracking,
RBAC enforcement, and audit trail synchronization.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.app.auth.policy import EvidenceAuthorizationPolicy
from backend.app.auth.principal import Principal
from backend.app.db.ingestion.identifiers import make_intelligence_event_id
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    CreateIntelligenceEventRequest,
    IntelligenceEvent,
    IntelligenceEventType,
    UserRole,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def compute_payload_integrity_hash(payload: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 digest over normalized payload dictionary."""
    normalized_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized_json.encode("utf-8")).hexdigest()


class IntelligenceEventService:
    """Application-layer service orchestrating IntelligenceEvent creation, validation, and retrieval."""

    def __init__(
        self,
        repository: Any,
        audit_service: AuditService,
        auth_policy: EvidenceAuthorizationPolicy | None = None,
    ) -> None:
        self._repo = repository
        self._audit = audit_service
        self._auth = auth_policy

    def record_event(
        self,
        request: CreateIntelligenceEventRequest,
        principal: Principal | None = None,
    ) -> IntelligenceEvent:
        """Validate, deterministically identify, hash, and persist an operational intelligence event."""
        # 1. Required field validation
        if not request.case_id or not request.case_id.strip():
            raise ValueError("IntelligenceEvent requires a valid, non-empty case_id.")

        clean_case_id = request.case_id.strip()

        # 2. RBAC check on creation if principal is present
        if principal and self._auth:
            allowed, reason = self._auth.can_access_case(principal, clean_case_id)
            if not allowed:
                raise PermissionError(f"Access denied: cannot record intelligence event for case '{clean_case_id}': {reason}")

        # 3. Determine Actor and Role
        now = _utcnow()
        now_iso = now.isoformat()

        actor_id = "SYSTEM"
        actor_role = request.actor_role

        if principal and not principal.is_anonymous:
            actor_id = principal.user_id
            actor_role = principal.role
        elif request.actor_id:
            actor_id = request.actor_id.strip()

        # 4. Generate deterministic canonical event ID (intevt-XXXX)
        discriminator = uuid.uuid4().hex[:6]
        event_id = make_intelligence_event_id(
            event_type=request.event_type.value,
            case_id=clean_case_id,
            timestamp_str=now_iso,
            discriminator=discriminator,
        )

        # 5. Compute tamper-evident payload hash
        integrity_hash = compute_payload_integrity_hash(request.payload)

        # 6. Construct authoritative IntelligenceEvent domain model
        event = IntelligenceEvent(
            event_id=event_id,
            event_type=request.event_type,
            event_version="1.0",
            event_timestamp=now,
            case_id=clean_case_id,
            fir_id=request.fir_id,
            source_id=request.source_id,
            evidence_refs=list(request.evidence_refs),
            snapshot_id=request.snapshot_id,
            related_entity_ids=list(request.related_entity_ids),
            related_edge_ids=list(request.related_edge_ids),
            source_type=request.source_type or "SYSTEM",
            actor_id=actor_id,
            actor_role=actor_role,
            observed_at=request.observed_at,
            ingested_at=now,
            processed_at=now,
            correlation_id=request.correlation_id,
            causation_id=request.causation_id,
            title=request.title.strip() if request.title else f"{request.event_type.value} on {clean_case_id}",
            description=request.description.strip(),
            payload=dict(request.payload),
            integrity_hash=integrity_hash,
        )

        # 7. Persist event immutably to repository
        event_dict = event.model_dump(mode="json")
        self._repo.save_intelligence_event(event_dict)

        # 8. Record audit log entry (distinguishing domain event from audit entry)
        self._audit.record(
            event_type=AuditEventType.INTELLIGENCE_EVENT_RECORDED,
            actor_id=actor_id,
            case_id=clean_case_id,
            entity_type="IntelligenceEvent",
            entity_id=event_id,
            details={
                "event_type": request.event_type.value,
                "title": event.title,
                "integrity_hash": integrity_hash,
                "evidence_refs": event.evidence_refs,
                "related_entity_ids": event.related_entity_ids,
            },
        )

        logger.info(
            "Recorded IntelligenceEvent %s (%s) for case %s by actor %s",
            event_id,
            request.event_type.value,
            clean_case_id,
            actor_id,
        )
        return event

    def get_event(
        self,
        event_id: str,
        principal: Principal | None = None,
    ) -> IntelligenceEvent | None:
        """Retrieve an intelligence event by canonical ID with case authorization check."""
        clean_id = str(event_id).strip()
        raw = self._repo.get_intelligence_event(clean_id)
        if not raw:
            return None

        event = IntelligenceEvent(**raw)

        # Enforce case access RBAC
        if principal and self._auth:
            allowed, reason = self._auth.can_access_case(principal, event.case_id)
            if not allowed:
                raise PermissionError(f"Access denied to event '{clean_id}' for case '{event.case_id}': {reason}")

        return event

    def list_events(
        self,
        case_id: str | None = None,
        event_type: IntelligenceEventType | str | None = None,
        entity_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        principal: Principal | None = None,
    ) -> tuple[list[IntelligenceEvent], int]:
        """List and filter intelligence events with pagination and RBAC authorization."""
        # If querying specific case, check permission upfront
        if case_id and principal and self._auth:
            allowed, reason = self._auth.can_access_case(principal, case_id)
            if not allowed:
                raise PermissionError(f"Access denied to intelligence events for case '{case_id}': {reason}")

        et_str = event_type.value if hasattr(event_type, "value") else (str(event_type) if event_type else None)

        raw_events, total_count = self._repo.list_intelligence_events(
            case_id=case_id,
            event_type=et_str,
            entity_id=entity_id,
            limit=limit,
            offset=offset,
        )

        events: list[IntelligenceEvent] = []
        for r in raw_events:
            ev = IntelligenceEvent(**r)
            if principal and self._auth and not case_id:
                # Filter out events belonging to cases caller has no clearance for
                allowed, _ = self._auth.can_access_case(principal, ev.case_id)
                if not allowed:
                    continue
            events.append(ev)

        return events, total_count
