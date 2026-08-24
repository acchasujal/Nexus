"""backend/app/core/graph/algorithms/centrality.py

Deterministic Person-Only Centrality Intelligence for NEXUS.

Developer Documentation:
1. Person-Only Scope:
   All centrality metrics (degree centrality, in-degree, out-degree, betweenness centrality)
   operate strictly on the Person-Only Projection graph. Non-person entities (Phones, Vehicles,
   Accounts, Cases, Evidence, SourceRecords, Locations, etc.) are excluded to ensure that
   centrality reflects true suspect-to-suspect network importance.

2. Degree Centrality:
   - In-degree centrality: Normalized incoming Person-to-Person relationships.
   - Out-degree centrality: Normalized outgoing Person-to-Person relationships.
   - Total degree centrality: Normalized combined Person-to-Person connections.

3. Betweenness Centrality:
   - Measures how frequently a Person lies on shortest paths between other Person nodes
     in the network. Uses NetworkX normalized betweenness centrality.

4. Determinism & Non-Mutation:
   - Results are sorted deterministically using explicit tie-breaking rules.
   - Centrality calculations do not mutate the input GraphStore or Person-Only graph.
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

from backend.app.core.graph.algorithms.projection import project_person_graph
from backend.app.core.graph.algorithms.utils import GraphStore


def _require_nx() -> None:
    if not _NX_AVAILABLE:
        raise ImportError(
            "NetworkX is required for centrality algorithms. "
            "Install it with: pip install networkx"
        )


@dataclass
class PersonDegreeResult:
    """Degree centrality summary for a single Person node."""

    person_id: str
    canonical_label: str
    degree_centrality: float
    in_degree_centrality: float
    out_degree_centrality: float
    raw_degree: int


@dataclass
class PersonBetweennessResult:
    """Betweenness centrality summary for a single Person node."""

    person_id: str
    canonical_label: str
    betweenness_centrality: float


def _to_person_networkx_graph(store: GraphStore, directed: bool = True) -> Any:
    """
    Build a NetworkX Graph/DiGraph from a GraphStore, automatically applying
    Person-Only Projection if non-person nodes exist.
    """
    _require_nx()
    # 1. Ensure Person-Only Projection
    projected = project_person_graph(store)

    # 2. Build NetworkX graph
    G = nx.DiGraph() if directed else nx.Graph()

    for nid, node in sorted(projected.nodes.items()):
        label = node.properties.get("canonical_label") or node.properties.get("full_name") or nid
        G.add_node(nid, canonical_label=label, properties=node.properties)

    for etype, edges in sorted(projected.edge_index.items()):
        for edge in sorted(edges, key=lambda e: (e.edge_type, e.source_id, e.target_id)):
            if edge.source_id in G.nodes and edge.target_id in G.nodes:
                if directed or not G.has_edge(edge.source_id, edge.target_id):
                    G.add_edge(edge.source_id, edge.target_id, edge_type=etype, properties=edge.properties)

    return G


def compute_person_degree_centrality(store: GraphStore) -> list[PersonDegreeResult]:
    """
    Compute deterministic degree centrality (total, in-degree, out-degree)
    for all Person nodes on the Person-Only Projection graph.

    Returns list of PersonDegreeResult sorted by degree_centrality descending,
    then person_id ascending.
    """
    _require_nx()
    projected = project_person_graph(store)
    G = _to_person_networkx_graph(projected, directed=True)

    n_nodes = len(G.nodes)
    if n_nodes <= 1:
        # 0 or 1 node
        results = []
        for nid in sorted(G.nodes):
            node = projected.nodes[nid]
            label = node.properties.get("canonical_label") or node.properties.get("full_name") or nid
            results.append(
                PersonDegreeResult(
                    person_id=nid,
                    canonical_label=label,
                    degree_centrality=0.0,
                    in_degree_centrality=0.0,
                    out_degree_centrality=0.0,
                    raw_degree=0,
                )
            )
        return results

    deg_dict = nx.degree_centrality(G)
    in_deg_dict = nx.in_degree_centrality(G)
    out_deg_dict = nx.out_degree_centrality(G)

    results = []
    for nid in sorted(G.nodes):
        node = projected.nodes[nid]
        label = node.properties.get("canonical_label") or node.properties.get("full_name") or nid
        raw_deg = G.degree(nid)

        results.append(
            PersonDegreeResult(
                person_id=nid,
                canonical_label=label,
                degree_centrality=round(deg_dict.get(nid, 0.0), 4),
                in_degree_centrality=round(in_deg_dict.get(nid, 0.0), 4),
                out_degree_centrality=round(out_deg_dict.get(nid, 0.0), 4),
                raw_degree=raw_deg,
            )
        )

    # Deterministic sorting: degree_centrality descending, then person_id ascending
    results.sort(key=lambda r: (-r.degree_centrality, r.person_id))
    return results


def compute_person_betweenness_centrality(
    store: GraphStore, k: int | None = None
) -> list[PersonBetweennessResult]:
    """
    Compute deterministic normalized betweenness centrality for all Person nodes
    on the Person-Only Projection graph.

    Returns list of PersonBetweennessResult sorted by betweenness_centrality descending,
    then person_id ascending.
    """
    _require_nx()
    projected = project_person_graph(store)
    G = _to_person_networkx_graph(projected, directed=False)

    if len(G.nodes) <= 2:
        results = []
        for nid in sorted(G.nodes):
            node = projected.nodes[nid]
            label = node.properties.get("canonical_label") or node.properties.get("full_name") or nid
            results.append(
                PersonBetweennessResult(
                    person_id=nid,
                    canonical_label=label,
                    betweenness_centrality=0.0,
                )
            )
        return results

    # NetworkX betweenness centrality over undirected graph
    bw_dict = nx.betweenness_centrality(G, k=k, normalized=True)

    results = []
    for nid in sorted(G.nodes):
        node = projected.nodes[nid]
        label = node.properties.get("canonical_label") or node.properties.get("full_name") or nid
        score = round(bw_dict.get(nid, 0.0), 4)

        results.append(
            PersonBetweennessResult(
                person_id=nid,
                canonical_label=label,
                betweenness_centrality=score,
            )
        )

    # Deterministic sorting: betweenness descending, then person_id ascending
    results.sort(key=lambda r: (-r.betweenness_centrality, r.person_id))
    return results
