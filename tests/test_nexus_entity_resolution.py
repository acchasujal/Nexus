"""tests/test_nexus_entity_resolution.py

Evaluates the multi-attribute Entity Resolution engine against the synthetic ground truth.
Verifies precision, recall, phonetic normalization, and explainable scoring.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

_GRAPH_TESTS = Path(__file__).resolve().parent / "graph"
if str(_GRAPH_TESTS) not in sys.path:
    sys.path.insert(0, str(_GRAPH_TESTS))

from helpers import _FakeNode, make_store  # noqa: E402

from backend.app.core.graph.algorithms.entity_resolution import (
    EntityResolutionEngine,
    evaluate_ground_truth_dataset,
    phonetic_fingerprint,
)
from backend.app.db.in_memory import InMemoryBackendRepository


def test_phonetic_fingerprint_normalization() -> None:
    # Test Indian name variations
    assert phonetic_fingerprint("Vikram Sharma") == phonetic_fingerprint("Bikram Sarma")
    assert phonetic_fingerprint("Mohammed Yusuf") == phonetic_fingerprint("Mohammad Yousuf")
    assert phonetic_fingerprint("Rajesh Kumar") == phonetic_fingerprint("Rajesh Kumar")


def test_entity_resolution_with_ground_truth() -> None:
    repo = InMemoryBackendRepository()
    engine = EntityResolutionEngine(repo.to_graph_store())

    ground_truth_path = Path("artifacts/nexus_graph/ground_truth.json")
    if not ground_truth_path.exists():
        return

    with open(ground_truth_path, encoding="utf-8") as f:
        ground_truth = json.load(f)

    metrics = evaluate_ground_truth_dataset(engine, ground_truth)
    assert metrics["precision"] >= 0.85, f"Precision too low: {metrics['precision']}"
    assert metrics["recall"] >= 0.80, f"Recall too low: {metrics['recall']}"
    assert metrics["f1"] >= 0.80, f"F1 score too low: {metrics['f1']}"


def test_name_token_match_not_hardcoded_85() -> None:
    """Test 1 & 7: Word token match does NOT yield hardcoded 0.85 and separates candidate from confirmed match."""
    from backend.app.core.graph.algorithms.entity_resolution import NAME_FAMILY, resolve_person
    from backend.app.core.graph.enums import ResolutionStatus

    p1 = _FakeNode("Person", {"full_name": "Vikram Sharma", "phone_number": "9845012345"})
    p2 = _FakeNode("Person", {"full_name": "Vikram Kumar Malhotra", "phone_number": "9876543210"})
    store = make_store([p1, p2], [])

    # Query only given name "Vikram"
    matches = resolve_person(store, {"full_name": "Vikram"}, confidence_threshold=0.30)
    assert len(matches) == 2

    # Vikram vs Vikram Sharma: 1 common word out of 2 = 0.50
    # Vikram vs Vikram Kumar Malhotra: 1 common word out of 3 = 0.333
    scores = {m.properties["full_name"]: m.confidence for m in matches}
    assert scores["Vikram Sharma"] == 0.50
    assert scores["Vikram Kumar Malhotra"] == 0.333
    assert 0.85 not in scores.values(), "0.85 should NEVER be hardcoded for token matches!"

    # Verify candidate resolution state
    for m in matches:
        assert m.status == ResolutionStatus.REVIEW_REQUIRED
        assert m.resolution_state == "CANDIDATE_PARTIAL_NAME"
        assert m.evidence_families == [NAME_FAMILY]
        assert len(m.evidence_families) == 1, "Name-derived token match must ONLY belong to 1 evidence family!"


def test_name_and_prefix_does_not_count_as_two_independent_signals() -> None:
    """Test 2: Name token match must only belong to NAME_FAMILY, never inflating family count."""
    from backend.app.core.graph.algorithms.entity_resolution import NAME_FAMILY, resolve_person

    p1 = _FakeNode("Person", {"full_name": "Vikram Hegde"})
    store = make_store([p1], [])

    matches = resolve_person(store, {"full_name": "Vikram"}, confidence_threshold=0.30)
    assert len(matches) == 1
    m = matches[0]

    assert m.evidence_families == [NAME_FAMILY]
    assert len(m.evidence_families) == 1
    assert m.resolution_state != "STRONGLY_CORROBORATED"
    assert "Multi-field corroborated" not in m.explanation


def test_independent_families_corroborate_strongly() -> None:
    """Test 3 & 6: Matching phone + matching address produces STRONGLY_CORROBORATED with 2+ families."""
    from backend.app.core.graph.algorithms.entity_resolution import resolve_person
    from backend.app.core.graph.enums import ResolutionStatus

    p1 = _FakeNode("Person", {
        "full_name": "Vikram Sharma",
        "phone_number": "9845012345",
        "address_text": "Main Bazaar, Bengaluru",
    })
    store = make_store([p1], [])

    matches = resolve_person(store, {
        "full_name": "Vikram Sharma",
        "phone_number": "9845012345",
        "address_text": "Main Bazaar, Bengaluru",
    })
    assert len(matches) == 1
    m = matches[0]

    assert m.confidence == 1.0
    assert m.status == ResolutionStatus.MATCHED
    assert m.resolution_state == "STRONGLY_CORROBORATED"
    assert len(m.evidence_families) >= 2
    assert "NAME_FAMILY" in m.evidence_families
    assert "TELECOM_FAMILY" in m.evidence_families
    assert m.independent_sources >= 2


def test_conflict_detection_reduces_resolution() -> None:
    """Test 4: Material conflict (e.g. matching name but conflicting phone) flags AMBIGUOUS_CONFLICT."""
    from backend.app.core.graph.algorithms.entity_resolution import resolve_person
    from backend.app.core.graph.enums import ResolutionStatus

    p1 = _FakeNode("Person", {
        "full_name": "Vikram Sharma",
        "phone_number": "9845012345",
    })
    store = make_store([p1], [])

    # Query with exact name but conflicting phone number
    matches = resolve_person(store, {
        "full_name": "Vikram Sharma",
        "phone_number": "9999999999",
    }, confidence_threshold=0.20)

    assert len(matches) == 1
    m = matches[0]
    assert m.status == ResolutionStatus.REVIEW_REQUIRED
    assert m.resolution_state == "AMBIGUOUS_CONFLICT"
    assert len(m.conflicting_factors) >= 1
    assert m.confidence < 1.0  # Conflict penalty applied


def test_deterministic_scoring_reproducibility() -> None:
    """Test 8: Scoring is 100% deterministic across repeated runs."""
    from backend.app.core.graph.algorithms.entity_resolution import resolve_person

    p1 = _FakeNode("Person", {"full_name": "Vikram Sharma", "phone_number": "9845012345"})
    p2 = _FakeNode("Person", {"full_name": "Vikram Malhotra", "phone_number": "9822001122"})
    store = make_store([p1, p2], [])

    run1 = resolve_person(store, {"full_name": "Vikram"}, confidence_threshold=0.30)
    run2 = resolve_person(store, {"full_name": "Vikram"}, confidence_threshold=0.30)

    assert [(m.matched_node_id, m.confidence, m.resolution_state) for m in run1] == \
           [(m.matched_node_id, m.confidence, m.resolution_state) for m in run2]

