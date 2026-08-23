"""backend/app/core/graph/graph_schema.py

Declarative schema for the NEXUS Unified Intelligence Graph.
"""

from __future__ import annotations

from pydantic import BaseModel

from .enums import GraphEntityType, GraphRelationshipType


class GraphSchema(BaseModel):
    name: str
    version: str
    entities: tuple[GraphEntityType, ...]
    relationships: tuple[GraphRelationshipType, ...]
    derived_relationships: tuple[GraphRelationshipType, ...]


GRAPH_SCHEMA = GraphSchema(
    name="nexus_intelligence_graph",
    version="2.0",
    entities=(
        GraphEntityType.PERSON,
        GraphEntityType.CASE,
        GraphEntityType.PHONE,
        GraphEntityType.VEHICLE,
        GraphEntityType.LOCATION,
        GraphEntityType.ORGANIZATION,
        GraphEntityType.DEVICE,
        GraphEntityType.ACCOUNT,
        GraphEntityType.TRANSACTION,
        GraphEntityType.EVENT,
        GraphEntityType.INTELLIGENCE_REPORT,
        GraphEntityType.EVIDENCE,
        GraphEntityType.OFFICER,
        GraphEntityType.UNIT,
        GraphEntityType.COURT,
    ),
    relationships=(
        GraphRelationshipType.INVOLVED_IN,
        GraphRelationshipType.ACCUSED_IN,
        GraphRelationshipType.VICTIM_IN,
        GraphRelationshipType.COMPLAINANT_IN,
        GraphRelationshipType.WITNESS_IN,
        GraphRelationshipType.USED_PHONE,
        GraphRelationshipType.USED_VEHICLE,
        GraphRelationshipType.SEEN_AT,
        GraphRelationshipType.ASSOCIATED_WITH,
        GraphRelationshipType.CONNECTED_TO,
        GraphRelationshipType.OWNS_ACCOUNT,
        GraphRelationshipType.TRANSFERRED_TO,
        GraphRelationshipType.OCCURRED_AT,
        GraphRelationshipType.OCCURRED_IN,
        GraphRelationshipType.MENTIONED_IN,
        GraphRelationshipType.HAS_EVIDENCE,
        GraphRelationshipType.SUPPORTED_BY,
        GraphRelationshipType.CHARGED_UNDER,
        GraphRelationshipType.INVESTIGATED_BY,
        GraphRelationshipType.BELONGS_TO_UNIT,
    ),
    derived_relationships=(
        GraphRelationshipType.CO_ACCUSED_WITH,
        GraphRelationshipType.LINKED_TO,
    ),
)