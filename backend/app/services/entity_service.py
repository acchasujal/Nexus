"""backend/app/services/entity_service.py

Entity profile and search service for the NEXUS Criminal Intelligence Platform.

Provides:
  - EntityService: full entity profiles with evidence, centrality, and community data
  - Entity search across graph nodes by name/phone/vehicle

Design: wraps GraphStore reads, EvidenceService, and clustering algorithms
into a single profile response per entity.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.core.graph.algorithms.clustering import (
    betweenness_centrality,
    detect_communities,
)
from backend.app.core.graph.algorithms.traversals import get_subgraph
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.evidence_service import EvidenceService
from shared.contracts.api import (
    EntityProfileResponse,
    GraphEdgeResponse,
    GraphNodeResponse,
    NetworkGraphResponse,
)

logger = logging.getLogger(__name__)


class EntityService:
    """Application service for entity profile retrieval, search, and network expansion.

    Every public method returns JSON-serializable Pydantic models.
    Audit events are logged for profile retrievals (ENTITY_VIEWED).
    """

    def __init__(
        self,
        repository: Any,
        audit_service: AuditService,
        evidence_service: EvidenceService,
    ) -> None:
        self._repo = repository
        self._audit = audit_service
        self._evidence = evidence_service

    # ── Profile ────────────────────────────────────────────────────────────────

    def get_entity_profile(
        self,
        entity_id: str,
        actor_id: str,
        request_id: str | None = None,
    ) -> EntityProfileResponse | None:
        """Retrieve a full entity profile including evidence, centrality, and community.

        Returns None if entity_id is not found in the graph.
        """
        store = self._repo.to_graph_store()
        node = store.nodes.get(entity_id)
        if node is None:
            return None

        props = node.properties or {}

        # Degree: count edges where this entity is source or target
        degree = 0
        for edges in store.edge_index.values():
            for edge in edges:
                if edge.source_id == entity_id or edge.target_id == entity_id:
                    degree += 1

        # Community assignment
        community_id: str | None = None
        try:
            communities = detect_communities(store)
            for comm in communities:
                if entity_id in comm.member_ids:
                    community_id = comm.community_id
                    break
        except (ValueError, TypeError, AttributeError):  # pragma: no cover
            community_id = None

        # Betweenness score
        betweenness_score: float | None = None
        try:
            btw = betweenness_centrality(store)
            betweenness_score = btw.get(entity_id)
        except (ValueError, TypeError, ZeroDivisionError):  # pragma: no cover
            betweenness_score = None

        # Aliases from properties
        aliases: list[str] = props.get("aliases", [])
        if isinstance(aliases, str):
            aliases = [aliases]

        # Evidence citations
        evidence_items = self._evidence.get_evidence_for_entity(
            entity_id=entity_id,
            actor_id=actor_id,
            request_id=request_id,
        )

        # Label: prefer human-readable name fields
        label = (
            props.get("full_name")
            or props.get("fir_number")
            or props.get("phone_number")
            or props.get("vehicle_number")
            or props.get("name")
            or entity_id
        )

        self._audit.record(
            AuditEventType.ENTITY_VIEWED,
            actor_id=actor_id,
            entity_id=entity_id,
            entity_type=node.entity_type,
            request_id=request_id,
        )

        return EntityProfileResponse(
            entity_id=entity_id,
            entity_type=node.entity_type,
            label=label,
            properties=props,
            aliases=aliases,
            degree=degree,
            community_id=community_id,
            betweenness_score=round(betweenness_score, 6) if betweenness_score is not None else None,
            evidence_items=evidence_items[:20],  # cap at 20 items for response size
        )

    # ── Network Expansion ──────────────────────────────────────────────────────

    def get_entity_network(
        self,
        entity_id: str,
        depth: int = 2,
        actor_id: str = "system",
        request_id: str | None = None,
    ) -> NetworkGraphResponse:
        """Expand a BFS subgraph centered on the given entity.

        Returns a NetworkGraphResponse compatible with the frontend canvas.
        """
        store = self._repo.to_graph_store()
        subgraph = get_subgraph(store, node_id=entity_id, depth=depth)

        nodes: list[GraphNodeResponse] = []
        edges: list[GraphEdgeResponse] = []

        for node_record in subgraph.nodes:
            props = node_record.properties or {}
            label = (
                props.get("full_name")
                or props.get("fir_number")
                or props.get("phone_number")
                or node_record.node_id
            )
            nodes.append(
                GraphNodeResponse(
                    id=node_record.node_id,
                    entity_type=node_record.entity_type,
                    label=label,
                    properties=props,
                )
            )

        for edge in subgraph.edges:
            from shared.contracts.api import EvidenceProvenanceContract
            prov_dict = (edge.properties or {}).get("provenance") or {}
            edges.append(
                GraphEdgeResponse(
                    id=f"{edge.source_id}-{edge.edge_type}-{edge.target_id}",
                    source_id=edge.source_id,
                    target_id=edge.target_id,
                    edge_type=edge.edge_type,
                    weight=float((edge.properties or {}).get("weight", 1.0)),
                    provenance=EvidenceProvenanceContract(
                        source_type=prov_dict.get("source_type", "DIRECT_RECORD"),
                        source_id=prov_dict.get("source_id", ""),
                        timestamp=prov_dict.get("timestamp") or None,
                        extracted_fact=prov_dict.get("extracted_fact", ""),
                        derivation_method=prov_dict.get("derivation_method", "DIRECT"),
                        confidence=float(prov_dict.get("confidence", 1.0)),
                    ),
                    properties=edge.properties or {},
                )
            )

        return NetworkGraphResponse(
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
        )

    # ── Search ────────────────────────────────────────────────────────────────

    def search_entities(
        self,
        query: str,
        entity_type: str | None = None,
        limit: int = 20,
        actor_id: str = "system",
    ) -> list[EntityProfileResponse]:
        """Search for entities matching a query string.

        Searches: full_name, phone_number, vehicle_number, fir_number, national_id.
        Optionally filter by entity_type (e.g. "Person", "Case", "Phone").
        Returns up to `limit` results.
        """
        store = self._repo.to_graph_store()
        query_lower = query.strip().lower()
        results: list[EntityProfileResponse] = []

        for nid, node in store.nodes.items():
            if entity_type and node.entity_type != entity_type:
                continue

            props = node.properties or {}
            searchable = " ".join(
                str(v)
                for k, v in props.items()
                if k in ("full_name", "phone_number", "vehicle_number", "fir_number", "national_id", "name")
            ).lower()

            if query_lower not in searchable:
                continue

            # Build lightweight profile (no evidence fetch for search — use get_entity_profile for detail)
            label = (
                props.get("full_name")
                or props.get("fir_number")
                or props.get("phone_number")
                or props.get("vehicle_number")
                or nid
            )
            results.append(
                EntityProfileResponse(
                    entity_id=nid,
                    entity_type=node.entity_type,
                    label=label,
                    properties=props,
                    aliases=props.get("aliases", []),
                    degree=0,
                    community_id=None,
                    betweenness_score=None,
                    evidence_items=[],
                )
            )

            if len(results) >= limit:
                break

        return results
