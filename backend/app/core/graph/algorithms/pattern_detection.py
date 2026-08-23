"""
graph/algorithms/pattern_detection.py

Rule-based, deterministic pattern detection for the unified investigation graph.

Design rules
------------
* All rules are explicit threshold comparisons — no ML, no probability.
* Every result type carries a human-readable ``reason`` field so findings
  can be displayed or logged without further processing.
* Thresholds are keyword-argument defaults so callers can tune them without
  modifying source code.
* Single-pass scans wherever possible — patterns are never computed via
  nested loops over the full node set.

No database calls.  No API code.  No ML.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.graph.algorithms.aggregation import officer_workload
from backend.app.core.graph.algorithms.utils import (
    GraphStore,
    get_edges_of_type,
    iter_nodes_by_type,
    prop_str,
)
from backend.app.core.graph.algorithms.entity_resolution import resolve_person

# ── Entity / edge type literals ───────────────────────────────────────────────

_CASE = "Case"
_PERSON = "Person"
_OFFICER = "Officer"
_DEPENDENCY = "Dependency"
_ACCUSED_IN = "ACCUSED_IN"
_CASE_HAS_DEPENDENCY = "CASE_HAS_DEPENDENCY"


# ── Result dataclasses ────────────────────────────────────────────────────────


@dataclass
class RepeatAccusedResult:
    """
    A person accused in multiple cases.

    Attributes
    ----------
    person_id  : str — node id of the accused person
    case_ids   : list of case node ids the person is accused in
    case_count : number of cases (len(case_ids))
    reason     : human-readable summary (e.g. "Accused in 4 cases")
    """

    person_id: str
    case_ids: list[str]
    case_count: int
    reason: str


@dataclass
class ClusterResult:
    """
    A shared attribute cluster (phone / vehicle / address) linking persons.

    Attributes
    ----------
    cluster_id   : str — e.g. "phone-03", "vehicle-07", "address-12"
    cluster_type : str — "phone", "vehicle", or "address"
    person_ids   : persons sharing this cluster attribute
    case_ids     : union of cases these persons appear in (any role)
    reason       : human-readable summary
    """

    cluster_id: str
    cluster_type: str
    person_ids: list[str]
    case_ids: list[str]
    reason: str


@dataclass
class OfficerWorkloadResult:
    """
    An officer carrying an unusually high case load.

    Attributes
    ----------
    officer_id   : str — node id
    badge_number : str — human-readable label
    case_count   : int
    reason       : human-readable summary
    """

    officer_id: str
    badge_number: str
    case_count: int
    reason: str


@dataclass
class DependencyHotspotResult:
    """
    A case with an unusually high number of unresolved dependencies.

    Attributes
    ----------
    case_id             : str
    fir_number          : str — human-readable label
    pending_count       : int
    total_dependency_count: int
    reason              : human-readable summary
    """

    case_id: str
    fir_number: str
    pending_count: int
    total_dependency_count: int
    reason: str


@dataclass
class DistrictHotspotResult:
    """
    A district with a disproportionately high case count.

    Attributes
    ----------
    district    : str
    case_count  : int
    reason      : human-readable summary
    """

    district: str
    case_count: int
    reason: str


@dataclass
class TemporalHotspotResult:
    """
    A date with a disproportionately high case count.

    Attributes
    ----------
    date        : str
    case_count  : int
    reason      : human-readable summary
    """

    date: str
    case_count: int
    reason: str


# ── Pattern: repeat accused ───────────────────────────────────────────────────


def detect_repeat_accused(
    store: GraphStore,
    min_cases: int = 2,
) -> list[RepeatAccusedResult]:
    """
    Detect persons who appear as accused in ``min_cases`` or more distinct cases.

    Uses ``ACCUSED_IN`` edges (Person → Case).  Single pass over all edges.

    Parameters
    ----------
    store     : GraphStore
    min_cases : minimum number of cases to be flagged (default 2)

    Returns
    -------
    list[RepeatAccusedResult]
        Sorted by case_count descending.  Empty list if none found.
    """
    # Build person_id → [case_ids] from ACCUSED_IN edges
    accused_map: dict[str, list[str]] = {}
    for edge in get_edges_of_type(store, _ACCUSED_IN):
        pid = edge.source_id
        cid = edge.target_id
        accused_map.setdefault(pid, []).append(cid)

    results: list[RepeatAccusedResult] = []
    for pid, case_ids in accused_map.items():
        if len(case_ids) >= min_cases:
            results.append(
                RepeatAccusedResult(
                    person_id=pid,
                    case_ids=sorted(set(case_ids)),
                    case_count=len(set(case_ids)),
                    reason=f"Accused in {len(set(case_ids))} cases",
                )
            )

    results.sort(key=lambda r: r.case_count, reverse=True)
    return results


# ── Pattern: shared phone cluster ────────────────────────────────────────────


def detect_repeat_phone(
    store: GraphStore,
    min_persons: int = 2,
) -> list[ClusterResult]:
    """
    Detect phone clusters shared by ``min_persons`` or more persons.

    Reads ``shared_phone_cluster_id`` from Person node properties.

    Parameters
    ----------
    store       : GraphStore
    min_persons : minimum cluster size to flag (default 2)

    Returns
    -------
    list[ClusterResult]
        Sorted by number of persons descending.
    """
    return _detect_cluster(
        store,
        cluster_prop="shared_phone_cluster_id",
        cluster_type="phone",
        min_persons=min_persons,
    )


# ── Pattern: shared vehicle cluster ──────────────────────────────────────────


def detect_repeat_vehicle(
    store: GraphStore,
    min_persons: int = 2,
) -> list[ClusterResult]:
    """
    Detect vehicle registration clusters shared by ``min_persons`` or more persons.

    Reads ``shared_vehicle_cluster_id`` from Person node properties.

    Parameters
    ----------
    store       : GraphStore
    min_persons : minimum cluster size to flag (default 2)

    Returns
    -------
    list[ClusterResult]
        Sorted by number of persons descending.
    """
    return _detect_cluster(
        store,
        cluster_prop="shared_vehicle_cluster_id",
        cluster_type="vehicle",
        min_persons=min_persons,
    )


# ── Pattern: shared address cluster ──────────────────────────────────────────


def detect_repeat_address(
    store: GraphStore,
    min_persons: int = 2,
) -> list[ClusterResult]:
    """
    Detect address clusters shared by ``min_persons`` or more persons.

    Reads ``shared_address_cluster_id`` from Person node properties.

    Parameters
    ----------
    store       : GraphStore
    min_persons : minimum cluster size to flag (default 2)

    Returns
    -------
    list[ClusterResult]
        Sorted by number of persons descending.
    """
    return _detect_cluster(
        store,
        cluster_prop="shared_address_cluster_id",
        cluster_type="address",
        min_persons=min_persons,
    )


# ── Internal cluster helper ───────────────────────────────────────────────────


def _detect_cluster(
    store: GraphStore,
    cluster_prop: str,
    cluster_type: str,
    min_persons: int,
) -> list[ClusterResult]:
    """
    Generic cluster detection over a named person property.

    Builds a cluster_id → [person_ids] map in one pass, then collects the
    union of cases each person appears in via all role edges.

    Parameters
    ----------
    store        : GraphStore
    cluster_prop : property key on Person nodes (e.g. "shared_phone_cluster_id")
    cluster_type : human-readable type label
    min_persons  : minimum cluster size to report

    Returns
    -------
    list[ClusterResult]
        Sorted by person count descending.
    """
    # Pass 1 — group persons by cluster id
    cluster_persons: dict[str, list[str]] = {}
    for node in iter_nodes_by_type(store, _PERSON):
        cid = prop_str(node, cluster_prop)
        if cid:
            cluster_persons.setdefault(cid, []).append(node.node_id)

    # Pass 2 — for clusters that qualify, collect case ids
    _ROLE_EDGES = {"ACCUSED_IN", "VICTIM_IN", "COMPLAINANT_IN", "WITNESS_IN"}
    results: list[ClusterResult] = []

    for cluster_id, person_ids in cluster_persons.items():
        if len(person_ids) < min_persons:
            continue

        case_ids: set[str] = set()
        for pid in person_ids:
            for edge in store.adj.get(pid, []):
                if edge.edge_type in _ROLE_EDGES:
                    case_ids.add(edge.target_id)

        results.append(
            ClusterResult(
                cluster_id=cluster_id,
                cluster_type=cluster_type,
                person_ids=sorted(person_ids),
                case_ids=sorted(case_ids),
                reason=(
                    f"{len(person_ids)} persons share {cluster_type} cluster "
                    f"'{cluster_id}' across {len(case_ids)} case(s)"
                ),
            )
        )

    results.sort(key=lambda r: len(r.person_ids), reverse=True)
    return results


# ── Pattern: high workload officers ──────────────────────────────────────────


def detect_high_workload_officers(
    store: GraphStore,
    min_cases: int = 5,
) -> list[OfficerWorkloadResult]:
    """
    Detect officers assigned to ``min_cases`` or more cases.

    Uses ``INVESTIGATED_BY`` edges (Case → Officer).

    Parameters
    ----------
    store     : GraphStore
    min_cases : minimum case count to flag (default 5)

    Returns
    -------
    list[OfficerWorkloadResult]
        Sorted by case_count descending.
    """
    workload = officer_workload(store)
    results: list[OfficerWorkloadResult] = []

    for oid, count in workload.items():
        if count < min_cases:
            continue
        node = store.nodes.get(oid)
        badge = (
            prop_str(node, "badge_number") or prop_str(node, "full_name") or oid
            if node is not None
            else oid
        )
        results.append(
            OfficerWorkloadResult(
                officer_id=oid,
                badge_number=badge,
                case_count=count,
                reason=f"Officer {badge} has {count} cases (threshold: {min_cases})",
            )
        )

    results.sort(key=lambda r: r.case_count, reverse=True)
    return results


# ── Pattern: dependency hotspots ──────────────────────────────────────────────


def detect_dependency_hotspots(
    store: GraphStore,
    min_pending: int = 3,
) -> list[DependencyHotspotResult]:
    """
    Detect cases with ``min_pending`` or more **pending** dependencies.

    Reads dependency status from Dependency node properties.
    Single pass: builds case_id → [dep_nodes] from CASE_HAS_DEPENDENCY edges,
    then counts pending status.

    Parameters
    ----------
    store       : GraphStore
    min_pending : minimum pending dependency count to flag (default 3)

    Returns
    -------
    list[DependencyHotspotResult]
        Sorted by pending_count descending.
    """
    # Build case_id → [dep_node_ids]
    case_dep_map: dict[str, list[str]] = {}
    for edge in get_edges_of_type(store, _CASE_HAS_DEPENDENCY):
        case_dep_map.setdefault(edge.source_id, []).append(edge.target_id)

    results: list[DependencyHotspotResult] = []
    for case_id, dep_ids in case_dep_map.items():
        pending_count = 0
        for did in dep_ids:
            dep_node = store.nodes.get(did)
            if dep_node is not None and prop_str(dep_node, "status") == "pending":
                pending_count += 1

        if pending_count < min_pending:
            continue

        case_node = store.nodes.get(case_id)
        fir = (
            prop_str(case_node, "fir_number") or case_id
            if case_node is not None
            else case_id
        )
        results.append(
            DependencyHotspotResult(
                case_id=case_id,
                fir_number=fir,
                pending_count=pending_count,
                total_dependency_count=len(dep_ids),
                reason=(
                    f"Case {fir} has {pending_count} pending dependencies "
                    f"(total: {len(dep_ids)})"
                ),
            )
        )

    results.sort(key=lambda r: r.pending_count, reverse=True)
    return results


# ── Pattern: district hotspots ────────────────────────────────────────────────


def detect_district_hotspots(
    store: GraphStore,
    min_cases: int = 50,
) -> list[DistrictHotspotResult]:
    """
    Detect districts with ``min_cases`` or more cases registered.

    Single pass over Case nodes.

    Parameters
    ----------
    store     : GraphStore
    min_cases : minimum case count to flag a district (default 50)

    Returns
    -------
    list[DistrictHotspotResult]
        Sorted by case_count descending.
    """
    district_counts: dict[str, int] = {}
    for node in iter_nodes_by_type(store, _CASE):
        district = prop_str(node, "district", default="unknown")
        district_counts[district] = district_counts.get(district, 0) + 1

    results: list[DistrictHotspotResult] = []
    for district, count in district_counts.items():
        if count >= min_cases:
            results.append(
                DistrictHotspotResult(
                    district=district,
                    case_count=count,
                    reason=f"District '{district}' has {count} cases (threshold: {min_cases})",
                )
            )

    results.sort(key=lambda r: r.case_count, reverse=True)
    return results


# ── Pattern: temporal hotspots ────────────────────────────────────────────────


def detect_temporal_hotspots(
    store: GraphStore,
    min_cases: int = 3,
) -> list[TemporalHotspotResult]:
    """
    Detect dates with ``min_cases`` or more cases registered.

    Single pass over Case nodes.

    Parameters
    ----------
    store     : GraphStore
    min_cases : minimum case count to flag a date (default 3)

    Returns
    -------
    list[TemporalHotspotResult]
        Sorted by case_count descending.
    """
    from datetime import datetime

    date_counts: dict[str, int] = {}
    for node in iter_nodes_by_type(store, "Case"):
        reported_at = prop_str(node, "reported_at")
        if not reported_at or reported_at.lower() == "none":
            continue

        is_iso = False
        try:
            datetime.fromisoformat(reported_at)
            is_iso = True
        except ValueError:
            pass

        date_key = reported_at[:10] if is_iso else reported_at
        date_counts[date_key] = date_counts.get(date_key, 0) + 1

    results: list[TemporalHotspotResult] = []
    for date, count in date_counts.items():
        if count >= min_cases:
            results.append(
                TemporalHotspotResult(
                    date=date,
                    case_count=count,
                    reason=f"Date '{date}' has {count} cases (threshold: {min_cases})",
                )
            )

    results.sort(key=lambda r: (-r.case_count, r.date))
    return results


# ── Pattern: resolved repeat accused ──────────────────────────────────────────


@dataclass
class ResolvedRepeatAccusedResult:
    """
    A resolved person accused in multiple cases across duplicate nodes.

    Attributes
    ----------
    canonical_person_name : str — canonical (longest) name found for the person
    person_ids            : list of physical Person node IDs grouped under this entity
    case_ids              : union of case node IDs the person is accused in
    case_count            : number of unique cases (len(case_ids))
    reason                : human-readable explanation
    """

    canonical_person_name: str
    person_ids: list[str]
    case_ids: list[str]
    case_count: int
    reason: str


def detect_repeat_accused_resolved(
    store: GraphStore,
    min_cases: int = 2,
    confidence_threshold: float = 0.70,
) -> list[ResolvedRepeatAccusedResult]:
    """
    Detect repeat accused persons by clustering Person nodes using Entity Resolution.
    
    This clusters individuals who have multiple Person nodes in the graph due to
    spelling variations, alias usage, or other data entry differences.

    Parameters
    ----------
    store                : GraphStore
    min_cases            : minimum number of unique cases to flag (default 2)
    confidence_threshold : threshold above which entities are grouped together

    Returns
    -------
    list[ResolvedRepeatAccusedResult]
        Sorted by case_count descending.
    """
    # 1. Collect all Person nodes that have ACCUSED_IN edges
    accused_persons: set[str] = set()
    person_cases: dict[str, set[str]] = {}
    for edge in get_edges_of_type(store, _ACCUSED_IN):
        pid = edge.source_id
        cid = edge.target_id
        accused_persons.add(pid)
        person_cases.setdefault(pid, set()).add(cid)

    # 2. Cluster Person nodes
    visited: set[str] = set()
    clusters: list[list[str]] = []

    for pid in sorted(accused_persons):
        if pid in visited:
            continue

        node = store.nodes.get(pid)
        if not node:
            continue

        # Initialize cluster with current person
        cluster = [pid]
        visited.add(pid)

        # Build query for entity resolution
        query = {
            "full_name": node.properties.get("full_name", ""),
            "phone_number": node.properties.get("phone_number", ""),
            "address_text": node.properties.get("address_text", ""),
            "aliases": node.properties.get("aliases", []),
        }

        # Find other candidate matches in the store
        matches = resolve_person(
            store,
            query,
            confidence_threshold=confidence_threshold,
            candidate_limit=50,
        )
        for match in matches:
            mid = match.matched_node_id
            if (
                mid in accused_persons
                and mid not in visited
                and match.confidence >= confidence_threshold
            ):
                cluster.append(mid)
                visited.add(mid)

        clusters.append(cluster)

    # 3. For each cluster, calculate the union of case_ids and build results
    results: list[ResolvedRepeatAccusedResult] = []
    for cluster in clusters:
        union_case_ids: set[str] = set()
        for pid in cluster:
            union_case_ids.update(person_cases.get(pid, set()))

        if len(union_case_ids) >= min_cases:
            # Pick canonical name
            canonical_name = ""
            for pid in cluster:
                p_node = store.nodes.get(pid)
                if p_node:
                    p_name = p_node.properties.get("full_name", "")
                    if len(p_name) > len(canonical_name):
                        canonical_name = p_name
            if not canonical_name:
                canonical_name = "Unknown Accused"

            results.append(
                ResolvedRepeatAccusedResult(
                    canonical_person_name=canonical_name,
                    person_ids=sorted(cluster),
                    case_ids=sorted(union_case_ids),
                    case_count=len(union_case_ids),
                    reason=(
                        f"Resolved accused '{canonical_name}' (via {len(cluster)} entity nodes) "
                        f"is accused in {len(union_case_ids)} case(s)"
                    ),
                )
            )

    results.sort(key=lambda r: (-r.case_count, r.canonical_person_name))
    return results
