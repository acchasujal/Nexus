"""backend/app/services/copilot_service.py

Copilot service for CaseClock.

## Architecture

From the QuickML spike (docs/spikes/quickml.md):
  - QuickML parses natural language → structured intent JSON
  - The backend executes the intent against graph data deterministically
  - QuickML must NEVER perform: legal reasoning, BNSS calculation, predictions

## Phase 6 pipeline

    Investigator NL query
        │
        ▼
    CopilotService.handle_query()
        │
        ├─ Safety filter (pre-check prohibited terms) → refuse immediately
        │
        ├─ QuickML intent parse → IntentParseResult
        │
        ├─ Pydantic validation on parsed result
        │
        ├─ Allowed-intent guard → refuse if unsupported
        │
        ├─ Intent executor (case lookup, clock summary, etc.)
        │
        └─ Grounded response → CopilotQueryResponse

## Phase 1/5 stopgap

QuickML is not yet integrated.  The service delegates to InMemoryBackendRepository
for a keyword-based fallback, exactly as the prototype did, while exposing the
correct interface for Phase 6 to slot in.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from backend.app.auth.principal import Principal
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import CopilotQueryRequest, CopilotQueryResponse

logger = logging.getLogger(__name__)


# ── Prohibited inference check ─────────────────────────────────────────────────
# From shared.contracts.api: "Refusal is a first-class, tested behavior."

_PROHIBITED_TERMS = frozenset({
    "guilty", "culpable", "reoffend", "re-offend", "criminal mindset",
    "predict", "lie", "innocent", "commit crimes again", "repeat offender",
})


def _is_prohibited(query: str) -> bool:
    """Return True if the query requests a legally prohibited inference."""
    normalized = query.lower()
    return any(term in normalized for term in _PROHIBITED_TERMS)


# ── Allowed intent enum ────────────────────────────────────────────────────────

class CopilotIntent(str, Enum):
    """Allowed intents for the copilot.  From QuickML spike schema constraints."""
    RETRIEVE_CASES = "retrieve_cases"
    AGGREGATE = "aggregate"
    GRAPH_QUERY = "graph_query"
    CASE_STATUS = "case_status"          # clock + dependency summary for a case
    UNSUPPORTED = "unsupported_request"  # QuickML sentinel for unrecognized queries


# ── Service ────────────────────────────────────────────────────────────────────

class CopilotService:
    """Orchestrates the copilot pipeline.

    Phase 5: keyword-based fallback (no QuickML).
    Phase 6: QuickML integration replaces `_parse_intent()`.

    The safety filter, allowed-intent guard, and audit logging are always active.
    """

    def __init__(
        self,
        repository: Any,
        audit_service: AuditService,
    ) -> None:
        self._repo = repository
        self._audit = audit_service

    def handle_query(
        self,
        request: CopilotQueryRequest,
        principal: Principal,
        request_id: str | None = None,
    ) -> CopilotQueryResponse:
        """Process a copilot query through the full safety + intent pipeline.

        Args:
            request: The NL query request from the frontend.
            principal: Verified caller identity.
            request_id: Request correlation ID.

        Returns:
            CopilotQueryResponse — always non-None (may be a refusal).
        """
        # Step 1: Prohibited inference pre-check
        if _is_prohibited(request.query):
            self._audit.record(
                AuditEventType.COPILOT_REFUSED,
                actor_id=principal.user_id,
                case_id=request.case_id,
                reason="prohibited_inference",
                request_id=request_id,
            )
            return CopilotQueryResponse(
                refused=True,
                refusal_reason=(
                    "I cannot infer guilt, innocence, culpability, or reoffense risk. "
                    "I can only summarize recorded case facts."
                ),
                confidence=0.95,
            )

        # Step 2: Intent parsing (Phase 5: keyword fallback; Phase 6: QuickML)
        intent = self._parse_intent(request.query, request.case_id)

        if intent == CopilotIntent.UNSUPPORTED:
            self._audit.record(
                AuditEventType.COPILOT_REFUSED,
                actor_id=principal.user_id,
                case_id=request.case_id,
                reason="unsupported_intent",
                request_id=request_id,
            )
            return CopilotQueryResponse(
                refused=True,
                refusal_reason="I can only answer questions about case clocks, dependencies, escalations, and graph facts.",
                confidence=0.8,
            )

        # Step 3: Execute intent against repository
        response = self._repo.copilot_query(request.query, request.case_id)

        self._audit.record(
            AuditEventType.COPILOT_ANSWERED,
            actor_id=principal.user_id,
            case_id=request.case_id,
            intent=intent.value,
            confidence=response.confidence,
            request_id=request_id,
        )
        return response

    def _parse_intent(self, query: str, case_id: str | None) -> CopilotIntent:
        """Phase 5 keyword-based intent parser.

        Phase 6 replaces this with a QuickML HTTP call:
            POST /quickml/predict
            {"query": query, "schema": INTENT_SCHEMA, "temperature": 0.0}

        Returns CopilotIntent.UNSUPPORTED if the query is not recognized.
        """
        normalized = query.lower()

        if case_id:
            return CopilotIntent.CASE_STATUS

        if any(term in normalized for term in ("case", "fir", "status", "clock", "deadline", "blocker", "dependency")):
            return CopilotIntent.RETRIEVE_CASES

        if any(term in normalized for term in ("count", "aggregate", "how many", "total", "district", "station")):
            return CopilotIntent.AGGREGATE

        if any(term in normalized for term in ("network", "graph", "connected", "co-accused", "accused")):
            return CopilotIntent.GRAPH_QUERY

        return CopilotIntent.UNSUPPORTED
