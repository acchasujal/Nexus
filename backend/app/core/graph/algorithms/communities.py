"""backend/app/core/graph/algorithms/communities.py

Deterministic Person-Only Louvain Community Intelligence for NEXUS (Schema V2).

Developer Documentation:
1. Person-Only Scope:
   Community detection runs strictly over the Person-Only Projection graph
   (via project_person_graph). Non-person entities (Phones, Vehicles, Accounts,
   Cases, Evidence, SourceRecords, Locations, etc.) are excluded from community
   membership.

2. Undirected Analytical Graph:
   Louvain community detection evaluates bi-directional social and communication
   clusters using an undirected analytical view (nx.Graph). The canonical graph is
   never mutated.

3. Determinism & Seed:
   Uses nx.community.louvain_communities with a fixed seed (seed=42) or deterministic
   greedy modularity fallback to ensure reproducible partitions.

4. Stable Community Identifiers:
   Raw integer community indices are transformed into stable deterministic hashes
   based on sorted member IDs:
     comm_<sha256(sorted_member_ids)[:12]>
   Same member set always yields the exact same community_id.

5. Deterministic Ordering:
   - Within community: member_ids sorted ascending by person_id.
   - Across communities: sorted by size descending, then by smallest member_id ascending.

6. Explainable & Neutral Labels:
   Explanations describe topological structure (e.g., "Cohesive Person network module of 4 members").
   NO guilt scores, criminal probabilities, or LLM-generated labels.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
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
            "NetworkX is required for Louvain community detection. "
            "Install it with: pip install networkx"
        )


@dataclass
class PersonCommunityResult:
    """Detailed community result for a Person-Only cluster."""

    community_id: str
    size: int
    member_ids: list[str]
    dominant_entity_type: str  # Always "Person"
    top_influencer_id: str
    internal_edge_count: int
    boundary_edge_count: int
    reason: str


@dataclass
class NetworkCommunitiesSummary:
    """Overall community partition summary for the Person-Only network."""

    community_count: int
    modularity: float
    communities: list[PersonCommunityResult]


def generate_stable_community_id(member_ids: list[str]) -> str:
    """
    Generate a deterministic, stable community ID based on sorted member IDs.
    Same member set always produces the exact same community ID regardless of algorithm state.
    """
    sorted_members = sorted(member_ids)
    raw_str = ",".join(sorted_members)
    member_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:12]
    return f"comm_{member_hash}"


def detect_louvain_communities(
    store: GraphStore, seed: int = 42
) -> NetworkCommunitiesSummary:
    """
    Detect Person-Only communities using deterministic Louvain / modularity partitioning.

    Parameters
    ----------
    store : GraphStore
        Input investigation graph (unmutated).
    seed : int, default 42
        Fixed random seed for deterministic Louvain execution.

    Returns
    -------
    NetworkCommunitiesSummary
        Structured community partition containing stable community IDs, member lists,
        community sizes, top influencers, and overall network modularity.
    """
    _require_nx()

    # 1. Person-Only Projection
    projected = project_person_graph(store)

    # 2. Build undirected analytical NetworkX graph
    G = nx.Graph()
    for nid in sorted(projected.nodes.keys()):
        G.add_node(nid)

    for etype, edges in sorted(projected.edge_index.items()):
        for edge in sorted(edges, key=lambda e: (e.edge_type, e.source_id, e.target_id)):
            if edge.source_id in G.nodes and edge.target_id in G.nodes:
                if not G.has_edge(edge.source_id, edge.target_id):
                    G.add_edge(edge.source_id, edge.target_id, edge_type=etype)

    node_count = len(G.nodes)
    if node_count == 0:
        return NetworkCommunitiesSummary(community_count=0, modularity=0.0, communities=[])

    if node_count == 1:
        single_member = list(G.nodes)[0]
        cid = generate_stable_community_id([single_member])
        res = PersonCommunityResult(
            community_id=cid,
            size=1,
            member_ids=[single_member],
            dominant_entity_type="Person",
            top_influencer_id=single_member,
            internal_edge_count=0,
            boundary_edge_count=0,
            reason=f"Single Person node component for {single_member}.",
        )
        return NetworkCommunitiesSummary(community_count=1, modularity=0.0, communities=[res])

    # 3. Louvain / Modularity Community Detection
    raw_communities: list[set[str]] = []

    try:
        # Louvain community detection with fixed seed
        if hasattr(nx.community, "louvain_communities"):
            raw_communities = [set(c) for c in nx.community.louvain_communities(G, seed=seed)]
        else:  # Fallback for older NetworkX versions
            raw_communities = [set(c) for c in nx.community.greedy_modularity_communities(G)]
    except Exception:
        raw_communities = [set(c) for c in nx.connected_components(G)]

    # Compute overall modularity score
    try:
        if len(raw_communities) > 1 and len(G.edges) > 0:
            modularity_score = round(float(nx.community.modularity(G, raw_communities)), 4)
        else:
            modularity_score = 0.0
    except Exception:
        modularity_score = 0.0

    # 4. Process each community deterministically
    community_results: list[PersonCommunityResult] = []

    for member_set in raw_communities:
        sorted_members = sorted(member_set)
        size = len(sorted_members)
        cid = generate_stable_community_id(sorted_members)

        # Internal edges vs. boundary edges
        sub = G.subgraph(sorted_members)
        internal_edges = len(sub.edges)

        boundary_edges = 0
        for nid in sorted_members:
            for neighbor in G.neighbors(nid):
                if neighbor not in member_set:
                    boundary_edges += 1

        # Top influencer (node with highest degree inside subgraph)
        top_influencer = max(
            sorted_members,
            key=lambda n: (sub.degree(n), G.degree(n), n)
        )

        reason = (
            f"Cohesive Person network module of {size} members centered around {top_influencer} "
            f"({internal_edges} internal relationships)."
        )

        community_results.append(
            PersonCommunityResult(
                community_id=cid,
                size=size,
                member_ids=sorted_members,
                dominant_entity_type="Person",
                top_influencer_id=top_influencer,
                internal_edge_count=internal_edges,
                boundary_edge_count=boundary_edges,
                reason=reason,
            )
        )

    # 5. Deterministic sorting across communities:
    #    1. Size descending
    #    2. Smallest member_id ascending
    community_results.sort(key=lambda c: (-c.size, c.member_ids[0]))

    return NetworkCommunitiesSummary(
        community_count=len(community_results),
        modularity=modularity_score,
        communities=community_results,
    )
