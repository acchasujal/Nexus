"""
graph/services/serializers.py

Convert algorithm dataclasses to plain JSON-serializable dicts.
No business logic — just structural transformation.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from backend.app.core.graph.algorithms.utils import NodeRecord, AdjEdge


def serialize_node(node: NodeRecord | None) -> dict[str, Any] | None:
    """Convert a NodeRecord to a JSON-safe dict."""
    if node is None:
        return None
    return {
        "node_id": node.node_id,
        "entity_type": node.entity_type,
        "properties": _clean_props(node.properties),
    }


def serialize_edge(edge: AdjEdge) -> dict[str, Any]:
    """Convert an AdjEdge to a JSON-safe dict."""
    return {
        "source_id": edge.source_id,
        "target_id": edge.target_id,
        "edge_type": edge.edge_type,
        "properties": _clean_props(edge.properties),
    }


def serialize_dataclass(obj: Any) -> dict[str, Any]:
    """Convert any dataclass to a JSON-safe dict."""
    d = asdict(obj)
    return _clean_props(d)


def _clean_props(value: Any) -> Any:
    """Recursively clean values for JSON serialization."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(list(value))
    if isinstance(value, frozenset):
        return sorted(list(value))
    if isinstance(value, dict):
        return {k: _clean_props(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean_props(v) for v in value]
    return value