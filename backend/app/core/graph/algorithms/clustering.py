"""backend/app/core/graph/algorithms/clustering.py

NetworkX-based clustering, centrality, community detection, and bridge-node analysis.
Deterministic, explainable, and local-first.
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


def _require_nx() -> None:
    if not _NX_AVAILABLE:
        raise ImportError(
            "NetworkX is required for clustering algorithms. "
            "Install it with: pip install networkx"
        )


def _to_networkx(store: GraphStore) -> Any:
    """Build a networkx.DiGraph from a GraphStore."""
    _require_nx()
    G = nx.DiGraph()

    for nid, node in store.nodes.items():
        G.add_node(nid, entity_type=node.entity_type, properties=node.properties)

    for etype, edges in store.edge_index.items():
        for edge in edges:
            if edge.source_id in store.nodes and edge.target_id in store.nodes:
                G.add_edge(edge.source_id, edge.target_id, edge_type=etype)

    return G


@dataclass
class ClusterSummary:
    size: int = 0
    entity_distribution: dict[str, int] = field(default_factory=dict)
    top_degree_node_id: str = ""
    top_degree_value: int = 0


@dataclass
class CommunityResult:
    community_id: str
    size: int
    member_ids: list[str]
    dominant_entity_type: str
    top_influencer_id: str
    reason: str


@dataclass
class BridgeNodeResult:
    node_id: str
    entity_type: str
    label: str
    connected_components_count: int
    betweenness_score: float
    reason: str


def connected_components(store: GraphStore) -> list[set[str]]:
    """Return all weakly-connected components sorted by size descending."""
    _require_nx()
    G = _to_networkx(store)
    components = list(nx.weakly_connected_components(G))
    components.sort(key=len, reverse=True)
    return components


def largest_connected_component(store: GraphStore) -> set[str]:
    """Return node ids of the largest weakly-connected component."""
    components = connected_components(store)
    return components[0] if components else set()


def degree_centrality(store: GraphStore) -> dict[str, float]:
    """Compute degree centrality for all Person nodes using Person-Only Projection."""
    from backend.app.core.graph.algorithms.centrality import compute_person_degree_centrality
    results = compute_person_degree_centrality(store)
    return {r.person_id: r.degree_centrality for r in results}


def in_degree_centrality(store: GraphStore) -> dict[str, float]:
    """Compute in-degree centrality for all Person nodes."""
    from backend.app.core.graph.algorithms.centrality import compute_person_degree_centrality
    results = compute_person_degree_centrality(store)
    return {r.person_id: r.in_degree_centrality for r in results}


def out_degree_centrality(store: GraphStore) -> dict[str, float]:
    """Compute out-degree centrality for all Person nodes."""
    from backend.app.core.graph.algorithms.centrality import compute_person_degree_centrality
    results = compute_person_degree_centrality(store)
    return {r.person_id: r.out_degree_centrality for r in results}


def betweenness_centrality(store: GraphStore, k: int | None = None) -> dict[str, float]:
    """Compute betweenness centrality for all Person nodes using Person-Only Projection."""
    from backend.app.core.graph.algorithms.centrality import compute_person_betweenness_centrality
    results = compute_person_betweenness_centrality(store, k=k)
    return {r.person_id: r.betweenness_centrality for r in results}


def detect_communities(store: GraphStore) -> list[CommunityResult]:
    """Detect discrete communities/gangs/cells using graph modularity / connected components."""
    _require_nx()
    G = _to_networkx(store).to_undirected()
    
    if len(G.nodes) == 0:
        return []

    # Community detection using greedy modularity or connected components fallback
    try:
        raw_communities = list(nx.community.greedy_modularity_communities(G))
    except (nx.NetworkXError, ValueError, ZeroDivisionError):
        raw_communities = list(nx.connected_components(G))

    results: list[CommunityResult] = []
    for idx, member_set in enumerate(raw_communities, start=1):
        member_ids = list(member_set)
        if len(member_ids) < 2:
            continue

        type_counts: dict[str, int] = {}
        for nid in member_ids:
            node = store.nodes.get(nid)
            if node:
                type_counts[node.entity_type] = type_counts.get(node.entity_type, 0) + 1

        dominant_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else "Unknown"

        # Find top influencer by degree within community
        sub = G.subgraph(member_ids)
        top_node = max(sub.nodes, key=lambda n: sub.degree(n)) if len(sub.nodes) > 0 else member_ids[0]

        results.append(
            CommunityResult(
                community_id=f"COMM-{idx:03d}",
                size=len(member_ids),
                member_ids=member_ids,
                dominant_entity_type=dominant_type,
                top_influencer_id=top_node,
                reason=f"Cohesive network module of {len(member_ids)} entities centered around {top_node}",
            )
        )

    results.sort(key=lambda c: c.size, reverse=True)
    return results


def find_bridge_nodes(store: GraphStore) -> list[BridgeNodeResult]:
    """Find articulation points / bridge brokers that connect disjoint network modules."""
    from backend.app.core.graph.algorithms.bridges import compute_person_bridge_intelligence
    intel_results = compute_person_bridge_intelligence(store)

    bridge_results: list[BridgeNodeResult] = []
    for b in intel_results:
        if b.articulation_point or b.betweenness_centrality > 0.0:
            bridge_results.append(
                BridgeNodeResult(
                    node_id=b.person_id,
                    entity_type="Person",
                    label=b.canonical_label,
                    connected_components_count=b.affected_components_count,
                    betweenness_score=b.betweenness_centrality,
                    reason=b.explanation,
                )
            )

    return bridge_results


def node_degree(store: GraphStore, node_id: str) -> tuple[int, int]:
    nid = safe_str(node_id)
    in_deg = len(store.radj.get(nid, []))
    out_deg = len(store.adj.get(nid, []))
    return (in_deg, out_deg)


def cluster_summary(store: GraphStore, component: set[str]) -> ClusterSummary:
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
    return [cluster_summary(store, comp) for comp in connected_components(store)]
