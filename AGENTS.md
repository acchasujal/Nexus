# NEXUS AI DEVELOPMENT CONTEXT

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
3. [`NEXUS.md`](file:///d:/Projects/CaseClock/NEXUS.md) (Ground-truth product and domain blueprint)
4. [`PROGRESS.md`](file:///d:/Projects/CaseClock/PROGRESS.md) (Central workstream task board and progress tracking)
5. [`docs/`](file:///d:/Projects/CaseClock/docs/) (Standardized architecture and domain specifications)

---

## 3. Strict Non-Negotiable Constraints
- ❌ **Zero Predictive Guilt Scoring:** Never output scores labeled "Guilt", "Probability of Criminality", or "Recidivism Risk". Determination of guilt is the sole constitutional prerogative of the judiciary.
- ❌ **No Unverified Relationship Edges:** Every graph relationship must carry an `EvidenceProvenance` citation referencing an underlying record.
- 🔒 **Deterministic Before Generative:** All graph traversals, entity resolution, community clustering, and centrality computations must run via deterministic algorithms. Generative AI is restricted to summarization and is gated by an architectural refusal interceptor.
- 🛡️ **Zero Real Citizen PII:** All development, testing, and demos operate strictly on synthetic datasets generated via [`synthetic_data/nexus_generator.py`](file:///d:/Projects/CaseClock/synthetic_data/nexus_generator.py).

---

## 4. Team Ownership & Modular Architecture

| Workstream | Domain Scope | Primary Directories |
| :--- | :--- | :--- |
| **Member 1 (Data & Ingestion)** | Synthetic generation, parsers, DB schemas | `synthetic_data/`, `backend/app/db/` |
| **Member 2 (Graph & Intelligence)** | Entity resolution, Louvain, Betweenness | `backend/app/core/graph/`, `scripts/` |
| **Member 3 (Backend & Copilot)** | REST APIs, refusal gate, audit, contracts | `backend/app/api/`, `backend/app/services/`, `shared/` |
| **Member 4 (Frontend & UX)** | Workspace UI, React Flow canvas, Copilot | `frontend/src/` |

---

## 5. Developer & AI Coding Agent Workflow

### Before Writing Any Code:
1. Check [`PROGRESS.md`](file:///d:/Projects/CaseClock/PROGRESS.md) for current task status and dependencies.
2. Confirm the branch originates from `origin/main` (`git switch main && git pull --rebase`).
3. Create a short-lived local feature branch (`git switch -c feature/<short-name>`).
4. Inspect existing utilities and algorithms before writing new functions (no duplicate logic).

### Before Opening a Pull Request:
1. Run backend lint: `python -m ruff check backend/ shared/ tests/`.
2. Run backend tests: `pytest` (Must pass all 493 tests).
3. Run ground truth validation: `python scripts/evaluate_ground_truth.py` (Must pass 100% Precision/Recall).
4. Run frontend tests and build: `cd frontend && npm test -- --run && npm run build`.
5. Update your task status in [`PROGRESS.md`](file:///d:/Projects/CaseClock/PROGRESS.md).
6. Open PR targeting `main`.
