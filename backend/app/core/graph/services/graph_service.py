"""
graph/services/graph_service.py

Main service layer: wraps raw graph algorithms into production-ready methods.
All return values are JSON-serializable dicts.
"""

from __future__ import annotations

from typing import Any

from backend.app.core.graph.algorithms.aggregation import (
    crime_count_by_district,
    crime_count_by_station,
    crime_count_by_crime_head,
    crime_count_by_offence_category,
    officer_workload,
    case_counts,
)
from backend.app.core.graph.algorithms.clustering import (
    connected_components,
    betweenness_centrality,
)
from backend.app.core.graph.algorithms.similarity import (
    find_similar_cases,
    compute_case_similarity,
)
from backend.app.core.graph.algorithms.statistics import compute_graph_statistics
from backend.app.core.graph.algorithms.traversals import (
    get_subgraph,
    get_co_accused,
)
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.serializers import (
    serialize_node,
    serialize_edge,
    serialize_dataclass,
)


MAX_SEARCH_RESULTS: int = 50


class GraphService:
    """
    Production service for all graph intelligence operations.
    
    Initialized with a GraphRepository (which holds the GraphStore).
    Every public method returns JSON-serializable data.
    """

    def __init__(self, repository: GraphRepository) -> None:
        self._repo = repository

    def search_cases(
        self,
        offence_category: str | None = None,
        district: str | None = None,
        police_station: str | None = None,
        case_stage: str | None = None,
        risk_band: str | None = None,
        fir_number: str | None = None,
        case_number: str | None = None,
        reported_at: str | None = None,
        incident_at: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Search and filter Case nodes via GraphRepository.

        Supported filters: offence_category, district, police_station, case_stage,
        risk_band, fir_number, case_number, reported_at, incident_at.

        Returns:
            dict with total matching "count", "returned" count, and serialized "cases" (capped at 50).
        """
        filters: dict[str, Any] = {
            "offence_category": offence_category,
            "district": district,
            "police_station": police_station,
            "case_stage": case_stage,
            "risk_band": risk_band,
            "fir_number": fir_number,
            "case_number": case_number,
            "reported_at": reported_at,
            "incident_at": incident_at,
        }
        for k, v in kwargs.items():
            if v is not None and k not in filters:
                filters[k] = v

        matching_nodes = self._repo.search_cases(**filters)
        total_count = len(matching_nodes)
        limited_nodes = matching_nodes[:MAX_SEARCH_RESULTS]

        return {
            "count": total_count,
            "returned": len(limited_nodes),
            "cases": [serialize_node(node) for node in limited_nodes],
        }

    # ═══════════════════════════════════════════════════════════════════════
    # NETWORK & TRAVERSAL
    # ═══════════════════════════════════════════════════════════════════════

    def get_case_network(self, case_id: str, depth: int = 2) -> dict[str, Any]:
        """
        Return the subgraph around a case: nodes + edges for visualization.
        
        Used by: Case Detail → Network tab
        """
        store = self._repo.store
        result = get_subgraph(store, case_id, depth=depth)

        return {
            "root_id": result.root_id,
            "depth": result.depth,
            "nodes": [serialize_node(n) for n in result.nodes],
            "edges": [serialize_edge(e) for e in result.edges],
            "node_count": len(result.nodes),
            "edge_count": len(result.edges),
        }

    def get_person_network(self, person_id: str, depth: int = 2) -> dict[str, Any]:
        """
        Return the subgraph around a person.
        
        Used by: Offender Profile → Network tab
        """
        store = self._repo.store
        result = get_subgraph(store, person_id, depth=depth)

        return {
            "root_id": result.root_id,
            "depth": result.depth,
            "nodes": [serialize_node(n) for n in result.nodes],
            "edges": [serialize_edge(e) for e in result.edges],
        }

    def get_co_accused_network(self, person_id: str) -> dict[str, Any]:
        """
        Return all co-accused for a person (1-hop via shared cases).

        Used by: Network Analysis → Co-accused view
        """
        store = self._repo.store

        # Step 1: Find all cases where this person is accused.
        person_cases = [
            edge.target_id
            for edge in store.adj.get(person_id, [])
            if edge.edge_type == "ACCUSED_IN"
        ]

        # Step 2: Collect co-accused across those cases.
        co_accused_map: dict[str, list] = {}

        for case_id in person_cases:
            accused = get_co_accused(store, case_id)

            for person in accused:
                if person.node_id == person_id:
                    continue  # Don't include the original person

                co_accused_map.setdefault(person.node_id, []).append(
                    store.nodes[case_id]
                )

        # Step 3: Build JSON response.
        return {
            "person_id": person_id,
            "co_accused": [
                {
                    "person_id": pid,
                    "shared_cases": [
                        serialize_node(case)
                        for case in shared_cases
                    ],
                }
                for pid, shared_cases in co_accused_map.items()
            ],
            "co_accused_count": len(co_accused_map),
        }

    def find_paths_between(self, source_id: str, target_id: str, max_depth: int = 4) -> dict[str, Any]:
        """
        Find one shortest path between two graph nodes using bidirectional edge traversal.

        This backs the graph router's /paths endpoint. It returns a small JSON
        payload instead of raw graph internals so route callers get a stable shape.
        """
        store = self._repo.store
        if source_id not in store.nodes or target_id not in store.nodes:
            return {
                "source_id": source_id,
                "target_id": target_id,
                "path_found": False,
                "nodes": [],
                "edges": [],
            }

        queue: list[tuple[str, list[str], list[Any]]] = [(source_id, [source_id], [])]
        visited: set[str] = {source_id}

        while queue:
            current_id, path_ids, path_edges = queue.pop(0)
            if len(path_ids) - 1 >= max_depth:
                continue

            incident_edges = [
                *store.adj.get(current_id, []),
                *store.radj.get(current_id, []),
            ]
            for edge in incident_edges:
                next_id = edge.target_id if edge.source_id == current_id else edge.source_id
                if next_id in visited:
                    continue
                next_path_ids = [*path_ids, next_id]
                next_path_edges = [*path_edges, edge]
                if next_id == target_id:
                    return {
                        "source_id": source_id,
                        "target_id": target_id,
                        "path_found": True,
                        "depth": len(next_path_ids) - 1,
                        "nodes": [serialize_node(store.nodes[node_id]) for node_id in next_path_ids],
                        "edges": [serialize_edge(path_edge) for path_edge in next_path_edges],
                    }
                visited.add(next_id)
                queue.append((next_id, next_path_ids, next_path_edges))

        return {
            "source_id": source_id,
            "target_id": target_id,
            "path_found": False,
            "nodes": [],
            "edges": [],
        }

    

    # ═══════════════════════════════════════════════════════════════════════
    # SIMILARITY
    # ═══════════════════════════════════════════════════════════════════════

    def get_similar_cases(self, case_id: str, top_k: int = 10, min_score: float = 0.1) -> dict[str, Any]:
        """
        Find cases similar to the given case with explainable scores.
        
        Used by: Case Detail → Similar Cases tab
        """
        store = self._repo.store
        results = find_similar_cases(store, case_id, top_k=top_k, min_score=min_score)

        matches = []
        for r in results:
            # Identify the OTHER case (not the requested anchor case)
            if r.case_a_id == case_id and r.case_b_id != case_id:
                other_case_id = r.case_b_id
            elif r.case_b_id == case_id and r.case_a_id != case_id:
                other_case_id = r.case_a_id
            else:
                raise ValueError(
                    "Similarity result does not contain the requested case as "
                    "exactly one endpoint."
                )
            matches.append({
                "case_id": other_case_id,
                "score": r.score,
                # reasons = human-readable matched feature names
                "reasons": r.matched_features,
                # properties = feature-to-weight contribution mapping
                "properties": r.feature_contributions,
            })

        return {
            "case_id": case_id,
            "top_k": top_k,
            "min_score": min_score,
            "matches": matches,
            "match_count": len(matches),
        }

    def compare_two_cases(self, case_a_id: str, case_b_id: str) -> dict[str, Any]:
        """
        Direct similarity comparison between two cases.
        
        Used by: Side-by-side case comparison
        """
        store = self._repo.store
        result = compute_case_similarity(store, case_a_id, case_b_id)

        return serialize_dataclass(result)

    # ═══════════════════════════════════════════════════════════════════════
    # AGGREGATIONS (for Dashboard)
    # ═══════════════════════════════════════════════════════════════════════

    def get_crime_summary(self) -> dict[str, Any]:
        """
        High-level case statistics.

        Used by: Dashboard → Summary cards
        """
        store = self._repo.store
        summary = case_counts(store)

        return {
            "total_cases": summary.total,
            "by_stage": summary.by_stage,
            "by_category": summary.by_offence_category,
            "by_risk": summary.by_risk_band,
        }

    def get_crime_by_district(self) -> dict[str, Any]:
        """Crime counts per district. Used by: Map layer / District rollup."""
        store = self._repo.store
        return {
            "dimension": "district",
            "counts": crime_count_by_district(store),
        }

    def get_crime_by_station(self) -> dict[str, Any]:
        """Crime counts per police station."""
        store = self._repo.store
        return {
            "dimension": "police_station",
            "counts": crime_count_by_station(store),
        }

    def get_crime_by_crime_head(self) -> dict[str, Any]:
        """Crime counts per crime head category."""
        store = self._repo.store
        return {
            "dimension": "crime_head",
            "counts": crime_count_by_crime_head(store),
        }

    def get_crime_by_offence_category(self) -> dict[str, Any]:
        """Crime counts per offence category (for BNSS clock mapping)."""
        store = self._repo.store
        return {
            "dimension": "offence_category",
            "counts": crime_count_by_offence_category(store),
        }

    def get_officer_workload(self) -> dict[str, Any]:
        """
        Case count per investigating officer.
        
        Used by: Supervisor dashboard → workload balancing
        """
        store = self._repo.store
        workload = officer_workload(store)

        return {
            "dimension": "officer",
            "workloads": [
                {"officer_id": oid, "case_count": count}
                for oid, count in workload.items()
            ],
            "total_officers": len(workload),
        }

    # ═══════════════════════════════════════════════════════════════════════
    # GRAPH STATISTICS & CLUSTERING
    # ═══════════════════════════════════════════════════════════════════════

    def get_graph_stats(self) -> dict[str, Any]:
        """Overall graph health metrics."""
        store = self._repo.store
        stats = compute_graph_statistics(store)

        return {
            "node_count": stats.num_nodes,
            "edge_count": stats.num_edges,
            "density": stats.density,
            "average_degree": stats.average_degree,
            "node_counts_by_type": stats.entity_distribution,
            "edge_counts_by_type": stats.relationship_distribution,
        }

    def get_connected_components(self) -> dict[str, Any]:
        """
        Find disconnected criminal networks.
        
        Used by: Network Analysis → Organized crime detection
        """
        store = self._repo.store
        components = connected_components(store)

        return {
            "component_count": len(components),
            "components": [
                {
                    "size": len(comp),
                    "node_ids": sorted(list(comp)),
                }
                for comp in components[:20]  # Limit to top 20 for perf
            ],
            "largest_component_size": len(components[0]) if components else 0,
        }

    def get_central_figures(self, top_k: int = 20) -> dict[str, Any]:
        """
        Most connected nodes by betweenness centrality.
        
        Used by: Intelligence → Key players identification
        """
        store = self._repo.store
        centrality = betweenness_centrality(store)

        sorted_nodes = sorted(
            centrality.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        return {
            "metric": "betweenness_centrality",
            "top_nodes": [
                {
                    "node_id": nid,
                    "score": round(score, 6),
                    "node": serialize_node(store.nodes.get(nid)),
                }
                for nid, score in sorted_nodes
            ],
        }



    
