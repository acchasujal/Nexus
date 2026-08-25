"""tests/graph/test_cross_case.py

Focused unit test suite for Cross-Case Bridge Detection (detect_cross_case_bridges).

Golden Test Coverage (Check 8):
  A. Person cross-case bridge (test_cross_case_person_bridge_positive_golden_fixture)
  B. Non-person cross-case bridge (test_cross_case_non_person_entity_types_positive)
  C. Single-case negative (test_cross_case_single_case_association_negative)
  D. Same-label/different-ID negative (test_cross_case_distinct_entity_ids_no_merge)
  E. Missing-provenance negative (test_cross_case_missing_provenance_suppressed_negative)
  F. Three-case aggregation (test_cross_case_three_cases_aggregation_deduplication)
  G. Duplicate relationship deduplication (test_cross_case_duplicate_relationship_deduplication)
  H. Invalid/non-case relationship negative (test_cross_case_invalid_non_case_relationship_negative)
"""


from backend.app.core.graph.algorithms.cross_case import detect_cross_case_bridges
from backend.app.core.graph.algorithms.utils import (
    AdjEdge,
    NodeRecord,
    build_graph_store,
)

# ── Golden Test A: Person Cross-Case Bridge ──────────────────────────────────

def test_cross_case_person_bridge_positive_golden_fixture():
    """Golden Test A: Person X connected to Case A and Case B with source-backed evidence."""
    nodes = [
        NodeRecord("case_A", "Case", properties={"fir_number": "FIR_100_2026"}),
        NodeRecord("case_B", "Case", properties={"fir_number": "FIR_200_2026"}),
        NodeRecord("person_X", "Person", {"canonical_label": "Rahul Sharma"}),
        NodeRecord("person_Y", "Person", {"canonical_label": "Sujal"}),  # Single case person
        NodeRecord("src_A", "SourceRecord"),
        NodeRecord("src_B", "SourceRecord"),
        NodeRecord("src_C", "SourceRecord"),
    ]
    edges = [
        AdjEdge("ACCUSED_IN", "person_X", "case_A", properties={"id": "r1", "source_record_id": "src_A"}),
        AdjEdge("INVOLVED_IN", "person_X", "case_B", properties={"id": "r2", "source_record_id": "src_B"}),
        AdjEdge("ACCUSED_IN", "person_Y", "case_A", properties={"id": "r3", "source_record_id": "src_C"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_cross_case_bridges(store)

    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "cross_case_bridge"
    assert f.derivation_class == "DERIVED"
    assert f.entity_ids == ["person_X"]
    assert set(f.case_ids) == {"case_A", "case_B"}
    assert set(f.edge_ids) == {"r1", "r2"}
    assert set(f.evidence_ids) == {"src_A", "src_B"}
    assert "Rahul Sharma" in f.explanation
    assert "creating a cross-case bridge" in f.explanation


# ── Golden Test B: Non-Person Cross-Case Bridge ──────────────────────────────

def test_cross_case_non_person_entity_types_positive():
    """Golden Test B: Verify Phone, Account, and Vehicle cross-case bridges."""
    nodes = [
        NodeRecord("case_A", "Case"),
        NodeRecord("case_B", "Case"),
        NodeRecord("phone_100", "Phone", {"canonical_label": "9876543210"}),
        NodeRecord("account_200", "Account", {"canonical_label": "ACC9988"}),
        NodeRecord("src_1", "SourceRecord"),
        NodeRecord("src_2", "SourceRecord"),
    ]
    edges = [
        AdjEdge("INVOLVED_IN", "phone_100", "case_A", properties={"id": "e1", "source_record_id": "src_1"}),
        AdjEdge("INVOLVED_IN", "phone_100", "case_B", properties={"id": "e2", "source_record_id": "src_2"}),
        AdjEdge("INVOLVED_IN", "account_200", "case_A", properties={"id": "e3", "source_record_id": "src_1"}),
        AdjEdge("INVOLVED_IN", "account_200", "case_B", properties={"id": "e4", "source_record_id": "src_2"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_cross_case_bridges(store)

    assert len(findings) == 2
    entity_ids = {f.entity_ids[0] for f in findings}
    assert entity_ids == {"phone_100", "account_200"}


# ── Golden Test C: Single-Case Negative ──────────────────────────────────────

def test_cross_case_single_case_association_negative():
    """Golden Test C: An entity associated with only 1 case must NOT produce a finding."""
    nodes = [
        NodeRecord("case_A", "Case", properties={"fir_number": "FIR_001_2026"}),
        NodeRecord("person_X", "Person", {"canonical_label": "Vikram"}),
        NodeRecord("src_A", "SourceRecord"),
    ]
    edges = [
        AdjEdge("ACCUSED_IN", "person_X", "case_A", properties={"source_record_id": "src_A"}),
    ]
    store = build_graph_store(nodes, edges)
    assert len(detect_cross_case_bridges(store)) == 0


# ── Golden Test D: Same-Label / Different-ID Negative ────────────────────────

def test_cross_case_distinct_entity_ids_no_merge():
    """Golden Test D: Different entity IDs with identical canonical labels MUST remain separate."""
    nodes = [
        NodeRecord("case_A", "Case"),
        NodeRecord("case_B", "Case"),
        NodeRecord("person_001", "Person", {"canonical_label": "Rahul Kumar"}),
        NodeRecord("person_002", "Person", {"canonical_label": "Rahul Kumar"}),
    ]
    edges = [
        AdjEdge("ACCUSED_IN", "person_001", "case_A", properties={"source_record_id": "s1"}),
        AdjEdge("ACCUSED_IN", "person_002", "case_B", properties={"source_record_id": "s2"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_cross_case_bridges(store)

    assert len(findings) == 0, "Separate entity IDs must not be merged by label similarity"


# ── Golden Test E: Missing-Provenance Negative ────────────────────────────────

def test_cross_case_missing_provenance_suppressed_negative():
    """Golden Test E: If one case association lacks source evidence, suppress the finding."""
    nodes = [
        NodeRecord("case_A", "Case"),
        NodeRecord("case_B", "Case"),
        NodeRecord("person_X", "Person"),
    ]
    edges = [
        AdjEdge("ACCUSED_IN", "person_X", "case_A", properties={"source_record_id": "src_valid"}),
        # Case B association has NO source_record_id or evidence -> INVALID
        AdjEdge("INVOLVED_IN", "person_X", "case_B"),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_cross_case_bridges(store)

    assert len(findings) == 0, "Missing provenance on case_B association must suppress finding"


# ── Golden Test F: Three-Case Aggregation ────────────────────────────────────

def test_cross_case_three_cases_aggregation_deduplication():
    """Golden Test F: An entity spanning 3 cases (Case A, Case B, Case C) yields ONE finding."""
    nodes = [
        NodeRecord("case_A", "Case"),
        NodeRecord("case_B", "Case"),
        NodeRecord("case_C", "Case"),
        NodeRecord("person_X", "Person", {"canonical_label": "Kingpin"}),
    ]
    edges = [
        AdjEdge("ACCUSED_IN", "person_X", "case_A", properties={"id": "r1", "source_record_id": "s1"}),
        AdjEdge("ACCUSED_IN", "person_X", "case_B", properties={"id": "r2", "source_record_id": "s2"}),
        AdjEdge("ACCUSED_IN", "person_X", "case_C", properties={"id": "r3", "source_record_id": "s3"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_cross_case_bridges(store)

    assert len(findings) == 1
    f = findings[0]
    assert f.entity_ids == ["person_X"]
    assert f.case_ids == ["case_A", "case_B", "case_C"]
    assert len(f.edge_ids) == 3
    assert len(f.evidence_ids) == 3


# ── Golden Test G: Duplicate Relationship Deduplication ─────────────────────

def test_cross_case_duplicate_relationship_deduplication():
    """Golden Test G: Duplicate relationships between Person X and Case A yield 1 unique case entry."""
    nodes = [
        NodeRecord("case_A", "Case"),
        NodeRecord("case_B", "Case"),
        NodeRecord("person_X", "Person"),
    ]
    # Multiple relationships targeting the same case
    edges = [
        AdjEdge("ACCUSED_IN", "person_X", "case_A", properties={"id": "r1", "source_record_id": "s1"}),
        AdjEdge("INVOLVED_IN", "person_X", "case_A", properties={"id": "r2", "source_record_id": "s1"}),
        AdjEdge("ACCUSED_IN", "person_X", "case_B", properties={"id": "r3", "source_record_id": "s2"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_cross_case_bridges(store)

    assert len(findings) == 1
    f = findings[0]
    assert f.case_ids == ["case_A", "case_B"]
    assert set(f.edge_ids) == {"r1", "r2", "r3"}


# ── Golden Test H: Invalid/Non-Case Relationship Negative ────────────────────

def test_cross_case_invalid_non_case_relationship_negative():
    """Golden Test H: Relationships like SEEN_AT or PRESENT_AT between Person and Location do NOT create Case membership."""
    nodes = [
        NodeRecord("person_X", "Person"),
        NodeRecord("location_L", "Location"),
        NodeRecord("event_E", "Event"),
    ]
    edges = [
        AdjEdge("SEEN_AT", "person_X", "location_L", properties={"source_record_id": "s1"}),
        AdjEdge("PRESENT_AT", "person_X", "event_E", properties={"source_record_id": "s2"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_cross_case_bridges(store)

    assert len(findings) == 0, "Non-case endpoints (Location/Event) must NOT create Case associations"


# ── General Tests: Empty, Singleton, Determinism, Non-Mutation, Safety ───────

def test_cross_case_empty_and_singleton_graph():
    store_empty = build_graph_store([], [])
    assert len(detect_cross_case_bridges(store_empty)) == 0

    nodes_single = [NodeRecord("person_001", "Person")]
    store_single = build_graph_store(nodes_single, [])
    assert len(detect_cross_case_bridges(store_single)) == 0


def test_cross_case_determinism_and_non_mutation():
    nodes = [
        NodeRecord("case_A", "Case"),
        NodeRecord("case_B", "Case"),
        NodeRecord("person_X", "Person", {"canonical_label": "Rahul"}),
    ]
    edges = [
        AdjEdge("ACCUSED_IN", "person_X", "case_A", properties={"id": "r1", "source_record_id": "s1"}),
        AdjEdge("ACCUSED_IN", "person_X", "case_B", properties={"id": "r2", "source_record_id": "s2"}),
    ]
    store = build_graph_store(nodes, edges)

    initial_node_count = len(store.nodes)
    initial_edge_count = sum(len(el) for el in store.edge_index.values())

    run1 = detect_cross_case_bridges(store)
    run2 = detect_cross_case_bridges(store)

    assert len(store.nodes) == initial_node_count
    assert sum(len(el) for el in store.edge_index.values()) == initial_edge_count

    assert len(run1) == len(run2)
    assert run1[0].rule_id == run2[0].rule_id
    assert run1[0].entity_ids == run2[0].entity_ids
    assert run1[0].case_ids == run2[0].case_ids
    assert run1[0].edge_ids == run2[0].edge_ids
    assert run1[0].evidence_ids == run2[0].evidence_ids
    assert run1[0].explanation == run2[0].explanation


def test_cross_case_safety_neutral_language():
    nodes = [
        NodeRecord("case_A", "Case"),
        NodeRecord("case_B", "Case"),
        NodeRecord("person_X", "Person", {"canonical_label": "Rahul"}),
    ]
    edges = [
        AdjEdge("ACCUSED_IN", "person_X", "case_A", properties={"source_record_id": "s1"}),
        AdjEdge("ACCUSED_IN", "person_X", "case_B", properties={"source_record_id": "s2"}),
    ]
    store = build_graph_store(nodes, edges)
    findings = detect_cross_case_bridges(store)

    forbidden_terms = ["criminal", "guilt", "mastermind", "recidivism", "probability", "fraud"]

    for f in findings:
        assert f.derivation_class == "DERIVED"
        exp_lower = f.explanation.lower()
        for term in forbidden_terms:
            assert term not in exp_lower, f"Forbidden term '{term}' found in explanation"
