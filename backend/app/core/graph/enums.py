"""Enumerations for the unified investigation graph."""

from __future__ import annotations

from enum import Enum


class GraphEntityType(str, Enum):
    CASE = "Case"
    PERSON = "Person"
    OFFICER = "Officer"
    UNIT = "Unit"
    COURT = "Court"
    LOCATION = "Location"
    ACT = "Act"
    SECTION = "Section"
    CRIME_HEAD = "CrimeHead"
    CRIME_SUB_HEAD = "CrimeSubHead"
    EVIDENCE = "Evidence"
    DEPENDENCY = "Dependency"
    CLOCK_INSTANCE = "ClockInstance"
    ESCALATION_EVENT = "EscalationEvent"
    CONVERSATION_LOG = "ConversationLog"


class GraphRelationshipType(str, Enum):
    ACCUSED_IN = "ACCUSED_IN"
    VICTIM_IN = "VICTIM_IN"
    COMPLAINANT_IN = "COMPLAINANT_IN"
    WITNESS_IN = "WITNESS_IN"
    CASE_HAS_DEPENDENCY = "CASE_HAS_DEPENDENCY"
    CASE_HAS_CLOCK = "CASE_HAS_CLOCK"
    CASE_HAS_EVIDENCE = "CASE_HAS_EVIDENCE"
    CASE_HAS_COURT = "CASE_HAS_COURT"
    CASE_HAS_CRIME_HEAD = "CASE_HAS_CRIME_HEAD"
    CASE_HAS_CRIME_SUB_HEAD = "CASE_HAS_CRIME_SUB_HEAD"
    CASE_HAS_ESCALATION_EVENT = "CASE_HAS_ESCALATION_EVENT"
    CASE_HAS_CONVERSATION_LOG = "CASE_HAS_CONVERSATION_LOG"
    INVESTIGATED_BY = "INVESTIGATED_BY"
    CHARGED_UNDER = "CHARGED_UNDER"
    OCCURRED_IN = "OCCURRED_IN"
    BELONGS_TO_UNIT = "BELONGS_TO_UNIT"
    BELONGS_TO_ACT = "BELONGS_TO_ACT"
    CO_ACCUSED_WITH = "CO_ACCUSED_WITH"
    LINKED_TO = "LINKED_TO"


class EdgeStorageMode(str, Enum):
    STORED = "Stored"
    DERIVED_NOT_STORED = "Derived - Not Stored"