"""Declarative schema for the unified investigation graph."""

from __future__ import annotations

from pydantic import BaseModel

from .enums import EdgeStorageMode, GraphEntityType, GraphRelationshipType


class GraphSchema(BaseModel):
    name: str
    version: str
    entities: tuple[GraphEntityType, ...]
    relationships: tuple[GraphRelationshipType, ...]
    derived_relationships: tuple[GraphRelationshipType, ...]


GRAPH_SCHEMA = GraphSchema(
    name="case_clock_investigation_graph",
    version="1.1",
    entities=(
        GraphEntityType.CASE,
        GraphEntityType.PERSON,
        GraphEntityType.OFFICER,
        GraphEntityType.UNIT,
        GraphEntityType.COURT,
        GraphEntityType.LOCATION,
        GraphEntityType.ACT,
        GraphEntityType.SECTION,
        GraphEntityType.CRIME_HEAD,
        GraphEntityType.CRIME_SUB_HEAD,
        GraphEntityType.EVIDENCE,
        GraphEntityType.DEPENDENCY,
        GraphEntityType.CLOCK_INSTANCE,
        GraphEntityType.ESCALATION_EVENT,
        GraphEntityType.CONVERSATION_LOG,
    ),
    relationships=(
        GraphRelationshipType.ACCUSED_IN,
        GraphRelationshipType.VICTIM_IN,
        GraphRelationshipType.COMPLAINANT_IN,
        GraphRelationshipType.WITNESS_IN,
        GraphRelationshipType.CASE_HAS_DEPENDENCY,
        GraphRelationshipType.CASE_HAS_CLOCK,
        GraphRelationshipType.CASE_HAS_EVIDENCE,
        GraphRelationshipType.CASE_HAS_COURT,
        GraphRelationshipType.CASE_HAS_CRIME_HEAD,
        GraphRelationshipType.CASE_HAS_CRIME_SUB_HEAD,
        GraphRelationshipType.CASE_HAS_ESCALATION_EVENT,
        GraphRelationshipType.CASE_HAS_CONVERSATION_LOG,
        GraphRelationshipType.INVESTIGATED_BY,
        GraphRelationshipType.CHARGED_UNDER,
        GraphRelationshipType.OCCURRED_IN,
        GraphRelationshipType.BELONGS_TO_UNIT,
        GraphRelationshipType.BELONGS_TO_ACT,
    ),
    derived_relationships=(
        GraphRelationshipType.CO_ACCUSED_WITH,
        GraphRelationshipType.LINKED_TO,
    ),
)


GRAPH_STORAGE_MODES = (
    EdgeStorageMode.STORED,
    EdgeStorageMode.DERIVED_NOT_STORED,
)