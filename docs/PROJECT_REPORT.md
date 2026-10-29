# NEXUS — Project Report

**Proactive, evidence-grounded criminal network change intelligence**

Smart India Hackathon 2026 · Problem Statement 26189 · Blockchain & Cybersecurity

Documentation review: 2026-10-28

NEXUS is an independent synthetic-data evaluation prototype developed for the MHA/NCRB problem context. This report describes the repository implementation and its limits; it does not claim official deployment, operational accreditation or legal certification.

## Abstract

Investigative records often arrive separately: an FIR identifies an incident, call records describe communications, and financial records describe transfers. A static link chart can reveal connections but gives limited help in deciding what changed, which evidence supports a finding, or what to verify next.

NEXUS combines deterministic graph analysis with evidence-linked investigation workflows. It connects synthetic records, compares network snapshots, surfaces review pulses, identifies evidence gaps and supports accountable follow-up. Grounded assistance explains tool results with citations. Human investigators retain decision authority, and insufficient evidence is an explicit outcome.

## Problem and objectives

The prototype addresses four practical needs:

1. Connect fragmented records while preserving source provenance.
2. Explain meaningful network changes instead of presenting undifferentiated alerts.
3. Separate observed facts, derived relationships and hypotheses.
4. Make verification, routing and integrity review part of the investigation workflow.

It does not determine guilt, predict individual criminality or autonomously authorize enforcement.

## Implemented system

| Subsystem | Implementation | Lifecycle |
| --- | --- | --- |
| Record and graph foundation | Synthetic FIR, communication and financial artifacts; indexed graph and provenance | CURRENT |
| Investigation workspace | Worklist, case detail, network exploration, paths, communities and bridge analysis | CURRENT |
| Entity resolution | Deterministic name/identifier comparison with reviewable candidates | CURRENT |
| Change intelligence | Before/after snapshots, deterministic differences and review pulses | EXTENSION |
| Evidence workflow | Assessments, missing evidence, verification tasks and intelligence routing | EXTENSION |
| Analytical radars | Identity drift, adaptation, digital identifier corroboration and Case DNA | NEW PROTOTYPE |
| Grounded copilot | Deterministic tools, source citations and refusal checks | CURRENT |
| Integrity and dossiers | Digests, audit-chain verification, local Merkle anchoring and PDF generation | CURRENT |
| Investigator entry | Server-confirmed login, persistent session and independently loading workspace panels | CURRENT |

Lifecycle labels describe implemented scope. They do not imply every screen is defect-free; the [status register](../progress.md) records known test failures.

## Architecture and data flow

The React 19/TypeScript frontend calls FastAPI application services. Shared Python and TypeScript contracts define API/domain shapes. PostgreSQL provides application persistence when configured. An in-memory graph supports deterministic analysis, and Neo4j provides a complementary graph projection with explicit readiness gates. Optional object storage and language-model providers are configuration-dependent.

```text
Synthetic records → Provenance and graph → Deterministic analysis
                 → Network changes → Evidence review → Verification → Audited action
```

The application distinguishes HTTP liveness, core readiness and graph readiness. A failed graph dependency must not be represented as an empty, successfully queried graph. See [architecture](ARCHITECTURE.md), [data model](DATA_MODEL.md) and [API](API.md).

## Synthetic dataset and reproducibility

The canonical base generator produces 445 graph nodes and 486 edges. Enriched runtime fixtures and historical benchmark workloads have different scopes and counts; they must not be presented as identical datasets.

The demo worklist snapshot is generated from the repository's canonical synthetic artifact rather than manually copied dashboard numbers. Its version and snapshot status remain visible until live reads reconcile. Planted identity ground truth enables deterministic regression checks.

Sources: [synthetic generator](../synthetic_data/nexus_generator.py), [development and fixture procedures](DEVELOPMENT.md), [benchmark provenance](BENCHMARKS.md).

## Demonstration experience

Four predefined profiles represent IO, SHO, SP and administrator perspectives. Role selection and credential entry both require server authentication, then open the existing Intelligence Center (`/intelligence`) with the full application shell. Panel queries do not block navigation rendering. Labelled synthetic snapshots and bounded read recovery remain in the existing data layer.

The retired `/demo` URL is a compatibility redirect through the same protected routes. The current server login/verifier remains a demo identity implementation.

The hosted evaluation uses Vercel and Render, with PostgreSQL and Neo4j dependencies. Cold starts and degraded graph connectivity remain operational considerations. See the [judge walkthrough](DEMO.md) and [deployment guide](DEPLOYMENT.md).

## Evidence, ethics and accountability

- All development and demonstration records are synthetic.
- Relationships retain provenance; an association is not a finding of guilt.
- Algorithms and source records support explanations; generated prose is not evidence.
- Early-warning cards are constrained prototype rule outputs. They are not calibrated probabilities.
- Insufficient or contradictory evidence must allow abstention.
- Hashes and Merkle proofs demonstrate integrity against recorded artifacts, not the truth of their contents.
- No raw sensitive records belong on a public ledger.
- Dossiers are evidence-oriented exports, not a guarantee of court admissibility.

The current backend is unsuitable for real citizen data without production identity and security work. [Security](SECURITY.md) describes implemented safeguards and missing guarantees.

## Validation

Local full-suite verification on 2026-10-28 recorded **921 backend tests passed and 2 skipped**. The frontend recorded **161 passed and 47 failed**; these reproduce the pre-existing baseline failure count and remain open. Ruff, the production frontend build and seeded ground-truth evaluation passed.

The seeded evaluation found two true-positive identity matches, no false positives and no false negatives. Its 100% precision/recall applies only to this planted fixture.

Historical in-memory benchmarks include 85.04 ms p95 snapshot diff on 10,000 nodes and 33.49 ms p95 warm evidence-to-signal execution. These are artifact-scoped experiments, not deployed latency guarantees. See [benchmarks](BENCHMARKS.md) and [latest verification](../progress.md).

## Limitations and next steps

**TARGET / FUTURE:**

- Production officer identity, revocation and deployment security validation.
- Real-world evaluation under approved governance, beyond synthetic fixtures.
- Calibrated operational forecasting with appropriate abstention and external validation.
- Verified integrations with government systems; no such integration is claimed here.
- Distributed/consortium trust infrastructure beyond local integrity demonstrations.

**Current engineering follow-up:** resolve the existing frontend test failures, verify the full hosted fresh-browser journey, correct deployed Neo4j connectivity and validate the frontend container build context. Do not confuse a hosted static page with a healthy data service.

## Repository and supporting material

Start with the [README](../README.md), [developer guide](DEVELOPMENT.md), [pipeline](INTELLIGENCE_PIPELINE.md) and [accepted decisions](../decisions.md). The former root “Project Report” was a planning document and is preserved in the [archive](archive/2026-10-28-product-hardening-plan.md), not treated as an implementation specification.
