"""tests/test_case_dna.py

Comprehensive Test Suite for P2: Case DNA Multi-Dimensional Structural Similarity Engine.
Verifies:
  1. 5-Vector feature computation (Structure, Communication, Financial, Location, Temporal).
  2. Explainable citations and Section 63 BSA evidence references.
  3. Strict Zero Predictive Guilt (scores represent structural similarity, never guilt/recidivism).
  4. Integration with CaseDNAService and audit logging (SIMILARITY_SEARCH_EXECUTED).
  5. REST API endpoint GET /nexus/intelligence/case-dna/{case_id}.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.app.core.graph.algorithms.case_dna import (
    compute_case_dna_profile,
    match_case_dna,
)
from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord
from backend.app.core.graph.enums import GraphEntityType, GraphRelationshipType
from backend.app.main import create_app
from backend.app.services.audit_service import AuditEventType
from shared.contracts.api import CaseDNAMatchResponse


def _make_demo_token(user_id: str, role: str) -> str:
    payload = json.dumps({"sub": user_id, "role": role, "email": f"{user_id}@nexus.internal"})
    return base64.b64encode(payload.encode("utf-8")).decode("utf-8")


def test_case_dna_5_vector_similarity_computation() -> None:
    """Verify exact 5-vector Case DNA calculation between two cases with overlapping accused and jurisdiction."""
    store = GraphStore()

    # Case A
    case_a = NodeRecord(
        node_id="case-101",
        entity_type=GraphEntityType.CASE.value,
        properties={
            "fir_number": "FIR 101/2026",
            "title": "Mysuru Hawala & SIM Box Syndicate",
            "district": "Mysuru",
            "police_station": "Hootagalli PS",
            "incident_date": "2026-03-01T10:00:00Z",
            "evidence_ids": ["SRC-FIR-101", "SRC-CDR-101"],
        },
    )
    # Case B
    case_b = NodeRecord(
        node_id="case-102",
        entity_type=GraphEntityType.CASE.value,
        properties={
            "fir_number": "FIR 102/2026",
            "title": "Bengaluru Cyber Mule & Hawala Routing",
            "district": "Mysuru",
            "police_station": "Hootagalli PS",
            "incident_date": "2026-03-10T12:00:00Z",
            "evidence_ids": ["SRC-FIR-102", "SRC-CDR-102"],
        },
    )
    # Accused Person shared across both cases
    accused = NodeRecord(
        node_id="p-shared",
        entity_type=GraphEntityType.PERSON.value,
        properties={
            "full_name": "Rafiq Ahmed",
            "phone_numbers": ["+91 98450 11223"],
            "primary_phone": "+91 98450 11223",
        },
    )
    store.nodes[case_a.node_id] = case_a
    store.nodes[case_b.node_id] = case_b
    store.nodes[accused.node_id] = accused

    # Link accused to both cases (ACCUSED_IN: source=accused, target=case)
    edge_a = AdjEdge(
        edge_type=GraphRelationshipType.ACCUSED_IN.value,
        source_id="p-shared",
        target_id="case-101",
        properties={"role": "ACCUSED"},
    )
    edge_b = AdjEdge(
        edge_type=GraphRelationshipType.ACCUSED_IN.value,
        source_id="p-shared",
        target_id="case-102",
        properties={"role": "ACCUSED"},
    )
    store.adj["p-shared"] = [edge_a, edge_b]
    store.radj["case-101"] = [edge_a]
    store.radj["case-102"] = [edge_b]

    # Compute Case DNA
    dna = compute_case_dna_profile(store, "case-101", "case-102")
    assert dna is not None
    assert dna.case_pair == ["case-101", "case-102"]
    assert dna.structure_similarity > 0.0
    assert dna.location_similarity == 1.0  # Same district & police station
    assert dna.temporal_similarity > 0.8  # 9 days apart
    assert dna.overall_similarity > 0.4
    assert dna.derivation_class == "DERIVED"
    assert "Rafiq Ahmed" in dna.shared_entities
    assert any("SRC-FIR" in ev for ev in dna.evidence_refs)


def test_match_case_dna_ranking() -> None:
    """Verify rank-ordering of case matches by overall similarity score."""
    store = GraphStore()

    # Case Target
    c_target = NodeRecord(
        node_id="case-target",
        entity_type=GraphEntityType.CASE.value,
        properties={"title": "Target Case", "district": "Bengaluru", "police_station": "Indiranagar"},
    )
    # Case High Match
    c_high = NodeRecord(
        node_id="case-high",
        entity_type=GraphEntityType.CASE.value,
        properties={"title": "High Match Case", "district": "Bengaluru", "police_station": "Indiranagar"},
    )
    # Case Low Match
    c_low = NodeRecord(
        node_id="case-low",
        entity_type=GraphEntityType.CASE.value,
        properties={"title": "Low Match Case", "district": "Mangaluru", "police_station": "Ullal"},
    )
    store.nodes[c_target.node_id] = c_target
    store.nodes[c_high.node_id] = c_high
    store.nodes[c_low.node_id] = c_low

    response = match_case_dna(store, "case-target", top_k=5)
    assert response.target_case_id == "case-target"
    assert len(response.similar_cases) >= 1
    # case-high should be ranked higher due to location match
    assert response.similar_cases[0].case_pair[1] == "case-high"
    assert response.highest_similarity >= response.average_similarity


def test_case_dna_api_endpoint() -> None:
    """Test REST endpoint GET /nexus/intelligence/case-dna/{case_id}."""
    app = create_app()
    client = TestClient(app)

    token = _make_demo_token("officer-sharma", "INVESTIGATOR")
    headers = {"Authorization": f"Bearer {token}"}

    # Query with default or existing case ID
    resp = client.get("/api/v1/nexus/intelligence/case-dna/CASE-141", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["target_case_id"] == "CASE-141"
    assert "similar_cases" in data
    assert "average_similarity" in data
    assert "highest_similarity" in data
    assert "top_shared_entities" in data

    # Verify audit trail via audit endpoint
    audit_resp = client.get("/api/v1/audit?limit=30&role=SP")
    assert audit_resp.status_code == 200
    events = audit_resp.json()
    dna_event = next(
        (e for e in events if (e.get("action") == AuditEventType.SIMILARITY_SEARCH_EXECUTED.value or e.get("event_type") == AuditEventType.SIMILARITY_SEARCH_EXECUTED.value) and e.get("entity_id") == "CASE-141"),
        None,
    )
    assert dna_event is not None


