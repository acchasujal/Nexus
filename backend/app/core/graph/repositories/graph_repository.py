"""
graph/repositories/graph_repository.py

Bridge between persistent database and in-memory GraphStore.
Currently stubs the DB layer — Dev 1 will wire real models.
"""

from __future__ import annotations

from typing import Any

from backend.app.core.graph.algorithms.utils import GraphStore, NodeRecord, AdjEdge


class GraphRepository:
    """
    Loads and persists graph data from/to the database.
    
    For now, operates on an injected GraphStore (in-memory).
    When Dev 1 provides DB models, replace the load methods
    with SQL queries that build NodeRecord/AdjEdge objects.
    """

    def __init__(self, store: GraphStore | None = None) -> None:
        self._store = store or GraphStore()
        self._db_session: Any = None  # Dev 1 will inject this

    # ── Public API ───────────────────────────────────────────────────────────

    @property
    def store(self) -> GraphStore:
        """Return the current in-memory graph."""
        return self._store

    def load_from_db(self, session: Any) -> GraphStore:
        """
        Load entire graph from database into memory.
        
        # Populate graph from persistent store (PostgreSQL / Neo4j session):
        
        cases = session.query(Case).all()
        for case in cases:
            self._add_node(case.id, "Case", { ...case fields... })
            for accused in case.accused:
                self._add_node(accused.person_id, "Person", { ... })
                self._add_edge(accused.person_id, case.id, "ACCUSED_IN")
        """
        self._db_session = session
        # For now, return whatever store was injected
        return self._store

    def refresh(self) -> GraphStore:
        """Reload graph from database (call after mutations)."""
        self._store = GraphStore()
        if self._db_session:
            self.load_from_db(self._db_session)
        return self._store

    def get_case(self, case_id: str) -> NodeRecord | None:
        """Fetch a single case node by ID."""
        return self._store.nodes.get(case_id)

    def get_person(self, person_id: str) -> NodeRecord | None:
        """Fetch a single person node by ID."""
        return self._store.nodes.get(person_id)

    def get_cases_for_person(self, person_id: str, role: str | None = None) -> list[NodeRecord]:
        """
        Return all cases a person is involved in.
        Optional role filter: "ACCUSED_IN", "VICTIM_IN", etc.
        """
        results: list[NodeRecord] = []
        for edge in self._store.adj.get(person_id, []):
            if role and edge.edge_type != role:
                continue
            case_node = self._store.nodes.get(edge.target_id)
            if case_node and case_node.entity_type == "Case":
                results.append(case_node)
        return results

    def search_cases(self, **filters: Any) -> list[NodeRecord]:
        """
        Search and filter Case nodes in the graph store based on metadata filters.

        Performs case-insensitive normalized substring matching across case properties.
        """
        active_filters = {
            k: str(v)
            for k, v in filters.items()
            if v is not None and str(v).strip() != ""
        }
        if not active_filters:
            return [n for n in self._store.nodes.values() if n.entity_type == "Case"]

        matching_cases: list[NodeRecord] = []
        for node in self._store.nodes.values():
            if node.entity_type != "Case":
                continue

            match = True
            for key, filter_val in active_filters.items():
                prop_val = node.properties.get(key)
                if key == "case_number" and prop_val is None:
                    prop_val = node.properties.get("case_id", node.node_id)
                elif key == "fir_number" and prop_val is None:
                    prop_val = node.properties.get("fir_no")

                if not _match_filter(prop_val, filter_val):
                    match = False
                    break

            if match:
                matching_cases.append(node)

        return matching_cases


def _match_filter(prop_val: Any, filter_val: str) -> bool:
    """Helper for case-insensitive normalized substring matching between properties and filters."""
    if prop_val is None:
        return False
    p_str = str(prop_val).strip().lower()
    f_str = str(filter_val).strip().lower()
    if p_str == f_str:
        return True
    p_norm = p_str.replace("_", " ").replace("-", " ")
    f_norm = f_str.replace("_", " ").replace("-", " ")
    if p_norm == f_norm:
        return True
    if f_norm in p_norm:
        return True
    return False



    # ── Internal helpers (for Dev 1 to extend) ─────────────────────────────

    def _add_node(self, node_id: str, entity_type: str, properties: dict) -> None:
        """Add or update a node in the store."""
        self._store.nodes[node_id] = NodeRecord(
            node_id=node_id,
            entity_type=entity_type,
            properties=properties,
        )

    def _add_edge(self, source_id: str, target_id: str, edge_type: str, properties: dict | None = None) -> None:
        """Add an edge to the store and update adjacency index."""
        edge = AdjEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            properties=properties or {},
        )
        self._store.edge_index.setdefault(edge_type, []).append(edge)
        self._store.adj.setdefault(source_id, []).append(edge)