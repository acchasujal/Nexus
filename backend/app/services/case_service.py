"""backend/app/services/case_service.py

Core case workflow service for CaseClock.

Phase 4 implementation: stateless service that orchestrates:
  - Case retrieval (via repository)
  - Clock computation (via ClockEngine — deterministic, no DB reads)
  - Dependency aggregation (via DependencyEngine)
  - Escalation evaluation (via EscalationEngine)
  - Audit trail (via AuditService)

Design contract:
  - No HTTP imports; this layer is transport-agnostic.
  - Takes Principal for identity — all decisions are logged with actor_id.
  - All business rule evaluation happens in the domain engines.
  - Repository reads/writes are the only I/O this service does.
  - Returns shared contract types (from shared.contracts.api) directly.

Phase transition:
  Phase 1/3: InMemoryBackendRepository satisfies all reads and writes.
  Phase 4:   Wired to Catalyst-backed repositories via the ABC interfaces.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.auth.principal import Principal
from backend.app.core.clock.engine import ClockEngine
from backend.app.core.dependency.engine import DependencyEngine
from backend.app.core.escalation.engine import EscalationEngine
from backend.app.core.time import utc_now
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    CaseDetailResponse,
    CaseSummaryResponse,
    DependencyResponse,
    DependencyStatus,
    EscalationResponse,
)


class CaseService:
    """Application service for case clock and dependency workflows.

    All methods are synchronous in Phase 1/3 (in-memory I/O).
    Phase 4 may convert to async when wired to Catalyst Data Store async SDK.
    """

    def __init__(
        self,
        repository: Any,
        audit_service: AuditService,
        reference_time: datetime | None = None,
    ) -> None:
        """
        Args:
            repository: Any repository implementing the case/dependency surface.
                        Phase 1: InMemoryBackendRepository.
                        Phase 4: Catalyst-backed DomainRepository.
            audit_service: Shared audit recorder.
            reference_time: Override the reference time (for tests).
        """
        self._repo = repository
        self._audit = audit_service
        ref = reference_time or utc_now()
        self._clock_engine = ClockEngine(ref)
        self._dep_engine = DependencyEngine(ref)
        self._esc_engine = EscalationEngine(ref)

    def list_worklist(
        self,
        principal: Principal,
        request_id: str | None = None,
    ) -> list[CaseSummaryResponse]:
        """Return the risk-ranked worklist visible to the principal's role."""
        self._audit.record(
            AuditEventType.WORKLIST_VIEWED,
            actor_id=principal.user_id,
            request_id=request_id,
            role=principal.role.value,
        )
        summaries = self._repo.list_worklist(role=principal.role.value)
        return summaries

    def get_case_detail(
        self,
        case_id: str,
        principal: Principal,
        request_id: str | None = None,
    ) -> CaseDetailResponse | None:
        """Return full case detail or None if not found."""
        detail = self._repo.get_case_detail(case_id)
        if detail is None:
            return None
        self._audit.record(
            AuditEventType.CASE_VIEWED,
            actor_id=principal.user_id,
            case_id=case_id,
            request_id=request_id,
        )
        return detail

    def update_dependency(
        self,
        dependency_id: str,
        new_status: DependencyStatus,
        principal: Principal,
        request_id: str | None = None,
    ) -> DependencyResponse | None:
        """Update dependency status.  Returns updated response or None if not found."""
        result = self._repo.update_dependency(dependency_id, new_status)
        if result is None:
            return None
        self._audit.record(
            AuditEventType.DEPENDENCY_UPDATED,
            actor_id=principal.user_id,
            case_id=result.case_id,
            dependency_id=dependency_id,
            status=new_status.value,
            request_id=request_id,
        )
        return result

    def list_escalations(
        self,
        principal: Principal,
        request_id: str | None = None,
    ) -> list[EscalationResponse]:
        """Return all escalations visible to the principal."""
        escalations = self._repo.list_escalations()
        self._audit.record(
            AuditEventType.ESCALATIONS_VIEWED,
            actor_id=principal.user_id,
            count=len(escalations),
            request_id=request_id,
        )
        return escalations

    def get_case_network(
        self,
        case_id: str,
        principal: Principal,
        request_id: str | None = None,
    ) -> dict | None:
        """Return React Flow graph for a case's network.  None if not found."""
        result = self._repo.case_network(case_id)
        if result is None:
            return None
        self._audit.record(
            AuditEventType.CASE_NETWORK_VIEWED,
            actor_id=principal.user_id,
            case_id=case_id,
            request_id=request_id,
        )
        return result

    def get_district_rollup(
        self,
        district: str,
        principal: Principal,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Return the exception-only operational overview of police stations in a district."""
        result = self._repo.get_district_rollup(district)
        self._audit.record(
            AuditEventType.WORKLIST_VIEWED,
            actor_id=principal.user_id,
            district=district,
            request_id=request_id,
        )
        return result
