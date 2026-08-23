"""
graph/algorithms/statistics.py

High-level graph metrics for the unified investigation graph.

All computations are deterministic single-pass scans over the ``GraphStore``.
No NetworkX dependency — raw adjacency maps are sufficient for every metric
implemented here.

No database calls.  No API code.  No ML.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.core.graph.algorithms.utils import GraphStore


# ── Return type ───────────────────────────────────────────────────────────────


@dataclass
class GraphStatistics:
    """
    Snapshot metrics for the unified investigation graph.

    Attributes
    ----------
    num_nodes               : total node count
    num_edges               : total edge count (de-duplicated)
    entity_distribution     : entity_type → node count
    relationship_distribution : edge_type → edge count
    density                 : |E| / (|V| * (|V| - 1))  — directed graph density
    average_degree          : mean number of outgoing edges per node
    largest_component_size  : number of nodes in the largest weakly-connected
                              component (computed via union-find)
    isolated_node_count     : nodes with neither incoming nor outgoing edges
    """

    num_nodes: int = 0
    num_edges: int = 0
    entity_distribution: dict[str, int] = field(default_factory=dict)
    relationship_distribution: dict[str, int] = field(default_factory=dict)
    density: float = 0.0
    average_degree: float = 0.0
    largest_component_size: int = 0
    isolated_node_count: int = 0


# ── Union-Find for weakly-connected components (no NetworkX) ─────────────────


class _UnionFind:
    """Simple path-compressed union-find for component detection."""

    def __init__(self, ids: list[str]) -> None:
        self._parent: dict[str, str] = {i: i for i in ids}
        self._rank: dict[str, int] = {i: 0 for i in ids}

    def find(self, x: str) -> str:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]  # path compression
            x = self._parent[x]
        return x

    def union(self, x: str, y: str) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self._rank[rx] < self._rank[ry]:
            rx, ry = ry, rx
        self._parent[ry] = rx
        if self._rank[rx] == self._rank[ry]:
            self._rank[rx] += 1

    def component_sizes(self) -> dict[str, int]:
        """Return root → component size."""
        sizes: dict[str, int] = {}
        for node in self._parent:
            root = self.find(node)
            sizes[root] = sizes.get(root, 0) + 1
        return sizes


# ── Main function ─────────────────────────────────────────────────────────────


def compute_graph_statistics(store: GraphStore) -> GraphStatistics:
    """
    Compute a ``GraphStatistics`` snapshot for the given ``GraphStore``.

    All metrics are derived in a small number of linear passes —
    no quadratic algorithms.

    Parameters
    ----------
    store : GraphStore

    Returns
    -------
    GraphStatistics
    """
    num_nodes = len(store.nodes)

    # Entity distribution — one pass over nodes
    entity_dist: dict[str, int] = {}
    for node in store.nodes.values():
        entity_dist[node.entity_type] = entity_dist.get(node.entity_type, 0) + 1

    # Edge distribution + total count — one pass over edge_index
    rel_dist: dict[str, int] = {}
    num_edges = 0
    for etype, edges in store.edge_index.items():
        rel_dist[etype] = len(edges)
        num_edges += len(edges)

    # Density (directed graph: max edges = N*(N-1))
    density = 0.0
    if num_nodes > 1:
        density = num_edges / (num_nodes * (num_nodes - 1))

    # Average out-degree
    total_out = sum(len(edges) for edges in store.adj.values())
    average_degree = total_out / num_nodes if num_nodes > 0 else 0.0

    # Isolated nodes: no outgoing AND no incoming edges
    isolated = sum(
        1
        for nid in store.nodes
        if not store.adj.get(nid) and not store.radj.get(nid)
    )

    # Largest weakly-connected component via union-find
    largest_component = 0
    if num_nodes > 0:
        all_ids = list(store.nodes.keys())
        uf = _UnionFind(all_ids)
        for etype, edges in store.edge_index.items():
            for edge in edges:
                if edge.source_id in store.nodes and edge.target_id in store.nodes:
                    uf.union(edge.source_id, edge.target_id)
        sizes = uf.component_sizes()
        largest_component = max(sizes.values()) if sizes else 0

    return GraphStatistics(
        num_nodes=num_nodes,
        num_edges=num_edges,
        entity_distribution=entity_dist,
        relationship_distribution=rel_dist,
        density=round(density, 6),
        average_degree=round(average_degree, 4),
        largest_component_size=largest_component,
        isolated_node_count=isolated,
    )
