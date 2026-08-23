"""
graph/algorithms/clustering.py

NetworkX-based clustering and centrality algorithms.

Design rules
------------
* The ``GraphStore`` is converted to a ``networkx.DiGraph`` **once** per
  call via ``_to_networkx``.  Callers that need multiple clustering metrics
  should convert once and pass the DiGraph to the private helpers, or
  simply call the public functions independently.
* All algorithms are deterministic.  For betweenness centrality, exact
  computation is used by default; an optional ``sample_k`` parameter
  enables approximate BFS-sample mode for large graphs.
* ``ClusterSummary`` provides human-readable descriptions so the output can
  feed explanations directly.

Requires
--------
    networkx >= 3.0   (``pip install networkx``)

No database calls.  No API code.  No ML.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

try:
    import networkx as nx  # type: ignore[import]
    _NX_AVAILABLE = True
except ImportError:  # pragma: no cover
    nx = None  # type: ignore[assignment]
    _NX_AVAILABLE = False

from backend.app.core.graph.algorithms.utils import GraphStore, safe_str


# ── NetworkX bridge ───────────────────────────────────────────────────────────


def _require_nx() -> None:
    """Raise a clear error if NetworkX is not installed."""
    if not _NX_AVAILABLE:
        raise ImportError(
            "NetworkX is required for clustering algorithms. "
            "Install it with: pip install networkx"
        )


def _to_networkx(store: GraphStore) -> Any:
    """
    Build a ``networkx.DiGraph`` from a ``GraphStore``.

    Node attributes preserved: ``entity_type``.
    Edge attributes preserved: ``edge_type``.

    O(N + E).
    """
    _require_nx()
    G = nx.DiGraph()

    for nid, node in store.nodes.items():
        G.add_node(nid, entity_type=node.entity_type)

    for etype, edges in store.edge_index.items():
        for edge in edges:
            if edge.source_id in store.nodes and edge.target_id in store.nodes:
                G.add_edge(edge.source_id, edge.target_id, edge_type=etype)

    return G


# ── Return types ──────────────────────────────────────────────────────────────


@dataclass
class ClusterSummary:
    """
    Human-readable summary of a single weakly-connected component.

    Attributes
    ----------
    size               : number of nodes in the component
    entity_distribution: entity_type → count within this component
    top_degree_node_id : node with the highest total degree (in + out)
    top_degree_value   : degree of the top node
    """

    size: int = 0
    entity_distribution: dict[str, int] = field(default_factory=dict)
    top_degree_node_id: str = ""
    top_degree_value: int = 0


# ── Public functions ──────────────────────────────────────────────────────────


def connected_components(store: GraphStore) -> list[set[str]]:
    """
    Return all weakly-connected components of the graph.

    A weakly-connected component treats every directed edge as undirected.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    list[set[str]]
        Sorted by component size descending (largest first).
        Each element is a ``set[str]`` of node ids.
    """
    _require_nx()
    G = _to_networkx(store)
    components = list(nx.weakly_connected_components(G))
    components.sort(key=len, reverse=True)
    return components


def largest_connected_component(store: GraphStore) -> set[str]:
    """
    Return the node ids of the largest weakly-connected component.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    set[str]
        Empty set if the graph has no nodes.
    """
    components = connected_components(store)
    return components[0] if components else set()


def degree_centrality(store: GraphStore) -> dict[str, float]:
    """
    Compute the degree centrality for every node.

    Degree centrality = (in_degree + out_degree) / (N - 1).

    Uses ``networkx.degree_centrality`` on the underlying DiGraph, which
    computes this on the *undirected* view of the graph.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    dict[str, float]
        node_id → centrality score (0.0–1.0).
        Empty dict if graph has fewer than 2 nodes.
    """
    _require_nx()
    G = _to_networkx(store)
    if G.number_of_nodes() < 2:
        return {}
    return dict(nx.degree_centrality(G))


def betweenness_centrality(
    store: GraphStore,
    sample_k: int | None = None,
    normalized: bool = True,
) -> dict[str, float]:
    """
    Compute betweenness centrality for every node.

    Betweenness measures how often a node lies on the shortest path between
    two other nodes — high values indicate structural brokers.

    Parameters
    ----------
    store      : GraphStore
    sample_k   : if given, use approximate computation sampling *k* source
                 nodes (faster for large graphs).  ``None`` = exact.
    normalized : divide by the maximum possible value (default True).

    Returns
    -------
    dict[str, float]
        node_id → centrality score.  Empty dict if graph has < 2 nodes.

    Notes
    -----
    Exact betweenness is O(N·E) which is fine for N=500, E=8000.
    For larger graphs, pass ``sample_k`` to use the approximate variant.
    """
    _require_nx()
    G = _to_networkx(store)
    if G.number_of_nodes() < 2:
        return {}
    return dict(
        nx.betweenness_centrality(G, k=sample_k, normalized=normalized)
    )


def node_degree(store: GraphStore, node_id: str) -> tuple[int, int]:
    """
    Return the ``(in_degree, out_degree)`` of a single node.

    Uses the ``GraphStore`` adjacency maps directly — no NetworkX overhead.

    Parameters
    ----------
    store   : GraphStore
    node_id : str | UUID

    Returns
    -------
    tuple[int, int]
        ``(in_degree, out_degree)``.  ``(0, 0)`` if the node is unknown.
    """
    nid = safe_str(node_id)
    in_deg = len(store.radj.get(nid, []))
    out_deg = len(store.adj.get(nid, []))
    return (in_deg, out_deg)


def cluster_summary(store: GraphStore, component: set[str]) -> ClusterSummary:
    """
    Build a human-readable ``ClusterSummary`` for a connected component.

    Parameters
    ----------
    store     : GraphStore
    component : set of node ids (typically from ``connected_components``)

    Returns
    -------
    ClusterSummary
        Empty summary if *component* is empty.
    """
    if not component:
        return ClusterSummary()

    entity_dist: dict[str, int] = {}
    top_id = ""
    top_deg = -1

    for nid in component:
        node = store.nodes.get(nid)
        if node is None:
            continue
        entity_dist[node.entity_type] = entity_dist.get(node.entity_type, 0) + 1
        in_deg, out_deg = node_degree(store, nid)
        total_deg = in_deg + out_deg
        if total_deg > top_deg:
            top_deg = total_deg
            top_id = nid

    return ClusterSummary(
        size=len(component),
        entity_distribution=entity_dist,
        top_degree_node_id=top_id,
        top_degree_value=max(top_deg, 0),
    )


def all_cluster_summaries(store: GraphStore) -> list[ClusterSummary]:
    """
    Return a ``ClusterSummary`` for every weakly-connected component,
    ordered by component size descending.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    list[ClusterSummary]
    """
    return [cluster_summary(store, comp) for comp in connected_components(store)]
