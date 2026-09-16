# NEXUS — Current State Baseline

## Product

Current positioning:
Evidence-grounded criminal network intelligence / investigative decision-support system for SIH 2026 PS 26189.

The current system is already a mature prototype, not a greenfield project.

## Current quality baseline

- Backend: 708/708 tests passing
- Frontend: 114/114 tests passing
- Ruff: clean
- TypeScript/build: clean
- Seeded entity-resolution benchmark: 100% precision / recall
- Render backend + Vercel frontend operational

Do not destroy these quality gates during transformation.

## Current architecture

### Presentation
- React 19 + Vite
- Investigation workspace
- React Flow graph explorer
- Grounded Copilot
- Timeline
- Entity Fusion Workbench

### API/security
- FastAPI
- RBAC/security verifier
- refusal gate
- immutable audit service

### Intelligence
- deterministic multi-attribute entity resolution
- Indian phonetic normalization
- Louvain
- betweenness / bridge discovery
- BFS/pathfinding
- cross-case bridge detection
- temporal/pattern queries

### Storage
- in-memory double-adjacency `GraphStore`
- Neo4j durable projection
- PostgreSQL for application state, users/RBAC/audit

### Trust
- edge-level evidence provenance
- SHA-256 integrity verification
- evidence drawer / citations
- audit trail

### AI
- case-grounded Copilot
- natural-language summarization of verified facts
- refusal gate against guilt/dangerousness/recidivism predictions

### Data
Current development/demo data is deterministic synthetic data with planted ground truth.

## Current graph

12 documented entity types:
Person, Case, Phone, Vehicle, Location, Organization, Device, Account, Transaction, Event, IntelligenceReport, Evidence.

Existing relationship model includes accused-in, victim-in, witness-in, co-accused, communicated-with, associated-with, transferred-money-to, owns-account, uses-phone, drives-vehicle, located-at, mentioned-in, resolved-to, has-evidence.

## Current pipeline

1. Multi-source ingestion
2. Normalization / NER
3. Entity resolution
4. Graph construction
5. Modularity / centrality
6. Temporal sequencing / patterns
7. Provenance + Copilot

## Current product limitations relevant to transformation

The current architecture is still primarily reactive. Temporal functionality exists, but network change is not yet a first-class intelligence object.

Not yet first-class:
- network snapshot/diff
- Network Pulse
- constrained early-warning engine
- abstention as a forecast outcome
- evidence sufficiency / support-conflict-missing reasoning
- next-best verification engine
- structured cross-branch Intelligence Pulse
- identity drift / network adaptation radar
- controlled SOCMINT graph fusion
- closed-loop graph update from investigator decisions
- formal evaluation protocol for proactive capabilities
