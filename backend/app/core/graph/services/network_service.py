"""
graph/services/network_service.py

Network traversal service: thin orchestration layer over the traversal algorithms.
All return values are JSON-serializable dicts.

Design rules
------------
* No traversal logic lives here -- all graph walking is delegated to the
  algorithm module (backend.app.core.graph.algorithms.traversals).
* GraphService already exposes get_case_network, get_person_network, and
  get_co_accused_network for its own callers (visualization endpoints).
  NetworkService does not duplicate those methods.
* Every public method is a thin wrapper: obtain store, call traversal, serialize.
"""

from __future__ import annotations

from typing import Any
from collections.abc import Sequence

from backend.app.core.graph.algorithms.traversals import (
    get_case,
    get_cases_for_person,
    get_cases_for_persons,
    get_clock_instances,
    get_co_accused,
    get_dependency_chain,
    get_evidence_for_case,
    get_neighbors,
    get_officer_cases,
    get_person,
    get_related_cases,
    get_sections_for_case,
    get_subgraph,
)
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.serializers import serialize_edge, serialize_node


class NetworkService:
    """
    Focused service for graph network and traversal operations.

    Initialized with a GraphRepository (which holds the GraphStore).
    Every public method returns JSON-serializable data.

    Notes
    -----
    Visualization-level subgraph methods (get_case_network, get_person_network,
    get_co_accused_network) already live in GraphService.  This service covers
    the remaining traversal surface not yet exposed at the service layer.
    """

    def __init__(self, repository: GraphRepository) -> None:
        self._repo = repository

    # =====================================================================
    # SINGLE-NODE LOOKUPS
    # =====================================================================

    def get_case(self, case_id: str) -> dict[str, Any]:
        store = self._repo.store

        print("=" * 50)
        print(f"Searching for: {case_id}")
        print(f"Total nodes: {len(store.nodes)}")

        node = get_case(store, case_id)

        if node is None:
            print("Case lookup returned None")
            return {"error": "Case not found", "case_id": case_id}

        print(f"Found node: {node.node_id}")
        return {"case": serialize_node(node)}

    def get_person(self, person_id: str) -> dict[str, Any]:
        """
        Return the Person node for person_id.

        Returns an error dict if the node does not exist or is not a Person.

        Used by: Person detail header / breadcrumb resolution
        """
        store = self._repo.store
        node = get_person(store, person_id)
        if node is None:
            return {"error": "Person not found", "person_id": person_id}
        return {"person": serialize_node(node)}

    # ======================================================================
    # CASE-CENTRIC TRAVERSALS
    # =====================================================================

    def get_related_cases(self, case_id: str) -> dict[str, Any]:
        """
        Return all cases linked to case_id via LINKED_TO edges.

        Used by: Case Detail -> Related Cases panel
        """
        store = self._repo.store
        if store.nodes.get(case_id) is None:
            return {"error": "Case not found", "case_id": case_id}
        nodes = get_related_cases(store, case_id)
        return {
            "case_id": case_id,
            "related_case_count": len(nodes),
            "related_cases": [serialize_node(n) for n in nodes],
        }

    def get_co_accused(self, case_id: str) -> dict[str, Any]:
        """
        Return all persons accused in case_id.

        Used by: Case Detail -> Accused Persons panel
        """
        store = self._repo.store
        if store.nodes.get(case_id) is None:
            return {"error": "Case not found", "case_id": case_id}
        nodes = get_co_accused(store, case_id)
        return {
            "case_id": case_id,
            "accused_count": len(nodes),
            "accused": [serialize_node(n) for n in nodes],
        }

    def get_dependency_chain(self, case_id: str) -> dict[str, Any]:
        """
        Return all Dependency nodes attached to case_id.

        Used by: Case Detail -> Dependencies / Investigation Blockers panel
        """
        store = self._repo.store
        if store.nodes.get(case_id) is None:
            return {"error": "Case not found", "case_id": case_id}
        nodes = get_dependency_chain(store, case_id)
        return {
            "case_id": case_id,
            "dependency_count": len(nodes),
            "dependencies": [serialize_node(n) for n in nodes],
        }

    def get_clock_instances(self, case_id: str) -> dict[str, Any]:
        """
        Return all ClockInstance nodes for case_id, sorted by days_remaining ascending.

        Used by: Case Detail -> BNS Clock panel
        """
        store = self._repo.store
        if store.nodes.get(case_id) is None:
            return {"error": "Case not found", "case_id": case_id}
        nodes = get_clock_instances(store, case_id)
        return {
            "case_id": case_id,
            "clock_count": len(nodes),
            "clocks": [serialize_node(n) for n in nodes],
        }

    def get_evidence_for_case(self, case_id: str) -> dict[str, Any]:
        """
        Return all Evidence nodes attached to case_id.

        Used by: Case Detail -> Evidence panel
        """
        store = self._repo.store
        if store.nodes.get(case_id) is None:
            return {"error": "Case not found", "case_id": case_id}
        nodes = get_evidence_for_case(store, case_id)
        return {
            "case_id": case_id,
            "evidence_count": len(nodes),
            "evidence": [serialize_node(n) for n in nodes],
        }

    def get_sections_for_case(self, case_id: str) -> dict[str, Any]:
        """
        Return all Section nodes a case is charged under.

        Used by: Case Detail -> Sections / Charges panel
        """
        store = self._repo.store
        if store.nodes.get(case_id) is None:
            return {"error": "Case not found", "case_id": case_id}
        nodes = get_sections_for_case(store, case_id)
        return {
            "case_id": case_id,
            "section_count": len(nodes),
            "sections": [serialize_node(n) for n in nodes],
        }

    # =======================================================================
    # PERSON-CENTRIC TRAVERSALS
    # =======================================================================

    def get_cases_for_person(self, person_id: str) -> dict[str, Any]:
        """
        Return all cases in which person_id appears (any role).

        Roles: accused, victim, complainant, witness.

        Used by: Person Profile -> Case History panel
        """
        store = self._repo.store
        if store.nodes.get(person_id) is None:
            return {"error": "Person not found", "person_id": person_id}
        nodes = get_cases_for_person(store, person_id)
        return {
            "person_id": person_id,
            "case_count": len(nodes),
            "cases": [serialize_node(n) for n in nodes],
        }

    def get_cases_for_persons(
        self,
        person_ids: Sequence[str],
    ) -> dict[str, Any]:
        """
        Batch version of get_cases_for_person.

        Returns a mapping of person_id to their case list.

        Used by: Bulk person-to-case resolution
        """
        store = self._repo.store
        raw = get_cases_for_persons(store, person_ids)
        return {
            "person_ids": list(person_ids),
            "results": {
                pid: [serialize_node(n) for n in cases]
                for pid, cases in raw.items()
            },
        }

    # ========================================================================
    # OFFICER-CENTRIC TRAVERSALS
    # ========================================================================

    def get_officer_cases(self, officer_id: str) -> dict[str, Any]:
        """
        Return all cases investigated by officer_id.

        Used by: Officer Profile -> Assigned Cases panel
        """
        store = self._repo.store
        if store.nodes.get(officer_id) is None:
            return {"error": "Officer not found", "officer_id": officer_id}
        nodes = get_officer_cases(store, officer_id)
        return {
            "officer_id": officer_id,
            "case_count": len(nodes),
            "cases": [serialize_node(n) for n in nodes],
        }

    # =======================================================================
    # GENERIC TRAVERSALS
    # ======================================================================

    def get_neighbors(self, node_id: str) -> dict[str, Any]:
        """
        Return all immediate outgoing neighbours of node_id.

        Used by: Generic graph explorer
        """
        store = self._repo.store
        if store.nodes.get(node_id) is None:
            return {"error": "Node not found", "node_id": node_id}
        nodes = get_neighbors(store, node_id)
        return {
            "node_id": node_id,
            "neighbor_count": len(nodes),
            "neighbors": [serialize_node(n) for n in nodes],
        }

    def get_subgraph(self, node_id: str, depth: int = 2) -> dict[str, Any]:
        """
        Return the node-induced subgraph reachable from node_id within depth hops.

        BFS runs in both directions (outgoing + incoming).

        Used by: Generic graph explorer / visualization
        """
        store = self._repo.store
        if store.nodes.get(node_id) is None:
            return {"error": "Node not found", "node_id": node_id}
        result = get_subgraph(store, node_id, depth=depth)
        return {
            "root_id": result.root_id,
            "depth": result.depth,
            "node_count": len(result.nodes),
            "edge_count": len(result.edges),
            "nodes": [serialize_node(n) for n in result.nodes],
            "edges": [serialize_edge(e) for e in result.edges],
        }
