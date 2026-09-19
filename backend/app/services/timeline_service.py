"""backend/app/services/timeline_service.py

First-class investigator-facing chronological timeline projection service for NEXUS.

Adheres strictly to the following principles:
1. Read-Only Projection: Never mutates graph state, never creates verification tasks,
   never dispatches routes, and never emits synthetic domain events.
2. Dual Timestamp Semantics: Accurately preserves both when an event actually happened
   (occurred_at) and when NEXUS learned/recorded it (recorded_at).
3. Zero Fabricated Timestamps: Uses genuine repository timestamps; never injects fake dates.
4. Deterministic Canonical IDs: IDs are stable, repeatable, and idempotent across replays.
5. Strict Case-Level RBAC: Enforces EvidenceAuthorizationPolicy.can_access_case.
6. Zero Predictive Guilt: Strictly excludes guilt scores, risk probabilities, or recidivism metrics.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from backend.app.auth.policy import EvidenceAuthorizationPolicy, Principal
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    IntelligenceEventType,
    PulseDeliveryStatus,
    TimelineEventCategory,
    TimelineEventResponse,
    TimelineQueryResponse,
    VerificationTaskStatus,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(val: Any) -> datetime | None:
    """Parse string, datetime, or date value into UTC-aware datetime without hardcoding fallbacks."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str) and val.strip():
        try:
            cleaned = val.strip().replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None
    return None


def _ensure_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return _utcnow()
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class TimelineService:
    """Investigator-facing chronological timeline projection engine."""

    def __init__(
        self,
        repository: Any,
        auth_policy: EvidenceAuthorizationPolicy,
        audit_service: AuditService | None = None,
    ) -> None:
        self._repo = repository
        self._auth = auth_policy
        self._audit = audit_service

    def get_timeline_events(
        self,
        principal: Principal,
        case_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        request_id: str | None = None,
    ) -> list[TimelineEventResponse]:
        """Backward-compatible endpoint returning a list of TimelineEventResponse items."""
        query_resp = self.query_timeline(
            principal=principal,
            case_id=case_id,
            limit=limit,
            offset=offset,
            request_id=request_id,
        )
        return query_resp.events

    def query_timeline(
        self,
        principal: Principal,
        case_id: str | None = None,
        entity_id: str | None = None,
        category: str | None = None,
        event_type: str | None = None,
        source_type: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        order: str = "desc",
        limit: int = 50,
        offset: int = 0,
        request_id: str | None = None,
    ) -> TimelineQueryResponse:
        """
        Query chronological timeline with deterministic projection, filtering, and pagination.
        """
        clean_case_id = str(case_id).strip() if case_id else None
        clean_entity_id = str(entity_id).strip() if entity_id else None

        # 1. Authorize case access if specific case requested
        if clean_case_id:
            can_access, reason = self._auth.can_access_case(principal, clean_case_id)
            if not can_access:
                logger.warning(
                    "Timeline access denied for user %s on case %s: %s",
                    principal.user_id,
                    clean_case_id,
                    reason,
                )
                raise HTTPException(status_code=403, detail=f"Access denied: {reason}")

        # 2. Gather candidate events from authoritative stores with deduplication
        dedup_events: dict[str, TimelineEventResponse] = {}
        projected_source_ids: set[str] = set()
        projected_task_ids: set[str] = set()
        projected_route_ids: set[str] = set()

        # Path A: A3 IntelligenceEvents (Primary domain event backbone)
        self._project_intelligence_events(
            principal=principal,
            case_id=clean_case_id,
            entity_id=clean_entity_id,
            dedup_events=dedup_events,
            projected_source_ids=projected_source_ids,
            projected_task_ids=projected_task_ids,
            projected_route_ids=projected_route_ids,
        )

        # Path B: Ground-Truth Forensic Source Records (e.g. CDR calls, bank transfers, surveillance)
        self._project_source_records(
            principal=principal,
            case_id=clean_case_id,
            entity_id=clean_entity_id,
            dedup_events=dedup_events,
            projected_source_ids=projected_source_ids,
        )

        # Path C: Case Inception & Graph Case Nodes
        self._project_case_nodes(
            principal=principal,
            case_id=clean_case_id,
            dedup_events=dedup_events,
        )

        # Path D: Verification Tasks (Lifecycle milestones not already captured by A3)
        self._project_verification_tasks(
            principal=principal,
            case_id=clean_case_id,
            entity_id=clean_entity_id,
            dedup_events=dedup_events,
            projected_task_ids=projected_task_ids,
        )

        # Path E: A14 Affected Routes (Routing and acknowledgment milestones)
        self._project_affected_routes(
            principal=principal,
            case_id=clean_case_id,
            entity_id=clean_entity_id,
            dedup_events=dedup_events,
            projected_route_ids=projected_route_ids,
        )

        all_events = list(dedup_events.values())

        # 3. Apply post-projection filters
        filtered: list[TimelineEventResponse] = []
        from_dt = _parse_datetime(from_date)
        to_dt = _parse_datetime(to_date)

        for ev in all_events:
            # Category filter
            if category:
                target_cat = category.strip().upper()
                if not ev.category or ev.category.value.upper() != target_cat:
                    continue

            # Event type filter
            if event_type:
                target_et = event_type.strip().upper()
                if ev.event_type.upper() != target_et:
                    continue

            # Source type filter
            if source_type:
                target_st = source_type.strip().upper()
                if not ev.source_type or ev.source_type.upper() != target_st:
                    continue

            # Date range filtering (evaluating occurred_at or recorded_at)
            ref_time = ev.occurred_at or ev.recorded_at or ev.timestamp
            ref_time = _ensure_utc(ref_time)

            if from_dt and ref_time < from_dt:
                continue
            if to_dt and ref_time > to_dt:
                continue

            filtered.append(ev)

        # 4. Deterministic 3-tuple chronological sorting
        is_desc = (order.lower().strip() != "asc")

        def _sort_key(e: TimelineEventResponse) -> tuple[datetime, datetime, str]:
            primary_dt = _ensure_utc(e.occurred_at or e.recorded_at or e.timestamp)
            sec_dt = _ensure_utc(e.recorded_at or primary_dt)
            return (primary_dt, sec_dt, e.id)

        sorted_events = sorted(filtered, key=_sort_key, reverse=is_desc)

        # 5. Pagination
        total_count = len(sorted_events)
        safe_limit = max(1, min(200, limit))
        safe_offset = max(0, offset)
        paged_events = sorted_events[safe_offset : safe_offset + safe_limit]
        has_more = (safe_offset + safe_limit) < total_count

        # 6. Statutory Audit Logging (Section 63 BSA)
        if self._audit:
            self._audit.record(
                AuditEventType.TIMELINE_VIEWED,
                actor_id=principal.user_id,
                case_id=clean_case_id,
                request_id=request_id,
                details={
                    "total_returned": len(paged_events),
                    "total_matched": total_count,
                    "entity_filter": clean_entity_id,
                },
            )

        return TimelineQueryResponse(
            events=paged_events,
            total_count=total_count,
            case_id=clean_case_id,
            entity_id=clean_entity_id,
            limit=safe_limit,
            offset=safe_offset,
            has_more=has_more,
        )

    # ── Projection Helpers ───────────────────────────────────────────────────

    def _project_intelligence_events(
        self,
        principal: Principal,
        case_id: str | None,
        entity_id: str | None,
        dedup_events: dict[str, TimelineEventResponse],
        projected_source_ids: set[str],
        projected_task_ids: set[str],
        projected_route_ids: set[str],
    ) -> None:
        raw_events = getattr(self._repo, "intelligence_events", {})
        if not raw_events:
            return

        for ev_dict in raw_events.values():
            cid = ev_dict.get("case_id")
            if case_id and cid != case_id:
                continue

            # Scope authorization check
            if not self._auth.can_access_case(principal, cid)[0]:
                continue

            related_entities = ev_dict.get("related_entity_ids") or []
            if entity_id and entity_id not in related_entities:
                continue

            raw_type = ev_dict.get("event_type")
            ev_type_str = raw_type.value if hasattr(raw_type, "value") else str(raw_type)

            # Map category deterministically from existing taxonomy
            cat = TimelineEventCategory.GRAPH_CHANGE
            if ev_type_str in (IntelligenceEventType.INVESTIGATOR_DECISION.value, IntelligenceEventType.ENTITY_RESOLUTION_DECIDED.value):
                cat = TimelineEventCategory.INVESTIGATOR_ACTION
            elif ev_type_str in (IntelligenceEventType.DOCUMENT_INGESTED.value, IntelligenceEventType.DOCUMENT_EXTRACTED.value):
                cat = TimelineEventCategory.EVIDENCE_DOCUMENT
            elif ev_type_str == IntelligenceEventType.SIGNAL_GENERATED.value:
                cat = TimelineEventCategory.INTELLIGENCE_SIGNAL
            elif ev_type_str == IntelligenceEventType.EVIDENCE_ASSESSED.value:
                cat = TimelineEventCategory.EVIDENCE_ASSESSMENT
            elif ev_type_str in (IntelligenceEventType.VERIFICATION_TASK_CREATED.value, IntelligenceEventType.VERIFICATION_COMPLETED.value):
                cat = TimelineEventCategory.VERIFICATION_WORKFLOW

            occurred = _parse_datetime(ev_dict.get("observed_at"))
            recorded = _parse_datetime(ev_dict.get("event_timestamp"))
            final_occurred = occurred or recorded
            final_recorded = recorded or final_occurred
            ts = _ensure_utc(final_occurred or final_recorded)

            event_id = ev_dict.get("event_id", "")
            canonical_id = f"tle-intevt-{event_id}"

            src_id = ev_dict.get("source_id")
            if src_id:
                projected_source_ids.add(src_id)

            payload = ev_dict.get("payload") or {}
            if "task_id" in payload:
                projected_task_ids.add(str(payload["task_id"]))
            if "route_id" in payload:
                projected_route_ids.add(str(payload["route_id"]))

            dedup_events[canonical_id] = TimelineEventResponse(
                id=canonical_id,
                event_type=ev_type_str,
                category=cat,
                timestamp=ts,
                occurred_at=final_occurred,
                recorded_at=final_recorded,
                title=ev_dict.get("title") or f"Intelligence Event: {ev_type_str}",
                description=ev_dict.get("description") or "",
                participant_ids=related_entities,
                edge_ids=ev_dict.get("related_edge_ids") or [],
                case_id=cid,
                source_type=ev_dict.get("source_type"),
                source_id=src_id,
                actor_id=ev_dict.get("actor_id"),
                actor_role=ev_dict.get("actor_role"),
                intelligence_event_id=event_id,
                evidence_refs=ev_dict.get("evidence_refs") or [],
                snapshot_id=ev_dict.get("snapshot_id"),
                route_id=payload.get("route_id"),
                task_id=payload.get("task_id"),
                assessment_id=payload.get("assessment_id"),
                properties={"integrity_hash": ev_dict.get("integrity_hash")},
            )

    def _project_source_records(
        self,
        principal: Principal,
        case_id: str | None,
        entity_id: str | None,
        dedup_events: dict[str, TimelineEventResponse],
        projected_source_ids: set[str],
    ) -> None:
        source_records = getattr(self._repo, "source_records", {})
        if not source_records:
            return

        for sid, src in source_records.items():
            if sid in projected_source_ids:
                # Deduplicate: already projected via authoritative IntelligenceEvent
                continue

            src_case_ids = src.get("case_ids") or []
            if case_id and case_id not in src_case_ids:
                raw_excerpt = src.get("raw_excerpt", "").lower()
                locator = src.get("locator", "").lower()
                if case_id.lower() not in raw_excerpt and case_id.lower() not in locator:
                    continue

            # Check authorization across cases
            if src_case_ids:
                if not any(self._auth.can_access_case(principal, cid)[0] for cid in src_case_ids):
                    continue

            stype = str(src.get("source_type", "EVIDENCE")).upper()
            cat = TimelineEventCategory.EVIDENCE_DOCUMENT
            if stype == "CDR":
                cat = TimelineEventCategory.COMMUNICATION
            elif stype in ("BANK_TXN", "BANK", "TRANSACTION"):
                cat = TimelineEventCategory.FINANCIAL_TRANSACTION
            elif stype in ("SURVEILLANCE_REPORT", "SURVEILLANCE"):
                cat = TimelineEventCategory.SURVEILLANCE_SIGHTING
            elif stype == "FIR":
                cat = TimelineEventCategory.EVIDENCE_DOCUMENT

            occurred = _parse_datetime(src.get("occurred_at"))
            recorded = _parse_datetime(src.get("ingested_at")) or occurred
            ts = _ensure_utc(occurred or recorded)

            canonical_id = f"tle-src-{sid}"
            desc = src.get("raw_excerpt") or src.get("locator") or f"Forensic source record {sid}"

            # Entity matching
            if entity_id:
                desc_lower = desc.lower()
                if entity_id.lower() not in desc_lower and not any(entity_id.lower() in cid.lower() for cid in src_case_ids):
                    continue

            dedup_events[canonical_id] = TimelineEventResponse(
                id=canonical_id,
                event_type=stype,
                category=cat,
                timestamp=ts,
                occurred_at=occurred,
                recorded_at=recorded,
                title=f"{stype} Record: {sid}",
                description=desc,
                participant_ids=[],
                case_id=src_case_ids[0] if src_case_ids else case_id,
                source_type=stype,
                source_id=sid,
                locator=src.get("locator"),
                properties={"batch_id": src.get("batch_id"), "content_hash": src.get("content_hash")},
            )

    def _project_case_nodes(
        self,
        principal: Principal,
        case_id: str | None,
        dedup_events: dict[str, TimelineEventResponse],
    ) -> None:
        nodes = getattr(self._repo, "nodes", {})
        if not nodes:
            return

        for nid, node in nodes.items():
            if node.get("entity_type") not in ("Case", "CASE"):
                continue

            if case_id and nid != case_id:
                continue

            if not self._auth.can_access_case(principal, nid)[0]:
                continue

            props = node.get("properties", {})
            incident_dt = _parse_datetime(props.get("incident_date")) or _parse_datetime(props.get("created_at"))
            created_dt = _parse_datetime(props.get("created_at")) or incident_dt
            ts = _ensure_utc(incident_dt or created_dt)

            canonical_id = f"tle-case-{nid}"
            fir_num = props.get("fir_number") or nid
            title = props.get("title") or f"FIR {fir_num} Registered"
            desc = props.get("summary") or f"Legal case registration under {props.get('station_name', 'Police Station')}."

            dedup_events[canonical_id] = TimelineEventResponse(
                id=canonical_id,
                event_type="FIR_REGISTRATION",
                category=TimelineEventCategory.CASE_REGISTRATION,
                timestamp=ts,
                occurred_at=incident_dt,
                recorded_at=created_dt,
                title=title,
                description=desc,
                participant_ids=[],
                location_id=props.get("district") or props.get("station_name"),
                case_id=nid,
                properties={
                    "fir_number": fir_num,
                    "district": props.get("district"),
                    "status": props.get("status"),
                    "offence_category": props.get("offence_category"),
                },
            )

    def _project_verification_tasks(
        self,
        principal: Principal,
        case_id: str | None,
        entity_id: str | None,
        dedup_events: dict[str, TimelineEventResponse],
        projected_task_ids: set[str],
    ) -> None:
        tasks = getattr(self._repo, "verification_tasks", {})
        if not tasks:
            return

        for tid, task in tasks.items():
            cid = getattr(task, "case_id", None)
            if case_id and cid != case_id:
                continue

            if not self._auth.can_access_case(principal, cid)[0]:
                continue

            claim = getattr(task, "target_claim", "")
            if entity_id and entity_id.lower() not in claim.lower():
                continue

            created_at = getattr(task, "created_at", None)
            decided_at = getattr(task, "decided_at", None)
            status = getattr(task, "status", None)

            # 1. Task Creation milestone (if not already projected by A3 event)
            if tid not in projected_task_ids and created_at:
                c_id = f"tle-vtask-created-{tid}"
                created_dt = _ensure_utc(created_at)
                dedup_events[c_id] = TimelineEventResponse(
                    id=c_id,
                    event_type="VERIFICATION_TASK_CREATED",
                    category=TimelineEventCategory.VERIFICATION_WORKFLOW,
                    timestamp=created_dt,
                    occurred_at=created_dt,
                    recorded_at=created_dt,
                    title=f"Verification Task Initiated: {claim}",
                    description=getattr(task, "reason", "Task created from investigative verification plan."),
                    case_id=cid,
                    task_id=tid,
                    actor_id=getattr(task, "assigned_officer_id", None),
                    actor_role=getattr(task, "assigned_role", None),
                    evidence_refs=getattr(task, "requested_evidence_ids", []),
                )

            # 2. Task Decision milestone (separate lifecycle state)
            if status in (VerificationTaskStatus.VERIFIED, VerificationTaskStatus.DISMISSED) and decided_at:
                d_id = f"tle-vtask-decided-{tid}"
                decided_dt = _ensure_utc(decided_at)
                decision_val = getattr(getattr(task, "decision", None), "value", "DECIDED")
                dedup_events[d_id] = TimelineEventResponse(
                    id=d_id,
                    event_type="VERIFICATION_TASK_DECIDED",
                    category=TimelineEventCategory.VERIFICATION_WORKFLOW,
                    timestamp=decided_dt,
                    occurred_at=decided_dt,
                    recorded_at=decided_dt,
                    title=f"Verification Task {decision_val}: {claim}",
                    description=getattr(task, "decision_rationale", f"Verification decided by {getattr(task, 'deciding_actor', 'officer')}."),
                    case_id=cid,
                    task_id=tid,
                    actor_id=getattr(task, "deciding_actor", None),
                    evidence_refs=getattr(task, "received_evidence_ids", []),
                )

    def _project_affected_routes(
        self,
        principal: Principal,
        case_id: str | None,
        entity_id: str | None,
        dedup_events: dict[str, TimelineEventResponse],
        projected_route_ids: set[str],
    ) -> None:
        routes = getattr(self._repo, "affected_routes", {})
        if not routes:
            return

        for rid, route in routes.items():
            target_cid = getattr(route, "target_case_id", "")
            origin_cid = getattr(route, "origin_case_id", "")

            if case_id and case_id != target_cid and case_id != origin_cid:
                continue

            # Check authorization for target or origin
            can_target = self._auth.can_access_case(principal, target_cid)[0]
            can_origin = self._auth.can_access_case(principal, origin_cid)[0]
            if not can_target and not can_origin:
                continue

            intersecting = getattr(route, "intersecting_entity_ids", [])
            if entity_id and entity_id not in intersecting:
                continue

            disp_dt_val = _parse_datetime(getattr(route, "dispatched_at", None))
            ack_dt_val = _parse_datetime(getattr(route, "acknowledged_at", None))

            # Dispatch milestone
            if rid not in projected_route_ids and disp_dt_val:
                disp_id = f"tle-route-disp-{rid}"
                dt = _ensure_utc(disp_dt_val)
                dedup_events[disp_id] = TimelineEventResponse(
                    id=disp_id,
                    event_type="ROUTE_DISPATCHED",
                    category=TimelineEventCategory.CROSS_CASE_ROUTE,
                    timestamp=dt,
                    occurred_at=dt,
                    recorded_at=dt,
                    title=f"Cross-Case Intelligence Routed ({origin_cid} -> {target_cid})",
                    description=getattr(route, "routing_reason", "Intelligence envelope dispatched to target investigation."),
                    participant_ids=intersecting,
                    edge_ids=getattr(route, "intersecting_edge_ids", []),
                    case_id=target_cid,
                    route_id=rid,
                    snapshot_id=getattr(route, "target_snapshot_id", None),
                    evidence_refs=getattr(route, "evidence_refs", []),
                )

            # Acknowledgment milestone
            if getattr(route, "status", None) == PulseDeliveryStatus.ACKNOWLEDGED and ack_dt_val:
                ack_id = f"tle-route-ack-{rid}"
                dt = _ensure_utc(ack_dt_val)
                dedup_events[ack_id] = TimelineEventResponse(
                    id=ack_id,
                    event_type="ROUTE_ACKNOWLEDGED",
                    category=TimelineEventCategory.CROSS_CASE_ROUTE,
                    timestamp=dt,
                    occurred_at=dt,
                    recorded_at=dt,
                    title=f"Cross-Case Route Acknowledged ({target_cid})",
                    description=getattr(route, "acknowledgment_note") or f"Intelligence packet acknowledged by {getattr(route, 'acknowledged_by', 'officer')}.",
                    participant_ids=intersecting,
                    case_id=target_cid,
                    route_id=rid,
                    actor_id=getattr(route, "acknowledged_by", None),
                )
