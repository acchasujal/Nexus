# DECISION_LOG.md

Every major decision made in developing this product, so future work (human or AI) doesn't re-litigate settled questions without new evidence. Ordered chronologically by when the decision was reached in the project lifecycle.

---

### D1 — PS1 over PS2

**Problem:** Choose between PS1 (Conversational AI for Crime Database) and PS2 (Crime Analytics & Visualization Platform).
**Alternatives considered:** PS2 initially looked lower-competition based on a single observed low-star public repo — this evidence was later explicitly retracted as too weak (one repo isn't a proven competitive landscape).
**Chosen approach:** PS1, anchored on statutory-deadline tracking as the core differentiator rather than generic NL2SQL.
**Reason:** PS2's problem shape (hotspot dashboards) has direct public precedent from a prior KSP-hackathon-family winner, making it a more saturated space than initially assumed. PS1 allows a legally-grounded, harder-to-research differentiator (BNSS deadline tracking).
**Trade-offs:** PS1 as literally stated is chatbot-shaped, which is easy to imitate at a surface level; the deadline-tracking mechanism underneath is the actual moat.
**Lessons learned:** Weak single-data-point evidence (one repo) should not drive a strategic pivot; this was caught and corrected before being finalized.

---

### D2 — Reject single composite "risk score" for dependency tracking

**Problem:** How should case risk be computed and displayed?
**Alternatives considered:** A single opaque composite score (days-remaining × evidence-completeness % × caseload factor).
**Chosen approach:** Named, specific dependencies (FSL/CDR/statement/sign-off) mapped to the specific clock each threatens.
**Reason:** A composite score doesn't survive a knowledgeable judge asking "risk of what, exactly, and why is it high?" A named-dependency view does. Also more accurately reflects how an IO actually reasons about a case.
**Trade-offs:** Named-dependency modeling is more complex to build convincingly than a single score; if it proves too complex, the fallback is the simpler single-clock/single-score version.

---

### D3 — Multiple concurrent statutory clocks, not one

**Problem:** Initial design assumed a single 60/90-day chargesheet clock per case.
**New evidence:** Deeper BNSS research revealed multiple, distinct, concurrent clocks: pre-FIR preliminary inquiry (14 days, offence-conditional), investigation/chargesheet clock (60/90 days), document-supply-to-accused clock (14 days post-filing, Section 230), further-investigation clock (90 days, Section 193(9)).
**Chosen approach:** Model clocks as a configurable rules table keyed by offence category, supporting multiple concurrent `ClockInstance` records per case.
**Reason:** A product only tracking the single most-cited clock looks naive to a legally literate judge or prosecutor who knows the other clocks exist.
**Known limitation:** Exact section number for the default-bail trigger is inconsistently cited across secondary sources (176(2) vs 187(2) BNSS) — flagged as unverified, must be checked against bare statute text before final submission.

---

### D4 — Unified investigation graph over parallel feature modules

**Problem:** Official PS1 brief requires network analysis, pattern discovery, socio-demographic insight, profiling, decision support, financial-link analysis, forecasting — risk of building each as an independent system.
**Chosen approach:** One property graph (Case, Person, Section, Location, Officer, Dependency, ClockInstance as nodes) where every mandated capability is a query/traversal over the same structure.
**Reason:** Directly counters this team's documented recurring failure mode across prior hackathons (mock/parallel systems that don't fully integrate — see D9). Also structurally guarantees internal consistency: a chatbot and a network view built on separate stores can silently disagree; a single graph cannot.
**Trade-offs:** Requires disciplined engineering to resist "just add a separate table for speed" under deadline pressure — explicitly called out as the most likely future mistake.

---

### D5 — Honest labeling over full-coverage claims for financial-link analysis and forecasting

**Problem:** Official brief explicitly requires financial-transaction link analysis and crime forecasting/early warning; organizer-provided schema contains neither financial entities nor sufficient data for real forecasting.
**Chosen approach:** Build both as clearly-labeled, minimal stubs — synthetic `FinancialAccount`/`Transaction` nodes explicitly stated as "not real KSP data," and a rule-based threshold alert explicitly stated as "not a predictive ML model."
**Reason:** Claiming full depth on capabilities the actual schema can't support is a bigger credibility risk than honestly scoping them down — a judge's follow-up question ("is this real data?") is a single-question path to destroying trust in every other claim made in the demo.
**Rejected alternative:** Silently building a convincing-looking but fabricated financial network graph without labeling it — rejected as the single most damaging possible mistake identified across all planning rounds.

---

### D6 — Rule-based similarity and profiling instead of embedding/ML-based

**Problem:** How should case-similarity and offender-profiling features work?
**Chosen approach:** Structured feature match (shared section/location/time-window) for similarity; templated summary of graph-derived facts (prior FIR count, section diversity) for profiling — never free-generated prose about a person.
**Reason:** Preserves explainability (every result traces to specific shared attributes) and avoids the fairness/defamation exposure of an LLM generating claims about a specific person's risk or guilt.
**Trade-offs:** Lower recall than an embedding-based approach; deliberately accepted given the judging panel's stated emphasis on explainable AI.

---

### D7 — Refusal-gate testing is mandatory before any demo claim about it

**Problem:** The conversational layer's refusal-on-low-confidence behavior is central to the product's trust narrative, but has never been tested against a real question set.
**Decision:** No demo claim about refusal reliability may be made until a held-out test set (10–15 questions, answerable + ambiguous) is run and scored.
**Status:** **Unresolved as of this writing** — flagged repeatedly across planning sessions, not yet executed. This is the single most-repeated open item in the project's history.

---

### D8 — Scale test against 1–2 lakh records is mandatory before any scalability claim

**Problem:** Organizer explicitly states solutions should handle 1–2 lakh records without breaking; no load test has been run.
**Decision:** No scalability claim (in deck, pitch, or documentation) may be made until this test is actually executed with a measured latency figure.
**Status:** **Unresolved as of this writing** — flagged across multiple planning sessions.

---

### D9 — Root-cause pattern: overbuilt pipelines and mock-mode fallbacks under deadline pressure

**Problem:** Across this team's prior hackathon submissions (HackerRank Orchestrate — non-importable pipeline, circular mock evaluation logic; MuleShield — metric overclaiming later corrected; ConflictSense — mock Azure AI Search layer discovered on live repo inspection; Infosys audit — discrepancy between claimed real dataset and synthetic generator found in repo), a consistent failure pattern emerges: ambitious architecture claimed, incomplete or faked execution delivered under time pressure.
**Decision:** This documentation system (`EXECUTION_RULES.md` anti-hallucination rules, explicit MVP/Finals/Roadmap labeling throughout `FEATURE_REGISTRY.md`) exists specifically as a structural countermeasure to this pattern, not as generic engineering hygiene.
**Implication for future work:** Any claim in code, docs, or the deck that isn't verifiably true of the actual current build should be treated as a defect to fix immediately, not a cosmetic issue.

---

### D10 — Cross-case pattern-linkage "AI copilot" explicitly excluded, even from roadmap

**Problem:** A tempting "wow factor" addition — an AI feature that infers links between unrelated cases/suspects.
**Decision:** Excluded even as a stated future roadmap item, not just deferred.
**Reason:** The legal and reputational downside of a false suspect/case linkage generated by an LLM vastly outweighs demo value; this is the single feature most likely to be misused or successfully challenged by a prosecutor in a real deployment context.

---

### D11 — Wow-moment demo design: pair deterministic escalation with a scripted (not open-floor) refusal demonstration

**Problem:** Selecting the single highest-impact demo moment.
**Alternatives considered:** Inviting judges to ask an unscripted live question (highest emotional ceiling, highest uncontrolled risk given D7's unresolved status).
**Chosen approach:** A live, staged threshold-crossing escalation immediately followed by a scripted correct-answer-then-refusal pair on the same case/screen.
**Reason:** Demonstrates the product's actual stated philosophy (deterministic where possible, honestly uncertain where not) in under 30 seconds, without exposing an untested refusal gate to fully unscripted input.
**Contingency:** Revisit the open-floor version only after D7 is resolved with a passing test score.

---

### D12 — Engineering organization: four lanes, not developer headcount

**Problem:** Prior planning phase (`ENGINEERING_OPERATING_MANUAL.md` Task 6) split ownership across 3 developers, contradicting `PROJECT_CONTEXT.md`'s stated 4-person team — an unresolved contradiction flagged but not fixed at the time.
**Alternatives considered:** (a) Fix the headcount mismatch by simply adding a 4th named-developer lane matching the original Person A–D split from `IMPLEMENTATION_PLAN.md`'s earlier parallel-work-streams table. (b) Reorganize entirely around function (lane) rather than name, with AI and Integration merged under one owner.
**Chosen approach:** (b) — four engineering lanes: Backend Core, Frontend, Graph Intelligence, AI + Architecture + Integration (the last owned by Sujal).
**Reason:** AI and Integration are unusually tightly coupled in this architecture — the conversational layer's grounding depends on stable contracts from every other lane, and integration bugs are most diagnosable by whoever also owns the AI layer's expected inputs/outputs. Merging them under one owner reduces coordination overhead and directly targets D9's failure pattern (disconnected pipelines), since the integration owner is structurally forced to understand every other lane's output, not just their own.
**Trade-offs:** Lane 4 (Sujal) now sits on the critical path for two of the three remaining Catalyst spikes (AppSail, QuickML) plus all cross-lane integration — a concentration-of-risk trade accepted deliberately in exchange for reduced drift, not an oversight. If Lane 4 falls behind, there is no equivalent backup owner for integration review.
**Consequences:** `ENGINEERING_OPERATING_MANUAL.md` Task 6, `IMPLEMENTATION_PLAN.md`'s Parallel Work Streams table, and `TASK.md`'s ownership tracking are all updated to lane-based assignment in the same session this decision was made, per `EXECUTION_RULES.md`'s documentation-update rule.
**Known limitation:** This resolves the 3-vs-4 contradiction structurally but does not by itself reduce total engineering risk — it relocates coordination risk from "ambiguous ownership" to "single point of failure in Lane 4," which is a different risk, not a smaller one.

---

### D13 — Migration from Long-Lived Lane Branches to GitHub Flow

**Problem:** Long-lived lane integration branches (`lane1`–`lane4`) introduce significant merge conflict risks during final integration phases, create redundant PR hops, and diverge over time as different lanes complete features.
**Alternatives considered:** 
1. Maintain the 4 long-lived lane branches and perform periodic weekly synchronization merges.
2. Traditional Git Flow with a `develop` branch.
3. Git Flow with direct task merges into lane branches and lane merges to develop.
**Chosen approach:** GitHub Flow directly to `main` with short-lived feature branches (`lane{N}/task-name`).
**Reason:** Direct merges to `main` (backed by status-checked consolidated CI) enforce continuous integration, preventing "big-bang" integration conflicts in the final week. Task branches remain short-lived (under 2 days), encouraging rapid cycles, clear scope, and immediate regression visibility.
**Trade-offs:** Puts higher emphasis on the reliability of the consolidated CI pipeline on the `main` branch. A broken `main` is visible to all developers, but mitigated by a strict "revert first, diagnose second" recovery strategy.

---

### D14 — Adopt QuickML as intent parser only; explicitly exclude it from legal reasoning

**Problem:** Phase 0 required a Catalyst QuickML capability spike before the AI architecture could be finalized. The spike was completed (see `docs/spikes/quickml.md`) and resulted in a concrete architectural decision, but was never logged here as required by `EXECUTION_RULES.md`.
**Spike findings (repository-backed):** Model: GLM-4.7-Flash at Temperature=0.0, Thinking disabled. Passed: structured JSON output, entity extraction, Kannada queries, prompt injection resistance, safety refusals with schema-constrained prompt. Failed without constraints: invented unsupported fields (hallucination). API stability concern: observed HTTP 400/500 errors during Playground testing — root cause unverified.
**Chosen approach:** Adopt QuickML exclusively for natural language → structured intent parsing (intent extraction, entity extraction, structured query generation). Explicitly prohibit QuickML from performing legal reasoning, BNSS calculations, deadline computation, graph traversal, database execution, guilt determination, or prediction.
**Reason:** Sufficient for the scoped role; deterministic backend handles all decision logic, keeping the architecture's core explainability guarantee intact. Temperature=0.0 + strict schema prompt produces reliable, parseable output.
**Trade-offs:** API stability is still unverified under backend integration load — this is a documented open risk requiring the next spike (Tool Calling, API Integration, Load & Latency per `docs/spikes/quickml.md`'s Next Spikes section). Do not build the full copilot pipeline until API stability is confirmed under real request volume.
**Known limitation:** RAG, Knowledge Base, Tool Calling, and Vision models were explicitly not evaluated in this spike and remain unverified.

---

### D15 — Graph schema v1.1: add Evidence node beyond original ARCHITECTURE.md conceptual list

**Problem:** `ARCHITECTURE.md`'s conceptual node type list did not include `Evidence` as a named node type. During Lane 3 graph foundation implementation, `Evidence` was added as a first-class node (`entities.py`, `enums.py`, `graph_schema.py` version 1.1) with a `CASE_HAS_EVIDENCE` stored edge, and the synthetic data spec (`docs/graph-intelligence/SYNTHETIC_DATA_SPEC.md`) was designed to generate 1000 evidence records.
**Reason:** Evidence items (FSL reports, CDR analyses, device records, documents) are a primary blocker category for the Dependency Tracker feature and are referenced explicitly in `FEATURE_REGISTRY.md` #2. Modeling them as a separate node rather than collapsing them into Dependency keeps the two concepts distinguishable and enables separate evidence-completeness queries.
**Consequence:** `ARCHITECTURE.md`'s conceptual node list is now slightly behind the implementation. This is intentional — `ARCHITECTURE.md` is explicitly labeled "conceptual only" — but implementors should treat the code (`entities.py`, `graph_schema.py` v1.1) as the authoritative node-type list, not the prose in `ARCHITECTURE.md`.
**Status:** No change to `ARCHITECTURE.md` prose required (it already states "conceptual only, implementation may differ"); this log entry is the authoritative record of the delta.

---

### D16 — Primary clock selection rule for CaseSummaryResponse

**Problem:** `shared/contracts/api.py` defines `CaseSummaryResponse.clock` as a single `ClockInstanceResponse` (singular), but a case may have multiple active `ClockInstance` nodes (e.g., the primary investigation clock plus a concurrent document-supply clock). Without a defined rule for which clock populates the worklist field, Lane 1 (backend query) and Lane 2 (frontend display logic) will independently invent different selection strategies and produce inconsistent risk rankings.

**Decision:** The primary clock for `CaseSummaryResponse.clock` is the `ClockInstance` with the lowest `days_remaining` value among all active (non-OVERDUE) clocks for that case. If all clocks are OVERDUE, select the one with the most negative `days_remaining` (most overdue). If only one clock exists, use it.

**Reason:** The worklist is a risk-ranked view; the most-urgent active clock drives the risk rank. Using the most-negative value for the all-overdue case keeps the ordering monotonically useful.

**Implementation note:** The backend query (Lane 1) must apply this rule server-side before returning the worklist. The frontend (Lane 2) must not re-implement its own primary-clock selection — it must display exactly what the backend returns in the `clock` field.

**Contract impact:** No change to `shared/contracts/api.py` — `CaseSummaryResponse.clock` remains a single `ClockInstanceResponse`. This decision documents the selection rule, not a contract change.

---

### D17 — Verified Legal Sections and Duration for Clocks

**Problem:** Clock references and durations for the statutory clocks in `shared/constants/clock_types.py` were previously unverified and contained stub values (e.g. 30 days for document supply). Legal inaccuracies could compromise the validity of the Case Clock calculations and system integrity.

**Decision:** Researched and verified the bare act text of the Bharatiya Nagarik Suraksha Sanhita (BNSS), 2023. We updated the clock rules and marked them `[VERIFIED]`:
- **Default Bail**: Section 187(3) BNSS, which mandates 90 days for serious offences (death, life, or >=10 years imprisonment) and 60 days for other offences.
- **Document Supply**: Section 230 BNSS, which mandates a strict limit of 14 days from date the accused is produced or appears in court (previously mapped as 30 days).
- **Further Investigation**: Section 193(9) BNSS, which mandates a 90-day completion limit for further investigation (previously mapped as 30 days).

**Reason:** True compliance with BNSS requires using exact statutory durations and legal citations. Assuring this correctness protects the credibility of the platform with the judging panel and future government purchasers.

**Contract impact:** Updated the durations and reference strings inside `shared/constants/clock_types.py`. Updated existing test assertions to match.

---

### D18 — Long-Term Hackathon Branch Strategy Migration

**Problem:** Inconsistent and redundant branches (like empty duplicates and old lane branches) created coordination overhead and threatened git history hygiene.

**Decision:** Formally migrated the repository branch strategy to a structured Git Flow:
- **`main`**: Permanent branch representing production-ready, stable code.
- **`develop`**: Permanent branch representing continuous integration.
- **Feature Branches**: Domain-scoped, short-lived branches created from `develop` and merged back to `develop` via PRs:
  - `feature/backend-*`
  - `feature/frontend-*`
  - `feature/graph-*`
  - `feature/ai-*`

All obsolete branches (`feature/backend-clock-engine`, `feature/catalyst-spikes`, `feature/copilot-parser`, `feature/frontend-shell`, `feature/graph-algorithms`, `lane3-graph-foundation`) were verified as fully merged, cleaned of junk/committed dependencies (like `node_modules`), and deleted locally and remotely.

**Reason:** Keeps history clean and provides isolated environments for the 4 developer lanes without "big bang" merge conflicts.

**Contract impact:** None. Git metadata update only.

---

### D19 — Deterministic and Explainable Entity Resolution Engine

**Problem:** Near-duplicate persons (e.g., spelling differences like Gowda/Gauda, Amit Sharma/Amit Sarma, or formatting differences in phone numbers like +91-9876543210/9876543210) created false negatives in the Criminal Network Analysis, Case Similarity, and Repeat Accused detection engines.

**Decision:** Developed a lightweight, fully deterministic, and explainable Entity Resolution (ER) module at [entity_resolution.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/entity_resolution.py):
- **Normalization**: Strips casing, excessive spacing, and non-alphanumeric punctuation.
- **Phonetic Mapping**: Handles sound-alike variations common in Indian names (e.g., mapping vowel variations "ee"/"oo"/"au"/"ou" and consonant patterns like "sh"->"s", "w"->"v", "y"->"i", "gh"->"g", "ng"->"n", and ignoring non-initial "h").
- **Alias Resolution**: Queries aliases/nicknames associated with Person records.
- **Similarity Scoring**: Computes character bigram Jaccard similarity.
- **Phone Suffix Matching**: Matches last 10 digits of phone numbers to bypass country code differences.
- **Address Boost**: Elevates confidence of name match if the address Jaccard similarity is high.
- **Low Confidence Refusal**: Matches below a threshold (`0.70`) return as manual candidates rather than linking automatically.
- **Explainability**: Every match returns a `ResolutionMatch` detailing matched fields and a human-readable reason.

**Reason:** Explanatory judicial systems demand transparent audit logs. Pure deterministic bigram and phonetic rules avoid the hallucination risk of LLM fuzzy matching, perform efficiently at O(N) without external API dependencies, and set a clean grounding framework for future QuickML integration.

**Contract impact:** Exposes `resolve_person` and `jaccard_similarity` in `backend/app/core/graph/algorithms/__init__.py`. Integrates with Case Similarity and Pattern Detection. Added full suite of unit tests.

---

### D20 — Graph Intelligence Architectural Pattern

**Problem:** Standardizing the backend data flow to prevent duplicate abstractions, avoid circular dependencies, ensure explainability, and maintain isolation between database logic and pure graph algorithms.

**Decision:** Formulated and implemented the following architectural principles:
- **Unified GraphStore**: Built a simple, memory-efficient [GraphStore](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/utils.py) that acts as the single source of truth for the investigation graph, avoiding fragmented storage models.
- **Data Pipeline Flow**: Standardized the flow strictly as: [GraphRepository](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/repositories/graph_repository.py) &rarr; [GraphLoader](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/graph_loader.py) &rarr; `GraphStore` &rarr; Services &rarr; Algorithms.
- **Database Isolation**: Graph algorithms are completely decoupled from database mechanics; they operate solely on the in-memory `GraphStore`.
- **Ownership Separation**: 
  - [GraphRepository](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/repositories/graph_repository.py) owns raw data queries and staging into memory.
  - [GraphLoader](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/graph_loader.py) owns graph index construction and referential validation.
- **Orchestration-Only Services**: Services are thin layers that perform orchestration, invoke core algorithms, and serialize domain models into JSON-friendly formats.
- **Deterministic Algorithms**: All analytical and traversal algorithms are completely deterministic and rule-based to ensure absolute explainability for legal auditing.
- **DTO Serializers**: [serializers.py](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/serializers.py) acts as a clean Data Transfer Object (DTO) mapping layer, ensuring services return serializable python dictionaries instead of raw graph objects.
- **Consolidated Pattern Detection**: Intentionally avoided introducing a redundant `PatternDetectionService`. Instead, pattern detection algorithms are owned by the [pattern_detection](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/algorithms/pattern_detection.py) module and orchestrated directly by [HotspotService](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/hotspot_service.py) and [OffenderService](file:///c:/Users/dyara/CaseClock/backend/app/core/graph/services/offender_service.py) to prevent code duplication.

**Reason:** Promotes high coherence, low coupling, and predictable memory patterns. Keeps the API responses uniform and isolates high-frequency graph traversals from blocking database operations.

**Contract impact:** None. Backend internal structure alignment only. Exposes new route mappings and unit testing coverage across all integrated modules.

