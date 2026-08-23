# Edge Model

This document catalogs the declared relationship constants in the graph foundation. It is descriptive only.

## Stored Relationships

| Edge Name                 | Source  | Target          | Storage Mode | Description                                                |
| ------------------------- | ------- | --------------- | ------------ | ---------------------------------------------------------- |
| ACCUSED_IN                | Person  | Case            | Stored       | Person participates in a case as an accused person.        |
| VICTIM_IN                 | Person  | Case            | Stored       | Person participates in a case as a victim.                 |
| COMPLAINANT_IN            | Person  | Case            | Stored       | Person participates in a case as a complainant.            |
| WITNESS_IN                | Person  | Case            | Stored       | Person participates in a case as a witness.                |
| CASE_HAS_DEPENDENCY       | Case    | Dependency      | Stored       | Attaches a named investigation blocker to a case.          |
| CASE_HAS_CLOCK            | Case    | ClockInstance   | Stored       | Attaches a statutory deadline instance to a case.          |
| CASE_HAS_EVIDENCE         | Case    | Evidence        | Stored       | Attaches an evidence item to a case.                       |
| CASE_HAS_COURT            | Case    | Court           | Stored       | Attaches a court context to a case.                        |
| CASE_HAS_CRIME_HEAD       | Case    | CrimeHead       | Stored       | Attaches a high-level offence classification to a case.    |
| CASE_HAS_CRIME_SUB_HEAD   | Case    | CrimeSubHead    | Stored       | Attaches a detailed offence sub-classification to a case.  |
| CASE_HAS_ESCALATION_EVENT | Case    | EscalationEvent | Stored       | Attaches a recorded escalation event to a case.            |
| CASE_HAS_CONVERSATION_LOG | Case    | ConversationLog | Stored       | Attaches an audit conversation record to a case.           |
| INVESTIGATED_BY           | Case    | Officer         | Stored       | Marks the officer responsible for investigation.           |
| CHARGED_UNDER             | Case    | Section         | Stored       | Marks the section or sections applied to the case.         |
| OCCURRED_IN               | Case    | Location        | Stored       | Marks where the incident occurred.                         |
| BELONGS_TO_UNIT           | Officer | Unit            | Stored       | Marks the organizational unit to which an officer belongs. |
| BELONGS_TO_ACT            | Section | Act             | Stored       | Marks the parent legal act for a section.                  |

## Derived Relationships

| Edge Name       | Source | Target | Storage Mode         | Description                                                                                                                                                 |
| --------------- | ------ | ------ | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| CO_ACCUSED_WITH | Person | Person | Derived - Not Stored | Derived when two Person nodes share the same Case through accused participation. This must never be manually invented as a stored fact.                     |
| LINKED_TO       | Case   | Case   | Derived - Not Stored | Generic derived cross-case linkage. Use only when the underlying data supports a real shared identifier or traceable shared attribute. Do not fabricate it. |

## Storage Notes

- Stored edges are canonical graph facts.
- Derived edges are computed from stored facts and must remain clearly labeled as not stored.
- The graph should never rely on derived edges as the only source of truth for downstream workflows.
- If a downstream feature needs a derived edge repeatedly, it may later be materialized in storage, but that is a separate design decision and not part of the current foundation.

## Canonicalization Notes

- ACCUSED_IN is the canonical person-to-case role edge; the old generic person attachment edge was removed to avoid duplicate semantics.
- INVESTIGATED_BY is the canonical case-to-officer edge.
- CHARGED_UNDER is the canonical case-to-section edge.
- OCCURRED_IN is the canonical case-to-location edge.
- BELONGS_TO_UNIT is the canonical officer-to-unit edge.
- BELONGS_TO_ACT keeps legal normalization explicit by linking Section to Act instead of duplicating a case-to-act edge.
