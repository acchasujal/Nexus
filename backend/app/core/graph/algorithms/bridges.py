"""backend/app/core/graph/algorithms/bridges.py

Deterministic Person-Only Bridge & Articulation Point Intelligence for NEXUS.

Developer Documentation:
1. Person-Only Analytical Graph:
   All bridge discovery and articulation-point calculations run strictly over the
   Person-Only Projection graph. Non-person entities (Phones, Vehicles, Accounts, etc.)
   do not become centrality or bridge nodes.

2. Articulation Point Semantics:
   An articulation point is a Person node whose removal increases the number of connected
   components in the Person-Only network (splitting the network into disjoint segments).

3. Transparent Combined Bridge Score Formula:
   bridge_score = round(0.50 * betweenness_centrality + 0.30 * degree_centrality + (0.20 if articulation_point else 0.0), 4)

4. Deterministic Ranking:
   Top bridge entities are ranked using explicit tie-breaking:
     1. articulation_point (True before False)
     2. bridge_score descending
     3. betweenness_centrality descending
     4. degree_centrality descending
     5. person_id ascending

5. Neutral & Explainable Language:
   All explanations describe network topology neutrally (e.g., "network bridge",
   "articulation point", "influential connector").
   NO guilt scores, criminal probabilities, or predictive guilt scoring.
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

from backend.app.core.graph.algorithms.centrality import (
    _to_person_networkx_graph,
    compute_person_betweenness_centrality,
    compute_person_degree_centrality,
)
from backend.app.core.graph.algorithms.projection import project_person_graph
from backend.app.core.graph.algorithms.utils import GraphStore


def _require_nx() -> None:
    if not _NX_AVAILABLE:
        raise ImportError(
            "NetworkX is required for bridge discovery algorithms. "
            "Install it with: pip install networkx"
        )


@dataclass
class BridgeCandidateResult:
    """
    Explainable network bridge candidate result.

    Attributes
    ----------
    person_id : str
        Unique stable identifier of the Person node.
    canonical_label : str
        Human-readable display name or alias.
    degree_centrality : float
        Normalized degree centrality (0.0 <= c <= 1.0).
    betweenness_centrality : float
        Normalized betweenness centrality (0.0 <= c <= 1.0).
    articulation_point : bool
        True if removal of this person splits the graph into multiple components.
    bridge_score : float
        Combined transparent score: 0.5*betweenness + 0.3*degree + (0.2 if articulation else 0.0).
    affected_components_count : int
        Number of disjoint network components formed if this person is removed.
    explanation : str
        Deterministic structural explanation (no LLM, no guilt bias).
    relationship_ids : list[str]
        IDs or descriptions of relationships connected to this node.
    case_ids : list[str]
        Preserved case association IDs if available in node attributes.
    """

    person_id: str
    canonical_label: str
    degree_centrality: float
    betweenness_centrality: float
    articulation_point: bool
    bridge_score: float
    affected_components_count: int
    explanation: str
    relationship_ids: list[str] = field(default_factory=list)
    case_ids: list[str] = field(default_factory=list)


def compute_person_bridge_intelligence(store: GraphStore) -> list[BridgeCandidateResult]:
    """
    Compute explainable bridge and articulation-point intelligence for all Person nodes
    on the Person-Only Projection graph.

    Returns
    -------
    list[BridgeCandidateResult]
        All Person nodes with centrality metrics, articulation point status,
        transparent bridge_score, and structural explanation.
    """
    _require_nx()
    # 1. Person-Only Projection
    projected = project_person_graph(store)
    G = _to_person_networkx_graph(projected, directed=False)

    if len(G.nodes) == 0:
        return []

    # 2. Compute centrality metrics
    degree_results = {r.person_id: r for r in compute_person_degree_centrality(projected)}
    betweenness_results = {r.person_id: r for r in compute_person_betweenness_centrality(projected)}

    # 3. Identify connected components and articulation points
    initial_components_count = nx.number_connected_components(G)
    articulation_set: set[str] = set()

    if len(G.nodes) > 2:
        articulation_set = set(nx.articulation_points(G))

    results: list[BridgeCandidateResult] = []

    for nid in sorted(G.nodes):
        node = projected.nodes[nid]
        props = node.properties or {}
        label = props.get("canonical_label") or props.get("full_name") or nid

        deg_res = degree_results.get(nid)
        bw_res = betweenness_results.get(nid)

        deg_val = deg_res.degree_centrality if deg_res else 0.0
        bw_val = bw_res.betweenness_centrality if bw_res else 0.0

        # Calculate affected components if node is removed
        G_sub = G.copy()
        G_sub.remove_node(nid)
        after_components_count = nx.number_connected_components(G_sub)

        is_articulation = (nid in articulation_set) or (
            G.degree(nid) > 1 and after_components_count > initial_components_count
        )

        # Transparent bridge score formula
        raw_bridge_score = 0.50 * bw_val + 0.30 * deg_val + (0.20 if is_articulation else 0.0)
        bridge_score = round(raw_bridge_score, 4)

        # Collect relationship IDs connected to this node
        rel_ids: list[str] = []
        out_edges = projected.adj.get(nid, [])
        in_edges = projected.radj.get(nid, [])

        for edge in out_edges + in_edges:
            rel_id = edge.properties.get("id") or f"rel_{edge.source_id}_{edge.edge_type}_{edge.target_id}"
            if rel_id not in rel_ids:
                rel_ids.append(rel_id)

        # Collect case IDs if present in properties
        case_ids = list(props.get("case_ids") or props.get("cases") or [])

        # Deterministic explanation string
        rel_str = ", ".join(rel_ids[:4]) + ("..." if len(rel_ids) > 4 else "")
        if is_articulation:
            explanation = (
                f"Person '{label}' ({nid}) is a key network bridge (articulation point) whose removal "
                f"splits the network into {after_components_count} separate components. "
                f"Connected via {len(rel_ids)} relationship(s)" + (f": {rel_str}." if rel_str else ".")
            )
        elif bw_val > 0.0:
            explanation = (
                f"Person '{label}' ({nid}) acts as an influential connector with a betweenness "
                f"centrality of {bw_val:.3f}. Connected via {len(rel_ids)} relationship(s)"
                + (f": {rel_str}." if rel_str else ".")
            )
        else:
            explanation = (
                f"Person '{label}' ({nid}) has direct connections with a degree centrality of {deg_val:.3f}."
            )

        results.append(
            BridgeCandidateResult(
                person_id=nid,
                canonical_label=label,
                degree_centrality=deg_val,
                betweenness_centrality=bw_val,
                articulation_point=is_articulation,
                bridge_score=bridge_score,
                affected_components_count=after_components_count,
                explanation=explanation,
                relationship_ids=rel_ids,
                case_ids=case_ids,
            )
        )

    # Sort deterministically
    results.sort(
        key=lambda r: (
            not r.articulation_point,  # True (False) before False (True)
            -r.bridge_score,
            -r.betweenness_centrality,
            -r.degree_centrality,
            r.person_id,
        )
    )

    return results


def top_bridge_entities(store: GraphStore, limit: int = 10) -> list[BridgeCandidateResult]:
    """
    Get top N bridge entities ranked using explicit deterministic tie-breaking:
      1. articulation_point (True before False)
      2. bridge_score descending
      3. betweenness_centrality descending
      4. degree_centrality descending
      5. person_id ascending
    """
    results = compute_person_bridge_intelligence(store)
    return results[:limit]


def get_network_centrality_summary(store: GraphStore, limit: int = 10) -> dict[str, Any]:
    """
    Return a structured network intelligence summary dictionary containing top bridge
    entities, degree centrality rankings, and overall network component counts.
    """
    projected = project_person_graph(store)
    G = _to_person_networkx_graph(projected, directed=False)

    top_bridges = top_bridge_entities(projected, limit=limit)
    degree_rankings = compute_person_degree_centrality(projected)

    return {
        "person_nodes_count": len(projected.nodes),
        "person_edges_count": sum(len(e) for e in projected.edge_index.values()),
        "connected_components_count": nx.number_connected_components(G) if len(G.nodes) > 0 else 0,
        "top_bridges": [
            {
                "person_id": b.person_id,
                "canonical_label": b.canonical_label,
                "degree_centrality": b.degree_centrality,
                "betweenness_centrality": b.betweenness_centrality,
                "articulation_point": b.articulation_point,
                "bridge_score": b.bridge_score,
                "affected_components_count": b.affected_components_count,
                "explanation": b.explanation,
                "relationship_ids": b.relationship_ids,
            }
            for b in top_bridges
        ],
        "degree_rankings": [
            {
                "person_id": d.person_id,
                "canonical_label": d.canonical_label,
                "degree_centrality": d.degree_centrality,
                "raw_degree": d.raw_degree,
            }
            for d in degree_rankings[:limit]
        ],
    }
