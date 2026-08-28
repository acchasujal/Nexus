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
