"""tests/test_proactive_intelligence.py

Comprehensive tests for the NEXUS Proactive Network Change Intelligence plane (P0):
  - Snapshots & Diff Service
  - Network Pulse significance filtering (review priority without guilt)
  - Evidence Assessment (SUPPORTS, CONFLICTS, MISSING)
  - Constrained Early Warning & Mandatory Abstention
  - Next Best Verification Suggestions
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.core.graph.algorithms.utils import AdjEdge, NodeRecord, build_graph_store
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.main import app
from backend.app.services.proactive_intelligence_service import ProactiveIntelligenceService
from shared.contracts.api import EpistemicState, ForecastTarget, ReviewPriority


@pytest.fixture
def proactive_service():
    repo = InMemoryBackendRepository()
    return ProactiveIntelligenceService(repo)


def test_snapshot_creation_and_listing(proactive_service):
    """Test point-in-time snapshot capture and listing."""
    snaps_initial = proactive_service.list_snapshots()
    assert len(snaps_initial) >= 1
    assert snaps_initial[0].snapshot_id == "snap-baseline-v1"

    new_snap = proactive_service.create_snapshot("snap-investigation-t1", case_scope="case-0001")
    assert new_snap.snapshot_id == "snap-investigation-t1"
    assert new_snap.case_scope == "case-0001"

    snaps_after = proactive_service.list_snapshots()
    assert any(s.snapshot_id == "snap-investigation-t1" for s in snaps_after)


def test_network_diff_with_expansion(proactive_service):
    """Test pure O(N+E) diff calculation between baseline and modified graph state."""
    # Seed a modified state in snapshots
    baseline_store = proactive_service.get_snapshot_store("snap-baseline-v1")
    assert baseline_store is not None

    # Construct modified store with 2 added nodes and 1 added edge
    nodes_t2 = list(baseline_store.nodes.values()) + [
        NodeRecord("person-new-1", "Person", {"full_name": "New Suspect"}),
        NodeRecord("phone-new-1", "Phone", {"phone_number": "9988776655"}),
    ]
    edges_t2 = [
        AdjEdge("USES_PHONE", "person-new-1", "phone-new-1", properties={"id": "rel_new_1"}),
    ]
    for etype, edge_list in baseline_store.edge_index.items():
        edges_t2.extend(edge_list)

    modified_store = build_graph_store(nodes_t2, edges_t2)
    proactive_service._snapshots["snap-t2"] = {
        "snapshot_id": "snap-t2",
        "case_scope": "GLOBAL",
        "created_at": "2026-09-17T01:00:00Z",
        "store": modified_store,
        "node_count": len(modified_store.nodes),
        "edge_count": len(edges_t2),
        "version": "v1.1",
    }

    diff_res = proactive_service.compute_network_diff("snap-baseline-v1", "snap-t2")
    assert "person-new-1" in diff_res.added_nodes
    assert "phone-new-1" in diff_res.added_nodes
    assert len(diff_res.added_relationships) >= 1
    assert len(diff_res.pulses) >= 1


def test_pulse_evidence_and_early_warning_structure(proactive_service):
    """Test that NetworkPulse contains evidence assessment, forecast, and verification."""
    pulses = proactive_service.list_active_pulses()
    assert len(pulses) >= 1
    p = pulses[0]

    # Check Review Priority compliance (No guilt / dangerousness scores)
    assert p.review_priority in [ReviewPriority.CRITICAL_REVIEW, ReviewPriority.PRIORITY_REVIEW, ReviewPriority.ROUTINE_REVIEW]
    assert 0.0 <= p.support_level <= 1.0
    assert 0.0 <= p.uncertainty <= 1.0

    # Evidence Assessment check
    assert len(p.assessment) >= 1
    claim = p.assessment[0]
    assert claim.state in [EpistemicState.SUPPORTS, EpistemicState.CONFLICTS, EpistemicState.MISSING, EpistemicState.INFERRED, EpistemicState.VERIFIED]
    assert len(claim.rationale) > 5

    # Early Warning & Constrained Forecast check
    assert p.forecast is not None
    assert p.forecast.target_state in [
        ForecastTarget.JURISDICTION_SHIFT,
        ForecastTarget.COMMUNICATION_PATTERN_SHIFT,
        ForecastTarget.FINANCIAL_ROUTE_TRANSITION,
        ForecastTarget.IDENTIFIER_DRIFT,
        ForecastTarget.NETWORK_RESTRUCTURING,
    ]

    # Verification Planner check
    assert len(p.verification_plan) >= 1
    v = p.verification_plan[0]
    assert len(v.recommended_action) > 5
    assert v.status == "PENDING"


def test_mandatory_abstention_gate(proactive_service):
    """Test that sparse/contradictory telemetry triggers mandatory abstention."""
    # Create empty graph vs store with lone disconnected node
    store_empty = build_graph_store([], [])
    store_sparse = build_graph_store([NodeRecord("p-isolated", "Person", {})], [])

    raw_diff = proactive_service.compute_network_diff.__wrapped__(
        proactive_service, "empty", "sparse"
    ) if hasattr(proactive_service.compute_network_diff, "__wrapped__") else None

    # Directly test filtering logic on sparse diff
    proactive_service._snapshots["snap-empty"] = {"store": store_empty, "snapshot_id": "snap-empty", "case_scope": "GLOBAL", "created_at": "", "node_count": 0, "edge_count": 0, "version": "v1"}
    proactive_service._snapshots["snap-sparse"] = {"store": store_sparse, "snapshot_id": "snap-sparse", "case_scope": "GLOBAL", "created_at": "", "node_count": 1, "edge_count": 0, "version": "v1"}

    diff_res = proactive_service.compute_network_diff("snap-empty", "snap-sparse")
    abstained_pulses = [p for p in diff_res.pulses if p.abstained]
    assert len(abstained_pulses) >= 1
    ab_pulse = abstained_pulses[0]
    assert ab_pulse.forecast is not None
    assert ab_pulse.forecast.abstained is True
    assert "INSUFFICIENT EVIDENCE / NO FORECAST" in (ab_pulse.forecast.abstention_reason or "")


def test_api_proactive_intelligence_endpoints():
    """Test FastAPI endpoints for Snapshots, Diff, and Pulses."""
    client = TestClient(app)

    # 1. Snapshots API
    res_snaps = client.get("/api/v1/nexus/snapshots")
    assert res_snaps.status_code == 200
    snaps = res_snaps.json()
    assert isinstance(snaps, list)
    assert len(snaps) >= 1

    # 2. Diff API
    res_diff = client.get("/api/v1/nexus/diff?before=snap-baseline-v1&after=snap-baseline-v1")
    assert res_diff.status_code == 200
    diff_data = res_diff.json()
    assert "added_nodes" in diff_data
    assert "summary" in diff_data

    # 3. Pulses API
    res_pulses = client.get("/api/v1/nexus/pulses")
    assert res_pulses.status_code == 200
    pulses = res_pulses.json()
    assert isinstance(pulses, list)
    assert len(pulses) >= 1
    p0 = pulses[0]
    assert "pulse_id" in p0
    assert "review_priority" in p0
    assert "assessment" in p0
    assert "forecast" in p0
    assert "verification_plan" in p0
