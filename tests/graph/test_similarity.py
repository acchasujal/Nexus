"""
tests/graph/test_similarity.py

Unit tests for backend.app.core.graph.algorithms.similarity.

Coverage
--------
* compute_case_similarity — identical cases (max score), no overlap, partial
* Feature contributions align with FEATURE_WEIGHTS
* Missing case → score=0.0
* find_similar_cases — ordering, min_score filter, top_k, missing anchor
* batch_similarity_matrix — all pairs scored, sorted, empty input
* Time window boundary conditions (same day, just inside, just outside)
* Determinism — same input always produces same output
"""

from __future__ import annotations

import pytest
from helpers import (
    _FakeEdge,
    make_case,
    make_crime_head,
    make_crime_sub_head,
    make_person,
    make_section,
    make_store,
)

from backend.app.core.graph.algorithms.similarity import (
    FEATURE_WEIGHTS,
    SimilarityResult,
    batch_similarity_matrix,
    compute_case_similarity,
    find_similar_cases,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _store_with_two_linked_cases(
    same_crime_head: bool = True,
    same_station: bool = True,
    same_accused: bool = True,
    reported_a: str = "2026-01-01T00:00:00+00:00",
    reported_b: str = "2026-01-05T00:00:00+00:00",
):
    """
    Build a minimal two-case store for similarity testing.
    Returns (store, case_a_id, case_b_id).
    """
    head_a = make_crime_head("Property")
    head_b = make_crime_head("Violence") if not same_crime_head else head_a
    sub_a = make_crime_sub_head("Theft")
    sub_b = make_crime_sub_head("Assault") if not same_crime_head else sub_a
    sec = make_section("SECTION_THEFT")

    station = "Ashok Nagar" if same_station else "Malleshwaram"
    case_a = make_case(
        station="Ashok Nagar",
        district="Bengaluru City",
        reported_at=reported_a,
    )
    case_b = make_case(
        station=station,
        district="Bengaluru City",
        reported_at=reported_b,
    )
    person = make_person()

    nodes = [case_a, case_b, head_a, head_b, sub_a, sub_b, sec, person]
    edges = [
        _FakeEdge("CASE_HAS_CRIME_HEAD", case_a.id, head_a.id),
        _FakeEdge("CASE_HAS_CRIME_HEAD", case_b.id, head_b.id),
        _FakeEdge("CASE_HAS_CRIME_SUB_HEAD", case_a.id, sub_a.id),
        _FakeEdge("CASE_HAS_CRIME_SUB_HEAD", case_b.id, sub_b.id),
        _FakeEdge("CHARGED_UNDER", case_a.id, sec.id),
        _FakeEdge("CHARGED_UNDER", case_b.id, sec.id),
    ]
    if same_accused:
        edges += [
            _FakeEdge("ACCUSED_IN", person.id, case_a.id),
            _FakeEdge("ACCUSED_IN", person.id, case_b.id),
        ]

    store = make_store(nodes, edges)
    return store, case_a.id, case_b.id


# ── compute_case_similarity ───────────────────────────────────────────────────


def test_similarity_same_case_max():
    """A case compared with itself should score 1.0 (all features match)."""

    store, case_id, _ = _store_with_two_linked_cases()
    # Compare case_a with itself
    result = compute_case_similarity(store, case_id, case_id)
    # All structural features match (same node); time delta = 0 days ≤ 30 days

    print(result.feature_contributions)
    print(result.score)
    assert result.score == pytest.approx(1.0, abs=1e-4)
    


def test_similarity_no_overlap():
    """Two cases with nothing in common score 0.0."""
    case_a = make_case(district="Bengaluru City", station="Ashok Nagar")
    case_b = make_case(district="Mysuru", station="Mysuru North")
    store = make_store([case_a, case_b], [])
    result = compute_case_similarity(store, case_a.id, case_b.id)
    # district differs, station differs, no shared crime head / accused
    assert result.score == pytest.approx(0.0, abs=1e-4)


def test_similarity_partial_match():
    """Partial match returns a score between 0 and 1 with correct features."""
    store, ca, cb = _store_with_two_linked_cases(
        same_crime_head=True,
        same_station=True,
        same_accused=True,
        reported_a="2026-01-01T00:00:00+00:00",
        reported_b="2026-01-05T00:00:00+00:00",
    )
    result = compute_case_similarity(store, ca, cb)
    assert 0.0 < result.score <= 1.0
    # Crime head, section, accused, station, district, time window should all match
    assert "shared_crime_head" in result.matched_features
    assert "shared_section" in result.matched_features
    assert "shared_accused" in result.matched_features
    assert "shared_police_station" in result.matched_features


def test_similarity_feature_contributions_sum_to_score():
    """feature_contributions values must sum to the reported score."""
    store, ca, cb = _store_with_two_linked_cases()
    result = compute_case_similarity(store, ca, cb)
    contribution_sum = sum(result.feature_contributions.values())
    assert contribution_sum == pytest.approx(result.score, abs=1e-6)


def test_similarity_contributions_match_weight_table():
    """Each feature contribution must equal FEATURE_WEIGHTS[feature]."""
    store, ca, cb = _store_with_two_linked_cases()
    result = compute_case_similarity(store, ca, cb)
    for feat, contrib in result.feature_contributions.items():
        assert contrib == pytest.approx(FEATURE_WEIGHTS[feat], abs=1e-9)


def test_similarity_missing_case_a(empty_store):
    result = compute_case_similarity(empty_store, "ghost-a", "ghost-b")
    assert result.score == 0.0
    assert result.matched_features == []


def test_similarity_missing_one_case():
    store, ca, _ = _store_with_two_linked_cases()
    result = compute_case_similarity(store, ca, "does-not-exist")
    assert result.score == 0.0


def test_similarity_result_is_dataclass():
    store, ca, cb = _store_with_two_linked_cases()
    result = compute_case_similarity(store, ca, cb)
    assert isinstance(result, SimilarityResult)
    assert isinstance(result.matched_features, list)
    assert isinstance(result.feature_contributions, dict)


# ── Time window tests ─────────────────────────────────────────────────────────


def test_time_window_same_day():
    store, ca, cb = _store_with_two_linked_cases(
        reported_a="2026-01-01T00:00:00+00:00",
        reported_b="2026-01-01T00:00:00+00:00",
        same_crime_head=False,
        same_station=False,
        same_accused=False,
    )
    result = compute_case_similarity(store, ca, cb, time_window_days=30)
    assert "shared_time_window" in result.matched_features


def test_time_window_just_outside():
    """31 days apart with window=30 should NOT match shared_time_window."""
    store, ca, cb = _store_with_two_linked_cases(
        reported_a="2026-01-01T00:00:00+00:00",
        reported_b="2026-02-01T00:00:00+00:00",  # 31 days later
        same_crime_head=False,
        same_station=False,
        same_accused=False,
    )
    result = compute_case_similarity(store, ca, cb, time_window_days=30)
    assert "shared_time_window" not in result.matched_features


def test_time_window_exactly_at_boundary():
    """Exactly 30 days apart with window=30 should match (≤ comparison)."""
    store, ca, cb = _store_with_two_linked_cases(
        reported_a="2026-01-01T00:00:00+00:00",
        reported_b="2026-01-31T00:00:00+00:00",  # exactly 30 days
        same_crime_head=False,
        same_station=False,
        same_accused=False,
    )
    result = compute_case_similarity(store, ca, cb, time_window_days=30)
    assert "shared_time_window" in result.matched_features


# ── find_similar_cases ────────────────────────────────────────────────────────


def test_find_similar_cases_returns_sorted():
    """Results must be sorted by score descending."""
    # Build three cases: A similar to B and C, B more similar to A than C
    head = make_crime_head("Property")
    sec = make_section("THEFT")
    case_a = make_case(station="Ashok Nagar", district="Bengaluru City",
                       reported_at="2026-01-01T00:00:00+00:00")
    case_b = make_case(station="Ashok Nagar", district="Bengaluru City",
                       reported_at="2026-01-02T00:00:00+00:00")
    case_c = make_case(station="Bantwal", district="Mangaluru",
                       reported_at="2026-06-01T00:00:00+00:00")
    store = make_store(
        [case_a, case_b, case_c, head, sec],
        [
            _FakeEdge("CASE_HAS_CRIME_HEAD", case_a.id, head.id),
            _FakeEdge("CASE_HAS_CRIME_HEAD", case_b.id, head.id),
            _FakeEdge("CHARGED_UNDER", case_a.id, sec.id),
            _FakeEdge("CHARGED_UNDER", case_b.id, sec.id),
        ],
    )
    results = find_similar_cases(store, case_a.id, min_score=0.0)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_find_similar_cases_min_score_filter():
    """Results below min_score must be excluded."""
    store, ca, cb = _store_with_two_linked_cases(
        same_crime_head=False,
        same_station=False,
        same_accused=False,
    )
    results = find_similar_cases(store, ca, min_score=0.9)
    assert all(r.score >= 0.9 for r in results)


def test_find_similar_cases_top_k():
    """top_k=1 returns at most one result."""
    store, ca, cb = _store_with_two_linked_cases()
    results = find_similar_cases(store, ca, min_score=0.0, top_k=1)
    assert len(results) <= 1


def test_find_similar_cases_missing_anchor(empty_store):
    assert find_similar_cases(empty_store, "ghost") == []


def test_find_similar_cases_excludes_self():
    """The anchor case itself must not appear in results."""
    store, ca, cb = _store_with_two_linked_cases()
    results = find_similar_cases(store, ca, min_score=0.0)
    result_ids = {r.case_b_id for r in results}
    assert ca not in result_ids


# ── batch_similarity_matrix ───────────────────────────────────────────────────


def test_batch_similarity_matrix_pairs():
    """N=3 → up to 3 pairs."""
    store, ca, cb = _store_with_two_linked_cases()
   
    
    results = batch_similarity_matrix(store, [ca, cb])
    # One pair
    assert len(results) <= 1


def test_batch_similarity_matrix_sorted():
    store, ca, cb = _store_with_two_linked_cases()
    results = batch_similarity_matrix(store, [ca, cb])
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_batch_similarity_matrix_empty_input(empty_store):
    assert batch_similarity_matrix(empty_store, []) == []


def test_batch_similarity_matrix_unknown_ids():
    """Unknown ids are silently skipped."""
    store, ca, cb = _store_with_two_linked_cases()
    results = batch_similarity_matrix(store, [ca, "ghost"])
    # ghost skipped; only 1 valid id → no pairs
    assert results == []


# ── Determinism ───────────────────────────────────────────────────────────────


def test_similarity_deterministic():
    """Same store, same inputs → identical result on two calls."""
    store, ca, cb = _store_with_two_linked_cases()
    r1 = compute_case_similarity(store, ca, cb)
    r2 = compute_case_similarity(store, ca, cb)
    assert r1.score == r2.score
    assert r1.matched_features == r2.matched_features
