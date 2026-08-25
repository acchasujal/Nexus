"""
graph/algorithms/traversals.py

All deterministic graph traversal functions for NEXUS.

Design rules
------------
* Every function accepts a ``GraphStore`` — no database calls, no HTTP.
* BFS is used wherever a multi-hop walk is needed.
* Functions that look up a single node return ``NodeRecord | None``.
* Functions that return collections return ``list[NodeRecord]`` (empty list,
  never ``None``) or a typed dataclass.
* IDs are always ``str``; callers may pass ``str`` or ``UUID`` — ``safe_str``
  normalises them.

Entity type literals used here come from ``GraphEntityType.value`` strings
defined in ``backend/app/core/graph/enums.py`` to avoid importing the enum
inside this pure-algorithm module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Sequence

from backend.app.core.graph.algorithms.utils import (
    AdjEdge,
    GraphStore,
    NodeRecord,
    bfs_with_depth,
    get_node,
    neighbor_ids,
    neighbors,
    safe_str,
)

# ── Edge type constants (mirrors GraphRelationshipType.value) ─────────────────

_ACCUSED_IN = "ACCUSED_IN"
_VICTIM_IN = "VICTIM_IN"
_COMPLAINANT_IN = "COMPLAINANT_IN"
_WITNESS_IN = "WITNESS_IN"
_INVESTIGATED_BY = "INVESTIGATED_BY"
_CASE_HAS_DEPENDENCY = "CASE_HAS_DEPENDENCY"
_CASE_HAS_CLOCK = "CASE_HAS_CLOCK"
_CASE_HAS_EVIDENCE = "CASE_HAS_EVIDENCE"
_CASE_HAS_COURT = "CASE_HAS_COURT"
_CASE_HAS_CRIME_HEAD = "CASE_HAS_CRIME_HEAD"
_CASE_HAS_CRIME_SUB_HEAD = "CASE_HAS_CRIME_SUB_HEAD"
_LINKED_TO = "LINKED_TO"
_CO_ACCUSED_WITH = "CO_ACCUSED_WITH"
_CHARGED_UNDER = "CHARGED_UNDER"
_OCCURRED_IN = "OCCURRED_IN"

# Entity type string literals (GraphEntityType.value)
_CASE = "Case"
_PERSON = "Person"
_OFFICER = "Officer"
_DEPENDENCY = "Dependency"
_CLOCK_INSTANCE = "ClockInstance"
_EVIDENCE = "Evidence"


# ── Return types ──────────────────────────────────────────────────────────────


@dataclass
class SubgraphResult:
    """
    A node-induced subgraph rooted at a given node.

    Attributes
    ----------
    root_id : str
        The starting node id.
    depth   : int
        Maximum BFS depth used.
    nodes   : list[NodeRecord]
        All nodes reachable within *depth* hops (including root).
    edges   : list[AdjEdge]
        All edges whose *both* endpoints are inside *nodes*.
    """

    root_id: str
    depth: int
    nodes: list[NodeRecord] = field(default_factory=list)
    edges: list[AdjEdge] = field(default_factory=list)


# ── Single-node lookups ───────────────────────────────────────────────────────


def get_case(store: GraphStore, case_id: str) -> NodeRecord | None:
    """
    Return the ``Case`` node for *case_id*, or ``None`` if not found.

    Lookup order:
    1. Try UUID lookup using get_node() (keep existing fast path).
    2. If not found, iterate over Case nodes only.
    3. Compare node.properties["fir_number"] with the supplied identifier.
    4. Compare node.properties["case_number"] with the supplied identifier.
    5. Return the matching NodeRecord.
    6. Otherwise return None.

    Parameters
    ----------
    store   : GraphStore
    case_id : str | UUID

    Returns
    -------
    NodeRecord | None
    """
    node = get_node(store, case_id)
    if node is not None and node.entity_type == _CASE:
        return node

    target_id = safe_str(case_id)
    for n in store.nodes.values():
        if n.entity_type != _CASE:
            continue
        if n.properties.get("fir_number") == target_id:
            return n
        if n.properties.get("case_number") == target_id:
            return n

    return None


def get_person(store: GraphStore, person_id: str) -> NodeRecord | None:
    """
    Return the ``Person`` node for *person_id*, or ``None`` if not found.

    Parameters
    ----------
    store     : GraphStore
    person_id : str | UUID

    Returns
    -------
    NodeRecord | None
    """
    node = get_node(store, person_id)
    if node is None or node.entity_type != _PERSON:
        return None
    return node


# ── Case-centric traversals ───────────────────────────────────────────────────


def get_related_cases(store: GraphStore, case_id: str) -> list[NodeRecord]:
    """
    Return all cases linked to *case_id* via the derived ``LINKED_TO`` edge.

    ``LINKED_TO`` is bidirectional (any case in a cluster may be the source
    or target), so this function checks both outgoing and incoming edges.

    Parameters
    ----------
    store   : GraphStore
    case_id : str | UUID

    Returns
    -------
    list[NodeRecord]
        Related case nodes; empty list if none exist or *case_id* is unknown.
    """
    nid = safe_str(case_id)
    if nid not in store.nodes:
        return []

    linked_ids = neighbor_ids(
        store,
        nid,
        edge_types=[_LINKED_TO],
        direction="both",
    )
    return [
        store.nodes[lid]
        for lid in linked_ids
        if lid in store.nodes and store.nodes[lid].entity_type == _CASE
    ]


def get_co_accused(store: GraphStore, case_id: str) -> list[NodeRecord]:
    """
    Return all persons accused in *case_id* (co-accused set).

    Uses the ``ACCUSED_IN`` edge (Person → Case).  Finding persons whose
    outgoing ``ACCUSED_IN`` edge targets *case_id* requires scanning the
    *incoming* ``ACCUSED_IN`` edges of *case_id*.

    Parameters
    ----------
    store   : GraphStore
    case_id : str | UUID

    Returns
    -------
    list[NodeRecord]
        Person nodes accused in *case_id*; empty list if none.
    """
    nid = safe_str(case_id)
    if nid not in store.nodes:
        return []

    accused_ids = neighbor_ids(
        store,
        nid,
        edge_types=[_ACCUSED_IN],
        direction="in",
    )
    return [
        store.nodes[aid]
        for aid in accused_ids
        if aid in store.nodes and store.nodes[aid].entity_type == _PERSON
    ]


def get_cases_for_person(store: GraphStore, person_id: str) -> list[NodeRecord]:
    """
    Return all cases in which *person_id* appears (any role).

    Roles considered: accused, victim, complainant, witness.

    Parameters
    ----------
    store     : GraphStore
    person_id : str | UUID

    Returns
    -------
    list[NodeRecord]
        Case nodes; empty list if none.
    """
    nid = safe_str(person_id)
    if nid not in store.nodes:
        return []

    role_edge_types = [_ACCUSED_IN, _VICTIM_IN, _COMPLAINANT_IN, _WITNESS_IN]
    case_ids = neighbor_ids(store, nid, edge_types=role_edge_types, direction="out")
    return [
        store.nodes[cid]
        for cid in case_ids
        if cid in store.nodes and store.nodes[cid].entity_type == _CASE
    ]


def get_officer_cases(store: GraphStore, officer_id: str) -> list[NodeRecord]:
    """
    Return all cases investigated by *officer_id*.

    The ``INVESTIGATED_BY`` edge runs Case → Officer.
    This function follows the edge *in reverse*: it looks for Cases whose
    outgoing ``INVESTIGATED_BY`` edge targets *officer_id*.

    Parameters
    ----------
    store      : GraphStore
    officer_id : str | UUID

    Returns
    -------
    list[NodeRecord]
        Case nodes; empty list if *officer_id* not found or has no cases.
    """
    oid = safe_str(officer_id)
    if oid not in store.nodes:
        return []

    case_ids = neighbor_ids(store, oid, edge_types=[_INVESTIGATED_BY], direction="in")
    return [
        store.nodes[cid]
        for cid in case_ids
        if cid in store.nodes and store.nodes[cid].entity_type == _CASE
    ]


def get_dependency_chain(store: GraphStore, case_id: str) -> list[NodeRecord]:
    """
    Return all ``Dependency`` nodes attached to *case_id*.

    Follows ``CASE_HAS_DEPENDENCY`` outgoing edges (Case → Dependency).

    Parameters
    ----------
    store   : GraphStore
    case_id : str | UUID

    Returns
    -------
    list[NodeRecord]
        Dependency nodes; empty list if none.
    """
    nid = safe_str(case_id)
    if nid not in store.nodes:
        return []

    dep_ids = neighbor_ids(store, nid, edge_types=[_CASE_HAS_DEPENDENCY], direction="out")
    return [
        store.nodes[did]
        for did in dep_ids
        if did in store.nodes and store.nodes[did].entity_type == _DEPENDENCY
    ]


def get_clock_instances(store: GraphStore, case_id: str) -> list[NodeRecord]:
    """
    Return all ``ClockInstance`` nodes attached to *case_id*.

    Follows ``CASE_HAS_CLOCK`` outgoing edges (Case → ClockInstance).

    Parameters
    ----------
    store   : GraphStore
    case_id : str | UUID

    Returns
    -------
    list[NodeRecord]
        ClockInstance nodes sorted by ``days_remaining`` ascending (most
        urgent first).  Empty list if none.
    """
    nid = safe_str(case_id)
    if nid not in store.nodes:
        return []

    clock_ids = neighbor_ids(store, nid, edge_types=[_CASE_HAS_CLOCK], direction="out")
    clocks = [
        store.nodes[cid]
        for cid in clock_ids
        if cid in store.nodes and store.nodes[cid].entity_type == _CLOCK_INSTANCE
    ]
    # Sort by days_remaining ascending (overdue / most urgent first)
    clocks.sort(key=lambda c: c.properties.get("days_remaining", 9999))
    return clocks


# ── Generic traversals ────────────────────────────────────────────────────────


def get_neighbors(store: GraphStore, node_id: str) -> list[NodeRecord]:
    """
    Return all immediate (1-hop) outgoing neighbours of *node_id*.

    Parameters
    ----------
    store   : GraphStore
    node_id : str | UUID

    Returns
    -------
    list[NodeRecord]
        All nodes reachable via any outgoing edge from *node_id*.
        Empty list if *node_id* is unknown or has no outgoing edges.
    """
    nid = safe_str(node_id)
    if nid not in store.nodes:
        return []
    return neighbors(store, nid, edge_types=None, direction="out")


def get_subgraph(
    store: GraphStore,
    node_id: str,
    depth: int = 2,
) -> SubgraphResult:
    """
    Return the node-induced subgraph reachable from *node_id* within *depth* hops.

    Uses iterative BFS in both directions (outgoing + incoming) so the
    subgraph includes the full neighbourhood regardless of edge orientation.

    Parameters
    ----------
    store   : GraphStore
    node_id : str | UUID
    depth   : maximum BFS hops (default 2, max enforced at 8)

    Returns
    -------
    SubgraphResult
        Contains all reachable nodes and the edges that connect them.
        If *node_id* is unknown, returns an empty ``SubgraphResult``.
    """
    nid = safe_str(node_id)
    depth = min(depth, 8)  # safety cap

    if nid not in store.nodes:
        return SubgraphResult(root_id=nid, depth=depth)

    # BFS to collect all node ids in the subgraph
    visited_with_depth = bfs_with_depth(
        store,
        nid,
        edge_types=None,
        direction="both",
        max_depth=depth,
    )
    subgraph_ids: set[str] = {vid for vid, _ in visited_with_depth}
    subgraph_nodes = [store.nodes[vid] for vid in subgraph_ids if vid in store.nodes]

    # Collect edges whose both endpoints are in the subgraph
    subgraph_edges: list[AdjEdge] = []
    seen_edge_keys: set[tuple[str, str, str]] = set()
    for nid_inner in subgraph_ids:
        for edge in store.adj.get(nid_inner, []):
            if edge.target_id in subgraph_ids:
                key = (edge.edge_type, edge.source_id, edge.target_id)
                if key not in seen_edge_keys:
                    seen_edge_keys.add(key)
                    subgraph_edges.append(edge)

    return SubgraphResult(
        root_id=nid,
        depth=depth,
        nodes=subgraph_nodes,
        edges=subgraph_edges,
    )


# ── Convenience: multi-case batch traversals ──────────────────────────────────


def get_cases_for_persons(
    store: GraphStore,
    person_ids: Sequence[str],
) -> dict[str, list[NodeRecord]]:
    """
    Batch version of ``get_cases_for_person``.

    Parameters
    ----------
    store      : GraphStore
    person_ids : sequence of person node ids

    Returns
    -------
    dict[str, list[NodeRecord]]
        person_id → list of Case nodes.  Missing persons map to empty lists.
    """
    return {pid: get_cases_for_person(store, pid) for pid in person_ids}


def get_evidence_for_case(store: GraphStore, case_id: str) -> list[NodeRecord]:
    """
    Return all ``Evidence`` nodes attached to *case_id*.

    Follows ``CASE_HAS_EVIDENCE`` outgoing edges.

    Parameters
    ----------
    store   : GraphStore
    case_id : str | UUID

    Returns
    -------
    list[NodeRecord]
        Evidence nodes; empty list if none.
    """
    nid = safe_str(case_id)
    if nid not in store.nodes:
        return []

    ev_ids = neighbor_ids(store, nid, edge_types=[_CASE_HAS_EVIDENCE], direction="out")
    return [
        store.nodes[eid]
        for eid in ev_ids
        if eid in store.nodes and store.nodes[eid].entity_type == _EVIDENCE
    ]


def get_sections_for_case(store: GraphStore, case_id: str) -> list[NodeRecord]:
    """
    Return all ``Section`` nodes a case is charged under.

    Follows ``CHARGED_UNDER`` outgoing edges (Case → Section).

    Parameters
    ----------
    store   : GraphStore
    case_id : str | UUID

    Returns
    -------
    list[NodeRecord]
        Section nodes; empty list if none.
    """
    nid = safe_str(case_id)
    if nid not in store.nodes:
        return []

    sec_ids = neighbor_ids(store, nid, edge_types=[_CHARGED_UNDER], direction="out")
    return [
        store.nodes[sid]
        for sid in sec_ids
        if sid in store.nodes
    ]
