"""
graph/algorithms/utils.py

Shared in-memory graph representation and low-level helpers used by
every other algorithm module.

Design decisions
----------------
* ``GraphStore`` is a plain dataclass — cheap to construct, easy to inspect.
* Adjacency lists are keyed by *string* node-ids (str(UUID)) to avoid repeated
  UUID parsing inside hot loops.
* ``build_graph_store`` is the **only** place that accepts the synthetic
  ``SyntheticNodeRecord`` / ``SyntheticEdgeRecord`` Pydantic types from
  ``synthetic_data.configs``.  All other algorithm functions receive only a
  ``GraphStore``; they never import from ``synthetic_data``.
* BFS is iterative (no recursion) and accepts a ``max_depth`` guard so
  callers never accidentally walk the whole graph.

No database calls.  No API code.  No ML.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Iterator


# ── Core data structures ──────────────────────────────────────────────────────


@dataclass(slots=True)
class AdjEdge:
    """A single directed edge stored in the adjacency index."""

    edge_type: str       # GraphRelationshipType.value  e.g. "ACCUSED_IN"
    source_id: str       # str(UUID)
    target_id: str       # str(UUID)
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NodeRecord:
    """
    A single graph node as seen by the algorithm layer.

    ``entity_type``  — GraphEntityType.value  e.g. "Case"
    ``properties``   — the full properties dict from SyntheticNodeRecord
    ``node_id``      — str(UUID), same as the key in GraphStore.nodes
    """

    node_id: str
    entity_type: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphStore:
    """
    Unified in-memory investigation graph.

    All look-ups are O(1) average via dict.  Adjacency lists give O(degree)
    neighbour iteration without scanning the full edge list.

    Attributes
    ----------
    nodes       : node_id → NodeRecord
    adj         : node_id → outgoing AdjEdge list
    radj        : node_id → incoming AdjEdge list
    edge_index  : edge_type → list[AdjEdge]  (all edges of that relationship)
    """

    nodes: dict[str, NodeRecord] = field(default_factory=dict)
    adj: dict[str, list[AdjEdge]] = field(default_factory=dict)
    radj: dict[str, list[AdjEdge]] = field(default_factory=dict)
    edge_index: dict[str, list[AdjEdge]] = field(default_factory=dict)


# ── Builder ───────────────────────────────────────────────────────────────────


def build_graph_store(nodes: Iterable[Any], edges: Iterable[Any]) -> GraphStore:
    """
    Convert raw ``SyntheticNodeRecord`` / ``SyntheticEdgeRecord`` collections
    into a ``GraphStore``.

    Accepts any objects that expose:
    - node: ``.id`` (UUID or str), ``.entity_type.value`` (str), ``.properties`` (dict)
    - edge: ``.edge_type.value`` (str), ``.source_id`` (UUID or str),
            ``.target_id`` (UUID or str), ``.properties`` (dict)

    Duplicate edges (same type + source + target) are silently deduplicated.

    Parameters
    ----------
    nodes : iterable of SyntheticNodeRecord
    edges : iterable of SyntheticEdgeRecord

    Returns
    -------
    GraphStore
        Fully indexed, ready for algorithm functions.
    """
    store = GraphStore()
    seen_edges: set[tuple[str, str, str]] = set()

    for raw in nodes:
        if hasattr(raw, "node_id"):          # NodeRecord
            nid = safe_str(raw.node_id)
        elif hasattr(raw, "id"):             # Fake/Synthetic node
            nid = safe_str(raw.id)
        else:                                # Legacy wrapper
            nid = safe_str(raw.entity.id)
        
        if hasattr(raw, "entity_type"):
            entity_type = (
                raw.entity_type.value
                if hasattr(raw.entity_type, "value")
                else str(raw.entity_type)
            )
        else:
            entity_type = raw.entity.entity_type.value

        if hasattr(raw, "properties"):
            properties = dict(raw.properties)
        else:
            properties = dict(raw.entity.properties)

        store.nodes[nid] = NodeRecord(
            node_id=nid,
            entity_type=entity_type,
            properties=properties,
        )

    for raw in edges:
        etype = (
            raw.edge_type.value
            if hasattr(raw.edge_type, "value")
            else str(raw.edge_type)
        )
        src = safe_str(raw.source_id)
        tgt = safe_str(raw.target_id)

        key = (etype, src, tgt)
        if key in seen_edges:
            continue
        seen_edges.add(key)

        props = dict(raw.properties) if hasattr(raw, "properties") else {}
        edge = AdjEdge(edge_type=etype, source_id=src, target_id=tgt, properties=props)

        # Ensure adjacency lists exist even for dangling references
        store.adj.setdefault(src, [])
        store.radj.setdefault(src, [])
        store.adj.setdefault(tgt, [])
        store.radj.setdefault(tgt, [])

        store.adj[src].append(edge)
        store.radj[tgt].append(edge)
        store.edge_index.setdefault(etype, []).append(edge)

    return store


# ── Node helpers ──────────────────────────────────────────────────────────────


def get_node(store: GraphStore, node_id: str) -> NodeRecord | None:
    """
    Safe O(1) node lookup.

    Returns ``None`` if *node_id* is not present rather than raising.
    """
    return store.nodes.get(safe_str(node_id))


def nodes_of_type(store: GraphStore, entity_type: str) -> list[NodeRecord]:
    """
    Return all nodes whose ``entity_type`` matches *entity_type*.

    O(N) scan — call once and cache the result when iterating repeatedly.
    """
    return [n for n in store.nodes.values() if n.entity_type == entity_type]


# ── Edge helpers ──────────────────────────────────────────────────────────────


def get_edges_of_type(store: GraphStore, edge_type: str) -> list[AdjEdge]:
    """Return all edges of *edge_type*.  Empty list if none exist."""
    return store.edge_index.get(edge_type, [])


def neighbors(
    store: GraphStore,
    node_id: str,
    edge_types: Iterable[str] | None = None,
    direction: str = "out",
) -> list[NodeRecord]:
    """
    Return neighbour ``NodeRecord``s reachable from *node_id*.

    Parameters
    ----------
    store       : GraphStore
    node_id     : source/target node
    edge_types  : restrict to these relationship types; ``None`` = all types
    direction   : ``"out"`` (follow outgoing), ``"in"`` (follow incoming),
                  ``"both"`` (union)

    Returns
    -------
    list[NodeRecord]
        De-duplicated list of reachable neighbours that exist in the store.
        Dangling edge targets (not in ``store.nodes``) are silently skipped.
    """
    nid = safe_str(node_id)
    allowed: set[str] | None = set(edge_types) if edge_types is not None else None

    result_ids: set[str] = set()

    def _collect(adj_edges: list[AdjEdge], peer_field: str) -> None:
        for edge in adj_edges:
            if allowed is not None and edge.edge_type not in allowed:
                continue
            peer = getattr(edge, peer_field)
            if peer != nid:
                result_ids.add(peer)

    if direction in ("out", "both"):
        _collect(store.adj.get(nid, []), "target_id")
    if direction in ("in", "both"):
        _collect(store.radj.get(nid, []), "source_id")

    return [store.nodes[i] for i in result_ids if i in store.nodes]


def neighbor_ids(
    store: GraphStore,
    node_id: str,
    edge_types: Iterable[str] | None = None,
    direction: str = "out",
) -> set[str]:
    """
    Like ``neighbors`` but returns a ``set[str]`` of ids (no NodeRecord fetch).

    Prefer this in hot paths where only the id is needed.
    """
    nid = safe_str(node_id)
    allowed: set[str] | None = set(edge_types) if edge_types is not None else None
    result: set[str] = set()

    def _collect(adj_edges: list[AdjEdge], peer_field: str) -> None:
        for edge in adj_edges:
            if allowed is not None and edge.edge_type not in allowed:
                continue
            peer = getattr(edge, peer_field)
            if peer != nid:
                result.add(peer)

    if direction in ("out", "both"):
        _collect(store.adj.get(nid, []), "target_id")
    if direction in ("in", "both"):
        _collect(store.radj.get(nid, []), "source_id")

    return result


# ── BFS ───────────────────────────────────────────────────────────────────────


def bfs(
    store: GraphStore,
    start_id: str,
    edge_types: Iterable[str] | None = None,
    direction: str = "out",
    max_depth: int = 6,
) -> list[str]:
    """
    Iterative BFS from *start_id* up to *max_depth* hops.

    Returns an ordered list of visited node ids (excluding *start_id* itself).
    Visits each node at most once (shortest-path guarantee).

    Parameters
    ----------
    store      : GraphStore
    start_id   : root node id
    edge_types : restrict traversal to these edge types; ``None`` = all
    direction  : ``"out"``, ``"in"``, or ``"both"``
    max_depth  : maximum number of hops from start (inclusive)
    """
    start = safe_str(start_id)
    if start not in store.nodes:
        return []

    visited: set[str] = {start}
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    order: list[str] = []

    allowed: set[str] | None = set(edge_types) if edge_types is not None else None

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue

        adj_out = store.adj.get(current, []) if direction in ("out", "both") else []
        adj_in = store.radj.get(current, []) if direction in ("in", "both") else []

        for edge in adj_out:
            if allowed is not None and edge.edge_type not in allowed:
                continue
            peer = edge.target_id
            if peer not in visited and peer in store.nodes:
                visited.add(peer)
                order.append(peer)
                queue.append((peer, depth + 1))

        for edge in adj_in:
            if allowed is not None and edge.edge_type not in allowed:
                continue
            peer = edge.source_id
            if peer not in visited and peer in store.nodes:
                visited.add(peer)
                order.append(peer)
                queue.append((peer, depth + 1))

    return order


def bfs_with_depth(
    store: GraphStore,
    start_id: str,
    edge_types: Iterable[str] | None = None,
    direction: str = "out",
    max_depth: int = 6,
) -> list[tuple[str, int]]:
    """
    Like ``bfs`` but returns ``(node_id, depth)`` pairs.

    Useful for ``get_subgraph`` which needs to know at what depth each node
    was discovered.
    """
    start = safe_str(start_id)
    if start not in store.nodes:
        return []

    visited: set[str] = {start}
    queue: deque[tuple[str, int]] = deque([(start, 0)])
    result: list[tuple[str, int]] = [(start, 0)]

    allowed: set[str] | None = set(edge_types) if edge_types is not None else None

    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue

        adj_out = store.adj.get(current, []) if direction in ("out", "both") else []
        adj_in = store.radj.get(current, []) if direction in ("in", "both") else []

        for edge in adj_out:
            if allowed is not None and edge.edge_type not in allowed:
                continue
            peer = edge.target_id
            if peer not in visited and peer in store.nodes:
                visited.add(peer)
                result.append((peer, depth + 1))
                queue.append((peer, depth + 1))

        for edge in adj_in:
            if allowed is not None and edge.edge_type not in allowed:
                continue
            peer = edge.source_id
            if peer not in visited and peer in store.nodes:
                visited.add(peer)
                result.append((peer, depth + 1))
                queue.append((peer, depth + 1))

    return result


# ── String normalisation ──────────────────────────────────────────────────────


def safe_str(value: Any) -> str:
    """
    Normalise a node / edge id to a plain ``str``.

    Accepts ``str``, ``uuid.UUID``, or anything with a ``__str__``.
    This is the single point where UUID → str conversion happens so the
    rest of the algorithms never import ``uuid``.
    """
    return str(value)


# ── Property accessors ────────────────────────────────────────────────────────


def prop(node: NodeRecord, key: str, default: Any = None) -> Any:
    """
    Convenience accessor for ``node.properties[key]`` with a default.

    Prefer this over direct dict access in algorithm code to avoid
    ``KeyError`` on sparse/optional properties.
    """
    return node.properties.get(key, default)


def prop_str(node: NodeRecord, key: str, default: str = "") -> str:
    """Like ``prop`` but always returns a ``str``."""
    return str(node.properties.get(key, default))


def prop_int(node: NodeRecord, key: str, default: int = 0) -> int:
    """Like ``prop`` but casts to ``int``."""
    v = node.properties.get(key, default)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# ── Iterator helpers ──────────────────────────────────────────────────────────


def iter_nodes_by_type(store: GraphStore, entity_type: str) -> Iterator[NodeRecord]:
    """Lazy iterator over all nodes of a given entity type."""
    for node in store.nodes.values():
        if node.entity_type == entity_type:
            yield node


def group_edges_by_source(
    edges: Iterable[AdjEdge],
) -> dict[str, list[AdjEdge]]:
    """
    Group a flat edge list by ``source_id``.

    Used in aggregation and pattern-detection to build per-node edge maps
    without re-scanning the full index repeatedly.
    """
    result: dict[str, list[AdjEdge]] = {}
    for edge in edges:
        result.setdefault(edge.source_id, []).append(edge)
    return result


def group_edges_by_target(
    edges: Iterable[AdjEdge],
) -> dict[str, list[AdjEdge]]:
    """Group a flat edge list by ``target_id``."""
    result: dict[str, list[AdjEdge]] = {}
    for edge in edges:
        result.setdefault(edge.target_id, []).append(edge)
    return result
