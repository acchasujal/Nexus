"""backend/app/core/graph/edges.py

Relationship definitions and provenance models for the NEXUS unified intelligence graph.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field

from .enums import EdgeStorageMode, GraphEntityType, GraphRelationshipType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceProvenance(BaseModel):
    """Provenance tracking for edges and derived relationships."""
    source_type: str = "DIRECT_RECORD"  # "FIR", "CDR", "BANK_TXN", "INTEL_REPORT", "INFERRED"
    source_id: str = ""
    timestamp: datetime = Field(default_factory=_utcnow)
    extracted_fact: str = ""
    derivation_method: str = "DIRECT"  # "DIRECT", "CO_OCCURRENCE", "CALL_RECORD", "FINANCIAL_LEDGER", "ENTITY_RESOLUTION"
    confidence: float = 1.0


class GraphEdge(BaseModel):
    """An instantiated edge in the NEXUS graph with provenance."""
    id: Optional[str] = None
    source_id: str
    target_id: str
    edge_type: GraphRelationshipType
    storage_mode: EdgeStorageMode = EdgeStorageMode.STORED
    weight: float = 1.0
    created_at: datetime = Field(default_factory=_utcnow)
    provenance: EvidenceProvenance = Field(default_factory=EvidenceProvenance)
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeDefinition(BaseModel):
    name: GraphRelationshipType
    source: GraphEntityType
    target: GraphEntityType
    storage_mode: EdgeStorageMode = EdgeStorageMode.STORED


# Relationship constants
ACCUSED_IN = GraphRelationshipType.ACCUSED_IN
VICTIM_IN = GraphRelationshipType.VICTIM_IN
COMPLAINANT_IN = GraphRelationshipType.COMPLAINANT_IN
WITNESS_IN = GraphRelationshipType.WITNESS_IN
INVOLVED_IN = GraphRelationshipType.INVOLVED_IN
USED_PHONE = GraphRelationshipType.USED_PHONE
USED_VEHICLE = GraphRelationshipType.USED_VEHICLE
SEEN_AT = GraphRelationshipType.SEEN_AT
ASSOCIATED_WITH = GraphRelationshipType.ASSOCIATED_WITH
CONNECTED_TO = GraphRelationshipType.CONNECTED_TO
OWNS_ACCOUNT = GraphRelationshipType.OWNS_ACCOUNT
TRANSFERRED_TO = GraphRelationshipType.TRANSFERRED_TO
OCCURRED_AT = GraphRelationshipType.OCCURRED_AT
OCCURRED_IN = GraphRelationshipType.OCCURRED_IN
MENTIONED_IN = GraphRelationshipType.MENTIONED_IN
HAS_EVIDENCE = GraphRelationshipType.HAS_EVIDENCE
SUPPORTED_BY = GraphRelationshipType.SUPPORTED_BY
CHARGED_UNDER = GraphRelationshipType.CHARGED_UNDER
INVESTIGATED_BY = GraphRelationshipType.INVESTIGATED_BY
BELONGS_TO_UNIT = GraphRelationshipType.BELONGS_TO_UNIT
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
        name=GraphRelationshipType.INVOLVED_IN,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.CASE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.USED_PHONE,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.PHONE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.USED_VEHICLE,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.VEHICLE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.SEEN_AT,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.LOCATION,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.ASSOCIATED_WITH,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.ORGANIZATION,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CONNECTED_TO,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.PERSON,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.OWNS_ACCOUNT,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.ACCOUNT,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.TRANSFERRED_TO,
        source=GraphEntityType.ACCOUNT,
        target=GraphEntityType.ACCOUNT,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.OCCURRED_AT,
        source=GraphEntityType.EVENT,
        target=GraphEntityType.LOCATION,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.OCCURRED_IN,
        source=GraphEntityType.CASE,
        target=GraphEntityType.LOCATION,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.MENTIONED_IN,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.INTELLIGENCE_REPORT,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.HAS_EVIDENCE,
        source=GraphEntityType.CASE,
        target=GraphEntityType.EVIDENCE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.CO_ACCUSED_WITH,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.PERSON,
        storage_mode=EdgeStorageMode.COMPUTED,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.LINKED_TO,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.PERSON,
        storage_mode=EdgeStorageMode.COMPUTED,
    ),
)