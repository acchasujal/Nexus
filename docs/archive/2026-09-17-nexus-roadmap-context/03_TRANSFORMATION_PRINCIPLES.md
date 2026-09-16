# Transformation Principles

## 1. Extend before replacing

Reuse existing:
- GraphStore
- Neo4j projection
- PostgreSQL
- entity resolution
- provenance
- audit
- RBAC
- Copilot refusal gate
- frontend design system
- investigator workspace
- benchmark harness

Prefer additive/vertical slices over rewrites.

## 2. Turn existing outputs into first-class objects

Examples:
- timeline events → temporal snapshots
- hotspot/bridge outputs → Network Pulse events
- candidate matches → reviewable identity decisions
- similarity results → Case DNA records
- evidence citations → support/conflict/missing evidence model

## 3. Preserve deterministic-before-generative

Graph facts, entity resolution, change detection, evidence state and forecast qualification must be deterministic or explicitly modelled.

LLM use remains downstream:
- explain
- summarize
- navigate
- answer evidence-grounded questions

Never let an LLM silently create authoritative relationships.

## 4. Build uncertainty into the data model

Every proactive signal must be able to represent:
- supporting evidence
- contradictory evidence
- missing evidence
- stale evidence
- uncertainty
- abstention

## 5. Separate current prototype from target vision

Use explicit implementation status:
- CURRENT
- EXTENSION
- NEW PROTOTYPE
- TARGET / FUTURE

Use the same distinction in docs, UI, APIs and PPT claims.

## 6. Optimize for investigator decision value

Every feature must answer:
- What decision improves?
- What evidence supports it?
- How are false positives/negatives measured?
- Who can act?
- How is it independently verified?
- What happens if evidence is missing/conflicting?

## 7. No feature inflation

Do not add features only because a competitor has them.
Do not add new graph algorithms unless they change an investigator decision.
