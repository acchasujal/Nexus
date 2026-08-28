"""backend/app/ai/orchestrator.py

AI Tool Orchestrator for NEXUS.
Executes the tool-calling agent loop:
  Query -> Safety Refusal Gate -> Real LLM -> Tool Selection ->
  NEXUS Deterministic Tool -> Grounded Synthesis.

Strict Enforcement:
  - The LLM is NEVER authoritative for citations, evidence IDs, case IDs, or provenance.
  - All citations and evidence IDs are extracted directly from deterministic tool outputs.
  - If no LLM is configured or an error occurs, returns None to trigger deterministic fallback.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from backend.app.ai.llm_client import BaseLLMClient, DeterministicMockLLMClient
from backend.app.ai.prompt_manager import PromptManager, PromptType
from backend.app.ai.schemas import ChatMessage, LLMRequest
from backend.app.ai.tools import NEXUSToolRegistry, NEXUSToolResult
from backend.app.auth.principal import Principal
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    CopilotQueryRequest,
    CopilotQueryResponse,
    GroundedCitation,
)

logger = logging.getLogger(__name__)

# Safety refusal prohibited terms (Legal & Judicial Guardrail)
_PROHIBITED_TERMS = frozenset({
    "guilty", "culpable", "reoffend", "re-offend", "criminal mindset",
    "predict", "predict guilt", "lie", "innocent", "commit crimes again",
    "will commit", "culpability", "mastermind", "convict", "punish",
})


def is_prohibited_query(query: str) -> bool:
    """Return True if the query requests a legally or ethically prohibited inference."""
    normalized = query.lower()
    return any(term in normalized for term in _PROHIBITED_TERMS)


def _json_safe_default(obj: Any) -> Any:
    """Generic JSON serializer for datetime, date, UUID, Enum, Pydantic models."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "value"):
        return obj.value
    return str(obj)


class AIToolOrchestrator:
    """Orchestrates LLM tool-calling and deterministic evidence synthesis."""

    def __init__(
        self,
        llm_client: BaseLLMClient | None,
        tool_registry: NEXUSToolRegistry,
        prompt_manager: PromptManager | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._tools = tool_registry
        self._prompts = prompt_manager or PromptManager()
        self._audit = audit_service

    @property
    def is_active(self) -> bool:
        """Return True if an LLM client (real or mock) is active."""
        return self._llm_client is not None

    def process_query(
        self,
        request: CopilotQueryRequest,
        principal: Principal,
        request_id: str | None = None,
    ) -> CopilotQueryResponse | None:
        """Process an investigator query through safety, tool selection, and grounded synthesis."""
        query_text = request.query.strip()
        if not query_text:
            return None

        # ── 1. Safety & Ethics Refusal Gate ───────────────────────────────────
        if is_prohibited_query(query_text):
            if self._audit:
                self._audit.record(
                    AuditEventType.COPILOT_REFUSED,
                    actor_id=principal.user_id,
                    case_id=request.case_id or request.investigation_id,
                    request_id=request_id,
                    details={"query": query_text, "reason": "Prohibited predictive/guilt inference query"},
                )
            return CopilotQueryResponse(
                query=query_text,
                intent="safety_refusal",
                answer=(
                    "I cannot provide opinions, predictions, or legal inferences regarding guilt, culpability, "
                    "or reoffending likelihood. As an evidence-grounded intelligence copilot, I provide only "
                    "verifiable facts, phone records, financial links, and network associations directly supported by the data."
                ),
                is_refusal=True,
                refusal_reason="Legal and ethical guardrail: automated guilt/predictive analysis is prohibited.",
                suggested_actions=[
                    "View confirmed phone call logs",
                    "Examine bank transfer chains",
                    "Inspect co-accused network graph",
                ],
                evidence_ids=[],
                reasoning_path=[],
            )

        # ── 2. Guard: No LLM configured -> Return None for deterministic fallback
        if not self._llm_client:
            return None

        # Determine generation mode
        is_mock = isinstance(self._llm_client, DeterministicMockLLMClient)
        generation_mode = "MOCK_LLM_TEST" if is_mock else "REAL_LLM"

        # ── 3. Build Conversation Messages ────────────────────────────────────
        system_prompt = self._prompts.get_prompt(PromptType.SYSTEM)
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=query_text),
        ]

        tool_declarations = self._tools.get_tool_declarations()

        # Telemetry tracking
        telemetry: dict[str, Any] = {
            "generation_mode": generation_mode,
            "provider": self._llm_client.provider_name,
            "model": self._llm_client.model_name,
            "tool_calls": [],
            "tool_duration_ms": 0.0,
            "retrieved_nodes_count": 0,
            "retrieved_edges_count": 0,
            "evidence_ids": [],
        }

        all_citations: list[GroundedCitation] = []
        all_evidence_ids: list[str] = []
        all_reasoning_paths: list[str] = []
        all_case_ids: list[str] = []
        all_entity_ids: list[str] = []
        final_answer = ""
        detected_intent = "ai_tool_synthesis"

        try:
            # ── 4. Multi-Turn Tool Execution Loop (Up to 4 turns) ─────────────
            max_turns = 4
            current_turn = 0
            while current_turn < max_turns:
                current_turn += 1
                req = LLMRequest(
                    messages=messages,
                    tools=tool_declarations,
                    temperature=0.0,
                )
                response = self._llm_client.generate(req)

                if response.tool_calls:
                    # Ensure every tool call has a consistent unique ID
                    tool_calls_meta = []
                    for i, tc in enumerate(response.tool_calls):
                        if not tc.call_id:
                            tc.call_id = f"call_{current_turn}_{i}_{tc.name}"
                        tool_calls_meta.append({
                            "id": tc.call_id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments, default=_json_safe_default) if isinstance(tc.arguments, dict) else str(tc.arguments),
                            },
                        })

                    messages.append(
                        ChatMessage(
                            role="assistant",
                            content=response.content or "",
                            metadata={"tool_calls": tool_calls_meta},
                        )
                    )

                    # Execute deterministic tools for this turn
                    for tc in response.tool_calls:
                        call_id = tc.call_id
                        t_start = time.perf_counter()
                        tool_result: NEXUSToolResult = self._tools.execute(tc.name, tc.arguments)
                        t_dur_ms = (time.perf_counter() - t_start) * 1000.0

                        telemetry["tool_calls"].append({
                            "tool": tc.name,
                            "arguments": tc.arguments,
                            "duration_ms": round(t_dur_ms, 2),
                            "success": tool_result.success,
                        })
                        telemetry["tool_duration_ms"] += t_dur_ms
                        telemetry["retrieved_nodes_count"] += tool_result.nodes_count
                        telemetry["retrieved_edges_count"] += tool_result.edges_count

                        _TOOL_INTENT_MAP = {
                            "find_shortest_path": "cross_case_analysis",
                            "resolve_person_identity": "entity_lookup",
                            "get_case_dossier": "case_summary",
                            "detect_bridge_brokers": "bridge_analysis",
                            "detect_communities": "community_detection",
                            "detect_financial_layering": "transaction_analysis",
                            "analyze_cdr_bursts": "communication_analysis",
                            "get_evidence_provenance": "evidence_query",
                            "get_cross_case_connections": "cross_case_analysis",
                        }
                        detected_intent = _TOOL_INTENT_MAP.get(tc.name, "ai_tool_synthesis")

                        # Extract Authoritative Citations & Lineage from Tool Output
                        all_citations.extend(tool_result.citations)
                        all_evidence_ids.extend(tool_result.evidence_ids)
                        all_reasoning_paths.extend(tool_result.reasoning_path)
                        all_case_ids.extend(tool_result.case_ids)
                        all_entity_ids.extend(tool_result.entity_ids)

                        # Append tool result message for LLM synthesis
                        tool_payload = json.dumps({
                            "success": tool_result.success,
                            "data": tool_result.data,
                            "evidence_ids": tool_result.evidence_ids,
                            "error": tool_result.error,
                        }, default=_json_safe_default)
                        messages.append(
                            ChatMessage(
                                role="tool",
                                name=tc.name,
                                content=tool_payload,
                                metadata={"tool_call_id": call_id},
                            )
                        )
                else:
                    final_answer = response.content or "NEXUS Intelligence Copilot processed your request."
                    break

            # Clean and deduplicate authoritative citations and IDs
            deduped_evidence_ids = list(dict.fromkeys(all_evidence_ids))
            telemetry["evidence_ids"] = deduped_evidence_ids

            resolved_case_id = (
                request.case_id
                or request.investigation_id
                or (all_case_ids[0] if all_case_ids else None)
            )

            # ── 7. Audit Logging ──────────────────────────────────────────────
            if self._audit:
                self._audit.record(
                    AuditEventType.COPILOT_ANSWERED,
                    actor_id=principal.user_id,
                    case_id=resolved_case_id,
                    request_id=request_id,
                    details={
                        "query": query_text,
                        "intent": detected_intent,
                        "telemetry": telemetry,
                    },
                )

            suggested_actions = [
                "Open Case Details",
                "Expand neighborhood in Network Explorer",
                "View verified evidence chain",
            ]

            return CopilotQueryResponse(
                query=query_text,
                intent=detected_intent,
                answer=final_answer,
                is_refusal=False,
                grounded_citations=all_citations,
                suggested_actions=suggested_actions,
                graph_context=None,
                evidence_ids=deduped_evidence_ids,
                reasoning_path=all_reasoning_paths,
                case_id=resolved_case_id,
            )

        except Exception as exc:
            logger.warning("AI Orchestrator failed, falling back to deterministic Copilot: %s", exc)
            return None
