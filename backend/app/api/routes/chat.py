"""backend/app/api/routes/chat.py

AI Copilot chat presentation layer for NEXUS.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_principal, get_request_id
from backend.app.auth.principal import Principal
from backend.app.dependencies.ai import get_copilot_service_dep
from backend.app.services.copilot_service import CopilotService
from shared.contracts.api import CopilotQueryRequest, CopilotQueryResponse

router = APIRouter(tags=["copilot-chat"])
logger = logging.getLogger(__name__)


class ChatRequestPayload(BaseModel):
    query: str
    case_id: str | None = None
    investigation_id: str | None = None
    session_id: str | None = None


@router.post(
    "/chat",
    response_model=CopilotQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Process Investigator Copilot Chat Query",
)
def chat(
    request: ChatRequestPayload,
    http_request: Request,
    copilot_svc: CopilotService = Depends(get_copilot_service_dep),
    principal: Principal = Depends(get_principal),
    request_id: str = Depends(get_request_id),
) -> CopilotQueryResponse:
    query_req = CopilotQueryRequest(
        query=request.query,
        case_id=request.case_id,
        investigation_id=request.investigation_id,
        session_id=request.session_id,
    )
    return copilot_svc.handle_query(query_req, principal=principal, request_id=request_id)
