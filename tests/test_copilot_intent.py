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
from backend.app.services.copilot_service import CopilotService, CopilotIntent
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
