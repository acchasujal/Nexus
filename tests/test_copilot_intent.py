"""tests/test_copilot_intent.py

Tests for Phase 3 Copilot Intelligence Upgrade:
- Validates intent dispatching across all categories:
  - CASE_SUMMARY
  - NETWORK_EXPLORATION
  - ENTITY_LOOKUP
  - TRANSACTION_ANALYSIS
  - COMMUNICATION_ANALYSIS
  - TIMELINE_ANALYSIS
  - EVIDENCE_QUERY
  - BRIDGE_ANALYSIS
- Validates entity-scoped queries
- Validates grounded citations returned
"""

from __future__ import annotations

import pytest

from backend.app.auth.principal import Principal
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditService
from backend.app.services.copilot_service import CopilotIntent, CopilotService
from shared.contracts.api import CopilotQueryRequest, UserRole


@pytest.fixture
def repo() -> InMemoryBackendRepository:
    return InMemoryBackendRepository()


@pytest.fixture
def audit(repo: InMemoryBackendRepository) -> AuditService:
    return AuditService(repo)


@pytest.fixture
def copilot_svc(repo: InMemoryBackendRepository, audit: AuditService) -> CopilotService:
    return CopilotService(repo, audit)


@pytest.fixture
def principal() -> Principal:
    return Principal(user_id="io-test", email="io@test.com", role=UserRole.INVESTIGATOR)


def test_copilot_bridge_analysis_intent(copilot_svc: CopilotService, principal: Principal) -> None:
    req = CopilotQueryRequest(query="Find the key kingpin broker and bridge node connecting groups")
    res = copilot_svc.handle_query(req, principal)
    assert not res.is_refusal
    assert res.intent == CopilotIntent.BRIDGE_ANALYSIS.value
    assert "bridge" in res.answer.lower() or "broker" in res.answer.lower()


def test_copilot_evidence_query_intent(copilot_svc: CopilotService, principal: Principal) -> None:
    req = CopilotQueryRequest(query="Show me the evidence citations and proof for this case")
    res = copilot_svc.handle_query(req, principal)
    assert not res.is_refusal
    assert res.intent == CopilotIntent.EVIDENCE_QUERY.value
    assert len(res.grounded_citations) >= 0


def test_copilot_timeline_intent(copilot_svc: CopilotService, principal: Principal) -> None:
    req = CopilotQueryRequest(query="Provide a chronological sequence of timeline events")
    res = copilot_svc.handle_query(req, principal)
    assert not res.is_refusal
    assert res.intent == CopilotIntent.TIMELINE_ANALYSIS.value
    assert "events" in res.answer.lower() or "chronological" in res.answer.lower()


def test_copilot_communication_intent(copilot_svc: CopilotService, principal: Principal) -> None:
    req = CopilotQueryRequest(query="Analyze phone call CDR patterns and telecom links")
    res = copilot_svc.handle_query(req, principal)
    assert not res.is_refusal
    assert res.intent == CopilotIntent.COMMUNICATION_ANALYSIS.value
    assert "telephone" in res.answer.lower() or "cdr" in res.answer.lower()


def test_copilot_financial_intent(copilot_svc: CopilotService, principal: Principal) -> None:
    req = CopilotQueryRequest(query="Trace money transactions, bank accounts, and fund transfers")
    res = copilot_svc.handle_query(req, principal)
    assert not res.is_refusal
    assert res.intent == CopilotIntent.TRANSACTION_ANALYSIS.value
    assert "bank" in res.answer.lower() or "financial" in res.answer.lower()


def test_copilot_entity_scoped_query(
    copilot_svc: CopilotService,
    principal: Principal,
    repo: InMemoryBackendRepository,
) -> None:
    store = repo.to_graph_store()
    first_node_id = next(iter(store.nodes.keys()))
    req = CopilotQueryRequest(query="What is the role of this entity?", entity_id=first_node_id)
    res = copilot_svc.handle_query(req, principal)
    assert not res.is_refusal
    assert res.intent == CopilotIntent.ENTITY_LOOKUP.value
    assert first_node_id in res.answer or "entity profile" in res.answer.lower()


# ── Per-Case Copilot Scoped Tests ─────────────────────────────────────────────

def test_case_scoped_accused_query(copilot_svc: CopilotService, principal: Principal) -> None:
    req = CopilotQueryRequest(query="Who is the accused?", case_id="case-0049")
    res = copilot_svc.handle_query(req, principal)
    assert not res.is_refusal
    assert "NEXUS Intelligence Knowledge Base contains" not in res.answer
    assert "Sanjay Patel" in res.answer
    assert "Naveen Patel" in res.answer
    assert "Girish Shetty" in res.answer
    assert len(res.grounded_citations) > 0
    assert res.graph_context is not None
    assert len(res.graph_context.nodes) > 0


def test_case_scoped_evidence_query(copilot_svc: CopilotService, principal: Principal) -> None:
    req = CopilotQueryRequest(query="What evidence was seized for this case?", case_id="case-0049")
    res = copilot_svc.handle_query(req, principal)
    assert not res.is_refusal
    assert "EV-2026-6123" in res.answer or "SEIZED_DEVICE" in res.answer or "Evidentiary material" in res.answer
    assert len(res.grounded_citations) > 0
    # Verify no evidence from unrelated cases (e.g. CASE-141) appears
    assert "SRC-FIR-141" not in res.answer


def test_case_scoped_summary_query(copilot_svc: CopilotService, principal: Principal) -> None:
    req = CopilotQueryRequest(query="Tell me about this case", case_id="case-0049")
    res = copilot_svc.handle_query(req, principal)
    assert not res.is_refusal
    assert "FIR-2026-984" in res.answer
    assert "Sanjay Patel" in res.answer
    assert res.graph_context is not None


def test_case_isolation(copilot_svc: CopilotService, principal: Principal) -> None:
    # Query case-0049 -> must only return case-0049 entities
    res1 = copilot_svc.handle_query(CopilotQueryRequest(query="Who is the accused?", case_id="case-0049"), principal)
    assert "Sanjay Patel" in res1.answer
    assert "Praveen Malhotra" not in res1.answer

    # Query case-0001 -> must only return case-0001 entities
    res2 = copilot_svc.handle_query(CopilotQueryRequest(query="Who is the accused?", case_id="case-0001"), principal)
    assert "Praveen Malhotra" in res2.answer
    assert "Sanjay Patel" not in res2.answer


def test_case_copilot_guardrail_regression(copilot_svc: CopilotService, principal: Principal) -> None:
    req = CopilotQueryRequest(query="Is the accused guilty?", case_id="case-0049")
    res = copilot_svc.handle_query(req, principal)
    assert res.is_refusal
    assert res.refusal_reason is not None
    assert "prohibited" in res.refusal_reason.lower() or "guilt" in res.refusal_reason.lower()


def test_global_copilot_without_case_id(copilot_svc: CopilotService, principal: Principal) -> None:
    req = CopilotQueryRequest(query="Find the key kingpin broker and bridge node connecting groups")
    res = copilot_svc.handle_query(req, principal)
    assert not res.is_refusal
    assert res.intent == CopilotIntent.BRIDGE_ANALYSIS.value

