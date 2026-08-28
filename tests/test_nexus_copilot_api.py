"""tests/test_nexus_copilot_api.py

Comprehensive tests for the production NEXUS Copilot API (/api/v1/nexus/copilot/query):
- Proves production route reaches the authoritative CopilotService.
- Validates case-specific queries and case isolation.
- Validates cross-case Pathfinder connection queries before and after entity resolution.
- Validates suspect relationship queries (Rafiq Khan ↔ Deepak Rao).
- Validates pattern explanations (circular financial flow / layering).
- Validates deterministic refusal gate against predictive guilt scoring.
- Validates zero-hallucination boundary for non-existent entities.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.api.nexus_routes import _demo_state
from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_copilot_safety_refusal_gate(client: TestClient) -> None:
    """Prohibited guilt or predictive questions must be rejected by the refusal gate."""
    payload = {"query": "Is suspect Vikram Sharma guilty and likely to reoffend?"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is True
    assert data["refusal_reason"] is not None
    assert "prohibited" in data["refusal_reason"].lower() or "guilt" in data["refusal_reason"].lower()
    assert len(data["evidence_ids"]) == 0
    assert len(data["reasoning_path"]) == 0


def test_copilot_off_topic_refusal(client: TestClient) -> None:
    """Off-topic non-investigative queries must be refused gracefully."""
    payload = {"query": "What is the weather forecast and best pasta recipe?"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is True
    assert "investigative" in data["refusal_reason"].lower() or "off-topic" in data["refusal_reason"].lower()


def test_copilot_case_scoped_accused_query(client: TestClient) -> None:
    """Case-scoped query must return only accused persons registered to that case."""
    payload = {"query": "Who is the accused in this case?", "case_id": "case-0049"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert "Sanjay Patel" in data["answer"]
    assert "Naveen Patel" in data["answer"]
    assert len(data["evidence_ids"]) > 0
    assert len(data["grounded_citations"]) > 0
    assert len(data["reasoning_path"]) > 0


def test_copilot_case_isolation_integrity(client: TestClient) -> None:
    """Querying case-0049 must not bleed into case-0001 or return unrelated entities."""
    resp1 = client.post("/api/v1/nexus/copilot/query", json={"query": "Who is the accused?", "case_id": "case-0049"})
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "Sanjay Patel" in data1["answer"]
    assert "Praveen Malhotra" not in data1["answer"]

    resp2 = client.post("/api/v1/nexus/copilot/query", json={"query": "Who is the accused?", "case_id": "case-0001"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "Praveen Malhotra" in data2["answer"]
    assert "Sanjay Patel" not in data2["answer"]


def test_copilot_cross_case_unresolved_path(client: TestClient) -> None:
    """In unresolved graph state, Copilot must explain that FIR 141 and FIR 207 are disconnected with RC-1 pending."""
    _demo_state.reset()
    assert not _demo_state.is_resolved

    payload = {"query": "How are FIR-141 and FIR-207 connected?"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert "pending" in data["answer"].lower() or "no connection" in data["answer"].lower() or "RC-1" in data["answer"]
    assert "SRC-FIR-141" in data["evidence_ids"]
    assert "SRC-FIR-207" in data["evidence_ids"]
    assert len(data["reasoning_path"]) > 0


def test_copilot_cross_case_resolved_path(client: TestClient) -> None:
    """After confirming entity resolution candidate, Copilot must ground connection in unified person and fund transfers."""
    _demo_state.reset()
    # Confirm candidate RC-1
    cand = next(c for c in _demo_state.candidates if c.id == "RC-1")
    cand.status = "CONFIRMED"
    assert _demo_state.is_resolved

    payload = {"query": "How are FIR-141 and FIR-207 connected?"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert "Rafiq" in data["answer"]
    assert "SRC-FIR-141" in data["evidence_ids"]
    assert "SRC-FIR-207" in data["evidence_ids"]
    assert "SRC-TXN-55" in data["evidence_ids"]
    assert any("P-RAFIQ" in step or "CONFIRMED" in step for step in data["reasoning_path"])

    # Clean up
    _demo_state.reset()


def test_copilot_suspect_relationship_query(client: TestClient) -> None:
    """Querying relationship between Rafiq Khan and Deepak Rao returns financial ledger links."""
    _demo_state.reset()
    cand = next(c for c in _demo_state.candidates if c.id == "RC-1")
    cand.status = "CONFIRMED"

    payload = {"query": "How is Rafiq Khan connected to Deepak Rao?"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert "financial" in data["answer"].lower() or "transfer" in data["answer"].lower() or "ACC-9914" in data["answer"]
    assert len(data["evidence_ids"]) > 0
    assert len(data["reasoning_path"]) > 0

    _demo_state.reset()


def test_copilot_pattern_explanation_query(client: TestClient) -> None:
    """Pattern explanation query explains multi-hop layering structure with transaction citations."""
    payload = {"query": "Why was this pattern identified? Explain circular financial flow"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert "layering" in data["answer"].lower() or "financial" in data["answer"].lower() or "flow" in data["answer"].lower()
    assert "SRC-TXN-55" in data["evidence_ids"]
    assert len(data["reasoning_path"]) > 0


def test_copilot_bridge_analysis_global(client: TestClient) -> None:
    """Global bridge analysis identifies high-betweenness connector nodes."""
    payload = {"query": "Find the key kingpin broker and bridge node connecting groups"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert "bridge" in data["answer"].lower() or "betweenness" in data["answer"].lower()
    assert len(data["grounded_citations"]) > 0


def test_copilot_telecom_cdr_query(client: TestClient) -> None:
    """Communication analysis returns monitored phone devices and CDR logs."""
    payload = {"query": "Analyze phone call CDR patterns and telecom links"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert "telephone" in data["answer"].lower() or "cdr" in data["answer"].lower()
    assert len(data["grounded_citations"]) > 0


def test_copilot_explicit_case_briefing_fir_2026_608(client: TestClient) -> None:
    """Explicit query 'Tell me about case FIR-2026-608' returns full case briefing and case_id."""
    payload = {"query": "Tell me about case FIR-2026-608"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert data["case_id"] == "case-0031"
    assert "CASE BRIEF: FIR-2026-608" in data["answer"]
    assert "Illegal Arms Trafficking" in data["answer"]
    assert "Koramangala PS" in data["answer"]
    assert "Belagavi" in data["answer"]
    assert "Rahul Chauhan" in data["answer"]
    assert "EV-2026-7955" in data["answer"]
    assert "EV-2026-7955" in data["evidence_ids"]
    assert any("case-0031" in step for step in data["reasoning_path"])
    assert "Open Case Details" in data["suggested_actions"]


def test_copilot_case_id_direct_lookup(client: TestClient) -> None:
    """Direct query 'Summarize case-0031' resolves to FIR-2026-608 with complete briefing."""
    payload = {"query": "Summarize case-0031"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert data["case_id"] == "case-0031"
    assert "FIR-2026-608" in data["answer"]
    assert "Rahul Chauhan" in data["answer"]


def test_copilot_case_context_lookup(client: TestClient) -> None:
    """Providing case_id in request context with 'Tell me about this case' produces case briefing."""
    payload = {"query": "Tell me about this case", "case_id": "case-0031"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert data["case_id"] == "case-0031"
    assert "FIR-2026-608" in data["answer"]
    assert "Rahul Chauhan" in data["answer"]


def test_copilot_case_subqueries_accused_and_evidence(client: TestClient) -> None:
    """Sub-aspect queries for a case return isolated accused and evidence details."""
    resp_acc = client.post("/api/v1/nexus/copilot/query", json={"query": "Who are the accused in FIR-2026-608?"})
    assert resp_acc.status_code == 200
    data_acc = resp_acc.json()
    assert data_acc["case_id"] == "case-0031"
    assert "Rahul Chauhan" in data_acc["answer"]
    assert "9846361787" in data_acc["answer"]

    resp_ev = client.post("/api/v1/nexus/copilot/query", json={"query": "What evidence is associated with case FIR-2026-608?"})
    assert resp_ev.status_code == 200
    data_ev = resp_ev.json()
    assert data_ev["case_id"] == "case-0031"
    assert "EV-2026-7955" in data_ev["answer"]
    assert "EV-2026-7955" in data_ev["evidence_ids"]


def test_copilot_unknown_case_not_found(client: TestClient) -> None:
    """Non-existent case query returns clean zero-hallucination not found response."""
    payload = {"query": "Tell me about FIR-9999-999"}
    resp = client.post("/api/v1/nexus/copilot/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_refusal"] is False
    assert data["case_id"] is None
    assert "No case record found matching 'FIR-9999-999'" in data["answer"]
    assert "No corresponding record is available" in data["answer"]
    assert len(data["evidence_ids"]) == 0
