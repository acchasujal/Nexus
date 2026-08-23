"""
graph/graph_loader.py

Graph loader layer: builds and validates the in-memory GraphStore.
Accepts and processes NodeRecord and AdjEdge objects directly.
"""

from __future__ import annotations

from typing import Any, Iterable

from backend.app.core.graph.algorithms.utils import GraphStore, NodeRecord, AdjEdge


class GraphLoader:
    """
    Constructs and validates the in-memory GraphStore.
    Operates strictly on injected collections of NodeRecord and AdjEdge objects.
    """

    def __init__(self) -> None:
        pass

    def load_graph(
        self,
        nodes: Iterable[NodeRecord],
        edges: Iterable[AdjEdge],
    ) -> GraphStore:
        """
        Populates a new GraphStore with the provided NodeRecords and AdjEdges.

        Every edge updates:
        - adj[source]
        - radj[target]
        - edge_index[edge_type]
        """
        store = GraphStore()
        
        seen_nids = set()
        duplicate_nids = set()

        for node in nodes:
            nid = node.node_id
            if nid in seen_nids:
                duplicate_nids.add(nid)
            seen_nids.add(nid)
            store.nodes[nid] = node

        store._duplicate_node_ids = duplicate_nids

        for edge in edges:
            src = edge.source_id
            tgt = edge.target_id
            etype = edge.edge_type

            # Ensure adjacency lists exist (even as empty for missing targets/sources)
            store.adj.setdefault(src, [])
            store.radj.setdefault(src, [])
            store.adj.setdefault(tgt, [])
            store.radj.setdefault(tgt, [])

            store.adj[src].append(edge)
            store.radj[tgt].append(edge)
            store.edge_index.setdefault(etype, []).append(edge)

        return store

    def validate_graph(
        self,
        store: GraphStore,
    ) -> dict[str, Any]:
        """
        Performs structural and referential validation on a GraphStore.

        Checks:
        ✓ duplicate node ids
        ✓ duplicate edges (same source, target, edge_type)
        ✓ missing source node
        ✓ missing target node
        ✓ orphan edges (either source or target node is missing from node list)
        ✓ invalid ids (not string)
        ✓ empty ids (None, empty string, or whitespace-only)
        ✓ self loops (warning only)

        Returns:
        {
            "is_valid": bool,
            "errors": list[str],
            "warnings": list[str],
            "node_count": int,
            "edge_count": int
        }
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Validate Duplicate Node IDs
        duplicate_nids = getattr(store, "_duplicate_node_ids", set())
        for nid in duplicate_nids:
            errors.append(f"Duplicate node ID detected: {nid}")

        # 2. Validate Nodes
        for nid, node in store.nodes.items():
            if node.node_id is None or str(node.node_id).strip() == "":
                errors.append(f"Empty node ID found for node: {node}")
            elif not isinstance(node.node_id, str):
                errors.append(f"Invalid node ID type (must be str) for node: {node}")

        # 3. Validate Edges
        seen_edges = set()
        all_edges = []
        for etype, edges in store.edge_index.items():
            all_edges.extend(edges)

        for edge in all_edges:
            src = edge.source_id
            tgt = edge.target_id
            etype = edge.edge_type

            # Validate IDs
            src_empty = src is None or str(src).strip() == ""
            tgt_empty = tgt is None or str(tgt).strip() == ""
            etype_empty = etype is None or str(etype).strip() == ""

            if src_empty:
                errors.append(f"Empty source ID in edge: {edge}")
            if tgt_empty:
                errors.append(f"Empty target ID in edge: {edge}")
            if etype_empty:
                errors.append(f"Empty edge type in edge: {edge}")

            if not src_empty and not isinstance(src, str):
                errors.append(f"Invalid source ID type (must be str) in edge: {edge}")
            if not tgt_empty and not isinstance(tgt, str):
                errors.append(f"Invalid target ID type (must be str) in edge: {edge}")

            # Duplicate edge detection
            edge_key = (src, tgt, etype)
            if edge_key in seen_edges:
                errors.append(f"Duplicate edge detected: source={src}, target={tgt}, type={etype}")
            else:
                seen_edges.add(edge_key)

            # Self-loops check (warning only)
            if src == tgt and not src_empty:
                warnings.append(f"Self-loop detected on node: {src}")

            # Missing endpoints and orphan edge checks
            src_missing = src not in store.nodes
            tgt_missing = tgt not in store.nodes

            if src_missing and not src_empty:
                errors.append(f"Missing source node ID: {src} in edge of type {etype}")
            if tgt_missing and not tgt_empty:
                errors.append(f"Missing target node ID: {tgt} in edge of type {etype}")

            if (src_missing or tgt_missing) and not (src_empty or tgt_empty):
                errors.append(f"Orphan edge detected: source={src}, target={tgt}, type={etype}")

        node_count = len(store.nodes)
        edge_count = len(all_edges)
        is_valid = len(errors) == 0

        return {
            "is_valid": is_valid,
            "errors": sorted(errors),
            "warnings": sorted(warnings),
            "node_count": node_count,
            "edge_count": edge_count,
        }
