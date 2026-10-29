# Architectural decisions

Current accepted decisions, consolidated on **2026-10-28**. The [original decision history](docs/archive/2026-10-28-decision-history.md) remains available with its original identifiers and chronology. This summary does not assign new meanings to historical decision IDs.

## Deterministic analysis with grounded assistance — CURRENT

Graph traversal, resolution, clustering and snapshot comparison use deterministic services. Language models may explain tool results and cite sources; they do not establish identity, invent relationships or decide guilt. Sparse or contradictory evidence must support abstention.

Sources: [architecture](docs/ARCHITECTURE.md), [pipeline](docs/INTELLIGENCE_PIPELINE.md), [security](docs/SECURITY.md).

## Synthetic records and provenance — CURRENT

Development, benchmarks and demonstrations use synthetic records. Relationship provenance and integrity artifacts are retained. Hash verification establishes consistency with recorded content; it is not a claim of factual truth or legal admissibility.

Sources: [generator](synthetic_data/nexus_generator.py), [data model](docs/DATA_MODEL.md).

## Repository authority and graph readiness — CURRENT / EXTENSION

PostgreSQL is the application repository when configured. The in-memory graph supports deterministic computation; Neo4j is a complementary projection with explicit readiness gates. Optional graph failure must not masquerade as a successful graph response or invalidate otherwise usable core data.

Essential persistence preparation remains on the startup path. Optional imports and graph recovery are separated where safe; readiness is distinct from HTTP liveness.

Source: [deployment](docs/DEPLOYMENT.md).

## Server-confirmed investigator entry — CURRENT

Updated 2026-10-30: role selection and credentials both require server login. Successful login restores a safe internal destination or opens `/intelligence` directly. The original application shell and page/query boundaries remain intact. The standalone local demo entry was removed; `/demo` is retained only as a protected compatibility redirect. Historical instant-demo decisions are superseded.

Labelled synthetic fallback data remains in existing workspace panels. It does not create server credentials. The backend identity implementation remains demonstrational; production identity is **TARGET / FUTURE**.

Sources: [security](docs/SECURITY.md), [development](docs/DEVELOPMENT.md).

## Evidence review before operational action — EXTENSION / NEW PROTOTYPE

Network changes, evidence assessments and verification suggestions remain distinct from confirmed facts and completed actions. Prototype forecast cards are constrained rule outputs, not calibrated probabilities. Backend-dependent actions must report real server success or failure.

Source: [intelligence pipeline](docs/INTELLIGENCE_PIPELINE.md).

## Local integrity proofs, no public sensitive payloads — CURRENT

Source digests, audit chains and local Merkle proofs support integrity demonstrations. They do not imply a deployed consortium blockchain. Raw sensitive records on public chains and naive phone-hash PSI are **REJECTED**.

Source: [security](docs/SECURITY.md).

## One current documentation set — CURRENT

The README is the navigation and onboarding entry point. Canonical guides describe implementation and explicit limits. Current progress belongs in one root status register; architectural decisions belong here. Superseded plans are archived with dates, not retained as competing active specifications.

The root document previously named “NEXUS - Project Report” contained a hardening plan. It is retained as [historical planning material](docs/archive/2026-10-28-product-hardening-plan.md); the current [project report](docs/PROJECT_REPORT.md) is written for reviewers.

Generic graph-design references and an unrelated Catalyst/CaseClock release workflow are archived. Executable application files and optional Neon infrastructure configuration remain in place.
