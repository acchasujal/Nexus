"""Relationship constants for the unified investigation graph."""

from __future__ import annotations

from pydantic import BaseModel

from .enums import EdgeStorageMode, GraphEntityType, GraphRelationshipType


class GraphEdgeDefinition(BaseModel):
    name: GraphRelationshipType
    source: GraphEntityType
    target: GraphEntityType
    storage_mode: EdgeStorageMode = EdgeStorageMode.STORED


ACCUSED_IN = GraphRelationshipType.ACCUSED_IN
VICTIM_IN = GraphRelationshipType.VICTIM_IN
COMPLAINANT_IN = GraphRelationshipType.COMPLAINANT_IN
WITNESS_IN = GraphRelationshipType.WITNESS_IN
CASE_HAS_DEPENDENCY = GraphRelationshipType.CASE_HAS_DEPENDENCY
CASE_HAS_CLOCK = GraphRelationshipType.CASE_HAS_CLOCK
CASE_HAS_EVIDENCE = GraphRelationshipType.CASE_HAS_EVIDENCE
CASE_HAS_COURT = GraphRelationshipType.CASE_HAS_COURT
CASE_HAS_CRIME_HEAD = GraphRelationshipType.CASE_HAS_CRIME_HEAD
CASE_HAS_CRIME_SUB_HEAD = GraphRelationshipType.CASE_HAS_CRIME_SUB_HEAD
CASE_HAS_ESCALATION_EVENT = GraphRelationshipType.CASE_HAS_ESCALATION_EVENT
CASE_HAS_CONVERSATION_LOG = GraphRelationshipType.CASE_HAS_CONVERSATION_LOG
INVESTIGATED_BY = GraphRelationshipType.INVESTIGATED_BY
CHARGED_UNDER = GraphRelationshipType.CHARGED_UNDER
OCCURRED_IN = GraphRelationshipType.OCCURRED_IN
BELONGS_TO_UNIT = GraphRelationshipType.BELONGS_TO_UNIT
BELONGS_TO_ACT = GraphRelationshipType.BELONGS_TO_ACT
CO_ACCUSED_WITH = GraphRelationshipType.CO_ACCUSED_WITH
LINKED_TO = GraphRelationshipType.LINKED_TO


GRAPH_EDGE_DEFINITIONS = (
    GraphEdgeDefinition(
        name=GraphRelationshipType.ACCUSED_IN,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.CASE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.VICTIM_IN,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.CASE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.COMPLAINANT_IN,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.CASE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.WITNESS_IN,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.CASE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CASE_HAS_DEPENDENCY,
        source=GraphEntityType.CASE,
        target=GraphEntityType.DEPENDENCY,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CASE_HAS_CLOCK,
        source=GraphEntityType.CASE,
        target=GraphEntityType.CLOCK_INSTANCE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CASE_HAS_EVIDENCE,
        source=GraphEntityType.CASE,
        target=GraphEntityType.EVIDENCE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CASE_HAS_COURT,
        source=GraphEntityType.CASE,
        target=GraphEntityType.COURT,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CASE_HAS_CRIME_HEAD,
        source=GraphEntityType.CASE,
        target=GraphEntityType.CRIME_HEAD,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CASE_HAS_CRIME_SUB_HEAD,
        source=GraphEntityType.CASE,
        target=GraphEntityType.CRIME_SUB_HEAD,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CASE_HAS_ESCALATION_EVENT,
        source=GraphEntityType.CASE,
        target=GraphEntityType.ESCALATION_EVENT,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CASE_HAS_CONVERSATION_LOG,
        source=GraphEntityType.CASE,
        target=GraphEntityType.CONVERSATION_LOG,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.INVESTIGATED_BY,
        source=GraphEntityType.CASE,
        target=GraphEntityType.OFFICER,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CHARGED_UNDER,
        source=GraphEntityType.CASE,
        target=GraphEntityType.SECTION,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.OCCURRED_IN,
        source=GraphEntityType.CASE,
        target=GraphEntityType.LOCATION,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.BELONGS_TO_UNIT,
        source=GraphEntityType.OFFICER,
        target=GraphEntityType.UNIT,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.BELONGS_TO_ACT,
        source=GraphEntityType.SECTION,
        target=GraphEntityType.ACT,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CO_ACCUSED_WITH,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.PERSON,
        storage_mode=EdgeStorageMode.DERIVED_NOT_STORED,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.LINKED_TO,
        source=GraphEntityType.CASE,
        target=GraphEntityType.CASE,
        storage_mode=EdgeStorageMode.DERIVED_NOT_STORED,
    ),
)