"""backend/app/services/case_service.py

Investigation and case intelligence service for NEXUS.
Provides case retrieval, network expansion, evidence tracking, and audit logging.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.auth.principal import Principal
from backend.app.core.time import utc_now
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    InvestigationDetailResponse,
    InvestigationSummaryResponse,
    NetworkGraphResponse,
)


class InvestigationService:
    """Core application service for criminal investigation workflows."""

    def __init__(
        self,
        repository: Any,
        audit_service: AuditService,
        reference_time: datetime | None = None,
    ) -> None:
        self._repo = repository
        self._audit = audit_service
        self._reference_time = reference_time or utc_now()

    def list_investigations(
        self,
        principal: Principal,
        district: str | None = None,
        category: str | None = None,
        status: str | None = None,
        request_id: str | None = None,
    ) -> list[InvestigationSummaryResponse]:
        self._audit.record(
            AuditEventType.INVESTIGATION_LIST_VIEWED,
            actor_id=principal.user_id,
            request_id=request_id,
            details={"role": principal.role.value, "district": district, "category": category},
        )
        return self._repo.list_investigations(district=district, category=category, status=status)

    def get_investigation_detail(
        self,
        case_id: str,
        principal: Principal,
        request_id: str | None = None,
    ) -> InvestigationDetailResponse | None:
        detail = self._repo.get_investigation_detail(case_id)
        if detail is None:
            return None
        self._audit.record(
            AuditEventType.INVESTIGATION_VIEWED,
            actor_id=principal.user_id,
            case_id=case_id,
            request_id=request_id,
        )
        return detail

    def get_case_network(
        self,
        case_id: str,
        principal: Principal,
        depth: int = 2,
        request_id: str | None = None,
    ) -> NetworkGraphResponse:
        self._audit.record(
            AuditEventType.NETWORK_EXPLORED,
            actor_id=principal.user_id,
            case_id=case_id,
            request_id=request_id,
            details={"depth": depth},
        )
        return self._repo.get_case_network(case_id, depth=depth)

    # ── Backward-compatibility aliases ───────────────────────────────────────
    def list_worklist(self, principal: Principal, request_id: str | None = None) -> list[Any]:
        return self.list_investigations(principal=principal, request_id=request_id)

    def get_case_detail(self, case_id: str, principal: Principal, request_id: str | None = None) -> Any:
        return self.get_investigation_detail(case_id=case_id, principal=principal, request_id=request_id)


# Legacy alias
CaseService = InvestigationService
