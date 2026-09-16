# NEXUS AI CODING GOVERNANCE & REPOSITORY DISCIPLINE

> **Target:** Smart India Hackathon 2026 — Problem Statement ID: 26189  
> **System:** NEXUS — Proactive, Evidence-Grounded Criminal Network Change Intelligence Platform  
> **Client Organization:** Ministry of Home Affairs (MHA) / National Crime Records Bureau (NCRB)  
> **Division:** Women Safety Division | **Theme:** Blockchain & Cybersecurity  

---

## 1. Core Mission & Value Proposition
NEXUS evolves criminal intelligence from retrospective network link charts into **proactive, evidence-grounded criminal network change intelligence**. Operating on the lifecycle:
$$\text{observe} \to \text{connect} \to \text{detect change} \to \text{forecast only what is justified} \to \text{alert} \to \text{verify} \to \text{act} \to \text{learn}$$
NEXUS transforms fragmented First Information Reports (FIRs), Call Detail Records (CDRs), and financial transactions into an explainable, graph-native investigative workspace. It detects meaningful network changes, grounds every finding in verifiable evidence, identifies evidence gaps, suggests next-best verification plans, and securely routes intelligence across jurisdictions without black-box predictive guilt bias.

---

## 2. Source of Truth Hierarchy
When resolving architectural, product, or implementation questions, follow this strict hierarchy:
1. **Actual Implemented Code** (`backend/app/`, `frontend/src/`, `synthetic_data/`, `shared/`)
2. **Automated Tests & Benchmarks** (`pytest`, `vitest`, `scripts/evaluate_ground_truth.py`, `tests/`)
3. [`decisions.md`](file:///d:/Projects/Nexus/decisions.md) (Single source of truth for architectural & product ADRs)
4. [`progress.md`](file:///d:/Projects/Nexus/progress.md) (Single source of truth for ongoing implementation progress and status)
5. **Canonical Documentation** in [`docs/`](file:///d:/Projects/Nexus/docs/):
   - [`ARCHITECTURE.md`](file:///d:/Projects/Nexus/docs/ARCHITECTURE.md) (Authoritative system architecture: Layers 1–9)
   - [`DATA_MODEL.md`](file:///d:/Projects/Nexus/docs/DATA_MODEL.md) (Authoritative graph ontology and target domain objects)
   - [`API.md`](file:///d:/Projects/Nexus/docs/API.md) (Authoritative API contract: implemented endpoints vs. target designs)
   - [`INTELLIGENCE_PIPELINE.md`](file:///d:/Projects/Nexus/docs/INTELLIGENCE_PIPELINE.md) (Authoritative intelligence processing lifecycle)
   - [`SECURITY.md`](file:///d:/Projects/Nexus/docs/SECURITY.md) (Statutory compliance, RBAC, Section 63 BSA, SOCMINT governance)
   - [`BENCHMARKS.md`](file:///d:/Projects/Nexus/docs/BENCHMARKS.md) (Verified performance SLA measurements and target evaluation protocols)
   - [`DEMO.md`](file:///d:/Projects/Nexus/docs/DEMO.md) (Authoritative 3-minute live evaluation demonstration journey)
   - [`DEPLOYMENT.md`](file:///d:/Projects/Nexus/docs/DEPLOYMENT.md) (Authoritative cloud and on-premise deployment specifications)
   - [`DEVELOPMENT.md`](file:///d:/Projects/Nexus/docs/DEVELOPMENT.md) (Authoritative setup, testing, and fixture seeding protocol)
6. [`README.md`](file:///d:/Projects/Nexus/README.md) (Executive overview, quick-start, and system navigation)
7. `docs/NEXUS_ROADMAP_CONTEXT/` (Target product reference context — **non-authoritative** after canonicalization)
8. `docs/archive/` (Historical and superseded documents — reference only)

---

## 3. Strict Non-Negotiable Constraints
- ❌ **Zero Predictive Guilt Scoring:** Never output scores labeled "Guilt", "Probability of Criminality", "Recidivism Risk", or "Dangerousness". Determination of guilt is the exclusive constitutional prerogative of the judiciary under Indian law.
- ❌ **No Unverified Relationship Edges:** Every graph relationship must carry an `EvidenceProvenance` citation referencing an underlying record.
- 🔒 **Deterministic Before Generative:** All graph traversals, entity resolution, community clustering, snapshot diffing, and centrality computations must run via deterministic algorithms. Generative AI is restricted to summarization/explanation and is strictly gated by an architectural refusal interceptor.
- 🛡️ **Zero Real Citizen PII:** All development, testing, CI benchmarks, and live demonstrations operate strictly on synthetic datasets generated via [`synthetic_data/nexus_generator.py`](file:///d:/Projects/Nexus/synthetic_data/nexus_generator.py).
- ⚖️ **Abstention is a First-Class State:** An analytical signal or early-warning engine must explicitly output `INSUFFICIENT EVIDENCE / NO FORECAST` when supporting evidence is sparse, stale, or contradictory.
- 🚫 **No Sensitive Data on Public Blockchains:** Never commit or transmit raw FIRs, CDRs, bank accounts, or citizen PII to public ledgers. Trust fabric mechanisms are restricted to cryptographic hashes and Merkle proofs.
- 🚫 **No Naive PSI:** Do not use naive `SHA256(phone)` or similar vulnerable schemes as production Private Set Intersection.
- 🚫 **No Covert Social Media Scraping:** Digital Shadow fusion is restricted to authorized, public, and structured digital identifier corroboration with strict association lifecycle states (`Observed` $\to$ `Candidate Link` $\to$ `Corroborated` $\to$ `Investigator Confirmed`).

---

## 4. Epistemic Classification Rules
Every feature, service, and documented capability must be explicitly labeled with its factual lifecycle state:
- **CURRENT:** Implemented in code, tested, and verified in the baseline.
- **EXTENSION:** Built directly on top of an existing current subsystem.
- **NEW PROTOTYPE:** Fresh slice implementing roadmap capabilities (P0/P1).
- **TARGET / FUTURE:** Formally designed specification not yet implemented.
- **REJECTED:** Explicitly evaluated and rejected (e.g. predictive guilt scores, raw on-chain PII).

Never document a future or target capability as implemented. Never fabricate benchmark figures.

---

## 5. AI Coding Agent Repository Discipline

All AI coding assistants (Claude, Cursor, Copilot, Windsurf, Gemini, Antigravity) MUST abide by the following rules:

### 5.1 Repository Discipline
- **Inspect Before Editing:** Always inspect existing code, schemas, and utilities before writing new logic. Never guess paths or symbol names.
- **Reuse Before Rewrite:** Search existing components in `backend/app/core/`, `backend/app/services/`, and `frontend/src/components/`. Extend existing helpers (such as `backend/app/core/graph/algorithms/snapshot_diff.py`) rather than creating duplicate engines.
- **Do Not Create Fragmented Docs:** Never create ad-hoc files like `progress-1.md`, `implementation-progress.md`, `task-plan.md`, or `phase-status.md`. All progress belongs strictly in [`progress.md`](file:///d:/Projects/Nexus/progress.md).
- **Do Not Create Ad-Hoc Decision Logs:** Never create individual `adr-XXX.md` or `decision.md` files. All architectural decisions belong in [`decisions.md`](file:///d:/Projects/Nexus/decisions.md).
- **Do Not Dump Tool Output:** Never dump raw terminal outputs, test logs, or temporary JSON files into the repository root.
- **No Speculative Abstractions:** Do not create wrapper classes, abstract factories, or interfaces for single implementations. Prefer clarity and simplicity.
- **Surgical Changes Only:** Modify only what is strictly necessary for the prompt. Never reformat unrelated files or reorder existing code blocks.

### 5.2 Documentation Consolidation Rule
Before creating ANY new Markdown file:
1. Search existing documentation in root and [`docs/`](file:///d:/Projects/Nexus/docs/).
2. Determine whether the information belongs in [`README.md`](file:///d:/Projects/Nexus/README.md), [`progress.md`](file:///d:/Projects/Nexus/progress.md), [`decisions.md`](file:///d:/Projects/Nexus/decisions.md), or an existing file in `docs/`.
3. If historical, move to `docs/archive/YYYY-MM-DD-description.md`. Never create competing versions like `ARCHITECTURE_V2.md`.

### 5.3 Code Quality & Engineering Rules
AI agents must:
- Write concise, idiomatic, typed Python (PEP 604 union syntax `X | None`) and TypeScript (`strict: true`).
- Preserve shared contracts in `shared/contracts/`.
- Explicitly handle exceptions, boundary conditions, and database disconnection fallbacks.
- Never use magic strings or numbers; reference defined constants and enums.
- Remove all dead code introduced during refactoring.

### 5.4 Testing Discipline
AI agents must:
- Add or update unit/integration tests for any non-trivial logic change.
- Never delete or disable tests merely to make a build or CI workflow pass.
- Never weaken assertion thresholds without explicit mathematical justification.
- Ensure all 708 backend tests and 114 frontend tests remain 100% green before completing work.

### 5.5 Completion Verification Rule
Before declaring any task complete, an AI agent must verify:
1. `python -m ruff check backend/ shared/ tests/` (0 lint errors)
2. `pytest` (All 708+ backend tests pass)
3. `python scripts/evaluate_ground_truth.py` (100% Precision / Recall)
4. `cd frontend && npm test -- --run && npm run build` (All 114 frontend tests pass, 0 TypeScript errors)
5. Central documentation ([`progress.md`](file:///d:/Projects/Nexus/progress.md) / [`decisions.md`](file:///d:/Projects/Nexus/decisions.md)) updated if applicable.
6. `git status` verified clean of accidental junk or temporary artifacts.

---

## 6. AI Output Optimization Principles
When designing or generating code, prioritize in this exact order:
$$\text{CORRECTNESS} > \text{SIMPLICITY} > \text{MAINTAINABILITY} > \text{REUSE} > \text{TESTABILITY} > \text{PERFORMANCE}$$
