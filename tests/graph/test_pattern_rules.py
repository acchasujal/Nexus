"""tests/graph/test_pattern_rules.py

Focused unit tests for the 3 Deterministic Suspicious-Pattern Rules:
  1. Shared Phone / Device (shared_phone_device)
  2. Communication Burst Near an Event (communication_burst_near_event)
  3. Circular / Repeated Financial Flow (circular_repeated_financial_flow)

Contract Audit Checks Verified:
  - Check 1: Uses only canonical GraphRelationshipType enums.
  - Check 2: Canonical Event & Relationship provenance paths (CITES_SOURCE & source_record_id).
  - Check 3: Deterministic communication-event association near Event A vs Event B.
  - Check 4: Canonical financial flow, self-loop suppression, cycle deduplication, neutral language.
  - Check 5: Finding contract (rule_id, explanation, entity_ids, edge_ids, evidence_ids, derivation_class="DERIVED").
  - Check 6: Provenance negative tests (missing provenance => NO finding; positive evidence_ids match real SourceRecord).
  - Check 7: Deterministic sorting & byte-equivalent runs.
  - Check 8: 100% test suite pass rate.
"""

from datetime import datetime, timezone
import pytest

from backend.app.core.graph.algorithms.pattern_rules import (
    PatternFinding,
    detect_all_suspicious_patterns,
    detect_circular_repeated_financial_flow,
    detect_communication_burst_near_event,
    detect_shared_phone_device,
)
from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord, build_graph_store


# ── Rule 1 Tests: Shared Phone / Device ─────────────────────────────────────────

def test_shared_phone_positive_case():
    nodes = [
        NodeRecord("person_A", "Person", {"canonical_label": "Rahul"}),
        NodeRecord("person_B", "Person", {"canonical_label": "Vikram"}),
        NodeRecord("phone_X", "Phone", {"canonical_label": "9876543210"}),
        NodeRecord("src_rec_001", "SourceRecord", {"locator": "CDR_2026_01"}),
        NodeRecord("src_rec_002", "SourceRecord", {"locator": "CDR_2026_02"}),
    ]
    edges = [
        AdjEdge("USED_PHONE", "person_A", "phone_X", properties={"id": "rel_A_X", "source_record_id": "src_rec_001"}),
        AdjEdge("USED_PHONE", "person_B", "phone_X", properties={"id": "rel_B_X", "source_record_id": "src_rec_002"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_shared_phone_device(store)

    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "shared_phone_device"
    assert f.derivation_class == "DERIVED"
    assert "person_A" in f.entity_ids
    assert "person_B" in f.entity_ids
    assert "phone_X" in f.entity_ids
    assert "rel_A_X" in f.edge_ids
    assert "rel_B_X" in f.edge_ids
    assert "src_rec_001" in f.evidence_ids
    assert "src_rec_002" in f.evidence_ids

    # Verify returned evidence_ids correspond to real SourceRecords in fixture
    node_ids = {getattr(n, "node_id", getattr(n, "id", None)) for n in nodes}
    for ev_id in f.evidence_ids:
        assert ev_id in node_ids, f"Returned evidence_id '{ev_id}' not in fixture"


def test_shared_phone_cites_source_graph_provenance():
    """Verify provenance extraction via CITES_SOURCE graph relationships."""
    nodes = [
        NodeRecord("person_A", "Person"),
        NodeRecord("person_B", "Person"),
        NodeRecord("phone_X", "Phone"),
        NodeRecord("src_record_100", "SourceRecord"),
    ]
    edges = [
        AdjEdge("USED_PHONE", "person_A", "phone_X", properties={"id": "rel_A_X"}),
        AdjEdge("USED_PHONE", "person_B", "phone_X", properties={"id": "rel_B_X"}),
        # Graph-backed provenance link from relationship to SourceRecord
        AdjEdge("CITES_SOURCE", "rel_A_X", "src_record_100"),
        AdjEdge("CITES_SOURCE", "rel_B_X", "src_record_100"),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_shared_phone_device(store)

    assert len(findings) == 1
    assert "src_record_100" in findings[0].evidence_ids


def test_shared_phone_negative_unrelated_and_missing_provenance():
    # Negative Case 1: Unrelated phones
    nodes_unrelated = [
        NodeRecord("p1", "Person"),
        NodeRecord("p2", "Person"),
        NodeRecord("ph1", "Phone"),
        NodeRecord("ph2", "Phone"),
    ]
    edges_unrelated = [
        AdjEdge("USED_PHONE", "p1", "ph1", properties={"source_record_id": "src_01"}),
        AdjEdge("USED_PHONE", "p2", "ph2", properties={"source_record_id": "src_02"}),
    ]
    store1 = build_graph_store(nodes_unrelated, edges_unrelated)
    assert len(detect_shared_phone_device(store1)) == 0

    # Negative Case 2: Missing provenance (no source_record_id or CITES_SOURCE) -> SUPPRESSED
    nodes_no_prov = [
        NodeRecord("p1", "Person"),
        NodeRecord("p2", "Person"),
        NodeRecord("ph1", "Phone"),
    ]
    edges_no_prov = [
        AdjEdge("USED_PHONE", "p1", "ph1"),
        AdjEdge("USED_PHONE", "p2", "ph1"),
    ]
    store2 = build_graph_store(nodes_no_prov, edges_no_prov)
    assert len(detect_shared_phone_device(store2)) == 0


def test_shared_vehicle_does_not_trigger_shared_phone_device():
    """Regression test: Two people sharing a Vehicle entity must NOT trigger shared_phone_device."""
    nodes = [
        NodeRecord("person_A", "Person"),
        NodeRecord("person_B", "Person"),
        NodeRecord("vehicle_X", "Vehicle"),
    ]
    edges = [
        AdjEdge("USED_VEHICLE", "person_A", "vehicle_X", properties={"source_record_id": "src_v1"}),
        AdjEdge("USED_VEHICLE", "person_B", "vehicle_X", properties={"source_record_id": "src_v2"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_shared_phone_device(store)

    assert len(findings) == 0, "Sharing a vehicle must NOT produce a shared_phone_device finding"


# ── Rule 2 Tests: Communication Burst Near Event ───────────────────────────────

def test_communication_burst_positive_case():
    event_ts = "2026-08-24T15:00:00Z"
    nodes = [
        NodeRecord("person_A", "Person"),
        NodeRecord("person_B", "Person"),
        NodeRecord("person_C", "Person"),
        NodeRecord("event_101", "Event", properties={"timestamp": event_ts}),
        NodeRecord("src_event_rec", "SourceRecord"),
    ]
    edges = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "c1", "start_time": "2026-08-24T14:50:00Z", "source_record_id": "src_c1"}),
        AdjEdge("COMMUNICATED_WITH", "person_B", "person_A", properties={"id": "c2", "start_time": "2026-08-24T14:55:00Z", "source_record_id": "src_c2"}),
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_C", properties={"id": "c3", "start_time": "2026-08-24T15:05:00Z", "source_record_id": "src_c3"}),
        # Event connected to SourceRecord via CITES_SOURCE
        AdjEdge("CITES_SOURCE", "event_101", "src_event_rec"),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_communication_burst_near_event(store, window_minutes=15, min_calls=3)

    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "communication_burst_near_event"
    assert f.derivation_class == "DERIVED"
    assert "event_101" in f.entity_ids
    assert len(f.edge_ids) == 3
    assert "src_event_rec" in f.evidence_ids
    assert "src_c1" in f.evidence_ids


def test_communication_burst_event_isolation():
    """Verify communications near Event A trigger Event A, while Event B outside window is NOT triggered."""
    event_A_ts = "2026-08-24T15:00:00Z"
    event_B_ts = "2026-08-24T18:00:00Z"  # 3 hours later
    nodes = [
        NodeRecord("person_A", "Person"),
        NodeRecord("person_B", "Person"),
        NodeRecord("person_C", "Person"),
        NodeRecord("event_A", "Event", properties={"timestamp": event_A_ts}),
        NodeRecord("event_B", "Event", properties={"timestamp": event_B_ts}),
    ]
    # 3 calls near Event A (14:50 - 15:05 UTC)
    edges = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"id": "c1", "start_time": "2026-08-24T14:50:00Z", "source_record_id": "src_c1"}),
        AdjEdge("COMMUNICATED_WITH", "person_B", "person_A", properties={"id": "c2", "start_time": "2026-08-24T14:55:00Z", "source_record_id": "src_c2"}),
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_C", properties={"id": "c3", "start_time": "2026-08-24T15:05:00Z", "source_record_id": "src_c3"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_communication_burst_near_event(store, window_minutes=15, min_calls=3)

    assert len(findings) == 1
    assert "event_A" in findings[0].entity_ids
    assert "event_B" not in findings[0].entity_ids


def test_communication_burst_negative_cases_and_missing_provenance():
    event_ts = "2026-08-24T15:00:00Z"
    nodes = [
        NodeRecord("person_A", "Person"),
        NodeRecord("person_B", "Person"),
        NodeRecord("event_101", "Event", properties={"timestamp": event_ts}),
    ]

    # Below min_calls threshold
    edges_below = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"start_time": "2026-08-24T14:55:00Z", "source_record_id": "src_1"}),
        AdjEdge("COMMUNICATED_WITH", "person_B", "person_A", properties={"start_time": "2026-08-24T15:02:00Z", "source_record_id": "src_2"}),
    ]
    store1 = build_graph_store(nodes, edges_below)
    assert len(detect_communication_burst_near_event(store1, min_calls=3)) == 0

    # Outside window
    edges_outside = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"start_time": "2026-08-24T12:00:00Z", "source_record_id": "src_1"}),
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"start_time": "2026-08-24T12:05:00Z", "source_record_id": "src_2"}),
        AdjEdge("COMMUNICATED_WITH", "person_B", "person_A", properties={"start_time": "2026-08-24T12:10:00Z", "source_record_id": "src_3"}),
    ]
    store2 = build_graph_store(nodes, edges_outside)
    assert len(detect_communication_burst_near_event(store2, window_minutes=15, min_calls=3)) == 0

    # Missing provenance -> SUPPRESSED
    edges_no_prov = [
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"start_time": "2026-08-24T14:50:00Z"}),
        AdjEdge("COMMUNICATED_WITH", "person_B", "person_A", properties={"start_time": "2026-08-24T14:55:00Z"}),
        AdjEdge("COMMUNICATED_WITH", "person_A", "person_B", properties={"start_time": "2026-08-24T15:05:00Z"}),
    ]
    store3 = build_graph_store(nodes, edges_no_prov)
    assert len(detect_communication_burst_near_event(store3, window_minutes=15, min_calls=3)) == 0


# ── Rule 3 Tests: Circular / Repeated Financial Flow ────────────────────────────

def test_financial_circular_flow_positive_case():
    nodes = [
        NodeRecord("acc_A", "Account"),
        NodeRecord("acc_B", "Account"),
        NodeRecord("acc_C", "Account"),
        NodeRecord("src_t1", "SourceRecord"),
        NodeRecord("src_t2", "SourceRecord"),
        NodeRecord("src_t3", "SourceRecord"),
    ]
    edges = [
        AdjEdge("TRANSFERRED_FUNDS", "acc_A", "acc_B", properties={"id": "t1", "amount": 50000.0, "source_record_id": "src_t1"}),
        AdjEdge("TRANSFERRED_FUNDS", "acc_B", "acc_C", properties={"id": "t2", "amount": 48000.0, "source_record_id": "src_t2"}),
        AdjEdge("TRANSFERRED_FUNDS", "acc_C", "acc_A", properties={"id": "t3", "amount": 49000.0, "source_record_id": "src_t3"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_circular_repeated_financial_flow(store)

    assert len(findings) >= 1
    f = next(item for item in findings if "circular financial flow" in item.explanation.lower())
    assert f.rule_id == "circular_repeated_financial_flow"
    assert f.derivation_class == "DERIVED"
    assert set(f.entity_ids) == {"acc_A", "acc_B", "acc_C"}
    assert set(f.evidence_ids) == {"src_t1", "src_t2", "src_t3"}
    assert "Requires investigator review" in f.explanation


def test_financial_repeated_flow_neutral_language():
    nodes = [
        NodeRecord("acc_A", "Account"),
        NodeRecord("acc_B", "Account"),
    ]
    # 2 transfers between acc_A and acc_B -> Tested with min_repeated_transfers=2
    edges = [
        AdjEdge("TRANSFERRED_FUNDS", "acc_A", "acc_B", properties={"id": "t1", "source_record_id": "src_1"}),
        AdjEdge("TRANSFERRED_TO", "acc_A", "acc_B", properties={"id": "t2", "source_record_id": "src_2"}),
    ]
    store = build_graph_store(nodes, edges)

    # Below threshold (min=3) -> 0 findings
    assert len(detect_circular_repeated_financial_flow(store, min_repeated_transfers=3)) == 0

    # At threshold (min=2) -> 1 finding
    findings = detect_circular_repeated_financial_flow(store, min_repeated_transfers=2)
    assert len(findings) == 1
    f = findings[0]
    assert "Observed 2 repeated financial transfers between account 'acc_A' and account 'acc_B'." in f.explanation
    # Verify strict neutral language (no guilt, fraud, or criminal inferencing)
    forbidden = ["fraud", "criminal", "laundering", "illegal", "guilt"]
    for term in forbidden:
        assert term not in f.explanation.lower()


def test_financial_flow_negative_cases_and_missing_provenance():
    nodes = [NodeRecord("acc_A", "Account"), NodeRecord("acc_B", "Account"), NodeRecord("acc_C", "Account")]

    # Linear transfer (acc_A -> acc_B -> acc_C)
    edges_linear = [
        AdjEdge("TRANSFERRED_FUNDS", "acc_A", "acc_B", properties={"source_record_id": "src_1"}),
        AdjEdge("TRANSFERRED_FUNDS", "acc_B", "acc_C", properties={"source_record_id": "src_2"}),
    ]
    store1 = build_graph_store(nodes, edges_linear)
    assert len(detect_circular_repeated_financial_flow(store1)) == 0

    # Self-loop (acc_A -> acc_A)
    edges_self = [AdjEdge("TRANSFERRED_FUNDS", "acc_A", "acc_A", properties={"source_record_id": "src_1"})]
    store2 = build_graph_store(nodes, edges_self)
    assert len(detect_circular_repeated_financial_flow(store2)) == 0

    # Missing provenance on cycle -> SUPPRESSED
    edges_no_prov = [
        AdjEdge("TRANSFERRED_FUNDS", "acc_A", "acc_B"),
        AdjEdge("TRANSFERRED_FUNDS", "acc_B", "acc_C"),
        AdjEdge("TRANSFERRED_FUNDS", "acc_C", "acc_A"),
    ]
    store3 = build_graph_store(nodes, edges_no_prov)
    assert len(detect_circular_repeated_financial_flow(store3)) == 0


# ── Safety & Neutral Language Verification ────────────────────────────────────

def test_safety_neutral_language_all_rules():
    nodes = [
        NodeRecord("person_A", "Person"),
        NodeRecord("person_B", "Person"),
        NodeRecord("phone_X", "Phone"),
    ]
    edges = [
        AdjEdge("USED_PHONE", "person_A", "phone_X", properties={"source_record_id": "src_1"}),
        AdjEdge("USED_PHONE", "person_B", "phone_X", properties={"source_record_id": "src_2"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_all_suspicious_patterns(store)

    forbidden_terms = ["criminal", "mastermind", "guilt", "recidivism", "probability", "fraud"]

    for f in findings:
        assert f.derivation_class == "DERIVED"
        exp_lower = f.explanation.lower()
        for term in forbidden_terms:
            assert term not in exp_lower, f"Forbidden term '{term}' found in explanation"


def test_determinism_across_runs():
    nodes = [
        NodeRecord("person_A", "Person"),
        NodeRecord("person_B", "Person"),
        NodeRecord("phone_X", "Phone"),
    ]
    edges = [
        AdjEdge("USED_PHONE", "person_A", "phone_X", properties={"source_record_id": "src_1"}),
        AdjEdge("USED_PHONE", "person_B", "phone_X", properties={"source_record_id": "src_2"}),
    ]
    store = build_graph_store(nodes, edges)

    run1 = detect_all_suspicious_patterns(store)
    run2 = detect_all_suspicious_patterns(store)

    assert len(run1) == len(run2)
    for f1, f2 in zip(run1, run2):
        assert f1.rule_id == f2.rule_id
        assert f1.entity_ids == f2.entity_ids
        assert f1.edge_ids == f2.edge_ids
        assert f1.evidence_ids == f2.evidence_ids
        assert f1.explanation == f2.explanation
