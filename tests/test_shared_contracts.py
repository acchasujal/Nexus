"""tests/test_shared_contracts.py

Targeted verification for Phase 1: Canonical dataset_version, snapshot IDs,
and shared contract consistency across Python and TypeScript schemas.
"""

from __future__ import annotations

import json
from shared.contracts.api import (
    CANONICAL_DATASET_VERSION,
    CANONICAL_SNAPSHOT_BASELINE,
    CANONICAL_SNAPSHOT_CURRENT,
    CaseDNA,
    CaseDNAMatchResponse,
    GraphSnapshotSummary,
    IntelligenceBootstrapResponse,
    IntelligenceKPIs,
    InvestigationContext,
    NetworkDiffResponse,
    NetworkPulseItem,
    NexusGraphEdge,
    NexusGraphNode,
    NexusNetworkResponse,
    SnapshotDiffResponse,
)


def test_canonical_constants() -> None:
    """Verify canonical constants conform to the authoritative contract."""
    assert CANONICAL_DATASET_VERSION == "NCRB_CALIBRATED:v1"
    assert CANONICAL_SNAPSHOT_BASELINE == "snap-baseline-v1"
    assert CANONICAL_SNAPSHOT_CURRENT == "snap-current"


def test_graph_snapshot_summary_contract() -> None:
    """Verify GraphSnapshotSummary carries dataset_version."""
    snap = GraphSnapshotSummary(
        snapshot_id=CANONICAL_SNAPSHOT_BASELINE,
        created_at="2026-08-25T10:00:00+00:00",
        node_count=42,
        edge_count=108,
    )
    assert snap.dataset_version == CANONICAL_DATASET_VERSION
    assert snap.snapshot_id == "snap-baseline-v1"
    payload = json.loads(snap.model_dump_json())
    assert payload["dataset_version"] == "NCRB_CALIBRATED:v1"


def test_network_diff_response_contract() -> None:
    """Verify NetworkDiffResponse carries dataset_version."""
    diff = NetworkDiffResponse(
        before_snapshot_id=CANONICAL_SNAPSHOT_BASELINE,
        after_snapshot_id=CANONICAL_SNAPSHOT_CURRENT,
        added_nodes=["person-0002"],
        added_relationships=["E-BRIDGE-01"],
    )
    assert diff.dataset_version == CANONICAL_DATASET_VERSION
    assert diff.before_snapshot_id == "snap-baseline-v1"
    assert diff.after_snapshot_id == "snap-current"


def test_nexus_network_response_contract() -> None:
    """Verify NexusNetworkResponse uses canonical IDs and dataset_version."""
    node = NexusGraphNode(
        id="person-0001",
        entity_type="Person",
        label="Test Person",
        case_ids=["CASE-141"],
    )
    edge = NexusGraphEdge(
        id="rel-0001",
        source_id="person-0001",
        target_id="person-0002",
        edge_type="ASSOCIATED_WITH",
        case_ids=["CASE-141"],
    )
    net = NexusNetworkResponse(
        snapshot_id=CANONICAL_SNAPSHOT_CURRENT,
        state="after",
        nodes=[node],
        edges=[edge],
        total_nodes=1,
        total_edges=1,
    )
    assert net.snapshot_id == "snap-current"
    assert net.dataset_version == CANONICAL_DATASET_VERSION
    dump = json.loads(net.model_dump_json())
    assert dump["dataset_version"] == "NCRB_CALIBRATED:v1"
    assert dump["nodes"][0]["id"] == "person-0001"


def test_snapshot_diff_response_contract() -> None:
    """Verify SnapshotDiffResponse uses canonical snapshot IDs."""
    sd = SnapshotDiffResponse(
        before_snapshot_id=CANONICAL_SNAPSHOT_BASELINE,
        after_snapshot_id=CANONICAL_SNAPSHOT_CURRENT,
        added_node_ids=["node-01"],
        added_edge_ids=["edge-01"],
    )
    assert sd.before_snapshot_id == "snap-baseline-v1"
    assert sd.after_snapshot_id == "snap-current"
    assert sd.dataset_version == CANONICAL_DATASET_VERSION


def test_case_dna_contract() -> None:
    """Verify CaseDNA models carry dataset_version."""
    cdna = CaseDNA(
        case_pair=["CASE-141", "CASE-207"],
        case_a_title="Case 141",
        case_b_title="Case 207",
        overall_similarity=0.88,
        structure_similarity=0.85,
        communication_similarity=0.90,
        financial_similarity=0.80,
        location_similarity=0.95,
        temporal_similarity=0.90,
        shared_entities=["P-RAFIQ-K"],
        explanation="High structural similarity across telecom and hawala conduits.",
    )
    assert cdna.dataset_version == CANONICAL_DATASET_VERSION
    assert cdna.snapshot_id == CANONICAL_SNAPSHOT_CURRENT

    match_res = CaseDNAMatchResponse(
        target_case_id="CASE-141",
        similar_cases=[cdna],
        average_similarity=0.88,
        highest_similarity=0.88,
        top_shared_entities=["P-RAFIQ-K"],
    )
    assert match_res.dataset_version == CANONICAL_DATASET_VERSION


def test_intelligence_bootstrap_contract() -> None:
    """Verify IntelligenceBootstrapResponse serialization and structure."""
    kpis = IntelligenceKPIs(
        active_pulses_count=3,
        critical_pulses_count=1,
        evidence_percent=94,
        supported_claims=16,
        total_claims=17,
        affected_cases_count=4,
        added_nodes=5,
        added_edges=8,
        total_changes=13,
    )
    pulse = NetworkPulseItem(
        pulse_id="pulse-001",
        signal_headline="Conduit Emergence",
        affected_cases=["CASE-141", "CASE-207"],
        affected_entities=["person-0002"],
    )
    bootstrap = IntelligenceBootstrapResponse(
        dataset_version=CANONICAL_DATASET_VERSION,
        snapshot_id=CANONICAL_SNAPSHOT_CURRENT,
        baseline_snapshot_id=CANONICAL_SNAPSHOT_BASELINE,
        kpis=kpis,
        primary_pulse=pulse,
        affected_cases=["CASE-141", "CASE-207"],
    )
    payload = json.loads(bootstrap.model_dump_json())
    assert payload["dataset_version"] == "NCRB_CALIBRATED:v1"
    assert payload["snapshot_id"] == "snap-current"
    assert payload["kpis"]["active_pulses_count"] == 3
    assert payload["kpis"]["total_changes"] == 13
    assert payload["primary_pulse"]["pulse_id"] == "pulse-001"


def test_investigation_context_contract() -> None:
    """Verify InvestigationContext round-tripping."""
    ctx = InvestigationContext(
        case_id="CASE-141",
        target_case_id="CASE-207",
        entity_id="person-0002",
        change_id="change-001",
        snapshot_id=CANONICAL_SNAPSHOT_CURRENT,
        focus="crosscase",
        drawer="entity",
    )
    dump = json.loads(ctx.model_dump_json())
    assert dump["case_id"] == "CASE-141"
    assert dump["target_case_id"] == "CASE-207"
    assert dump["focus"] == "crosscase"
    assert dump["drawer"] == "entity"
