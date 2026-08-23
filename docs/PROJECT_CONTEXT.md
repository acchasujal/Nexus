# PROJECT_CONTEXT.md

This document explains **why** Case Clock exists. Read this before reading any architecture or code. It describes intent, not implementation.

## The Real-World Problem

Under BNSS (Bharatiya Nagarik Suraksha Sanhita, effective July 2024), a chargesheet must be filed within 60 or 90 days of arrest (depending on offence severity), or the accused becomes eligible for statutory default bail — a hard, legally triggered outcome, not a soft KPI. [Fact, corroborated across multiple independent sources; exact section number for the default-bail trigger — 176(2) vs 187(2) BNSS — has been inconsistently cited across secondary sources in prior research and **must be verified against the bare statute text before being asserted in any user-facing material.**]

Today, this deadline is tracked in an investigating officer's (IO's) memory, a paper case diary, or station-level registers. There is no cross-station, supervisor-visible view of which cases are close to statutory failure. The failure is discovered *after* it happens (a magistrate grants default bail), not before. [Strong Inference, grounded in documented CCTNS interoperability gaps and general reporting on FSL backlogs — not Karnataka-specific verified data.]

Separately, KSP's official PS1 brief (Datathon 2026) asks for a conversational AI layer over the SCRB crime database supporting: natural-language query (English + Kannada, voice-enabled), criminal network analysis, crime pattern discovery, socio-demographic insight, behavioral/criminological profiling, investigator decision support, financial-transaction link analysis, crime forecasting/early warning, explainable AI with audit trails, and role-based access. [Fact — verbatim from organizer materials.]

## Why This Project Exists (the actual thesis)

Most likely competitor response to PS1 is a generic NL2SQL chatbot over the crime database. This is easy to imitate and hard to differentiate, because "add a confidence score so it doesn't hallucinate" is the obvious response any AI-literate team will independently reach.

Case Clock's bet: build one thing genuinely hard to research and copy — statutory-deadline-aware investigation tracking, grounded in real BNSS procedural detail — and make every organizer-mandated capability (network, pattern, profiling, etc.) emerge as a **query over the same underlying graph** that powers the deadline tracker, rather than as a bolted-on separate module. This keeps engineering surface area low (a documented, recurring failure mode for this team is overbuilt, disconnected pipelines under deadline pressure — see `DECISION_LOG.md`) while satisfying the brief's full capability list.

## Target Users (per organizer's stated hierarchy)

- **Investigating Officer (IO)** — primary daily user. Manages 15–40 open cases. Needs to know what's blocking a case and what to do next, not a generic dashboard.
- **SHO** — station-level oversight, reviews before filing.
- **SP / DCP** — district/state rollup, needs exception-only visibility, answers upward to Home Department.
- **Public Prosecutor** — chargesheet-readiness handoff (explicitly out of MVP scope, see Non-Goals).
- **Crime Analyst / Policymaker** — named by organizer as a user of pattern/socio-demographic insight views.

Organizer-confirmed rank hierarchy to model: DGP → IGP → DIG → SP, over Chief Office → Subdivision → Police Station units. [Fact.]

## Product Philosophy

1. **Deterministic before generative.** Never let an LLM decide something a rule engine can decide correctly and auditably (clock calculation, escalation triggers). This is the team's most consistent cross-project differentiator (see `DECISION_LOG.md`) and also the direct answer to explainability requirements.
2. **Refuse rather than guess.** The conversational layer must decline to answer when confidence is low, and this refusal behavior is a first-class, tested feature — not an afterthought. **As of this writing, no test set has been run against the refusal gate.** This is the single most-flagged unresolved risk across prior planning sessions.
3. **One graph, many lenses.** Network analysis, pattern discovery, socio-demographic insight, and profiling are traversals/aggregations over the same nodes used for clock tracking — never a separate data store.
4. **Honest scope labeling.** Where the organizer's real ER schema doesn't support a requested capability (financial-transaction data does not exist in the provided schema; deep sociological correlation requires fields — income, education, migration — not present in the schema), the product must say so explicitly rather than fabricate or imply coverage. Overclaiming has been a repeated, documented failure mode in this team's prior hackathon submissions (HackerRank Orchestrate, MuleShield, Infosys audit — see `DECISION_LOG.md`) and is the single highest-consequence risk to avoid repeating.

## Core Workflow

FIR registration → investigation (evidence/dependency gathering: FSL, CDR, witness statements, supervisory review) → chargesheet filing → post-filing clocks (document supply, further investigation). Case Clock instruments the evidence-gathering → filing window with named, specific dependency tracking rather than a single opaque risk score (a design correction made after finding that "evidence-completeness %" as a single score does not reflect how IOs actually reason about a case — see `DECISION_LOG.md`).

## Business Goals (hackathon-specific)

- Primary: pass initial shortlisting (500+ submissions → ~20 finalists) and place in the Grand Finale.
- Secondary, stated honestly: produce something a real KSP procurement conversation could plausibly continue past the hackathon — this requires the honest-scope-labeling principle above, since overclaimed AI capability is the single fastest way to lose institutional trust with a government buyer.

## Non-Goals (explicit, for MVP)

- Not a CCTNS replacement — sits above it as a workflow-intelligence layer.
- Not a full case-management system.
- Not a predictive-policing / crime-forecasting product in the deep-ML sense — any "forecasting" feature in MVP is a rule-based threshold alert, explicitly labeled as such, due to well-documented feedback-loop bias risks in predictive policing systems generally. [Medium-High confidence on the general critique; not Karnataka-specific.]
- Not a cross-case suspect-linkage / behavioral-risk-scoring tool used for guilt inference — any profiling output must be framed strictly as "investigative lead prioritization based on this person's own prior case involvement," never demographic-attribute-based risk of reoffending.
- No mobile app, offline mode, full ABAC, or prosecutor workflow in MVP — roadmap only.
- No real financial-transaction data — the organizer-provided schema has no such entities. Any financial-link feature is a labeled synthetic-data demo extension, not a claim of real capability.

## Engineering Organization

The team is organized around four engineering lanes (Backend Core, Frontend, Graph Intelligence, AI + Architecture + Integration) rather than by individual developer. This is a deliberate choice, not a headcount formality: it keeps ownership tied to what a module *does* rather than who happens to be free, and it puts the AI layer and cross-team integration under a single owner (Sujal) specifically because those two are the most tightly coupled parts of the system and the most likely place for architecture drift to enter unnoticed. Full reasoning and alternatives considered: `DECISION_LOG.md` D12. Operational detail (branching, PRs, daily workflow): `EXECUTION_RULES.md` (TEAM_PLAYBOOK was merged into EXECUTION_RULES — see `TASK.md` bootstrap note).

## Constraints

- Software only, no hardware/IoT.
- Must deploy on Zoho Catalyst (mandatory for eligibility).
- Must use synthetic data — organizer will not provide real/sensitive records, only schema + master tables.
- Team of 4, hackathon timeline (prototype submission per organizer timeline; verify exact current deadline against the live dashboard, as dates have shifted during implementation).
- Organizer target test scale: ~1–2 lakh (100,000–200,000) synthetic records; jury explicitly does not want "quick and dirty, throwaway" code.

## Key Assumptions (flagged, not asserted as fact)

- Entity resolution across cases (recognizing the same person across two FIRs with slightly different spelling) is **not solved** by this project. The organizer schema provides no unique cross-case person key. Network/similarity/profiling features depend on this working at least for exact/near-exact matches in the synthetic dataset — this is the single largest technical honesty risk in the whole product.
- Zoho Catalyst's native support for graph-style traversal queries is **unverified** — if it lacks a native graph engine, "the graph" is implemented as a relational adjacency/edge-list table with recursive queries, which is functionally equivalent but must not be described as "Neo4j" or similar unless actually integrated.
- KSP may already have an internal, non-public mechanism for deadline tracking. No evidence either way. If true, this weakens the core premise. Should be asked directly of any KSP-affiliated mentor before final submission.

## Glossary

- **BNSS** — Bharatiya Nagarik Suraksha Sanhita, the 2024 procedural code replacing CrPC.
- **Default bail** — statutory release of an accused when a chargesheet is not filed within the legal window.
- **Dependency** — a named, specific outstanding evidentiary item (FSL report, CDR analysis, Section 183 statement, supervisory sign-off) blocking chargesheet filing.
- **Clock instance** — a specific statutory deadline instance attached to a case (investigation/chargesheet clock, document-supply clock, further-investigation clock — multiple can run concurrently per case).
- **Refusal gate** — the deterministic check that causes the conversational layer to decline answering rather than guess, when confidence in a grounded answer is low.
- **SCRB** — State Crime Records Bureau, the data owner referenced in the organizer brief.

## Success Metrics

- Hackathon: shortlisting, finals placement, judge feedback referencing the deadline/dependency mechanism unprompted.
- Product (if piloted, aspirational): measurable reduction in cases crossing a statutory clock without a filed chargesheet — a concrete, non-gameable metric distinct from a generic "engagement" metric.

## Future Vision

A district/state-scale investigation command layer above CCTNS: prosecutor handoff workflows, real Kannada NLU, real entity resolution, mobile IO app with offline sync, full audit-grade RBAC. Explicitly multi-year and institutionally contingent — not a near-term commitment, and should never be represented as MVP scope.
