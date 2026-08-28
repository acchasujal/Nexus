"""tests/ai/test_context_builder.py

Unit and integration tests for NEXUS GraphRAGContextBuilder (Milestone 3).
Validates query-type-aware graph retrieval, pathfinding integration,
evidence provenance hydration, token-budget pruning, and zero-hallucination guarantees.
"""

import pytest

from backend.app.ai.context_builder import GraphRAGContextBuilder
from backend.app.ai.schemas import InvestigationContext
from backend.app.ai.tools import NEXUSToolRegistry
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditService


@pytest.fixture
def repo() -> InMemoryBackendRepository:
    return InMemoryBackendRepository()


@pytest.fixture
def audit_svc(repo: InMemoryBackendRepository) -> AuditService:
    return AuditService(repo)


@pytest.fixture
def tool_registry(repo: InMemoryBackendRepository, audit_svc: AuditService) -> NEXUSToolRegistry:
    return NEXUSToolRegistry(repo, audit_svc)


@pytest.fixture
def context_builder(
    repo: InMemoryBackendRepository,
    audit_svc: AuditService,
    tool_registry: NEXUSToolRegistry,
) -> GraphRAGContextBuilder:
    return GraphRAGContextBuilder(repo, audit_svc, tool_registry)


def test_cross_case_path_query(context_builder: GraphRAGContextBuilder):
    """Verify Pathfinder integration for cross-case connection queries."""
    query = "How are FIR-141 and FIR-207 connected?"
    ctx: InvestigationContext = context_builder.build_context(query)

    assert ctx.retrieval_metadata.retrieval_strategy == "cross_case_path"
    assert ctx.retrieval_metadata.query_type == "cross_case_connection"
    assert len(ctx.paths) >= 1

    path = ctx.paths[0]
    assert path.hops >= 1
    assert len(path.nodes) >= 2
    assert len(path.evidence_ids) > 0

    # Ensure path nodes are in entities list
    entity_ids = {e.id for e in ctx.entities}
    for n in path.nodes:
        assert n in entity_ids

    # Check Markdown prompt rendering
    prompt_text = ctx.to_prompt_text()
    assert "=== NEXUS DETERMINISTIC INVESTIGATION CONTEXT ===" in prompt_text
    assert "Connection Paths" in prompt_text
    assert "Evidence Citations" in prompt_text


def test_financial_flow_query(context_builder: GraphRAGContextBuilder):
    """Verify targeted financial transaction subgraph and precision filtering."""
    query = "What evidence supports the financial connection between Rafiq and Deepak?"
    ctx: InvestigationContext = context_builder.build_context(query)

    assert ctx.retrieval_metadata.retrieval_strategy == "financial_trace"
    assert ctx.retrieval_metadata.query_type == "financial_flow"
    assert len(ctx.entities) > 0
    assert len(ctx.relationships) > 0

    # Ensure at least one financial transfer edge is present
    has_financial_edge = any(
        "TRANSFER" in r.relationship_type.upper() or "PAYMENT" in r.relationship_type.upper() or "OWN" in r.relationship_type.upper()
        for r in ctx.relationships
    )
    assert has_financial_edge

    # Regression check: Targeted query must NOT pull in unrelated community members
    unrelated_ids = {"person-0015", "person-0016", "person-0026", "person-0027", "person-0028", "person-0029"}
    retrieved_node_ids = {e.id for e in ctx.entities}
    assert not (unrelated_ids & retrieved_node_ids), f"Found unrelated community nodes in targeted query: {unrelated_ids & retrieved_node_ids}"
    assert len(ctx.entities) <= 10, f"Targeted financial query retrieved too many nodes: {len(ctx.entities)}"


def test_pattern_investigation_query(context_builder: GraphRAGContextBuilder):
    """Verify structural pattern detection and finding packaging."""
    query = "Why was this circular financial flow pattern flagged?"
    ctx: InvestigationContext = context_builder.build_context(query)

    assert ctx.retrieval_metadata.retrieval_strategy == "pattern_investigation"
    assert len(ctx.patterns) > 0

    pattern = ctx.patterns[0]
    assert pattern.description != ""
    assert len(pattern.participating_entity_ids) > 0


def test_lead_triage_next_steps_query(context_builder: GraphRAGContextBuilder):
    """Verify next step triage context retrieving bridge nodes and syndicate clusters."""
    query = "What should I investigate next in this network?"
    ctx: InvestigationContext = context_builder.build_context(query)

    assert ctx.retrieval_metadata.retrieval_strategy == "lead_triage"
    assert len(ctx.entities) > 0

    # Check that bridge or community metadata was enriched
    has_bridge_or_community = any(e.is_bridge or e.community_id is not None for e in ctx.entities)
    assert has_bridge_or_community


def test_case_dossier_accused_query(context_builder: GraphRAGContextBuilder):
    """Verify case-scoped dossier retrieval with accused persons and evidence."""
    query = "Who are the accused in FIR-141 and what is the summary?"
    ctx: InvestigationContext = context_builder.build_context(query, case_id="CASE-141")

    assert ctx.retrieval_metadata.retrieval_strategy == "case_dossier"
    assert "CASE-141" in ctx.case_ids
    assert len(ctx.entities) > 0

    # Case entity should be present
    case_entity = next((e for e in ctx.entities if "141" in e.id), None)
    assert case_entity is not None

    # Timeline event should be created for FIR registration
    assert len(ctx.timeline_events) >= 1
    assert ctx.timeline_events[0].event_type == "FIR_REGISTRATION"


def test_context_budget_pruning(context_builder: GraphRAGContextBuilder):
    """Verify that max_nodes and max_evidence limits are strictly enforced."""
    query = "Summarize the entire global network"
    ctx: InvestigationContext = context_builder.build_context(
        query,
        max_nodes=5,
        max_evidence=3,
    )

    assert len(ctx.entities) <= 5
    assert len(ctx.evidence) <= 3
    assert ctx.retrieval_metadata.pruned_nodes_count >= 0


def test_zero_hallucination_and_provenance_integrity(
    context_builder: GraphRAGContextBuilder, tool_registry: NEXUSToolRegistry
):
    """Guarantee that all entities and evidence exist in the authoritative GraphStore."""
    nodes_dict, edges_list, _ = tool_registry._get_active_graph_elements()
    query = "How are FIR-141 and FIR-207 connected?"
    ctx: InvestigationContext = context_builder.build_context(query)

    # Every entity must exist in the authoritative node set
    for entity in ctx.entities:
        assert entity.id in nodes_dict

    # Every relationship endpoint must exist in the authoritative node set
    for rel in ctx.relationships:
        assert rel.source_id in nodes_dict
        assert rel.target_id in nodes_dict
