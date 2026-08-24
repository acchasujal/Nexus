"""backend/app/core/graph/enums.py

Graph entity and relationship types for the NEXUS Criminal Network Intelligence Platform.
Schema V2 contract definition.
"""

from __future__ import annotations

from enum import Enum


class GraphEntityType(str, Enum):
    PERSON = "Person"
    CASE = "Case"
    PHONE = "Phone"
    VEHICLE = "Vehicle"
    LOCATION = "Location"
    ORGANIZATION = "Organization"
    DEVICE = "Device"
    ACCOUNT = "Account"
    TRANSACTION = "Transaction"
    EVENT = "Event"
    INTELLIGENCE_REPORT = "IntelligenceReport"
    EVIDENCE = "Evidence"
    SOURCE_RECORD = "SourceRecord"
    
    # Supporting entities
    OFFICER = "Officer"
    UNIT = "Unit"
    COURT = "Court"
    ACT = "Act"
    SECTION = "Section"
    CRIME_HEAD = "CrimeHead"
    CRIME_SUB_HEAD = "CrimeSubHead"


class DerivationClass(str, Enum):
    """
    Explicit provenance classification for graph links and assertions.
    FACT: Directly present in an imported source record.
    DERIVED: Computed from source-backed facts by a named deterministic algorithm/rule.
    HYPOTHESIS: Human-review lead / investigative hypothesis.
    """
    FACT = "FACT"
    DERIVED = "DERIVED"
    HYPOTHESIS = "HYPOTHESIS"


class GraphRelationshipType(str, Enum):
    # Case participations
    INVOLVED_IN = "INVOLVED_IN"
    ACCUSED_IN = "ACCUSED_IN"
    VICTIM_IN = "VICTIM_IN"
    COMPLAINANT_IN = "COMPLAINANT_IN"
    WITNESS_IN = "WITNESS_IN"

    # Direct entity associations
    USED_PHONE = "USED_PHONE"
    USED_VEHICLE = "USED_VEHICLE"
    SEEN_AT = "SEEN_AT"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    CONNECTED_TO = "CONNECTED_TO"
    OWNS_ACCOUNT = "OWNS_ACCOUNT"
    TRANSFERRED_TO = "TRANSFERRED_TO"
    TRANSFERRED_FUNDS = "TRANSFERRED_FUNDS"
    COMMUNICATED_WITH = "COMMUNICATED_WITH"
    SHARED_PHONE = "SHARED_PHONE"
    OWNS_VEHICLE = "OWNS_VEHICLE"
    PRESENT_AT = "PRESENT_AT"
    OCCURRED_AT = "OCCURRED_AT"
    OCCURRED_IN = "OCCURRED_IN"
    MENTIONED_IN = "MENTIONED_IN"
    HAS_EVIDENCE = "HAS_EVIDENCE"
    SUPPORTED_BY = "SUPPORTED_BY"
    CHARGED_UNDER = "CHARGED_UNDER"
    INVESTIGATED_BY = "INVESTIGATED_BY"
    BELONGS_TO_UNIT = "BELONGS_TO_UNIT"
    CO_ACCUSED_WITH = "CO_ACCUSED_WITH"
    LINKED_TO = "LINKED_TO"
    CITES_SOURCE = "CITES_SOURCE"
    PARTICIPATED_IN = "PARTICIPATED_IN"


class EdgeStorageMode(str, Enum):
    STORED = "STORED"
    COMPUTED = "COMPUTED"


class ResolutionStatus(str, Enum):
    MATCHED = "MATCHED"
    PROBABLE_MATCH = "PROBABLE_MATCH"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_MATCHED = "NOT_MATCHED"


class InvestigationRole(str, Enum):
    INVESTIGATOR = "INVESTIGATOR"
    ANALYST = "ANALYST"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"
    # Legacy role mappings for backwards compatibility during migration
    IO = "IO"
    SHO = "SHO"
    SP = "SP"