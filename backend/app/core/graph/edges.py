"""backend/app/core/graph/edges.py

Relationship definitions and provenance models for the NEXUS unified intelligence graph (Schema V2).
Supports temporal windows (start_time, end_time), explicit DerivationClass (FACT, DERIVED, HYPOTHESIS),
and SourceRecord lineage tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from .enums import DerivationClass, EdgeStorageMode, GraphEntityType, GraphRelationshipType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceProvenance(BaseModel):
    """Provenance tracking for edges, assertions, and derived relationships."""
    source_type: str = "DIRECT_RECORD"  # "FIR", "CDR", "BANK_TXN", "INTEL_REPORT", "INFERRED"
    source_id: str = ""
    source_record_id: Optional[str] = None  # Pointer to canonical SourceRecord node ID
    timestamp: datetime = Field(default_factory=_utcnow)
    extracted_fact: str = ""
    derivation_method: str = "DIRECT"  # "DIRECT", "CO_OCCURRENCE", "CALL_RECORD", "FINANCIAL_LEDGER", "ENTITY_RESOLUTION"
    derivation_class: DerivationClass = DerivationClass.FACT
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Provenance confidence must be between 0.0 and 1.0, got {v}")
        return float(v)


class GraphEdge(BaseModel):
    """
    An instantiated relationship/edge in the NEXUS Schema V2 graph.

    Fields:
      id               : Stable edge identifier
      source_id        : Source node ID (non-empty)
      target_id        : Target node ID (non-empty)
      edge_type        : Relationship type enum
      start_time       : Optional start timestamp for temporal window
      end_time         : Optional end timestamp for temporal window
      confidence       : Numeric confidence score (0.0 <= confidence <= 1.0)
      derivation_class : Fact classification enum (FACT | DERIVED | HYPOTHESIS)
      source_record_id : Optional pointer to source record entity
      storage_mode     : Storage mode (STORED vs COMPUTED)
      weight           : Edge weight score
      created_at       : Instantiation timestamp
      provenance       : EvidenceProvenance citation object
      properties       : Additional edge properties
    """
    id: Optional[str] = None
    source_id: str
    target_id: str
    edge_type: GraphRelationshipType
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    derivation_class: DerivationClass = DerivationClass.FACT
    source_record_id: Optional[str] = None
    storage_mode: EdgeStorageMode = EdgeStorageMode.STORED
    weight: float = 1.0
    created_at: datetime = Field(default_factory=_utcnow)
    provenance: EvidenceProvenance = Field(default_factory=EvidenceProvenance)
    properties: dict[str, Any] = Field(default_factory=dict)

    @property
    def type(self) -> GraphRelationshipType:
        """Alias property for canonical Schema V2 type key."""
        return self.edge_type

    @field_validator("source_id", "target_id")
    @classmethod
    def validate_node_ids(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Edge source_id and target_id must be non-empty strings")
        return str(v).strip()

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Edge confidence must be between 0.0 and 1.0, got {v}")
        return float(v)

    @model_validator(mode="before")
    @classmethod
    def handle_type_alias_and_kwargs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Accept 'type' as alias for 'edge_type'
            if "type" in data and "edge_type" not in data:
                data["edge_type"] = data.pop("type")
        return data

    @model_validator(mode="after")
    def validate_and_sync(self) -> GraphEdge:
        # Auto-generate ID if missing
        if not self.id:
            etype_str = self.edge_type.value if hasattr(self.edge_type, "value") else str(self.edge_type)
            self.id = f"rel_{self.source_id}_{etype_str}_{self.target_id}"

        # Temporal validation
        if self.start_time and self.end_time:
            if self.start_time > self.end_time:
                raise ValueError(
                    f"Relationship start_time ({self.start_time}) cannot be later than end_time ({self.end_time})"
                )

        # Sync provenance metadata
        if self.source_record_id and not self.provenance.source_record_id:
            self.provenance.source_record_id = self.source_record_id
        elif self.provenance.source_record_id and not self.source_record_id:
            self.source_record_id = self.provenance.source_record_id

        if self.derivation_class != self.provenance.derivation_class:
            self.provenance.derivation_class = self.derivation_class

        if self.confidence != self.provenance.confidence:
            self.provenance.confidence = self.confidence

        return self


# Convenience Alias for V2 Contract
Relationship = GraphEdge


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
TRANSFERRED_FUNDS = GraphRelationshipType.TRANSFERRED_FUNDS
COMMUNICATED_WITH = GraphRelationshipType.COMMUNICATED_WITH
SHARED_PHONE = GraphRelationshipType.SHARED_PHONE
OWNS_VEHICLE = GraphRelationshipType.OWNS_VEHICLE
PRESENT_AT = GraphRelationshipType.PRESENT_AT
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
CITES_SOURCE = GraphRelationshipType.CITES_SOURCE
PARTICIPATED_IN = GraphRelationshipType.PARTICIPATED_IN


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
        name=GraphRelationshipType.OWNS_VEHICLE,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.VEHICLE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.SEEN_AT,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.LOCATION,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.PRESENT_AT,
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
        name=GraphRelationshipType.COMMUNICATED_WITH,
        source=GraphEntityType.PHONE,
        target=GraphEntityType.PHONE,
    ),
    GraphEdgeDefinition(
        name=GraphRelationshipType.SHARED_PHONE,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.PHONE,
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
        name=GraphRelationshipType.TRANSFERRED_FUNDS,
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
        name=GraphRelationshipType.PARTICIPATED_IN,
        source=GraphEntityType.PERSON,
        target=GraphEntityType.EVENT,
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
        name=GraphRelationshipType.CITES_SOURCE,
        source=GraphEntityType.EVIDENCE,
        target=GraphEntityType.SOURCE_RECORD,
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