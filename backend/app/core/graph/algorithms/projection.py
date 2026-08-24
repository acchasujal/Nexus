"""backend/app/core/graph/algorithms/projection.py

Person-Only Graph Projection for NEXUS (Schema V2).

Developer Documentation:
1. What Person-Only Projection Represents:
   A derived, deterministic view of the investigation graph that filters out all
   non-person entity nodes (Phones, Vehicles, Accounts, Organizations, Events,
   Cases, Evidence, SourceRecords, Locations, Devices, etc.) and retains strictly
   Person nodes and valid Person-to-Person relationships.

2. Why Non-Person Entities Are Excluded:
   For higher-order network intelligence (centrality, kingpin/broker discovery,
   community detection), structural algorithms require direct suspect-to-suspect
   topological connections without distortion from high-degree hub entities (e.g.
   cell towers, police stations, or shared vehicle attributes).

3. Projected Relationship Types:
   Direct semantically valid Person-to-Person relationship types:
   - COMMUNICATED_WITH
   - CONNECTED_TO
   - CO_ACCUSED_WITH
   - ASSOCIATED_WITH (when both endpoints are Person nodes)
   - LINKED_TO

4. Intentionally Excluded Relationships:
   - All relationships where source or target is a non-person node (e.g. OWNS_ACCOUNT,
     USED_PHONE, USED_VEHICLE, HAS_EVIDENCE, OCCURRED_AT, CITES_SOURCE).
   - Self-loops (where source_id == target_id) are excluded by default to prevent algorithm bias.
   - Indirect relationships (e.g. Person A -> Phone X <- Person B) are NOT automatically
     converted into Person A -> Person B edges during projection. Such inferential rules
     belong to explicit pattern detection modules.

5. Directed vs. Undirected Behavior:
   The projected GraphStore retains canonical directed edges (source_id -> target_id).
   For undirected network algorithms, callers can derive an undirected graph representation
   without modifying canonical directed relationship definitions.

6. Provenance Preservation:
   All projected edges retain their original relationship ID, edge_type, timestamps,
   confidence score, derivation_class (FACT, DERIVED, HYPOTHESIS), source_record_id,
   and properties dictionary.

7. Non-Mutating Guarantee:
   The projection function builds a fresh, isolated GraphStore object without modifying
   the input graph or node/edge dictionaries.
"""

from __future__ import annotations

from typing import Any, Iterable, Set
from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord, safe_str
from backend.app.core.graph.enums import GraphEntityType, GraphRelationshipType

# Valid Person-to-Person direct relationship types for network projection
DEFAULT_PERSON_RELATIONSHIPS: Set[str] = {
    GraphRelationshipType.COMMUNICATED_WITH.value,
    GraphRelationshipType.CONNECTED_TO.value,
    GraphRelationshipType.CO_ACCUSED_WITH.value,
    GraphRelationshipType.ASSOCIATED_WITH.value,
    GraphRelationshipType.LINKED_TO.value,
}

PERSON_ENTITY_TYPES: Set[str] = {
    GraphEntityType.PERSON.value,
    "Person",
    "PERSON",
}


def project_person_graph(
    store: GraphStore,
    include_self_loops: bool = False,
    allowed_relationships: Set[str] | None = None,
) -> GraphStore:
    """
    Project a full heterogeneous investigation graph into a deterministic Person-Only graph.

    Parameters
    ----------
    store : GraphStore
        The input canonical investigation graph (unmutated).
    include_self_loops : bool, default False
        Whether to retain self-loop relationships where source_id == target_id.
    allowed_relationships : Set[str], optional
        Set of edge_type values to project between Person nodes. Defaults to
        COMMUNICATED_WITH, CONNECTED_TO, CO_ACCUSED_WITH, ASSOCIATED_WITH, LINKED_TO.

    Returns
    -------
    GraphStore
        A fresh, isolated GraphStore containing ONLY Person nodes and valid
        Person-to-Person relationships.
    """
    rel_types = allowed_relationships if allowed_relationships is not None else DEFAULT_PERSON_RELATIONSHIPS
    projected = GraphStore()

    # 1. Identify all Person nodes deterministically
    person_node_ids: set[str] = set()
    sorted_node_ids = sorted(store.nodes.keys())

    for nid in sorted_node_ids:
        node = store.nodes[nid]
        if node.entity_type in PERSON_ENTITY_TYPES:
            person_node_ids.add(nid)
            # Retain exact NodeRecord with deep-copied properties dictionary
            projected.nodes[nid] = NodeRecord(
                node_id=node.node_id,
                entity_type=node.entity_type,
                properties=dict(node.properties),
            )
            projected.adj[nid] = []
            projected.radj[nid] = []

    if not person_node_ids:
        return projected

    # 2. Collect Person -> Person edges deterministically
    seen_edges: set[tuple[str, str, str]] = set()

    for etype in sorted(store.edge_index.keys()):
        if etype not in rel_types:
            continue

        edges = store.edge_index[etype]
        # Sort edges deterministically by (edge_type, source_id, target_id)
        sorted_edges = sorted(
            edges,
            key=lambda e: (e.edge_type, e.source_id, e.target_id)
        )

        for edge in sorted_edges:
            src = safe_str(edge.source_id)
            tgt = safe_str(edge.target_id)

            # Both endpoints MUST be Person nodes
            if src not in person_node_ids or tgt not in person_node_ids:
                continue

            # Check self-loops
            if not include_self_loops and src == tgt:
                continue

            edge_key = (edge.edge_type, src, tgt)
            if edge_key in seen_edges:
                continue
            seen_edges.add(edge_key)

            # Copy edge with full properties/metadata
            adj_edge = AdjEdge(
                edge_type=edge.edge_type,
                source_id=src,
                target_id=tgt,
                properties=dict(edge.properties),
            )

            projected.adj[src].append(adj_edge)
            projected.radj[tgt].append(adj_edge)
            projected.edge_index.setdefault(edge.edge_type, []).append(adj_edge)

    return projected


def project_person_nodes_and_edges(
    nodes: Iterable[Any],
    edges: Iterable[Any],
    include_self_loops: bool = False,
    allowed_relationships: Set[str] | None = None,
) -> tuple[list[Any], list[Any]]:
    """
    Project raw node and edge collections into Person-only node and edge lists.

    Parameters
    ----------
    nodes : Iterable[Any]
        Raw node objects (must have .id / .node_id and .entity_type).
    edges : Iterable[Any]
        Raw edge objects (must have .source_id, .target_id, and .edge_type / .type).
    include_self_loops : bool, default False
        Whether to retain self-loop relationships.
    allowed_relationships : Set[str], optional
        Set of edge_type values to project.

    Returns
    -------
    tuple[list[Any], list[Any]]
        (projected_person_nodes, projected_person_edges)
    """
    rel_types = allowed_relationships if allowed_relationships is not None else DEFAULT_PERSON_RELATIONSHIPS

    # 1. Filter Person nodes
    person_nodes: list[Any] = []
    person_ids: set[str] = set()

    for raw in nodes:
        nid = safe_str(getattr(raw, "node_id", getattr(raw, "id", None)))
        etype = getattr(raw, "entity_type", "")
        etype_str = etype.value if hasattr(etype, "value") else str(etype)

        if etype_str in PERSON_ENTITY_TYPES and nid:
            person_nodes.append(raw)
            person_ids.add(nid)

    # 2. Filter Person -> Person edges
    person_edges: list[Any] = []
    seen: set[tuple[str, str, str]] = set()

    for raw in edges:
        src = safe_str(getattr(raw, "source_id", ""))
        tgt = safe_str(getattr(raw, "target_id", ""))
        etype = getattr(raw, "edge_type", getattr(raw, "type", ""))
        etype_str = etype.value if hasattr(etype, "value") else str(etype)

        if src in person_ids and tgt in person_ids and etype_str in rel_types:
            if not include_self_loops and src == tgt:
                continue
            key = (etype_str, src, tgt)
            if key not in seen:
                seen.add(key)
                person_edges.append(raw)

    return person_nodes, person_edges
