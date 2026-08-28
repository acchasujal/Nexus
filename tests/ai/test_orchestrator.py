"""tests/ai/test_orchestrator.py

Integration and unit tests for AIToolOrchestrator and CopilotService AI integration.
Validates safety refusal gate, tool-calling loop, citation authority, telemetry, and fallback behavior.
"""

import pytest

from backend.app.ai.llm_client import DeterministicMockLLMClient
from backend.app.ai.orchestrator import AIToolOrchestrator
from backend.app.ai.prompt_manager import PromptManager
from backend.app.ai.tools import NEXUSToolRegistry
from backend.app.auth.principal import Principal
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.copilot_service import CopilotService
from shared.contracts.api import CopilotQueryRequest, UserRole


@pytest.fixture
def repo():
    return InMemoryBackendRepository()


@pytest.fixture
def audit_svc(repo):
    return AuditService(repo)


@pytest.fixture
def principal():
    return Principal(user_id="officer-test-01", email="officer@nexus.gov.in", role=UserRole.INVESTIGATOR)


@pytest.fixture
def tool_registry(repo, audit_svc):
    return NEXUSToolRegistry(repo, audit_svc)


@pytest.fixture
def mock_orchestrator(tool_registry, audit_svc):
    return AIToolOrchestrator(
        llm_client=DeterministicMockLLMClient(),
        tool_registry=tool_registry,
        prompt_manager=PromptManager(),
        audit_service=audit_svc,
    )


def test_safety_refusal_gate(mock_orchestrator, principal, audit_svc):
    req = CopilotQueryRequest(query="Predict if suspect Rafiq is guilty or will reoffend")
    res = mock_orchestrator.process_query(req, principal=principal)
    assert res is not None
    assert res.is_refusal is True
    assert "automated guilt/predictive analysis is prohibited" in res.refusal_reason

    # Verify audit event
    audits = audit_svc.list_events(limit=5)
    assert any(e.get("event_type") == AuditEventType.COPILOT_REFUSED.value for e in audits)


def test_orchestrator_tool_calling_and_citation_authority(mock_orchestrator, principal, audit_svc):
    req = CopilotQueryRequest(query="Find connection path between CASE-141 and CASE-207")
    res = mock_orchestrator.process_query(req, principal=principal)
    assert res is not None
    assert res.is_refusal is False
    assert "deterministic graph intelligence results" in res.answer
    assert isinstance(res.grounded_citations, list)
    assert isinstance(res.evidence_ids, list)
    assert isinstance(res.reasoning_path, list)

    # Verify audit event and telemetry
    audits = audit_svc.list_events(limit=5)
    answered_event = next(e for e in audits if e.get("event_type") == AuditEventType.COPILOT_ANSWERED.value)
    details = answered_event.get("details", {})
    assert "telemetry" in details
    telemetry = details["telemetry"]
    assert telemetry["generation_mode"] == "MOCK_LLM_TEST"
    assert telemetry["provider"] == "mock_test_provider"
    assert len(telemetry["tool_calls"]) > 0


def test_copilot_service_with_ai_orchestrator(repo, audit_svc, mock_orchestrator, principal):
    svc = CopilotService(repository=repo, audit_service=audit_svc, orchestrator=mock_orchestrator)
    req = CopilotQueryRequest(query="Find connection path between CASE-141 and CASE-207")
    res = svc.handle_query(req, principal=principal)
    assert res.is_refusal is False
    assert "deterministic graph intelligence results" in res.answer


def test_copilot_service_deterministic_fallback_when_unconfigured(repo, audit_svc, tool_registry, principal, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("NEXUS_LLM_API_KEY", raising=False)
    monkeypatch.delenv("NEXUS_USE_MOCK_LLM", raising=False)

    unconfigured_orchestrator = AIToolOrchestrator(
        llm_client=None,
        tool_registry=tool_registry,
        audit_service=audit_svc,
    )
    svc = CopilotService(repository=repo, audit_service=audit_svc, orchestrator=unconfigured_orchestrator)
    req = CopilotQueryRequest(query="How are the two cases connected?")
    res = svc.handle_query(req, principal=principal)
    assert res.is_refusal is False
    assert "connect" in res.answer.lower()
    assert len(res.grounded_citations) > 0


def test_orchestrator_datetime_json_serialization(principal, audit_svc):
    from datetime import datetime, timezone
    from unittest.mock import MagicMock
    from backend.app.ai.schemas import LLMResponse, ToolCall
    from backend.app.ai.tools import NEXUSToolResult

    # Mock tool registry that returns datetime objects in result data
    mock_tools = MagicMock()
    mock_tools.get_tool_declarations.return_value = [{"type": "function", "function": {"name": "test_dt_tool", "parameters": {}}}]
    mock_tools.execute.return_value = NEXUSToolResult(
        success=True,
        tool_name="test_dt_tool",
        data={"timestamp": datetime.now(timezone.utc), "nested": {"created_at": datetime(2026, 1, 1, 10, 0)}},
        evidence_ids=["EV-DT-01"],
        citations=[],
    )

    # Mock LLM client that issues a tool call on turn 1, then synthesizes on turn 2
    mock_client = MagicMock()
    mock_client.provider_name = "mock_test"
    mock_client.model_name = "mock-model"
    mock_client.generate.side_effect = [
        LLMResponse(content="", tool_calls=[ToolCall(name="test_dt_tool", arguments={}, call_id="c1")]),
        LLMResponse(content="Successfully parsed datetime payload", tool_calls=[]),
    ]

    orchestrator = AIToolOrchestrator(
        llm_client=mock_client,
        tool_registry=mock_tools,
        prompt_manager=PromptManager(),
        audit_service=audit_svc,
    )

    req = CopilotQueryRequest(query="Run datetime tool")
    res = orchestrator.process_query(req, principal=principal)
    assert res is not None
    assert res.answer == "Successfully parsed datetime payload"
    assert "EV-DT-01" in res.evidence_ids


def test_orchestrator_preserves_tools_on_multi_turn_calls(principal, audit_svc):
    from unittest.mock import MagicMock
    from backend.app.ai.schemas import LLMResponse, ToolCall
    from backend.app.ai.tools import NEXUSToolResult

    mock_tools = MagicMock()
    mock_tools.get_tool_declarations.return_value = [
        {"type": "function", "function": {"name": "tool_a", "parameters": {}}},
        {"type": "function", "function": {"name": "tool_b", "parameters": {}}},
    ]
    mock_tools.execute.side_effect = [
        NEXUSToolResult(success=True, tool_name="tool_a", data={"res": "a"}, evidence_ids=["EV-A"]),
        NEXUSToolResult(success=True, tool_name="tool_b", data={"res": "b"}, evidence_ids=["EV-B"]),
    ]

    captured_requests = []

    def mock_generate(request):
        captured_requests.append(request)
        if len(captured_requests) == 1:
            return LLMResponse(content="", tool_calls=[ToolCall(name="tool_a", arguments={}, call_id="c1")])
        elif len(captured_requests) == 2:
            return LLMResponse(content="", tool_calls=[ToolCall(name="tool_b", arguments={}, call_id="c2")])
        else:
            return LLMResponse(content="Final synthesis completed", tool_calls=[])

    mock_client = MagicMock()
    mock_client.provider_name = "mock_test"
    mock_client.model_name = "mock-model"
    mock_client.generate.side_effect = mock_generate

    orchestrator = AIToolOrchestrator(
        llm_client=mock_client,
        tool_registry=mock_tools,
        prompt_manager=PromptManager(),
        audit_service=audit_svc,
    )

    req = CopilotQueryRequest(query="Run multi turn tools")
    res = orchestrator.process_query(req, principal=principal)

    assert res is not None
    assert res.answer == "Final synthesis completed"
    assert "EV-A" in res.evidence_ids
    assert "EV-B" in res.evidence_ids

    # Assert that all requests sent to the LLM client retained the tools declaration
    for i, req in enumerate(captured_requests):
        assert req.tools is not None, f"Turn {i + 1} omitted tools declaration, which causes Groq 'Tool choice is none' error"
        assert len(req.tools) == 2
