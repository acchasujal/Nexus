"""backend/app/api/system_routes.py

Read-only status endpoints for CaseClock system monitoring and autonomous deadline tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends

from backend.app.api.dependencies import get_audit_service, get_principal, get_repository
from backend.app.auth.principal import Principal
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    CronLastRunSummary,
    CronScheduleInfo,
    DeadlineMonitorStatusResponse,
)


def _parse_iso_datetime(dt_str: str | None) -> datetime | None:
    if not dt_str:
        return None
    try:
        normalized = str(dt_str).replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def create_system_router() -> APIRouter:
    """Return router for system monitoring endpoints."""
    router = APIRouter(prefix="/system", tags=["system-monitoring"])

    @router.get(
        "/deadline-monitor/status",
        response_model=DeadlineMonitorStatusResponse,
    )
    def deadline_monitor_status(
        principal: Principal = Depends(get_principal),
        audit_svc: AuditService = Depends(get_audit_service),
        repo: Any = Depends(get_repository),
    ) -> DeadlineMonitorStatusResponse:
        """Return the operational status of the autonomous deadline monitor."""
        # Find latest DEADLINE_SWEEP_COMPLETED event
        sweep_events = audit_svc.list_events(
            limit=100,
            event_type=AuditEventType.DEADLINE_SWEEP_COMPLETED,
        )

        last_event: dict[str, Any] | None = sweep_events[-1] if sweep_events else None

        schedule_info = CronScheduleInfo(type="recursive", interval_minutes=15)

        if not last_event:
            return DeadlineMonitorStatusResponse(
                status="unavailable",
                schedule=schedule_info,
                last_run=None,
            )

        meta = last_event.get("metadata") or last_event.get("details") or {}
        raw_completed = meta.get("completed_at") or last_event.get("occurred_at")
        completed_dt = _parse_iso_datetime(raw_completed) or datetime.now(timezone.utc)
        completed_at_iso = completed_dt.isoformat()

        ref_time = getattr(repo, "reference_time", None) or datetime.now(timezone.utc)
        if ref_time.tzinfo is None:
            ref_time = ref_time.replace(tzinfo=timezone.utc)

        age_seconds = (ref_time - completed_dt).total_seconds()
        # Active if last sweep completed within 30 minutes (2x interval); delayed if older
        status_str = "active" if age_seconds <= 1800 else "delayed"

        last_run_summary = CronLastRunSummary(
            run_id=str(meta.get("run_id") or last_event.get("request_id") or "cron-run-unknown"),
            completed_at=completed_at_iso,
            cases_scanned=int(meta.get("cases_scanned") or 0),
            clocks_evaluated=int(meta.get("clocks_evaluated") or 0),
            state_transitions=int(meta.get("state_transitions") or 0),
            escalations_created=int(meta.get("escalations_created") or 0),
            errors=int(meta.get("errors") or 0),
            duration_ms=float(meta.get("duration_ms") or 0.0),
        )

        return DeadlineMonitorStatusResponse(
            status=status_str,
            schedule=schedule_info,
            last_run=last_run_summary,
        )

    return router
