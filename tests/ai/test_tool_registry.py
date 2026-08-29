"""tests/ai/test_tool_registry.py

Unit tests for NEXUSToolRegistry deterministic tools.
Validates structured output, machine-readable contracts, and citation generation.
"""

import pytest

from backend.app.ai.tools import NEXUSToolRegistry
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditService


@pytest.fixture
def repo():
    return InMemoryBackendRepository()


@pytest.fixture
def audit_svc(repo):
    return AuditService(repo)


@pytest.fixture
def registry(repo, audit_svc):
    return NEXUSToolRegistry(repo, audit_svc)


def test_tool_declarations_schema(registry):
    decls = registry.get_tool_declarations()
    assert len(decls) == 10
    tool_names = {d["function"]["name"] for d in decls}
    expected = {
        "find_shortest_path",
        "resolve_person_identity",
        "get_case_dossier",
        "list_cases",
        "detect_bridge_brokers",
        "detect_communities",
        "detect_financial_layering",
        "analyze_cdr_bursts",
        "get_evidence_provenance",
        "get_cross_case_connections",
    }
    assert tool_names == expected


def test_find_shortest_path_tool(registry):
    res = registry.execute("find_shortest_path", {"source_id": "CASE-141", "target_id": "CASE-207"})
    assert res.success is True
    assert res.tool_name == "find_shortest_path"
    assert isinstance(res.data, dict)
    assert "hops" in res.data
    assert isinstance(res.evidence_ids, list)
    assert isinstance(res.citations, list)
    assert isinstance(res.reasoning_path, list)


def test_resolve_person_identity_tool(registry):
    res = registry.execute(
        "resolve_person_identity",
        {"full_name": "Rafiq Khan", "phone_number": "9845011223"},
    )
    assert res.success is True
    assert res.tool_name == "resolve_person_identity"
    assert "matches" in res.data
    assert len(res.citations) >= 0


def test_get_case_dossier_tool(registry):
    res = registry.execute("get_case_dossier", {"case_id": "CASE-141"})
    assert res.success is True
    assert res.tool_name == "get_case_dossier"
    assert "FIR 141" in res.data["fir_number"]
    assert len(res.citations) > 0
    assert len(res.evidence_ids) > 0
    assert "CASE-141" in res.case_ids


def test_get_case_dossier_not_found(registry):
    res = registry.execute("get_case_dossier", {"case_id": "NON_EXISTENT_CASE_9999"})
    assert res.success is False
    assert "not found" in (res.error or "")


def test_detect_bridge_brokers_tool(registry):
    res = registry.execute("detect_bridge_brokers", {})
    assert res.success is True
    assert res.tool_name == "detect_bridge_brokers"
    assert "bridges" in res.data
    assert "GRAPH-CENTRALITY-BETWEENNESS" in res.evidence_ids


def test_detect_communities_tool(registry):
    res = registry.execute("detect_communities", {"resolution_state": "after"})
    assert res.success is True
    assert res.tool_name == "detect_communities"
    assert "communities" in res.data
    assert "GRAPH-LOUVAIN-COMMUNITIES" in res.evidence_ids


def test_detect_financial_layering_tool(registry):
    res = registry.execute("detect_financial_layering", {})
    assert res.success is True
    assert res.tool_name == "detect_financial_layering"
    assert "findings" in res.data


def test_analyze_cdr_bursts_tool(registry):
    res = registry.execute("analyze_cdr_bursts", {})
    assert res.success is True
    assert res.tool_name == "analyze_cdr_bursts"
    assert "phone_nodes_count" in res.data


def test_get_evidence_provenance_tool(registry):
    res = registry.execute("get_evidence_provenance", {})
    assert res.success is True
    assert res.tool_name == "get_evidence_provenance"
    assert "evidence_records" in res.data


def test_get_cross_case_connections_tool(registry):
    res = registry.execute("get_cross_case_connections", {"case_id_a": "CASE-141", "case_id_b": "CASE-207"})
    assert res.success is True
    assert res.tool_name == "find_shortest_path"


def test_unknown_tool(registry):
    res = registry.execute("non_existent_tool", {})
    assert res.success is False
    assert "Unknown tool" in (res.error or "")
