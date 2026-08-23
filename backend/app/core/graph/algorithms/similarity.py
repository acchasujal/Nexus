"""
graph/algorithms/similarity.py

Explainable, deterministic case-similarity scoring.

Design rules
------------
* Every similarity call returns a ``SimilarityResult`` that lists *which*
  features matched and *how much* each contributed.  No black-box scores.
* Weights are declared as module-level constants so they can be audited and
  changed without touching algorithm logic.
* ``find_similar_cases`` pre-builds per-case feature sets once and scans
  candidates in a single O(N) pass — not O(N²) per call.
* ``batch_similarity_matrix`` builds the matrix using the same pre-built
  index so the total cost is O(N² · F) in the worst case (all pairs,
  F features), which is acceptable for N ≤ 500.

No database calls.  No ML.  No embeddings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Sequence

from backend.app.core.graph.algorithms.utils import (
    GraphStore,
    get_node,
    neighbor_ids,
    nodes_of_type,
    prop,
    prop_str,
    safe_str,
)
from backend.app.core.graph.algorithms.entity_resolution import phonetic_normalize

# ── Edge / entity type string literals ───────────────────────────────────────

_ACCUSED_IN = "ACCUSED_IN"
_CHARGED_UNDER = "CHARGED_UNDER"
_CASE_HAS_CRIME_HEAD = "CASE_HAS_CRIME_HEAD"
_CASE_HAS_CRIME_SUB_HEAD = "CASE_HAS_CRIME_SUB_HEAD"
_OCCURRED_IN = "OCCURRED_IN"
_CASE = "Case"
_PERSON = "Person"

# ── Feature weight table (must sum to 1.0) ────────────────────────────────────

FEATURE_WEIGHTS: dict[str, float] = {
    "shared_crime_head":      0.20,
    "shared_crime_sub_head":  0.15,
    "shared_section":         0.15,
    "shared_accused":         0.15,
    "shared_police_station":  0.10,
    "shared_district":        0.05,
    "shared_phone_cluster":   0.05,
    "shared_vehicle_cluster": 0.05,
    "shared_address_cluster": 0.05,
    "shared_time_window":     0.05,
}

# Verify at import time so misconfiguration is caught early
assert abs(sum(FEATURE_WEIGHTS.values()) - 1.0) < 1e-9, (
    "FEATURE_WEIGHTS must sum to 1.0"
)

_DEFAULT_TIME_WINDOW_DAYS: int = 30


# ── Return type ───────────────────────────────────────────────────────────────


@dataclass
class SimilarityResult:
    """
    Explainable similarity between two cases.

    Attributes
    ----------
    case_a_id            : str
    case_b_id            : str
    score                : float  — 0.0 (no overlap) to 1.0 (identical features)
    matched_features     : list[str]  — human-readable names of matched features
    feature_contributions: dict[str, float]  — feature → weight added to score
    """

    case_a_id: str
    case_b_id: str
    score: float
    matched_features: list[str] = field(default_factory=list)
    feature_contributions: dict[str, float] = field(default_factory=dict)


# ── Internal per-case feature cache ──────────────────────────────────────────


@dataclass
class _CaseFeatures:
    """Pre-extracted feature sets for a single case node."""

    case_id: str
    crime_head_ids: frozenset[str]
    crime_sub_head_ids: frozenset[str]
    section_ids: frozenset[str]
    accused_ids: frozenset[str]
    accused_names: frozenset[str]
    accused_phones: frozenset[str]
    police_station: str
    district: str
    phone_cluster_ids: frozenset[str]
    vehicle_cluster_ids: frozenset[str]
    address_cluster_ids: frozenset[str]
    reported_at: datetime | None


def _extract_case_features(store: GraphStore, case_id: str) -> _CaseFeatures | None:
    """
    Extract all similarity features for *case_id* in one pass.

    Returns ``None`` if the node does not exist or is not a Case.
    """
    nid = safe_str(case_id)
    case_node = get_node(store, nid)
    if case_node is None or case_node.entity_type != _CASE:
        return None

    # Structural features via edge traversal
    crime_head_ids = frozenset(
        neighbor_ids(store, nid, edge_types=[_CASE_HAS_CRIME_HEAD], direction="out")
    )
    crime_sub_head_ids = frozenset(
        neighbor_ids(store, nid, edge_types=[_CASE_HAS_CRIME_SUB_HEAD], direction="out")
    )
    section_ids = frozenset(
        neighbor_ids(store, nid, edge_types=[_CHARGED_UNDER], direction="out")
    )

    # Accused persons
    accused_ids = frozenset(
        neighbor_ids(store, nid, edge_types=[_ACCUSED_IN], direction="in")
    )

    # Property-based features
    police_station = prop_str(case_node, "police_station")
    district = prop_str(case_node, "district")

    # Cluster ids gathered from accused persons
    phone_clusters: set[str] = set()
    vehicle_clusters: set[str] = set()
    address_clusters: set[str] = set()
    accused_names: set[str] = set()
    accused_phones: set[str] = set()
    for pid in accused_ids:
        pnode = get_node(store, pid)
        if pnode is None:
            continue
        pc = prop_str(pnode, "shared_phone_cluster_id")
        vc = prop_str(pnode, "shared_vehicle_cluster_id")
        ac = prop_str(pnode, "shared_address_cluster_id")
        if pc:
            phone_clusters.add(pc)
        if vc:
            vehicle_clusters.add(vc)
        if ac:
            address_clusters.add(ac)
            
        full_name = prop_str(pnode, "full_name")
        if full_name:
            accused_names.add(phonetic_normalize(full_name))
        phone = prop_str(pnode, "phone_number")
        if phone:
            accused_phones.add(re.sub(r'\D', '', phone))

    # Timestamp
    reported_at_raw = prop(case_node, "reported_at")
    reported_at: datetime | None = None
    if isinstance(reported_at_raw, datetime):
        reported_at = reported_at_raw
    elif isinstance(reported_at_raw, str):
        try:
            reported_at = datetime.fromisoformat(reported_at_raw)
        except ValueError:
            reported_at = None

    return _CaseFeatures(
        case_id=nid,
        crime_head_ids=crime_head_ids,
        crime_sub_head_ids=crime_sub_head_ids,
        section_ids=section_ids,
        accused_ids=accused_ids,
        accused_names=frozenset(accused_names),
        accused_phones=frozenset(accused_phones),
        police_station=police_station,
        district=district,
        phone_cluster_ids=frozenset(phone_clusters),
        vehicle_cluster_ids=frozenset(vehicle_clusters),
        address_cluster_ids=frozenset(address_clusters),
        reported_at=reported_at,
    )


def _build_feature_index(
    store: GraphStore,
) -> dict[str, _CaseFeatures]:
    """
    Build a {case_id → _CaseFeatures} mapping for every Case in the store.

    O(N + E) — called once per ``find_similar_cases`` invocation.
    """
    index: dict[str, _CaseFeatures] = {}
    for node in nodes_of_type(store, _CASE):
        feats = _extract_case_features(store, node.node_id)
        if feats is not None:
            index[node.node_id] = feats
    return index


# ── Core scoring ──────────────────────────────────────────────────────────────


def _score_pair(
    a: _CaseFeatures,
    b: _CaseFeatures,
    time_window_days: int = _DEFAULT_TIME_WINDOW_DAYS,
) -> SimilarityResult:
    """
    Compute similarity between two pre-extracted feature sets.

    Returns a fully populated ``SimilarityResult``.
    """
    matched: list[str] = []
    contributions: dict[str, float] = {}
    score = 0.0

    def _add(feature: str, matched_flag: bool) -> None:
        nonlocal score
        if matched_flag:
            w = FEATURE_WEIGHTS[feature]
            score += w
            matched.append(feature)
            contributions[feature] = w

    # Crime head: at least one shared
    _add("shared_crime_head", bool(a.crime_head_ids & b.crime_head_ids))

    # Crime sub head: at least one shared
    _add("shared_crime_sub_head", bool(a.crime_sub_head_ids & b.crime_sub_head_ids))

    # Section: at least one shared
    _add("shared_section", bool(a.section_ids & b.section_ids))

    # Accused: at least one person in common (by node_id, phonetic name, or digits-only phone)
    shared_acc_flag = (
        bool(a.accused_ids & b.accused_ids)
        or bool(a.accused_names & b.accused_names)
        or bool(a.accused_phones & b.accused_phones)
    )
    _add("shared_accused", shared_acc_flag)

    # Police station: exact match (both non-empty)
    _add(
        "shared_police_station",
        bool(a.police_station and b.police_station and a.police_station == b.police_station),
    )

    # District: exact match (both non-empty)
    _add(
        "shared_district",
        bool(a.district and b.district and a.district == b.district),
    )

    # Phone cluster: at least one shared cluster id
    _add("shared_phone_cluster", bool(a.phone_cluster_ids & b.phone_cluster_ids))

    # Vehicle cluster: at least one shared cluster id
    _add("shared_vehicle_cluster", bool(a.vehicle_cluster_ids & b.vehicle_cluster_ids))

    # Address cluster: at least one shared cluster id
    _add("shared_address_cluster", bool(a.address_cluster_ids & b.address_cluster_ids))

    # Time window: both have timestamps and they fall within the window
    in_window = False
    if a.reported_at is not None and b.reported_at is not None:
        at = a.reported_at
        bt = b.reported_at
        # Make both timezone-aware for safe subtraction
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        if bt.tzinfo is None:
            bt = bt.replace(tzinfo=timezone.utc)
        delta_days = abs((at - bt).days)
        in_window = delta_days <= time_window_days
    _add("shared_time_window", in_window)

    return SimilarityResult(
        case_a_id=a.case_id,
        case_b_id=b.case_id,
        score=round(score, 4),
        matched_features=matched,
        feature_contributions=contributions,
    )


# ── Public API ────────────────────────────────────────────────────────────────


def compute_case_similarity(
    store: GraphStore,
    case_a_id: str,
    case_b_id: str,
    time_window_days: int = _DEFAULT_TIME_WINDOW_DAYS,
) -> SimilarityResult:
    """
    Compute the explainable similarity score between two cases.

    Parameters
    ----------
    store            : GraphStore
    case_a_id        : str | UUID
    case_b_id        : str | UUID
    time_window_days : cases are considered temporally similar if their
                       ``reported_at`` timestamps are within this many days
                       (default 30)

    Returns
    -------
    SimilarityResult
        score=0.0 if either case is missing; feature lists will be empty.

    Notes
    -----
    The score is a weighted sum of binary feature matches — see
    ``FEATURE_WEIGHTS`` for the full weight table.
    """
    if safe_str(case_a_id) == safe_str(case_b_id):
        return SimilarityResult(
            case_a_id=safe_str(case_a_id),
            case_b_id=safe_str(case_b_id),
            score=1.0,
            matched_features=list(FEATURE_WEIGHTS.keys()),
            feature_contributions=FEATURE_WEIGHTS.copy(),
    )



    a = _extract_case_features(store, case_a_id)
    b = _extract_case_features(store, case_b_id)

    if a is None or b is None:
        return SimilarityResult(
            case_a_id=safe_str(case_a_id),
            case_b_id=safe_str(case_b_id),
            score=0.0,
        )

    return _score_pair(a, b, time_window_days=time_window_days)


def find_similar_cases(
    store: GraphStore,
    case_id: str,
    min_score: float = 0.1,
    top_k: int = 20,
    time_window_days: int = _DEFAULT_TIME_WINDOW_DAYS,
) -> list[SimilarityResult]:
    """
    Return the top-*k* most similar cases to *case_id*, ordered by
    descending similarity score.

    Pre-builds a feature index over all cases once, then compares in a
    single O(N) pass — no nested loops.

    Parameters
    ----------
    store            : GraphStore
    case_id          : str | UUID
    min_score        : exclude results below this threshold (default 0.1)
    top_k            : maximum results to return (default 20)
    time_window_days : passed through to ``_score_pair``

    Returns
    -------
    list[SimilarityResult]
        Sorted by score descending.  Empty list if *case_id* not found.
    """
    nid = safe_str(case_id)
    index = _build_feature_index(store)

    anchor = index.get(nid)
    if anchor is None:
        return []

    results: list[SimilarityResult] = []
    for other_id, other_feats in index.items():
        if other_id == nid:
            continue
        result = _score_pair(anchor, other_feats, time_window_days=time_window_days)
        if result.score >= min_score:
            results.append(result)

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]


def batch_similarity_matrix(
    store: GraphStore,
    case_ids: Sequence[str],
    time_window_days: int = _DEFAULT_TIME_WINDOW_DAYS,
) -> list[SimilarityResult]:
    """
    Compute pairwise similarity for a list of case ids.

    Each unique pair (A, B) where A < B is scored once.  The returned list
    is sorted by score descending.

    Parameters
    ----------
    store            : GraphStore
    case_ids         : sequence of case ids to compare
    time_window_days : passed through to ``_score_pair``

    Returns
    -------
    list[SimilarityResult]
        All pairs with score > 0, sorted by score descending.
    """
    index = _build_feature_index(store)
    ids = [safe_str(cid) for cid in case_ids if safe_str(cid) in index]

    results: list[SimilarityResult] = []
    n = len(ids)
    for i in range(n):
        for j in range(i + 1, n):
            result = _score_pair(index[ids[i]], index[ids[j]], time_window_days=time_window_days)
            if result.score > 0.0:
                results.append(result)

    results.sort(key=lambda r: r.score, reverse=True)
    return results
