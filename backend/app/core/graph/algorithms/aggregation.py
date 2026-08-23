"""
graph/algorithms/aggregation.py

Reusable aggregation functions for dashboard-facing counts and summaries.

Design rules
------------
* Every function is a single-pass O(N) or O(E) scan.
* All results are plain dicts or typed dataclasses — no Pydantic models
  here to keep this module import-free from the API layer.
* Functions accept only a ``GraphStore`` — no DB calls, no HTTP.

No database calls.  No API code.  No ML.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.core.graph.algorithms.utils import (
    GraphStore,
    get_edges_of_type,
    iter_nodes_by_type,
    prop_str,
)

# ── Edge / entity type string literals ───────────────────────────────────────

_CASE = "Case"
_OFFICER = "Officer"
_DEPENDENCY = "Dependency"
_CLOCK_INSTANCE = "ClockInstance"
_EVIDENCE = "Evidence"
_INVESTIGATED_BY = "INVESTIGATED_BY"
_CASE_HAS_DEPENDENCY = "CASE_HAS_DEPENDENCY"
_CASE_HAS_CLOCK = "CASE_HAS_CLOCK"
_CASE_HAS_EVIDENCE = "CASE_HAS_EVIDENCE"
_CASE_HAS_CRIME_HEAD = "CASE_HAS_CRIME_HEAD"


# ── Return type ───────────────────────────────────────────────────────────────


@dataclass
class CaseCounts:
    """
    High-level case counts broken down by key dimensions.

    Attributes
    ----------
    total              : total Case nodes
    by_stage           : case_stage → count
    by_risk_band       : risk_band (green/amber/red/overdue) → count
    by_offence_category: offence_category → count
    """

    total: int = 0
    by_stage: dict[str, int] = field(default_factory=dict)
    by_risk_band: dict[str, int] = field(default_factory=dict)
    by_offence_category: dict[str, int] = field(default_factory=dict)


# ── Case-level aggregations ───────────────────────────────────────────────────


def crime_count_by_district(store: GraphStore) -> dict[str, int]:
    """
    Return the number of cases per district.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    dict[str, int]
        district → case count.  Empty dict if no Case nodes exist.
    """
    counts: dict[str, int] = {}
    for node in iter_nodes_by_type(store, _CASE):
        district = prop_str(node, "district", default="unknown")
        counts[district] = counts.get(district, 0) + 1
    return counts


def crime_count_by_station(store: GraphStore) -> dict[str, int]:
    """
    Return the number of cases per police station.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    dict[str, int]
        police_station → case count.
    """
    counts: dict[str, int] = {}
    for node in iter_nodes_by_type(store, _CASE):
        station = prop_str(node, "police_station", default="unknown")
        counts[station] = counts.get(station, 0) + 1
    return counts


def crime_count_by_crime_head(store: GraphStore) -> dict[str, int]:
    """
    Return the number of cases linked to each crime head.

    Uses ``CASE_HAS_CRIME_HEAD`` edges and resolves the crime head name
    from the target node's ``head_name`` property.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    dict[str, int]
        head_name → case count.
    """
    counts: dict[str, int] = {}
    for edge in get_edges_of_type(store, _CASE_HAS_CRIME_HEAD):
        head_node = store.nodes.get(edge.target_id)
        head_name = (
            prop_str(head_node, "head_name", default=edge.target_id)
            if head_node is not None
            else edge.target_id
        )
        counts[head_name] = counts.get(head_name, 0) + 1
    return counts


def crime_count_by_offence_category(store: GraphStore) -> dict[str, int]:
    """
    Return the number of cases per offence category.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    dict[str, int]
        offence_category → case count.
    """
    counts: dict[str, int] = {}
    for node in iter_nodes_by_type(store, _CASE):
        cat = prop_str(node, "offence_category", default="unknown")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def case_counts(store: GraphStore) -> CaseCounts:
    """
    Return a multi-dimensional case count summary.

    Single pass over all Case nodes.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    CaseCounts
    """
    result = CaseCounts()
    for node in iter_nodes_by_type(store, _CASE):
        result.total += 1
        stage = prop_str(node, "case_stage", default="unknown")
        result.by_stage[stage] = result.by_stage.get(stage, 0) + 1
        band = prop_str(node, "risk_band", default="unknown")
        result.by_risk_band[band] = result.by_risk_band.get(band, 0) + 1
        cat = prop_str(node, "offence_category", default="unknown")
        result.by_offence_category[cat] = result.by_offence_category.get(cat, 0) + 1
    return result


# ── Dependency aggregations ───────────────────────────────────────────────────


def dependency_status_counts(store: GraphStore) -> dict[str, int]:
    """
    Return the number of dependencies in each status bucket.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    dict[str, int]
        status (pending/resolved/escalated) → count.
    """
    counts: dict[str, int] = {}
    for node in iter_nodes_by_type(store, _DEPENDENCY):
        status = prop_str(node, "status", default="unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def average_dependencies_per_case(store: GraphStore) -> float:
    """
    Return the mean number of Dependency nodes per Case.

    Uses ``CASE_HAS_DEPENDENCY`` edges — O(E).

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    float
        0.0 if no cases exist.
    """
    case_count = sum(1 for _ in iter_nodes_by_type(store, _CASE))
    if case_count == 0:
        return 0.0
    dep_edges = len(get_edges_of_type(store, _CASE_HAS_DEPENDENCY))
    return round(dep_edges / case_count, 4)


# ── Clock aggregations ────────────────────────────────────────────────────────


def clock_status_counts(store: GraphStore) -> dict[str, int]:
    """
    Return the number of clock instances in each status bucket.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    dict[str, int]
        status (green/amber/red/overdue) → count.
    """
    counts: dict[str, int] = {}
    for node in iter_nodes_by_type(store, _CLOCK_INSTANCE):
        status = prop_str(node, "status", default="unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


# ── Evidence aggregations ─────────────────────────────────────────────────────


def average_evidence_per_case(store: GraphStore) -> float:
    """
    Return the mean number of Evidence nodes per Case.

    Uses ``CASE_HAS_EVIDENCE`` edges — O(E).

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    float
        0.0 if no cases exist.
    """
    case_count = sum(1 for _ in iter_nodes_by_type(store, _CASE))
    if case_count == 0:
        return 0.0
    ev_edges = len(get_edges_of_type(store, _CASE_HAS_EVIDENCE))
    return round(ev_edges / case_count, 4)


# ── Officer aggregations ──────────────────────────────────────────────────────


def officer_workload(store: GraphStore) -> dict[str, int]:
    """
    Return the number of cases per officer (via ``INVESTIGATED_BY`` edges).

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    dict[str, int]
        officer_node_id → case count.  Officers with zero cases are omitted.
    """
    counts: dict[str, int] = {}
    for edge in get_edges_of_type(store, _INVESTIGATED_BY):
        # Edge: Case → Officer  (source=case, target=officer)
        oid = edge.target_id
        counts[oid] = counts.get(oid, 0) + 1
    return counts


def officer_workload_named(store: GraphStore) -> dict[str, int]:
    """
    Like ``officer_workload`` but keys are officer badge numbers or names
    rather than raw node ids — more useful for human-readable dashboards.

    Falls back to node id if neither ``badge_number`` nor ``full_name``
    is present on the Officer node.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    dict[str, int]
        officer label → case count.
    """
    raw = officer_workload(store)
    result: dict[str, int] = {}
    for oid, count in raw.items():
        node = store.nodes.get(oid)
        if node is not None:
            label = (
                prop_str(node, "badge_number")
                or prop_str(node, "full_name")
                or oid
            )
        else:
            label = oid
        result[label] = count
    return result
