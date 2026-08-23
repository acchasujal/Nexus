# IMPLEMENTATION_PLAN.md

Blueprint for building Case Clock from an empty repository to a demoable, honestly-scoped MVP. Read `PROJECT_CONTEXT.md`, `EXECUTION_RULES.md`, `ARCHITECTURE.md`, `FEATURE_REGISTRY.md`, `DECISION_LOG.md`, and `TASK.md` before this file — this plan assumes their content and does not repeat it.

## Reasoning Before Sequencing

**The single most dangerous ordering mistake available here is building UI or AI features before the graph schema and the Catalyst storage decision are settled.** Every other module (clock engine, dependency tracker, escalation, similarity, copilot) reads and writes the same graph. If the schema shifts after three modules are built against it, all three need rework — this is exactly the "overbuilt, disconnected pipeline" failure pattern already documented in D9 (`DECISION_LOG.md`), and the plan below is designed specifically to prevent it.

**The second most dangerous mistake is deferring deployment to the end.** `ARCHITECTURE.md` already states "deploy early and iterate" as a philosophy; this plan enforces it structurally by requiring a deployed walking skeleton before any feature work begins, not as an afterthought in a late phase. Catalyst's actual capabilities (does it support the storage pattern the graph needs?) are unverified per `TASK.md` — this must be resolved by building something real and deploying it, not by reading documentation and assuming.

**The third danger is starting the AI/conversational layer before the deterministic layers are stable.** The copilot's grounded-query generation depends on a stable, tested clock engine and dependency tracker to query against. Building the AI layer first means building against a moving target, and it also risks masking whether a bug is in the deterministic logic or the generative logic (a distinction `EXECUTION_RULES.md`'s debugging methodology depends on being able to make).

**The fourth danger, specific to this project:** the two most-repeated unresolved items across the initial planning phase (`DECISION_LOG.md` D7, D8) — the refusal-gate test set and the scale test — are exactly the kind of work that gets silently dropped under time pressure because they don't produce visible UI progress. This plan places them as **blocking gates**, not final-phase nice-to-haves, so they cannot be skipped without the plan visibly saying so.

**Assumption this plan makes, flagged explicitly:** a 4-person team can parallelize after the graph schema is frozen (end of Phase 2). Before that point, parallelization is dangerous — two people building against different guesses of the schema is a direct path to rework.

---

# Phase 0 — Repository Initialization & Walking Skeleton

**Goal:** A minimal but real, end-to-end deployed system (one dummy endpoint, one dummy page, deployed on Catalyst) — proving the deployment path works before any real feature is built.

**Why it comes now:** Catalyst's actual capabilities are unverified (`TASK.md`). Discovering a deployment blocker in the final week is the single most common late-stage failure mode for this team (D9). Resolve it in hours, not in week three.

**Deliverables:**

- Git repository with backend (`/backend`) and frontend (`/frontend`) folders per `README.md`'s target structure.
- Linting, formatting, type-checking configured (Python: ruff/mypy; JS/TS: eslint/prettier).
- Environment variable handling (`.env` pattern, never committed).
- CI: a consolidated `ci.yml` workflow that runs lint + type-check + unit tests for both backend and frontend on every PR.
- A single dummy backend endpoint deployed to Catalyst, a single dummy frontend page deployed to Catalyst, and confirmation they can talk to each other over the real deployment.
- A written note (append to `TASK.md`) recording what Catalyst actually supports (data store type, whether native graph/recursive query capability exists, auth service availability).

**Dependencies:** None — this is the true starting point.

**Files:** `/backend` scaffold, `/frontend` scaffold, `.env.example`, consolidated CI config, `TASK.md` update.

**Risks:** Catalyst may not support the storage pattern `ARCHITECTURE.md` assumed (relational adjacency table). If so, **stop and update `ARCHITECTURE.md` and log the change in `DECISION_LOG.md` immediately** — do not proceed to Phase 2 on a storage assumption known to be wrong.

**Acceptance Criteria:** A URL exists, on Catalyst, that a browser can load, showing data that came from a real deployed backend call — not a mock.

**Definition of Done:** Deployed, verified working by all 4 team members independently loading the URL.

**Common mistakes:** Skipping real deployment in favor of local-only development "to save time" — this directly reintroduces the exact risk this phase exists to eliminate.

**Review checklist:** [ ] Deployed and reachable [ ] Catalyst capability findings logged in `TASK.md` [ ] CI passes on a clean clone.

Record actual Catalyst capabilities by completing the following implementation spikes:

- Catalyst Data Store
  - recursive queries
  - joins
  - indexes
  - query limits

- Catalyst QuickML
  - supported models
  - RAG support
  - document ingestion
  - citations
  - structured output
  - API latency

- Catalyst SmartBrowz
  - HTML → PDF generation

- Catalyst Zia
  - English STT/TTS
  - Kannada STT/TTS

## Update TASK.md with findings.

# Phase 1 — Foundation

**Goal:** Shared infrastructure every later module depends on: config, logging, error handling, validation, constants, auth skeleton.

**Why it comes now:** Every subsequent phase needs consistent error handling and config — building this after Phase 2 means retrofitting it into already-written modules.

**Deliverables:**

- Centralized config loading (env-driven, no hardcoded values).
- Structured logging (every request/query loggable — this feeds the audit log requirement in `FEATURE_REGISTRY.md` #15).
- Centralized error-handling middleware/pattern with consistent error response shape.
- Input validation pattern (schema-based, reusable across endpoints).
- Constants module including the **offence-category → clock-type mapping table skeleton** — populated with `[UNVERIFIED]` markers per `EXECUTION_RULES.md`'s anti-hallucination rules until checked against BNSS text.
- Auth skeleton: 3-role model (IO/SHO/SP) per `FEATURE_REGISTRY.md` #14 — role-check middleware, not full permission logic yet.

**Dependencies:** Phase 0 (repo + deployment path must exist).

**Files:** `/backend/app/core/auth`, `/shared/constants/clock_types.py`, validation & logging configurations.

**Risks:** Populating the clock-mapping table with unverified section numbers and forgetting to mark them — cross-check against `EXECUTION_RULES.md` rule on legal citations before considering this phase done.

**Acceptance Criteria:** A deliberately-thrown error returns a consistent, logged, non-leaking error response. Auth skeleton rejects an unauthenticated request.

**Definition of Done:** Unit tests for validation and error-handling pass; clock-mapping table exists with explicit unverified flags, not silent placeholders.

**Common mistakes:** Hardcoding a BNSS section number without the `[UNVERIFIED]` marker "to make the demo look more confident" — this is precisely the overclaiming risk flagged throughout `DECISION_LOG.md`.

**Review checklist:** [ ] No hardcoded secrets [ ] Every legal citation marked verified/unverified [ ] Auth skeleton actually rejects bad requests, tested.

---

# Phase 2 — Data Model (Graph Schema + Synthetic Data)

Validate that Catalyst Data Store can efficiently represent the adjacency-list graph model before freezing the schema. If limitations are found, redesign now instead of after backend development.

**Goal:** Implement the node/edge model from `ARCHITECTURE.md` and generate synthetic data that can actually exercise every downstream feature — including deliberately-engineered repeat entities for network analysis to have something real to show.

**Why it comes now:** This is the schema every other module depends on. It must be frozen (with a documented process for controlled change) before Phase 3 begins in earnest — freezing it late means rework across every dependent module.

**Deliverables:**

- Node types: Case, Person (role-typed via edges), Section, Act, CrimeHead/SubHead, Location, Officer, Unit, Court, Evidence, Dependency, ClockInstance, EscalationEvent, ConversationLog — per `ARCHITECTURE.md` and `DECISION_LOG.md` D15 (Evidence added in graph schema v1.1).
- Edge types: ACCUSED_IN, VICTIM_IN, COMPLAINANT_IN, WITNESS_IN, CHARGED_UNDER, BELONGS_TO_ACT, OCCURRED_IN, INVESTIGATED_BY, BELONGS_TO_UNIT, CASE_HAS_DEPENDENCY, CASE_HAS_CLOCK, CASE_HAS_EVIDENCE, CASE_HAS_COURT, CASE_HAS_CRIME_HEAD, CASE_HAS_CRIME_SUB_HEAD, CASE_HAS_ESCALATION_EVENT, CASE_HAS_CONVERSATION_LOG, and the two derived (not stored) edges CO_ACCUSED_WITH and (only if justified) LINKED_TO.
- Migration/creation scripts against whatever storage pattern Phase 0 confirmed Catalyst supports.
- **Synthetic data generator** producing ~500–1,000 realistic cases for early development (not yet the full 1–2 lakh scale test — that's Phase 7), with:
  - Deliberate repeat entities (same person as accused across 2+ cases) so network analysis has real signal.
  - Deliberate variety in offence categories so every clock-mapping-table entry gets exercised.
  - Deliberate missing/stale dependencies so escalation logic has real trigger conditions.
- Seed data script, idempotent (safe to re-run).

**Dependencies:** Phase 1 (config/validation needed for generator scripts).

**Files:** `/backend/app/db/` (models and migrations), `/scripts/seed_synthetic_data.py`.

**Risks:** If the generator produces data that's too clean (no realistic near-duplicate entity spellings, no genuinely stale dependencies), every downstream feature will look artificially good in development and then behave differently against messier data later. Deliberately inject imperfection.

**Acceptance Criteria:** Seed script populates the store; a manual query confirms at least one genuine cross-case person link exists in the seeded data.

**Definition of Done:** Schema frozen and documented; any future change to it requires a `DECISION_LOG.md` entry per `EXECUTION_RULES.md`'s refactoring rules.

**Common mistakes:** Generating data with no deliberate repeat entities, then being surprised in Phase 3/4 that the network-analysis feature has nothing to show.

**Review checklist:** [ ] Every node/edge type in `ARCHITECTURE.md` is represented [ ] Generator produces at least one verifiable cross-case link [ ] Migration is re-runnable without manual cleanup.

---

# Phase 3 — Backend (Deterministic Layers First, Then Aggregation, Then API)

**Goal:** Build and unit-test the deterministic modules in dependency order: Legal Clock Engine → Dependency Tracker → Escalation Rule Engine → Aggregation Layer (pattern/trend) → Similarity Function → API layer exposing all of it.

**Why it comes now, and in this internal order:** The Clock Engine has no dependencies on any other backend module and is the most legally sensitive (errors here are accuracy risks, not just bugs) — build and test it in isolation first. The Dependency Tracker and Escalation Engine both consume ClockInstance data, so they come next. Aggregation and Similarity consume the same Case/Person nodes but don't depend on the clock/escalation logic, so they can be built in parallel with each other once the graph is stable. The API layer comes last because it's a thin exposure layer over already-tested logic — building it first would mean testing against unstable internals.

**Deliverables (in order):**

1. Legal Clock Engine — resolves offence category to clock(s), computes days-remaining. Unit tests cover every mapping-table entry plus the missing-mapping edge case (must flag "undetermined," never guess).
2. Dependency Tracker — CRUD for named dependencies, staleness computation.
3. Escalation Rule Engine — deterministic trigger logic, correct-rank routing using Officer/Unit hierarchy, writes to `EscalationEvent` and audit log.
4. Aggregation Layer — pattern/trend grouped queries; rule-based trend-alert threshold check (`FEATURE_REGISTRY.md` #17), explicitly labeled non-ML in code comments. Exists inside `backend/app/core/graph/`.
5. Similarity Function — structured feature match, returns the specific shared attributes with every result (not just a score). Exists inside `backend/app/core/graph/`.
6. Catalyst Integration Layer

Responsible for:
- Data Store access
- QuickML wrapper
- SmartBrowz wrapper
- Zia wrapper

No frontend or business logic may call Catalyst SDKs directly.
Reason: Keeps Catalyst isolated. If Catalyst APIs change, only `backend/app/catalyst/` changes.

7. API layer — REST/GraphQL endpoints exposing the above, with the validation and auth middleware from Phase 1 applied to every endpoint.

**Dependencies:** Phase 2 (frozen schema + seeded data).

**Files:** `backend/app/core/clock/`, `backend/app/core/dependency/`, `backend/app/core/escalation/`, `backend/app/core/graph/` (aggregation and similarity), `backend/app/catalyst/`, `backend/app/api/`.

**Risks:** Skipping the missing-mapping edge case test for the Clock Engine — this is the single highest-consequence silent-failure mode in the whole backend (a case silently getting a wrong or default clock).

**Acceptance Criteria:** Every unit listed has passing tests, including the deliberate edge cases named above. The escalation trigger is reproducible against seeded data, not a one-off manual demo.

**Definition of Done:** API layer returns correct, tested data for every endpoint; Postman/equivalent collection or equivalent test script exists.

**Common mistakes:** Building the API layer before the underlying logic is stable "to unblock frontend work" — this just moves the instability into the frontend instead of removing it. If frontend needs to start early, give it a mocked API contract, not a half-finished real one (see Parallel Work section).

**Review checklist:** [ ] Clock Engine handles the undetermined case without guessing [ ] Escalation only fires on real, tested conditions [ ] Every API endpoint has an auth check.

---

# Phase 4 — Frontend

**Goal:** Case Detail (the universal object), Risk-Ranked Worklist, Network tab, Similarity tab, District Rollup, Escalation Queue view — built against the real API from Phase 3.

**Why it comes now:** Building against a real, tested API avoids the double-rework of building against a mock and then reconciling. Frontend work on layout/routing/design-system can start earlier in parallel (see Parallel Work) using a mocked contract, but feature screens wait for real endpoints.

**Deliverables:**

- Layout, routing, base design system/components.
- Case Detail screen: clock badges, dependency panel, Network tab, Similarity tab, Copilot box (wired to a stub until Phase 5 completes).
- Risk-Ranked Worklist (IO view).
- District/Pattern Rollup (SP/DCP view, exception-only).
- Escalation Queue view.
- Conversation History
  ↓
  SmartBrowz HTML→PDF Export (`FEATURE_REGISTRY.md` #13) — this has no AI dependency, can be built as soon as `ConversationLog` shape exists.

**Dependencies:** Phase 3 API layer for real data; Phase 0 design/routing scaffold can start earlier.

**Files:** `/frontend/case_detail`, `/frontend/worklist`, `/frontend/pattern_rollup`, `/frontend/escalation_queue`, `/frontend/copilot` (shell only).

**Risks:** Building rich UI polish before the underlying data is trustworthy — polish should follow correctness, not precede it, given the team's documented pattern of impressive-looking-but-incomplete demos.

**Acceptance Criteria:** Every screen renders real data from the real seeded dataset, not hardcoded mock JSON.

**Definition of Done:** All MVP screens in `FEATURE_REGISTRY.md` are navigable end-to-end against real backend data.

**Common mistakes:** Leaving the Copilot box wired to fake canned responses past this phase without a clear plan to replace it in Phase 5 — track this explicitly in `TASK.md` so it isn't forgotten.

**Review checklist:** [ ] No hardcoded mock data remains in "done" screens [ ] Every screen matches its acceptance criteria in `FEATURE_REGISTRY.md`.

---

# Phase 5 — AI (Conversational Layer)

**Goal:** Grounded NL query generation, deterministic verification/refusal gate, path-annotated responses — built last among core features because it depends on a stable graph and API to query against.

**Why it comes now:** Building this earlier risks masking bugs (is a wrong answer a graph problem or a prompt problem?) per `EXECUTION_RULES.md`'s debugging methodology, which depends on the deterministic layers already being trustworthy.

**Deliverables:**
Production pipeline:
Voice (optional)
↓
Zia STT
↓
QuickML
↓
Structured Query
↓
Deterministic Verification
↓
Catalyst Data Store
↓
Evidence Collection
↓
QuickML Response Generation
↓
Evidence Annotation
↓
Zia TTS (optional)

- NL → structured query translation, grounded against the real API/schema (never inventing fields). Exists inside `backend/app/core/copilot/`.
- Deterministic verification gate: checks the translated query against known schema/entities before execution; if grounding confidence is low, triggers refusal instead of guessing.
- Path-annotated response formatting: every successful answer returns the specific nodes/edges/rows that produced it.
- Refusal response: explicit, states why, logged to audit log.
- **The refusal-gate test set (10–15 questions, answerable + ambiguous) — build and run this now, as part of this phase, not deferred.** This directly resolves D7 in `DECISION_LOG.md`.

Grounding Strategy:
QuickML never makes final investigative decisions.
QuickML only performs:
- intent understanding
- response generation
- summarization

All evidence retrieval comes from Catalyst Data Store.
Every response must include:
- FIR IDs
- Entity IDs
- Evidence source
- Query path
Otherwise refuse.

**Dependencies:** Phase 3 (stable API), Phase 2 (stable schema).

**Files:** `backend/app/core/copilot/` (NL engine and refusal gate), `backend/tests/refusal_testset/` (test set definitions).

**Risks:** Under-refusal (answering confidently when it shouldn't) is more dangerous than over-refusal (declining when it could have answered) — bias the gate's threshold toward caution, and say so explicitly in the deck as a deliberate design choice.

**Acceptance Criteria:** The refusal test set is actually run, with a recorded pass rate — this number must exist before any demo claim about refusal reliability, per D7.

**Definition of Done:** Copilot box in Case Detail (Phase 4) is wired to real responses; test set results are logged in `TASK.md`.

**Common mistakes:** Treating a passing demo on 2–3 rehearsed questions as sufficient evidence of refusal reliability — this is exactly the untested-claim risk D7 exists to prevent.

**Review checklist:** [ ] Test set actually run, not just designed [ ] Pass rate recorded [ ] No free-generated prose about a specific person's guilt/risk anywhere in output (cross-check against `FEATURE_REGISTRY.md` #8).

---

# Phase 6 — Integration

**Goal:** Connect all modules end-to-end, add error recovery and basic caching/performance work.

**Why it comes now:** Individual modules are tested in isolation through Phases 3–5; this phase catches interaction bugs between them (e.g., escalation firing based on stale clock data due to a caching bug).

**Deliverables:** Full end-to-end flow (worklist → case detail → escalation → copilot) working against real deployed backend; basic caching where profiling shows it's needed (not speculative); error recovery per `EXECUTION_RULES.md`'s error-recovery process (revert-first, diagnose-second).

**Dependencies:** Phases 3, 4, 5 complete.

**Files:** Cross-cutting — no new module, primarily integration tests and bugfixes.

**Risks:** Discovering a Phase-2 schema limitation only now — if this happens, follow the refactoring rule in `EXECUTION_RULES.md` (log in `DECISION_LOG.md`, don't patch silently).

**Acceptance Criteria:** A full walkthrough of the demo flow (per the demo script established in prior planning) works without manual intervention, twice in a row.

**Definition of Done:** Demo flow reproducible by a team member who didn't build it, following only the UI.

**Common mistakes:** Adding caching pre-emptively where no measured performance problem exists — this adds complexity without evidence it's needed.

**Review checklist:** [ ] Full demo flow works end-to-end [ ] No manual data-fixing required between runs.

---

# Phase 7 — Testing (Including the Two Mandatory Gates)

**Goal:** Execute the two outstanding, repeatedly-flagged mandatory tests — refusal-gate scoring (if not already fully completed in Phase 5) and the 1–2 lakh record scale test — plus general unit/integration/E2E/manual QA.

**Why it comes now:** These require a stable, integrated system (Phase 6) to test meaningfully. They are listed as their own phase specifically so they cannot be silently dropped as "already handled" without an explicit checkmark.

**Deliverables:**

- Scale test: generate ~1–2 lakh synthetic records (extend the Phase 2 generator), run core queries (worklist ranking, escalation check, similarity, copilot grounding), record actual latency numbers.
- Full refusal-gate test set results, if not finalized in Phase 5.
- Manual QA: at least 2 non-team members (or team members acting as skeptical judges) run the demo flow and specifically try to break the refusal gate and the escalation trigger.
- Rehearsal of the live threshold-crossing escalation moment, multiple times, checking specifically whether it reads as competence or malfunction to a non-technical observer (a risk flagged repeatedly across prior planning rounds).

Measure:
- latency
- memory
- Catalyst API response time
- QuickML response time
- PDF generation time
- Graph traversal time

**Dependencies:** Phase 6.

**Files:** `tests/scale/` (for metrics and run files), test result logs appended to `TASK.md`.

**Acceptance Criteria:** A measured latency number exists and is recorded — not an estimate. Refusal-gate pass rate is recorded. At least one non-builder has successfully triggered the live escalation demo without assistance.

**Definition of Done:** `TASK.md` shows both D7 and D8 as DONE with evidence, not just NOT STARTED.

**Common mistakes:** Running the scale test against a dataset that doesn't resemble the real schema's messiness (e.g., no realistic duplicate/near-duplicate entities) — this produces an optimistic, unrepresentative number.

**Review checklist:** [ ] Scale test used realistic (not artificially clean) data [ ] Latency number is measured, not estimated [ ] Refusal test set score recorded.

---

# Phase 8 — Deployment (Production Hardening)

**Goal:** Finalize the Catalyst deployment (already exists as a walking skeleton since Phase 0) with monitoring, logging, and basic backup consideration for the submission.

**Why it comes now:** The deployment path itself was de-risked in Phase 0; this phase is about hardening an already-working deployment, not standing one up for the first time under deadline pressure.

**Deliverables:** Production environment variables separated from development; basic monitoring/alerting if Catalyst supports it; audit log confirmed persisting correctly in the deployed environment; README setup instructions verified by following them on a clean machine.

**Dependencies:** Phase 7.

**Files:** Deployment config, `README.md` setup section verified/updated.

**Risks:** Discovering a dev/production environment mismatch this late — mitigated by the fact that Phase 0 already deployed early and repeatedly, so this should be a refinement, not a first attempt.

**Acceptance Criteria:** Fresh deployment from a clean clone succeeds, following only `README.md`.

**Definition of Done:** Submission checklist (per `PROTOTYPE_SUBMISSION_GUIDE.md` — Prototype Brief, GitHub, Catalyst Deployment, Demo Video, Deck) fully satisfied.

**Common mistakes:** Treating deployment as done because it worked once during development — verify it works from a clean state, not just the developer's own machine.

**Review checklist:** [ ] Clean-clone deployment succeeds [ ] All submission deliverables present.

Verify every required Catalyst service used in the project is actually deployed through Catalyst.
Record:
- Frontend
- Backend
- Authentication
- Data Store
- QuickML
- SmartBrowz
- Zia
- Cron
- Storage

---

## Dependency Graph

```
Phase 0 (repo + walking skeleton deploy)
   │
   ▼
Phase 1 (foundation: config, logging, errors, validation, auth skeleton, clock-mapping constants)
   │
   ▼
Phase 2 (graph schema + synthetic data) ──────────────┐
   │                                                    │
   ▼                                                    ▼
Phase 3 (backend: clock → dependency → escalation   Phase 4 partial (layout/routing/design
   → aggregation/similarity → API)                   system — can start once Phase 1 done,
   │                                                    using a mocked API contract)
   ▼                                                    │
Phase 4 full (feature screens against real API) ◄───────┘
   │
   ▼
Phase 5 (AI / conversational layer + refusal-gate test set)
   │
   ▼
Phase 6 (integration)
   │
   ▼
Phase 7 (testing: scale test + refusal test finalization + manual QA)
   │
   ▼
Phase 8 (deployment hardening)
```

**Hard rule:** Phase 3's Clock Engine must be complete and tested before Escalation Engine begins. Phase 5 must not begin before Phase 3's API layer is stable. Phase 7's scale test must not be skipped or merged silently into Phase 6 — it needs its own checkpoint in `TASK.md`.

---

## Critical Path (shortest path to a working, demoable MVP)

```
Phase 0 (skeleton deployed)
→ Phase 1 (foundation + clock-mapping constants)
→ Phase 2 (schema frozen + seed data with deliberate repeat entities)
→ Phase 3.1 Clock Engine (tested)
→ Phase 3.2 Dependency Tracker
→ Phase 3.3 Escalation Engine (reproducible trigger)
→ Phase 3.6 API layer (minimum: worklist, case detail, escalation endpoints)
→ Phase 4 (Case Detail + Worklist screens only — Network/Similarity/Rollup can trail)
→ Phase 5 (Copilot: correct-answer + refusal, minimum viable, test set run)
→ Phase 6 (integration of just this critical slice)
→ Phase 7 (refusal test finalized + at least a partial scale test)
→ Phase 8 (deployed, submission-ready)
```

Everything else in `FEATURE_REGISTRY.md` (Network beyond co-accused, Similarity, Pattern/Trend, Kannada, Voice, Financial stub, Forecasting alert, full RBAC) is **off the critical path** — valuable for score, not required for a working demoable core. If time runs short, cut from the outside in (Financial stub and Forecasting alert first, per their own Finals-only labeling in `FEATURE_REGISTRY.md`), never cut the Clock Engine, Escalation trigger, or refusal gate.

---

## Parallel Work Streams (organized by engineering lane, not headcount — see `DECISION_LOG.md` D12)

Before Phase 2 is frozen, **do not parallelize feature work** — only Lane 4 (Sujal, owns Repository Architecture and API Contracts) should be driving schema decisions, with the other lanes on Phase 0/1 foundation tasks, to avoid the two-people-guessing-differently rework risk named at the top of this document.

After schema freeze (post-Phase 2), four independent, non-conflicting streams:

| Lane | Stream | Touches |
|---|---|---|
| Lane 1 — Backend Core | Clock Engine → Dependency Tracker → Escalation Engine → Backend APIs, Auth, Database (incl. Catalyst Data Store spike) | `backend/app/core/clock/`, `backend/app/core/dependency/`, `backend/app/core/escalation/`, `backend/app/core/auth/`, `shared/constants/` |
| Lane 3 — Graph Intelligence | Aggregation, Similarity, Pattern/Trend, Risk Analysis, rule-based Forecasting alert | `backend/app/core/graph/` |
| Lane 2 — Frontend | Layout/routing/design system + Worklist + Rollup + Dashboard screens (against a documented mock contract until Lane 1's real API lands) | `frontend/` (excluding Case Detail's AI-dependent parts) |
| Lane 4 — AI + Architecture + Integration (Sujal) | Synthetic data generator, Conversational/NL layer, refusal-gate test set, API Contracts, Catalyst AppSail + QuickML spikes, CI/CD, cross-lane integration and merge review | `synthetic_data/`, `backend/app/core/copilot/`, `backend/app/catalyst/`, `shared/contracts/`, `deployment/`, `.github/`, `docs/` |

**Merge-conflict risk points:** Lane 1 and Lane 3 both touch graph query patterns — agree on a shared query-helper interface before splitting, don't let both write ad hoc graph traversal code independently (Lane 4 arbitrates this contract, per its Repository Architecture ownership). Lane 2's mocked API contract must match Lane 1's real API contract exactly — write the contract down (even informally, reviewed by Lane 4) before Lane 2 starts building against it, to avoid late reconciliation.

If Lane 4 becomes blocked, Lane 1 becomes backup reviewer for API contracts and integration.

---

## Implementation Order (Numbered, Through MVP)

```
001  Initialize git repository, folder structure per README.md
002  Configure linting, formatting, type-checking (backend + frontend)
003  Configure environment variable handling (.env pattern)
004  Set up consolidated CI pipeline (ci.yml)
005  Build one dummy backend endpoint
006  Build one dummy frontend page calling that endpoint
007  Deploy both to Zoho Catalyst
008  Verify deployment works from a clean machine / second team member
009  Record actual Catalyst capabilities (storage type, graph/recursive query support) in TASK.md
010  If Catalyst capability contradicts ARCHITECTURE.md's storage assumption, update ARCHITECTURE.md and log in DECISION_LOG.md now
011  Build centralized config loader
012  Build structured logging
013  Build centralized error-handling pattern
014  Build reusable input validation pattern
015  Build constants module incl. offence-category clock-mapping table skeleton, marked [UNVERIFIED]
016  Verify BNSS section numbers against actual statute text; update markers to [VERIFIED] or leave [UNVERIFIED] with reason
017  Build 3-role auth skeleton (IO/SHO/SP) with role-check middleware
018  Write unit tests for validation and error handling
019  Design and freeze graph node/edge schema per ARCHITECTURE.md
020  Implement node/edge models against Catalyst's confirmed storage pattern (backend/app/db/)
021  Write migration/creation scripts
022  Build synthetic data generator (deliberate repeat entities, deliberate stale dependencies, deliberate offence-category variety)
023  Run generator to produce ~500–1,000 seed records
024  Manually verify at least one genuine cross-case person link exists in seed data
025  Freeze schema; any future change requires a DECISION_LOG.md entry
026  Build Legal Clock Engine (offence category → clock(s), days-remaining)
027  Write Clock Engine unit tests incl. missing-mapping edge case
028  Build Dependency Tracker (CRUD, staleness computation)
029  Build Escalation Rule Engine (deterministic trigger, correct-rank routing, audit log write)
030  Write Escalation Engine tests against seeded data, confirm reproducible trigger
031  Build Aggregation Layer in graph module (pattern/trend grouped queries, rule-based trend-alert)
032  Build Similarity Function in graph module (structured feature match, returns shared attributes)
033  Build API layer: worklist endpoint, case detail endpoint, escalation endpoint (minimum for critical path)
034  Apply auth middleware to all endpoints
035  Begin frontend layout/routing/design system against a documented mock API contract
036  Build Case Detail screen (clock badges, dependency panel) against real API
037  Build Risk-Ranked Worklist screen against real API
038  Build Conversation history panel shell + PDF export (no AI dependency yet)
039  Extend API layer: network (co-accused) endpoint, similarity endpoint, pattern/rollup endpoint
040  Build Network tab, Similarity tab, District/Pattern Rollup screen, Escalation Queue view
041  Draft refusal-gate test set (10–15 questions, answerable + ambiguous) in backend/tests/refusal_testset/
042  Build NL → structured query grounding layer against the real, stable API
043  Build deterministic verification/refusal gate in copilot module
044  Build path-annotated response formatting
045  Wire Copilot box (from step 036) to real responses
046  Run the refusal-gate test set; record pass rate in TASK.md
047  If pass rate is inadequate, tune the gate's threshold toward caution (bias against under-refusal), retest
048  Integrate all modules end-to-end; walk the full demo flow manually
049  Fix interaction bugs found in 048 (revert-first, diagnose-second per EXECUTION_RULES.md)
050  Extend synthetic data generator to ~1–2 lakh records for scale testing
051  Run scale test against core queries (worklist, escalation check, similarity, copilot grounding); record real latency numbers in TASK.md
052  Rehearse the live threshold-crossing escalation moment multiple times with a non-builder observer
053  Run manual QA: attempt to break the refusal gate and escalation trigger deliberately
054  Harden deployment: separate prod/dev environment variables, confirm audit log persists correctly in deployed environment
055  Verify fresh deployment from a clean clone, following only README.md
056  Confirm all submission deliverables present (Prototype Brief, GitHub, Catalyst Deployment, Demo Video, Deck) per PROTOTYPE_SUBMISSION_GUIDE.md
057  Final self-review against EXECUTION_RULES.md's anti-hallucination checklist across all user-facing copy and deck claims
```

Steps beyond 057 (Kannada wrapper, voice I/O, financial stub, forecasting alert, full RBAC) are Finals-scope per `FEATURE_REGISTRY.md` and are explicitly not required for MVP completion.

---

## Self-Review — Challenging This Plan

**Bad ordering found and corrected:** An earlier draft of this reasoning placed deployment (Phase 8) at the very end, matching the phase-number ordering in your prompt structure. This was corrected: a minimal deployment happens in Phase 0 (step 007) specifically because `ARCHITECTURE.md` already states "deploy early" as a philosophy, and because Catalyst's real capabilities are unverified — discovering a deployment blocker at the literal end of the project (original Phase 8 position) would be the worst possible time. Phase 8 as written above is deployment _hardening_, not first deployment.

**Hidden dependency found:** The Copilot (Phase 5) implicitly depends on the API layer's query shape being stable, which itself depends on the Aggregation and Similarity modules being done, not just the Clock/Dependency/Escalation modules. Step 039 (extending the API) is placed explicitly before step 042 (grounding layer) to make this dependency visible in the numbered list, rather than leaving it implicit.

**Unnecessary work identified and removed:** An initial version of this plan included building full ABAC in the Foundation phase "since auth needs to exist anyway." This is removed — `FEATURE_REGISTRY.md` explicitly scopes MVP to 3 shallow roles; building ABAC now is scope creep into Roadmap territory and directly violates `EXECUTION_RULES.md`'s instruction not to scope-creep.

**Possible simplification:** Steps 031–032 (Aggregation, Similarity) could be deferred entirely past the critical path if time is short, since they're explicitly off-critical-path per the Critical Path section — the numbered list above includes them inline for completeness, but a team under time pressure should feel free to skip straight from step 030 to step 033 (API layer, critical-path endpoints only) and return to 031–032 only if time remains.

**Remaining risk this plan cannot fully eliminate:** Entity resolution quality (flagged throughout `PROJECT_CONTEXT.md` and `ARCHITECTURE.md`) depends on synthetic data design quality (step 022), which depends on human judgment about what "realistic messiness" looks like — no amount of process ordering removes this risk, it only ensures the risk is visible and tested (step 024) rather than silently assumed away.

**Verdict on the plan itself:** This ordering minimizes rework by freezing the schema before parallelizing, de-risks deployment before feature work begins, and places the two most-neglected items (refusal-gate test, scale test) as named, checkable gates rather than end-of-project hopes — directly countering this team's documented D9 failure pattern rather than just hoping it doesn't recur.

Never build a workaround for Catalyst until the Catalyst service itself has been tested.
Always spike first.
Then architect.
Never architect from documentation alone.

Catalyst Validation Checklist:
□ Data Store
□ QuickML
□ SmartBrowz
□ Zia Voice
□ Authentication
□ AppSail
□ Web Hosting
□ Cron
□ Storage

Each spike must answer:
Supported?
Limitations?
Workaround?
Use?
Skip?
Owner?
Decision?
