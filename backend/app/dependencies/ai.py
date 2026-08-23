"""backend/app/dependencies/ai.py

Dependency providers for AI and Copilot in NEXUS.
"""

from __future__ import annotations

from fastapi import Depends

from backend.app.api.dependencies import get_audit_service, get_repository
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditService
from backend.app.services.copilot_service import CopilotService


def get_copilot_service_dep(
    repo: InMemoryBackendRepository = Depends(get_repository),
    audit_svc: AuditService = Depends(get_audit_service),
) -> CopilotService:
    return CopilotService(repo, audit_svc)