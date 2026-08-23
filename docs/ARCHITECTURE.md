# ARCHITECTURE.md

Conceptual architecture only. No specific database schemas, API contracts, or prompt formats are asserted here — those depend on implementation choices not yet made, and inventing them prematurely violates `EXECUTION_RULES.md`'s anti-hallucination rules. This document describes how the system is organized; `TASK.md` tracks what's actually built.

## Architecture Principle

**One unified investigation graph. Every mandated capability is a query or traversal over it — not a parallel system.** This is the single organizing decision for the whole project (see `DECISION_LOG.md` for how this was arrived at across several rounds of revision).

## System Modules and Responsibilities

### 1. Graph Layer

Owns the node/edge model representing cases, people, offences, locations, officers, courts, dependencies, and clock instances. Ingests from the organizer-provided schema (CaseMaster, Accused, Victim, ComplainantDetails, ArrestSurrender, ChargesheetDetails, Act, Section, CrimeHead, CrimeSubHead, Employee, Unit, Court, District, State) plus two extensions the organizer schema does not natively support: `Dependency`/`ClockInstance` (for Case Clock) and, in Finals scope only, synthetic `FinancialAccount`/`Transaction` nodes explicitly labeled as demo extensions.

**Conceptual node types:** Case, Person (role-typed via edges: accused/victim/complainant/witness), Section, Act, CrimeHead/SubHead, Location, Officer, Unit, Court, Dependency, ClockInstance, EscalationEvent, ConversationLog. Finals-only: FinancialAccount, Transaction.

> **Schema evolution note (D15):** The implementation (`backend/app/core/graph/entities.py`, `graph_schema.py` v1.1) also includes `Evidence` as a first-class node with a `CASE_HAS_EVIDENCE` stored edge. This addition was made during Lane 3 graph foundation work and is logged in `DECISION_LOG.md` D15. The implementation is authoritative over this conceptual list — always check the code for the current node roster.


**Conceptual edge types:** role edges (ACCUSED_IN, VICTIM_IN, COMPLAINANT_IN, WITNESS_IN), CHARGED_UNDER (Case→Section), BELONGS_TO_ACT (Section→Act), OCCURRED_IN (Case→Location), INVESTIGATED_BY (Case→Officer), BELONGS_TO_UNIT (Officer→Unit), CASE_HAS_DEPENDENCY / CASE_HAS_CLOCK (Case→Dependency/ClockInstance), and two **derived, not stored** edges: CO_ACCUSED_WITH (computed from shared Case membership) and, only if a real shared identifier exists in the schema, LINKED_TO — this must never be fabricated if no such field exists.

**Open question, unresolved:** Whether the storage layer is a genuine graph database or a relational adjacency/edge-list table depends on what Zoho Catalyst actually supports. This must be verified before the architecture slide of the pitch deck asserts a specific technology (e.g., do not claim "Neo4j" unless actually integrated).

### 2. Legal Clock Engine

Deterministic, rule-based. Maps offence category to applicable statutory clock(s). Owns the offence-category → clock-type mapping table, which must be built and verified against actual BNSS text, not assumed from secondary sources.

### 3. Dependency Tracker

Owns named, per-case blocker records (FSL, CDR, statement, sign-off) and their staleness computation. Feeds the Escalation Rule Engine.

### 4. Escalation Rule Engine

Deterministic trigger logic: days-remaining + unresolved dependency + staleness threshold → auto-generate escalation, route to the correct supervisor by rank (using the Officer/Unit hierarchy already in the graph). Never LLM-driven — an escalation engine that's ever wrong in a way nobody can explain is a legal-context liability, not just a UX flaw.

### 5. Aggregation Layer

Computes pattern/trend and socio-demographic views as grouped queries over Case/Person nodes — not a separate analytics warehouse. Also computes the rule-based trend-alert (threshold-crossing) used for the "early warning" requirement.

### 6. Similarity Function

Structured feature match (shared section combination, location, time window) over Case nodes — deliberately not an embedding-based model, so results remain traceable to specific shared attributes (explainability requirement).

### 7. Conversational Layer (NL / Copilot)

Grounded natural-language input → deterministic verification/grounding gate → query execution against the graph → either (a) a path-annotated answer showing which nodes/edges produced it, or (b) an explicit refusal if confidence is low. This is the PS1-mandated conversational interface. Kannada and voice are thin wrappers around this same layer, not separate reasoning paths.

### 8. Access & Audit Layer

Three-role gating (IO/SHO/SP) in MVP; append-only audit log of views, queries, escalations, and refusals.

## Frontend Responsibilities

Case Detail (the universal object every persona lands on — clock badges, dependency panel, network tab, similarity tab, copilot box), Risk-Ranked Worklist (IO), District/Pattern Rollup (SP/DCP, exception-only), Escalation Queue, Conversation history + PDF export.

## Backend Responsibilities

Graph ingestion and query execution, clock/escalation rule evaluation, aggregation computation, NL grounding and refusal-gate logic, audit logging.

## AI Responsibilities (and non-responsibilities)

The LLM component is responsible **only** for: natural-language understanding of the investigator's query intent, and translating that intent into a structured query against the graph, subject to the deterministic verification gate. The LLM is explicitly **not** responsible for: clock calculation, escalation decisions, or generating free-text claims about a specific person's risk/guilt. This split is the architecture's core explainability and safety mechanism.

## Authentication Strategy

Role-based (IO/SHO/SP) for MVP. Full ABAC is roadmap. Specific auth provider/mechanism not yet chosen — depends on Catalyst's available services (verify before commit).

## Storage Strategy

Depends on Catalyst's actual data-store offerings (unverified as of this writing — see Open Question above). Graph semantics can be implemented over a relational store via adjacency tables if no native graph engine is available; this is a legitimate, honest implementation choice and should be described as such, not disguised.

## Deployment Philosophy

Mandatory Catalyst deployment per organizer eligibility rules. Deploy early and iterate — do not leave first deployment until submission week, given this team's documented pattern of late-stage integration failures.

## Scalability Philosophy

Target: correctness and demonstrated (not just claimed) performance at 1–2 lakh synthetic records, per organizer's explicit guidance. A measured latency number beats an unmeasured architecture claim.

## Security Philosophy

Sensitive-data handling deferred to synthetic data only, per organizer's DPDP-compliance data policy — no real PII is ever introduced. Audit logging covers reads and refusals, not just writes.

## Extension Points

- Graph schema can accept new node/edge types (e.g., real financial-intelligence integration) without redesigning the clock/escalation engines, since those consume Case/ClockInstance/Dependency only.
- The Conversational Layer's query-grounding logic should be extensible to new question types without retraining — new capabilities should mean new query templates, not new models.

## Architecture Principles (restated)

1. Deterministic before generative.
2. One graph, many lenses — never a second parallel data store for a "new" capability.
3. Honest labeling of shallow/synthetic/stub components — see `FEATURE_REGISTRY.md` for which features carry this label.
4. Explainability is structural (a traceable path), not asserted (a claim in a slide).

## Trade-offs

- Choosing structured similarity over embedding-based similarity sacrifices some recall for full explainability — an intentional trade given the judging panel's stated emphasis on explainable AI and audit trails.
- Choosing a shallow 3-role RBAC over full ABAC sacrifices realism for MVP buildability within a 4-person hackathon timeline.

## Rejected Approaches (see `DECISION_LOG.md` for full reasoning)

- Single opaque composite "risk score" for dependency tracking — rejected in favor of named, specific dependencies, because a composite score doesn't survive a judge asking "risk of what, exactly."
- Treating PS1 vs. PS2 as a binary choice — rejected in favor of anchoring on PS1 with the deadline-clock mechanism as the primary differentiator.
- Cross-case pattern-linkage / suspect-network "AI copilot" as a headline feature — rejected due to legal exposure from false linkage; kept only as a narrow, structurally-derived (not LLM-inferred) co-accused traversal.

## Common Pitfalls (for future AI agents to actively avoid)

- Building network/pattern/profiling as separate services "for speed" — this defeats the entire architectural thesis and reintroduces the overbuilt-disconnected-pipeline failure mode this design specifically exists to prevent.
- Fabricating a `LINKED_TO` edge from data that doesn't actually support it.
- Letting the LLM generate free text about a specific person's risk or guilt.

## Future Evolution

Real entity resolution service, real Kannada NLU, prosecutor workflow, mobile/offline, full ABAC, real financial-intelligence integration contingent on actual KSP data-sharing agreements — all explicitly roadmap, not near-term commitments.

---

## ER Diagram Notes (Merged from ER_DIAGRAM_NOTES.md)

### Overview

Summary of the Karnataka Police FIR database schema.

### Central Entity

- CaseMaster

### Connected Entities

- Victim
- Accused
- ComplainantDetails
- ArrestSurrender
- ChargesheetDetails
- Act
- Section
- CrimeHead
- CrimeSubHead
- Employee
- Unit
- Court
- District
- State

### Key Insights

- CaseMaster is the hub.
- One FIR can have many victims, accused, complainants and arrests.
- Existing schema supports conversational AI, graph analysis, analytics and profiling.
- Investigation workflow and deadline management are not present and can be added as an extension.
