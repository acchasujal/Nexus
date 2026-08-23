# Case Clock — KSP Datathon 2026 (PS1: Intelligent Conversational AI for KSP Crime Database)

## Project Overview

Case Clock is an investigation-intelligence platform built on a **single unified investigation graph**. Every mandated PS1 capability (conversational query, criminal network analysis, crime pattern discovery, socio-demographic insight, offender profiling, decision support, explainability) is implemented as a **query or traversal over one graph**, not as separate parallel subsystems. The flagship differentiator is dependency-aware statutory deadline tracking (BNSS 60/90-day chargesheet clocks), with a scoped natural-language interface as the PS1-compliant conversational layer sitting on top.

See `PROJECT_CONTEXT.md` for the full why. This file is only the map.

## Problem Statement (source: organizer brief, verified against explainer video + webinar)

KSP's State Crime Records Bureau manages crime data from 1,100+ stations. Existing systems (CCTNS-class) are static, siloed, and non-conversational. PS1 asks for a conversational AI over this data that surfaces network links, patterns, socio-demographic insight, behavioral profiling, and predictive/preventive intelligence — while remaining explainable, auditable, and role-gated.

## High-Level Architecture

```
Organizer schema (CaseMaster, Accused, Victim, ChargesheetDetails, Act, Section, CrimeHead/SubHead,
Employee, Unit, Court, District, State)
        │
        ▼
Unified Investigation Graph (nodes + typed edges — see ARCHITECTURE.md)
        │
        ├── Legal Clock Engine (deterministic, rule-based)
        ├── Dependency Tracker
        ├── Escalation Rule Engine (deterministic)
        ├── Aggregation Layer (pattern / trend / socio-demographic views)
        ├── Similarity Function (structured feature match — not embeddings)
        └── Conversational Layer (grounded NL → query → refusal gate → path-annotated answer)
        │
        ▼
UI: Case Detail / Risk Worklist / Network / Pattern & Trends / District Rollup / Copilot
```

Full detail: `ARCHITECTURE.md`. Conceptual only — no schema or API specifics are asserted here because none have been implemented yet (see `TASK.md` for what's actually built vs. planned).

## Tech Stack

- Frontend: React
- Backend: FastAPI (Python)
- AI/ML: LLM-based NL layer with deterministic pre/post-processing gates
- Deployment: Zoho Catalyst (**mandatory per organizer rules** — verify Catalyst's actual data-store capabilities before finalizing graph storage approach; this is an open item, see `TASK.md`)
- Team constraint: software-only, no hardware/IoT

## Repository Structure (target — create as work begins)

```
/backend
  /graph            — node/edge models, ingestion from organizer schema
  /clock_engine      — deterministic BNSS clock rules
  /dependency        — dependency tracker + escalation rules
  /nl_layer          — grounded query generation + refusal gate
  /api
/frontend
  /case_detail
  /worklist
  /network
  /pattern_rollup
  /copilot
/docs                — this documentation set
/synthetic_data      — generator + fixtures (must model repeat entities deliberately — see PROJECT_CONTEXT.md)
```

## Setup

See `README.md` at the repository root for setup instructions. The repository scaffold exists (backend + frontend directories created, CI configured).

## Development Workflow

Governed by `EXECUTION_RULES.md`. Any AI agent or engineer picking up this repo should read, in order: `PROJECT_CONTEXT.md` → `EXECUTION_RULES.md` → `ARCHITECTURE.md` → `TASK.md`, before writing any code.

## Documentation Index

| File | Purpose |
|---|---|
| `README.md` | This file — entry point |
| `PROJECT_CONTEXT.md` | Why the project exists, users, philosophy, non-goals |
| `EXECUTION_RULES.md` | How any AI agent must reason and behave while working on this repo |
| `FEATURE_REGISTRY.md` | Every planned feature — what, not how |
| `ARCHITECTURE.md` | Conceptual system architecture |
| `DECISION_LOG.md` | Every major decision made and why, to prevent re-litigating settled choices |
| `TASK.md` | Live execution plan — what's built, what's next, what's blocked |
| `IMPLEMENTATION_PLAN.md` | Phased build sequence and parallel work stream plan |
| `PARALLELIZATION_READINESS.md` | Current parallel development readiness assessment |
| `spikes/quickml.md` | QuickML capability spike results and architectural decision (D14) |
| `graph-intelligence/DATA_MODEL.md` | Detailed graph entity catalog with planned fields |
| `graph-intelligence/EDGE_MODEL.md` | Stored and derived edge definitions |
| `graph-intelligence/DATASTORE_SPIKE.md` | Catalyst Data Store spike validation plan |
| `graph-intelligence/MIGRATION_PLAN.md` | Adjacency-list mapping strategy for Catalyst |
| `graph-intelligence/SYNTHETIC_DATA_SPEC.md` | Synthetic dataset targets and repeat-entity strategy |

## Engineering Ownership

Four lanes, not four fixed roles-by-name: Backend Core, Frontend, Graph Intelligence, and AI + Architecture + Integration (owned by Sujal). See `EXECUTION_RULES.md` for daily workflow, branch naming, and PR process — this README doesn't duplicate it.

## Contribution Workflow

Single-team hackathon project (4 members: Sujal, Shriraj, Vikram, Dhiren). No external contributors expected before submission. Any change to architecture must be reflected in `DECISION_LOG.md` in the same session it's made — do not defer.
