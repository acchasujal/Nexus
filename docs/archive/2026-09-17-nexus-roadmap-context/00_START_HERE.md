# NEXUS — Roadmap Context Pack

> [!NOTE]
> **REFERENCE / TARGET CONTEXT — NON-AUTHORITATIVE AFTER CANONICALIZATION**  
> This directory contains the original background target roadmap context pack. Following the canonical documentation transformation, the authoritative single source of truth resides in root (`README.md`, `AGENTS.md`, `progress.md`, `decisions.md`) and `docs/` (`ARCHITECTURE.md`, `DATA_MODEL.md`, `API.md`, `INTELLIGENCE_PIPELINE.md`, `SECURITY.md`, `BENCHMARKS.md`, `DEMO.md`, `DEPLOYMENT.md`, `DEVELOPMENT.md`).

Purpose: this folder is the reference context pack for the target proactive, evidence-grounded intelligence platform.

## Read order

1. `01_CURRENT_STATE.md`
2. `02_TARGET_ROADMAP.md`
3. `03_TRANSFORMATION_PRINCIPLES.md`
4. `04_TARGET_ARCHITECTURE.md`
5. `05_CAPABILITY_MATRIX.md`
6. `06_DATA_MODEL_DELTA.md`
7. `07_API_AND_SERVICE_DELTA.md`
8. `08_FRONTEND_WORKFLOW_DELTA.md`
9. `09_EVALUATION_AND_BENCHMARKS.md`
10. `10_SECURITY_GOVERNANCE_DELTA.md`
11. `11_IMPLEMENTATION_SEQUENCE.md`
12. `12_DOCUMENTATION_MIGRATION.md`
13. `13_AI_AGENT_WORKING_RULES.md`

Then inspect the actual repository and existing canonical docs before making changes.

## Authority

- The actual source code and tests define what is implemented.
- `progress.md` records implementation status.
- `decisions.md` records accepted engineering decisions.
- This context pack defines the TARGET PRODUCT DIRECTION.
- Target/vision capabilities must never be documented as already implemented.

## Core product evolution

Current:
`multi-source data → entity resolution → graph → graph analytics → evidence → investigator`

Target:
`observe → connect → detect change → forecast only what is justified → verify → route intelligence → human decision → learn`

Primary target message:

> NEXUS does not stop at finding connections. It detects how an observed investigative network changes, determines what evidence supports that change, identifies what should be verified next, and securely propagates actionable intelligence to the investigators who need it.
