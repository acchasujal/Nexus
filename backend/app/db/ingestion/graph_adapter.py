"""Adapter from V2 ingestion bundles to the M1 GraphStore."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord
from backend.app.core.graph.edges import GraphEdge
from backend.app.core.graph.entities import GraphEntityBase, SourceRecord

from .contracts import IngestionBundle


def _node_id(node: GraphEntityBase) -> str:
    return str(node.id)


def _edge_properties(edge: GraphEdge) -> dict[str, Any]:
    """Flatten edge metadata into adapter properties for current M1 readers."""
    properties = dict(edge.properties)
    properties.update(
        {
            "id": str(edge.id) if edge.id else None,
            "start_time": edge.start_time,
            "end_time": edge.end_time,
            "source_record_id": edge.source_record_id,
            "derivation_class": edge.derivation_class.value,
            "confidence": edge.confidence,
            "provenance": edge.provenance.model_dump(mode="json"),
        }
    )
    return properties


def build_m1_graph_store(
    nodes: Iterable[GraphEntityBase],
    relationships: Iterable[GraphEdge],
) -> GraphStore:
    """Build an M1-compatible store without changing existing adapters."""
    store = GraphStore()
    node_list = list(nodes)
    relationship_list = list(relationships)
    for node in node_list:
        store.nodes[_node_id(node)] = NodeRecord(
            node_id=_node_id(node),
            entity_type=node.entity_type.value,
            properties=dict(node.properties),
        )
    for relationship in relationship_list:
        properties = _edge_properties(relationship)
        edge = AdjEdge(
            source_id=str(relationship.source_id),
            target_id=str(relationship.target_id),
            edge_type=relationship.edge_type.value,
            properties=properties,
        )
        store.adj.setdefault(edge.source_id, []).append(edge)
        store.radj.setdefault(edge.target_id, []).append(edge)
        store.edge_index.setdefault(edge.edge_type, []).append(edge)
    return store


def validate_graph_references(
    nodes: Iterable[GraphEntityBase],
    relationships: Iterable[GraphEdge],
    source_records: Iterable[SourceRecord],
) -> list[str]:
    """Return deterministic referential-integrity errors for a bundle."""
    node_ids = {str(node.id) for node in nodes}
    source_ids = {str(record.id) for record in source_records}
    errors: list[str] = []
    for edge in relationships:
        if edge.source_id not in node_ids:
            errors.append(f"orphan source node: {edge.source_id}")
        if edge.target_id not in node_ids:
            errors.append(f"orphan target node: {edge.target_id}")
        if edge.derivation_class.value == "FACT":
            if not edge.source_record_id:
                errors.append(f"fact edge missing source_record_id: {edge.id}")
            elif edge.source_record_id not in source_ids:
                errors.append(f"fact edge references unknown source record: {edge.id}")
    return sorted(errors)


def graph_store_from_bundle(bundle: IngestionBundle) -> GraphStore:
    """Build a GraphStore after validating the bundle's references."""
    errors = validate_graph_references(bundle.nodes, bundle.relationships, bundle.source_records)
    if errors:
        raise ValueError("; ".join(errors))
    return build_m1_graph_store(bundle.nodes, bundle.relationships)


__all__ = ["build_m1_graph_store", "graph_store_from_bundle", "validate_graph_references"]
