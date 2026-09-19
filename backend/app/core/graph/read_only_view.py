"""backend/app/core/graph/read_only_view.py

Strict read-only abstraction over the investigation graph repository.
Exposes only safe read operations needed for candidate resolution and analytical queries.
Guarantees at interface level that candidate extraction and resolution cannot mutate the graph.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class ReadOnlyGraphView:
    """Read-only view over the graph repository.

    Exposes ONLY safe inspection operations.
    Does NOT expose:
      - add_node, update_node, delete_node, upsert_node
      - add_edge, update_edge, delete_edge, upsert_edge
      - write transactions or state mutations
    """

    def __init__(self, repository: Any) -> None:
        self._repo = repository

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        """Retrieve a node record by its canonical ID."""
        nodes = getattr(self._repo, "nodes", {})
        node = nodes.get(node_id)
        if node is None:
            return None
        # Return a copy to prevent in-place mutation of internal dictionary
        return dict(node)

    def find_nodes(self, entity_type: str | None = None) -> list[dict[str, Any]]:
        """Find nodes optionally filtered by entity type."""
        nodes = getattr(self._repo, "nodes", {})
        if entity_type is None:
            return [dict(n) for n in nodes.values()]
        etype_lower = entity_type.lower()
        return [
            dict(n)
            for n in nodes.values()
            if str(n.get("entity_type", "")).lower() == etype_lower
        ]

    def iterate_nodes(self) -> Iterable[tuple[str, dict[str, Any]]]:
        """Iterate over all node IDs and node records."""
        nodes = getattr(self._repo, "nodes", {})
        for nid, n in nodes.items():
            yield str(nid), dict(n)

    def find_by_identifier(self, identifier: str) -> list[dict[str, Any]]:
        """Search nodes by identifier (phone number, account number, vehicle registration)."""
        clean_id = str(identifier).strip().lower()
        if not clean_id:
            return []
        matches: list[dict[str, Any]] = []
        nodes = getattr(self._repo, "nodes", {})
        for n in nodes.values():
            props = n.get("properties", {})
            for key in ("phone_number", "msisdn", "account_number", "vehicle_number", "registration_number", "imei"):
                val = str(props.get(key) or "").strip().lower()
                if val and (val == clean_id or clean_id in val):
                    matches.append(dict(n))
                    break
        return matches

    def get_relationships(self, node_id: str | None = None) -> list[dict[str, Any]]:
        """Retrieve edges, optionally incident to node_id."""
        edges = getattr(self._repo, "edges", [])
        if node_id is None:
            return [dict(e) for e in edges]
        nid_str = str(node_id)
        return [
            dict(e)
            for e in edges
            if str(e.get("source_id")) == nid_str or str(e.get("target_id")) == nid_str
        ]

    def get_case_context(self, case_id: str) -> dict[str, Any] | None:
        """Resolve district and station metadata for a case."""
        nodes = getattr(self._repo, "nodes", {})
        node = nodes.get(case_id)
        if node:
            props = node.get("properties", {})
            return {
                "case_id": case_id,
                "district": props.get("district"),
                "station_name": props.get("station_name") or props.get("police_station"),
            }
        return None

    def get_node_count(self) -> int:
        """Return the current count of graph nodes."""
        return len(getattr(self._repo, "nodes", {}))

    def get_edge_count(self) -> int:
        """Return the current count of graph edges."""
        return len(getattr(self._repo, "edges", []))
