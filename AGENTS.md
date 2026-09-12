# NEXUS AI CODING GOVERNANCE & REPOSITORY DISCIPLINE

> **Target:** Smart India Hackathon 2026 — Problem Statement ID: 26189  
> **System:** NEXUS — Evidence-Grounded Criminal Network Intelligence Platform  
> **Client Organization:** Ministry of Home Affairs (MHA) / National Crime Records Bureau (NCRB)  
> **Division:** Women Safety Division | **Theme:** Blockchain & Cybersecurity  

---

## 1. Core Mission & Value Proposition
NEXUS transforms fragmented First Information Reports (FIRs), Call Detail Records (CDRs), and financial transaction logs into an explainable, graph-native investigative workspace for Indian law enforcement, resolving suspect aliases and uncovering hidden kingpin brokers without black-box predictive bias.

---

## 2. Source of Truth Hierarchy
When resolving architectural or implementation questions, follow this strict hierarchy:
1. **Actual Implemented Code** (`backend/app/`, `frontend/src/`, `synthetic_data/`)
2. **Automated Tests & Benchmarks** (`pytest`, `vitest`, `scripts/evaluate_ground_truth.py`)
3. [`decisions.md`](file:///d:/Projects/CaseClock/decisions.md) (Single source of truth for architectural & product ADRs)
4. [`progress.md`](file:///d:/Projects/CaseClock/progress.md) (Single source of truth for ongoing progress and tasks)
5. [`docs/`](file:///d:/Projects/CaseClock/docs/) (Canonical architecture, deployment, and security specifications)
6. [`README.md`](file:///d:/Projects/CaseClock/README.md) (Executive orientation and developer quick-start)

---

## 3. Strict Non-Negotiable Constraints
- ❌ **Zero Predictive Guilt Scoring:** Never output scores labeled "Guilt", "Probability of Criminality", or "Recidivism Risk". Determination of guilt is the sole constitutional prerogative of the judiciary.
- ❌ **No Unverified Relationship Edges:** Every graph relationship must carry an `EvidenceProvenance` citation referencing an underlying record.
- 🔒 **Deterministic Before Generative:** All graph traversals, entity resolution, community clustering, and centrality computations must run via deterministic algorithms. Generative AI is restricted to summarization and is gated by an architectural refusal interceptor.
- 🛡️ **Zero Real Citizen PII:** All development, testing, and demos operate strictly on synthetic datasets generated via [`synthetic_data/nexus_generator.py`](file:///d:/Projects/CaseClock/synthetic_data/nexus_generator.py).

---

## 4. AI Coding Agent Repository Discipline

All AI coding assistants (Claude, Cursor, Copilot, Windsurf, Gemini, Antigravity) MUST abide by the following rules:

### 4.1 Repository Discipline
- **Inspect Before Editing:** Always inspect existing code, schemas, and utilities before writing new logic. Never guess paths or symbol names.
- **Reuse Before Rewrite:** Search existing components in `backend/app/core/`, `backend/app/services/`, and `frontend/src/components/`. Extend existing helpers rather than creating duplicates.
- **Do Not Create Fragmented Docs:** Never create files like `progress-1.md`, `implementation-progress.md`, `task-plan.md`, or `phase-status.md`. All progress belongs strictly in [`progress.md`](file:///d:/Projects/CaseClock/progress.md).
- **Do Not Create Ad-Hoc Decision Logs:** Never create individual `adr-XXX.md` or `decision.md` files. All architectural decisions belong in [`decisions.md`](file:///d:/Projects/CaseClock/decisions.md).
- **Do Not Dump Tool Output:** Never dump raw terminal outputs, test logs, or temporary JSON files into the repository root.
- **No Speculative Abstractions:** Do not create wrapper classes, abstract factories, or interfaces for single implementations. Prefer clarity and simplicity.
- **Surgical Changes Only:** Modify only what is strictly necessary for the prompt. Never reformat unrelated files or reorder existing code blocks.

### 4.2 Documentation Rule
Before creating ANY new Markdown file:
1. Search existing documentation in root and [`docs/`](file:///d:/Projects/CaseClock/docs/).
2. Determine whether the information belongs in [`README.md`](file:///d:/Projects/CaseClock/README.md), [`progress.md`](file:///d:/Projects/CaseClock/progress.md), [`decisions.md`](file:///d:/Projects/CaseClock/decisions.md), or an existing file in `docs/`.
3. Create a new document **ONLY** if it represents an ongoing canonical specification with long-term maintenance value.

### 4.3 Code-Quality & Engineering Rule
AI agents must:
- Write concise, idiomatic, typed Python (PEP 604 union syntax `X | None`) and TypeScript (`strict: true`).
- Preserve shared contracts in `shared/contracts/`.
- Explicitly handle exceptions, boundary conditions, and database disconnection fallbacks.
- Never use magic strings or numbers; reference defined constants and enums.
- Remove all dead code introduced during refactoring.

### 4.4 Testing Discipline
AI agents must:
- Add or update unit/integration tests for any non-trivial logic change.
- Never delete or disable tests merely to make a build or CI workflow pass.
- Never weaken assertion thresholds without explicit mathematical justification.
- Ensure all 708 backend tests and 114 frontend tests remain 100% green before completing work.

### 4.5 Git & Safety Discipline
AI agents must:
- Inspect `git status` before making edits.
- Never discard uncommitted user changes.
- Never force-push or rewrite published commit history.
- Never commit credentials, private keys, `.env` files, or local database caches.

### 4.6 Completion Verification Rule
Before declaring any task complete, an AI agent must verify:
1. `python -m ruff check backend/ shared/ tests/` (0 lint errors)
2. `pytest` (All 708+ backend tests pass)
3. `python scripts/evaluate_ground_truth.py` (100% Precision / Recall)
4. `cd frontend && npm test -- --run && npm run build` (All 114 frontend tests pass, 0 TypeScript errors)
5. Central documentation ([`progress.md`](file:///d:/Projects/CaseClock/progress.md) / [`decisions.md`](file:///d:/Projects/CaseClock/decisions.md)) updated if applicable.
6. `git status` verified clean of accidental junk or temporary artifacts.

---

## 5. AI Output Optimization Principles

When designing or generating code, AI agents must prioritize in this exact order:

$$\text{CORRECTNESS} > \text{SIMPLICITY} > \text{MAINTAINABILITY} > \text{REUSE} > \text{TESTABILITY} > \text{PERFORMANCE}$$

- When two implementations are equally correct, **choose the simpler one**.
- When an existing utility solves 90% of the problem, **extend it rather than inventing a new one**.
- Prefer concise, self-explanatory code over long docstrings narrating what the code does.
