# NEXUS — Prototype System Design and Team Execution Plan

**PS 26189 | Internal Hackathon | V1.0**

A non-overlapping six-member plan to convert the existing CaseClock codebase into an evidence-first criminal network intelligence prototype.

> **Prototype Win Condition:** In one controlled demo, two apparently separate cases become a source-backed connected network after an investigator reviews one entity match. Every insight remains explainable, clickable, and auditable.

| Project | Source Baseline | Delivery Window |
|---|---|---|
| NEXUS / PS 26189 | CaseClock @ `214f9f2` | PPT: 26 Aug 2026, 09:00 · Demo: 29 Aug 2026 |

**Scope note:** This document covers the internal-hackathon prototype only. It deliberately excludes production integrations, real police data, predictive guilt scoring, blockchain, face recognition, and any claim not visible in the code, demo, or measured test output.

### How to use this plan
1. M1–M4 execute only their assigned code boundary and publish the listed contract outputs.
2. M5 validates every factual or benchmark claim; M6 owns the master deck, demo choreography, and submission package.
3. A feature enters the PPT only after its acceptance gate passes. If it slips, delete its slide and demo step.
4. The three protected wow factors are **Entity Fusion**, **Before/After Network Diff**, and the **Click-any-link Evidence Drawer**.

---

## 1. Executive Prototype Decision

> **Decision:** Do not rebuild CaseClock. Reuse its FastAPI, React, React Flow, NetworkX, OCR review, auth/audit scaffolding, and synthetic-data foundation; replace the deadline-centric story with a narrow NEXUS network-intelligence golden path.

### The Single Golden Path
1. Open two disconnected synthetic case files.
2. Import one FIR/report fixture, one CDR CSV, and one transaction CSV.
3. Show extracted people, phones, accounts, locations, and source records.
4. Review one ambiguous alias match; confirm it with visible reasons and conflicts.
5. Replay the network before and after confirmation; the two components join.
6. Surface a cross-case bridge lead plus three explainable pattern findings.
7. Click a relationship to open its exact source row/document, timestamp, confidence, and derivation label.
8. Ask how the cases connect; return the graph path with evidence citations, then accept or reject the lead.

### Protected Wow Factors

| Wow Factor | Judge Moment | Why It Is Defensible |
|---|---|---|
| **1. Entity Fusion** | The investigator confirms an alias; the network updates immediately. | Human-in-the-loop decision, reasons/conflicts, raw-source preservation, and audit event. |
| **2. Network Diff** | Before/after replay reveals the bridge between cases. | Two deterministic snapshots; no vague black-box animation or unsupported prediction. |
| **3. Evidence Drawer** | Any edge opens its provenance and classification. | Every displayed link must carry `source_record_id` plus Fact / Derived / Hypothesis. |

### Prototype Success Targets
- **Traceability:** 100% of demo-visible relationships open at least one valid source record.
- **Resolution:** every labeled match and non-match in the golden fixture is decided correctly; show counts as well as percentages.
- **Network intelligence:** the planted bridge person ranks in the top three bridge results and its explanation names the connected components/cases.
- **Copilot grounding:** every connection answer contains node/edge evidence IDs; unsupported questions are refused or redirected.
- **Demo performance:** complete the golden path in at most three minutes on the presentation laptop with a local fallback fixture.

> **Measurement rule:** Targets are not results. M5 replaces them with actual measured values only after the integration build is frozen.

---

## 2. Existing Codebase: Reuse, Modify, Remove From The Story

The repository is a strong technical foundation but its current product story is case deadlines and operational escalation. The prototype wins by making a small number of high-impact modifications rather than presenting existing screens as criminal-network analysis.

| Current Asset | Keep / Modify | Prototype Change |
|---|---|---|
| FastAPI services + repository adapters | KEEP | Add stable NEXUS endpoints and reuse dependency injection; do not migrate databases. |
| NetworkX graph core + paths/centrality | MODIFY | Add first-class Phone, Account, Vehicle, Event, Organization, and SourceRecord plus person-only bridge/community intelligence. |
| React Flow case network panel | MODIFY | Create a global explorer with layer filters, two-state time replay, pathfinder, and edge evidence inspection. |
| OCR/document review + synthetic generator | MODIFY | Add one controlled FIR/CDR/transaction ingestion path and a labeled cross-district golden scenario. |
| Auth, principal, and audit scaffolding | KEEP + EXTEND | Protect graph reads/decisions and log resolution, lead, evidence, and copilot actions. Label demo auth honestly. |
| Patterns page | REPLACE IN STORY | Remove deadline dashboards from the demo route; show explainable network findings and cross-case leads. |
| Header search + timeline | FIX | Enable real entity/case search and derive timeline/network snapshots from imported records, not fixed dates. |
| Multiple copilot paths | CONSOLIDATE | Expose one evidence-grounded connection assistant; deterministic path explanation is the fallback. |

### High-Priority Modification Master List

| ID | Modification | Minimum Prototype Scope | Owner | Gate |
|---|---|---|---|---|
| P0-1 | Golden synthetic investigation | Two cases, three source types, one alias ambiguity, one planted bridge, known ground truth. | M2 | Fixture reset completes and reproduces the same graph. |
| P0-2 | Graph schema v2 | First-class investigative entities, source lineage, temporal edges, confidence and derivation class. | M1 | Schema contract and projection tests pass. |
| P0-3 | Entity Fusion | Candidate compare, reasons/conflicts, confirm/reject/defer, deterministic graph update. | M2 + M3 + M4 | One golden alias can be reviewed end to end. |
| P0-4 | Global Network Explorer | Type/layer filters, case focus, two-state network diff, person bridge score, communities. | M1 + M4 | Before/after state visibly joins the planted networks. |
| P0-5 | Evidence-first relationships | Every edge exposes raw source, timestamp, confidence and Fact/Derived/Hypothesis label. | M3 + M4 | No demo-visible orphan edge. |
| P0-6 | Explainable lead workflow | Cross-case bridge, three rule findings, pathfinder, grounded answer, accept/reject with audit. | M1 + M3 + M4 | One lead is explainable and decision-ready. |
| P0-7 | Prototype validation | Resolution truth set, traceability audit, graph expectation tests, local latency and demo timing. | M5 | Metrics artifact is generated from the frozen build. |
| P0-8 | Winning submission | Modification-only deck, three-minute demo, fallback capture, claim-to-code register. | M6 | Every slide has code/demo evidence and a named owner. |

### Explicitly Outside The Internal Prototype
- Live CCTNS/ICJS/NCRB integration, production identity federation, or deployment inside a government network.
- Real FIR/CDR/financial data, social-media scraping, face recognition, surveillance ingestion, or mobile interception.
- GNNs, crime prediction, guilt/mastermind scores, autonomous alerts, or automated adverse decisions.
- Blockchain, streaming pipelines, Neo4j migration, multi-tenant scaling, full multilingual NLP, map intelligence, or a generic chatbot.

---

## 3. Prototype System Design and Ownership Flow

The architecture is deliberately linear. Each coding member produces one typed handoff consumed by the next layer. Human review loops through M3's audited decision service; no UI component writes directly to graph storage.

```
 M2                M1                  M3                  M4
DATA TRUST  →  GRAPH INTEL     →  DECISION SVCS   →  INVESTIGATOR UI
- FIR text/PDF    - Schema v2         - Stable APIs       - Fusion review
- CDR CSV         - Bridge+community  - Evidence lineage   - Network explorer
- Transactions    - 3 explainable     - Leads+pathfinder   - Evidence drawer
- Normalize+        rules             - Grounded copilot   - Lead decision
  resolve         - Before/after diff

HUMAN LOOP: Confirm/reject match → graph updates → bridge alert → lead decision → audit
```

*Figure 1. Prototype source-to-decision architecture and non-overlapping code ownership.*

### Canonical Data Contract

| Object | Required Fields | Owner of Definition | Owner of Values |
|---|---|---|---|
| **Node** | id, entity_type, canonical_label, aliases[], attributes, confidence | M1 | M2 |
| **Relationship** | id, source_id, target_id, type, start/end time, confidence, derivation_class | M1 | M2 for facts; M1 for derived |
| **SourceRecord** | id, batch_id, source_type, locator, raw_excerpt/hash, occurred_at | M1 contract | M2 |
| **ResolutionCandidate** | left/right IDs, score, reasons[], conflicts[], status | M2 | M2 |
| **Finding** | rule_id, entity/edge IDs, explanation, evidence_ids[], severity label | M1 | M1 |
| **Lead** | finding_id, case_ids[], status, assignee, decision note, audit metadata | M3 | M3 |

### Source and Derivation Policy
- **Fact:** Directly present in an imported source record; must link to its locator and raw excerpt/row.
- **Derived:** Computed from facts by a named deterministic algorithm/rule; must cite every input relationship.
- **Hypothesis:** A human-review lead, never displayed as fact; must show why it was generated and allow accept/reject.

> **Safety language:** Use "influential/bridge entity in this dataset" and "investigative lead." Never label a person a criminal, mastermind, or high-risk individual because of a model score.

### Frozen Backend Interface for M4

| Endpoint | Prototype Contract |
|---|---|
| `POST /api/v1/nexus/ingest` | Upload/reset golden files; returns batch + extraction summary. |
| `GET /api/v1/nexus/resolution/candidates` | List unresolved candidate pairs with reasons/conflicts. |
| `POST /api/v1/nexus/resolution/{id}/decision` | Confirm/reject/defer; returns affected node IDs + new snapshot ID. |
| `GET /api/v1/nexus/network` | Global graph by snapshot, types, case IDs, and time bounds. |
| `GET /api/v1/nexus/relationships/{id}/evidence` | Return source records and derivation chain for one edge. |
| `GET /api/v1/nexus/path` | Return shortest explainable connection with evidence IDs. |
| `GET/POST /api/v1/nexus/leads` | List leads and record accept/reject decisions. |
| `POST /api/v1/nexus/copilot/query` | Grounded connection answer; deterministic fallback supported. |
| `GET /api/v1/nexus/search` | Search cases/entities for the header and pathfinder controls. |

---

## 4. Six-Member Operating Model

| Member | Primary Ownership | Exclusive Output | Does Not Own |
|---|---|---|---|
| **M1 — Shriraj** | Graph + Network Intelligence | Schema v2, projections, bridge/community metrics, three rules, snapshots/diff | Parsing, entity matching, APIs, UI |
| **M2 — Vikram** | Data + Entity Resolution | Golden fixtures, parsers, normalization, canonical mapping, resolution candidates | Graph algorithms, route orchestration, UI |
| **M3 — Sujal** | Backend + Copilot + Evidence | Stable APIs, provenance service, leads, grounded copilot, auth/audit enforcement | Extraction, match scoring, graph math, frontend |
| **M4 — Ram** | Frontend + Investigator Workspace | Explorer, fusion review, evidence drawer, lead/pathfinder flow, search | Backend rules, parsing, data persistence |
| **M5 — Vaishali** | PPT + Research + Validation | Claim register, problem evidence, benchmark protocol, actual results, technical sign-off pack | Master deck design, demo direction, coding |
| **M6 — Ananya** | PPT + Demo + Product | Scope board, narrative, master PPT, demo runbook, submission and rehearsal | Research claims, metrics computation, code ownership |

### No-Overlap Handoff Rule
1. M1 publishes the graph contract and intelligence outputs; M2 writes data that conforms to it.
2. M2 publishes canonical batches and candidate decisions; M3 exposes them through API/services without changing match logic.
3. M3 publishes a frozen OpenAPI/fixture contract; M4 consumes it through the frontend API client and never bypasses it.
4. M5 accepts only test output/screenshots signed off by the technical owner; M6 accepts only M5-validated claims into the master deck.
5. If a member must touch another boundary, the owning member reviews and merges that change. Ownership does not move silently.
6. Parallelize behind contracts, not by editing the same file; coding members should rarely resolve conflicts because their primary directories differ.

### Interface Freeze Sequence
1. M1 freezes entity/relationship enums and example graph JSON.
2. M2 freezes fixture schemas and one expected canonical output.
3. M3 freezes endpoint payloads using those examples; mocks become the frontend contract.
4. M4 builds against mocks while M1–M3 implement; integration replaces mocks without component rewrites.
5. M5 receives metrics JSON and evidence screenshots; M6 receives approved slide content and final demo build.

---

## 5. Coding Plan — M1 Shriraj

**Graph + Network Intelligence** — Make NEXUS's core intelligence genuinely impressive.

**Code boundary:** `backend/app/core/graph/enums.py`; `graph_schema.py`; `entities.py`; `edges.py`; `algorithms/*`; `services/network_intelligence_service.py` (new)

### Exclusive Feature Ownership
1. **Graph schema v2:** define Phone, Vehicle, Account, Organization, Event, and SourceRecord as first-class nodes; add temporal/confidence/derivation fields to relationships.
2. **Person-only intelligence projection:** exclude cases/evidence/source nodes from influencer math so the score reflects the social/operational network rather than data volume.
3. **Bridge score and communities:** return degree/betweenness plus a bridge explanation that names the connected cases/components; use deterministic community detection on the fixture.
4. **Three explainable rules only:** shared phone/device, communication burst near the event, and circular/repeated financial flow. Every finding returns evidence IDs and a human-readable rule explanation.
5. **Cross-case bridge finding:** emit one lead candidate when a confirmed entity or strong fact connects two case components.
6. **Two-state network snapshots:** compute pre-resolution and post-resolution graphs plus added/removed/changed IDs for M4's before/after replay.

### Deliverables

| Deliverable | Output Contract | Acceptance Test |
|---|---|---|
| `graph_contract_v2` | Enums + typed node/edge/source examples | M2 fixture validates without custom fields or coercion. |
| `intelligence_summary` | centrality[], communities[], findings[] | Known bridge appears in top three and rule output is deterministic. |
| `snapshot_diff` | before_id, after_id, added/removed/changed IDs | Golden resolution adds the planted bridge path and no unrelated delta. |
| algorithm tests | Small hand-authored graphs + golden graph | Projection excludes non-person entities; empty/singleton graphs do not fail. |

### Definition of Done
- All intelligence is deterministic on the golden fixture and can be reproduced from source-backed facts.
- Every finding includes `rule_id`, explanation, input entity/edge IDs, evidence IDs, and `derivation_class=Derived`.
- No endpoint/UI code is added by M1; service methods are callable by M3 and covered by unit tests.
- No "criminal score", "mastermind", guilt, or future-crime label exists in code or copy.

> **M1 cut line:** If time slips, keep bridge score + cross-case finding + snapshot diff. Drop the financial-cycle rule before weakening evidence traceability.

---

## 6. Coding Plan — M2 Vikram

**Data + Entity Resolution** — Make fragmented crime data usable and trustworthy.

**Code boundary:** `backend/app/core/ingestion/*` (new); `backend/app/core/resolution/*` (new); `backend/app/services/document_service.py` (adapter only); `synthetic_data/nexus/*` (new)

### Exclusive Feature Ownership
1. **Golden scenario:** two initially disconnected cases across districts; two FIR/report texts, one CDR CSV, one transaction CSV, one alias ambiguity, one shared phone/bridge, and exact ground-truth labels.
2. **Controlled parsers:** accept only the supplied FIR/report fixture format, the documented CDR columns, and the documented transaction columns. Preserve the raw row/text locator before normalization.
3. **Normalization:** canonicalize names, phone numbers, account references, vehicle registration, organization strings, locations, and timestamps without discarding the source value.
4. **Canonical mapping:** emit M1's node/relationship/source contract with stable IDs and idempotent batch re-runs.
5. **Entity-resolution candidate generator:** deterministic weighted evidence (name similarity, phone overlap, account/vehicle conflict, location/time context) with reasons and conflicts.
6. **Decision application:** confirm merges aliases into one canonical person; reject keeps entities separate; defer changes nothing. Preserve original IDs and decision history for M3 audit exposure.

### Golden Fixture Specification

| Fixture | Planted Signal | Expected Output |
|---|---|---|
| `case_A_fir.txt` | Alias, phone suffix, vehicle mention, event location | Facts + one candidate person. |
| `case_B_fir.txt` | Alternate spelling and organization mention | Second person before review; match candidate after ingest. |
| `cdr.csv` | Burst of calls around event time; shared number | Temporal CALLED/USES facts with row locators. |
| `transactions.csv` | Repeated/circular transfer pattern | TRANSFERRED_TO facts with amount/time and source rows. |
| `truth.json` | Expected canonical IDs, match/non-match labels, bridge entity | Validation oracle for M2/M5; never consumed by the app. |

### Definition of Done
- Reset + ingest produces the same IDs, counts, candidates, and raw-source locators on every run.
- The golden true match and at least one planted non-match are separated correctly, with visible reasons/conflicts.
- Every canonical fact relationship carries `source_record_id`; derived relationships are not created by M2.
- No API routes, centrality/pattern algorithms, or frontend components are added by M2.

> **M2 cut line:** If generic uploads become risky, ship three "Load demo source" actions with fixed schemas. Do not cut raw-source preservation or the confirm/reject resolution loop.

---

## 7. Coding Plan — M3 Sujal

**Backend + Copilot + Evidence** — Turn intelligence into investigator-facing decisions.

**Code boundary:** `backend/app/api/nexus_models.py` (new); `backend/app/api/nexus_routes.py` (new); `backend/app/services/evidence_service.py` (new); `lead_service.py` (new); `nexus_copilot_service.py` (new); `dependencies.py` / `audit_service.py` / `main.py`

### Exclusive Feature Ownership
1. **API orchestration:** expose the frozen ingest, resolution, network, evidence, path, lead, copilot, and search contracts without embedding M1 algorithms or M2 match logic in routes.
2. **Evidence service:** resolve edge → derivation → source records and return raw locator/excerpt, timestamp, confidence, and Fact/Derived/Hypothesis classification.
3. **Lead lifecycle:** convert M1 findings into New/Accepted/Rejected leads; record actor, note, time, and linked case/entity/evidence IDs.
4. **Grounded copilot:** support only connection/path, evidence, and finding-explanation intents. Compose answers from graph/path payloads and cite evidence IDs in every material sentence.
5. **Deterministic fallback:** if the external AI provider is unavailable, format the same source-backed path and evidence using templates so the demo never depends on network access.
6. **Security and audit baseline:** attach principal checks to all NEXUS reads/decisions; add audit events for graph view, evidence view, resolution decision, lead decision, search, and copilot query.
7. **Prototype metrics endpoint/artifact:** export counts, traceability coverage, resolution confusion counts, path latency, and rule expectation checks for M5.

### Evidence Response Minimum

| Field | Required Behavior | Fail Condition |
|---|---|---|
| relationship | IDs, type, endpoints, time range, confidence | UI has to infer or fabricate labels. |
| classification | Fact / Derived / Hypothesis with named producer | A score is shown without its meaning. |
| sources[] | source type, filename, row/page locator, excerpt/hash, occurred_at | A displayed edge has no clickable source. |
| derivation[] | rule/algorithm + input relationship/evidence IDs | Derived finding cites only itself. |
| audit | actor, action, target IDs, timestamp, request ID | Resolution/lead action cannot be reconstructed. |

### Definition of Done
- OpenAPI payloads match the frontend fixtures; breaking changes require M4 acknowledgement before merge.
- No demo-visible relationship can return an empty evidence chain; the service fails closed with a clear unavailable state.
- Copilot cannot produce an uncited accusation, prediction, or recommendation; unsupported intent is refused safely.
- Demo-mode identity is labeled in settings/readme and must never be described as production SSO or government deployment.

> **M3 cut line:** If generative copilot integration is unstable, ship the deterministic connection explainer. Keep evidence, pathfinder, lead decision, and audit routes.

---

## 8. Coding Plan — M4 Ram

**Frontend + Investigator Workspace** — Make the prototype judge-ready.

**Code boundary:** `frontend/src/pages/NetworkExplorer.tsx` (new); `EntityFusion.tsx` (new); `LeadInbox.tsx` (new); `frontend/src/components/nexus/*` (new); `router.tsx` / `Sidebar.tsx` / `Header.tsx`; `NetworkAnalysisPanel.tsx` (reuse/refactor)

### Exclusive Feature Ownership
1. **NEXUS navigation and brand pass:** expose Network, Entity Fusion, and Leads as the demo route; remove deadline-centric Patterns from the primary demo path without deleting reusable code.
2. **Entity Fusion Workbench:** side-by-side candidate records, match score, reasons, conflicts, source links, and Confirm/Reject/Defer actions with a clear post-decision state.
3. **Global Network Explorer:** render all relevant cases/entities, type/layer toggles, case focus, legend, selected-node neighborhood, and person bridge/community badges.
4. **Before/After Replay:** two-position control (Before resolution / After resolution), highlight added nodes/edges, and animate only the delta from M1's snapshot contract.
5. **Click-any-link Evidence Drawer:** relationship details, Fact/Derived/Hypothesis badge, confidence, time, source rows/pages, derivation chain, and copyable evidence IDs.
6. **Lead Inbox + Pathfinder:** show cross-case bridge finding, its evidence-backed connection path, and Accept/Reject controls; place grounded copilot explanation beside the same selected lead.
7. **Real search and timeline:** enable header search against M3; timeline entries and network state come from source timestamps, not hard-coded display dates.
8. **Judge-safe states:** loading, empty, error, provider-offline, and Reset Demo controls; all content comes through the API client or contract mocks.

### Screen-Level Acceptance

| Screen | Must Show | Must Not Do |
|---|---|---|
| Entity Fusion | Reasons + conflicts + sources + three decisions | Auto-merge silently or hide raw identities. |
| Network Explorer | Filters, two snapshots, bridge badge, selected path | Display an unexplained "criminal score." |
| Evidence Drawer | Exact relationship and full lineage | Show a generic summary without locators. |
| Lead Inbox | Finding explanation, cited path, accept/reject | Treat a hypothesis as a fact or auto-escalate. |
| Search/Timeline | API-backed results and source time | Use disabled controls or fixed demo dates. |

### Definition of Done
- The golden demo completes on a 1366x768 laptop view without scrolling away from the active decision.
- After upload, the core path needs no more than seven purposeful clicks before the grounded connection explanation.
- No component embeds graph algorithms, source parsing, entity-match scoring, or direct storage writes.
- A network/API failure has a recoverable state; Reset Demo restores the fixture without restarting the frontend.

> **M4 cut line:** Protect Entity Fusion, Network Diff, Evidence Drawer, and the single bridge lead. If time slips, reduce styling/animation and use preset filters before cutting these moments.

---

## 9. Development Plan: 24–29 August 2026

> **Schedule assumption:** PPT submission is 26 August at 09:00 and the internal hackathon demo is 29 August. If either date changes, preserve the milestone order and shift the clock, not the scope.

| Milestone | Parallel Execution | Exit Gate |
|---|---|---|
| **24 Aug** — Scope + contract freeze | M1 schema/examples; M2 fixtures/truth; M3 endpoint stubs; M4 UI wireframes; M5 claim register; M6 deck shell + demo storyboard | 18:00 contract pack; 21:00 mocked golden path |
| **25 Aug** — Vertical slice | M1 bridge/diff; M2 ingest/resolution; M3 evidence/lead routes; M4 fusion/explorer/drawer; M5 research + metric harness; M6 narrative + rehearsal v0 | 17:00 first integrated alias decision; 22:00 screenshots |
| **26 Aug** — Deck lock + integration | 07:00 claim check; 08:15 final export; 09:00 submit. Then complete API integration and offline fallback. | PPT submitted; one end-to-end golden path by 20:00 |
| **27 Aug** — Intelligence + evidence day | Fix graph diff, pattern findings, provenance chains, lead/path/cited explanation; M5 records actual test output; M6 rehearsal v1 | All three wow factors pass; no orphan edge |
| **28 Aug** — Freeze + hardening | Bug fixes only after 14:00; reset fixture, laptop test, offline test, timing, backup capture, judge Q&A | Release candidate tagged; three clean rehearsals |
| **29 Aug** — Demo day | Smoke test, local services, preloaded fixture, screen zoom, presenter handoff, backup video ready | Three-minute live demo + evidence-backed Q&A |

### Branch and Merge Discipline
- **Integration branch:** `prototype/nexus-golden-path` — only green, reviewed slices merge into it.
- **Member branches:** `feat/nexus-m1-graph-intelligence`, `feat/nexus-m2-data-resolution`, `feat/nexus-m3-decision-services`, `feat/nexus-m4-investigator-workspace`, `docs/nexus-m5-validation`, `submission/nexus-m6-demo-deck`.
- **PR rule:** One contract or user-visible slice per PR; include owner, test command/output, before/after capture, and rollback note.
- **Merge order:** Schema contract → fixture/canonical mapper → API contract → UI integration. Algorithms and UI may develop in parallel against frozen examples.
- **Feature freeze:** 28 Aug 14:00. After freeze: defects, copy accuracy, performance, demo reset, and evidence only.

### Daily Operating Rhythm
- **10:00** — 12-minute contract sync: blockers and interface changes only.
- **16:00** — integration checkpoint: run the golden path from reset through lead decision.
- **20:00** — evidence checkpoint: M5 captures test output; M6 rehearses the current build and updates the cut list.
- **End of day** — one owner posts build hash, known issues, fallback mode, and next day's first merge.

---

## 10. Integration, Testing, and Prototype Definition of Done

### Golden-Path Test Suite

| Test | Action | Pass Condition | Owner |
|---|---|---|---|
| T1 | Reset fixture twice | IDs/counts/snapshots are identical | M2 |
| T2 | Load FIR, CDR, transactions | Every fact has a raw locator; expected counts match truth | M2 + M3 |
| T3 | Confirm planted alias; reject planted non-match | Only intended entities merge; decision is audited | M2 + M3 |
| T4 | Recompute bridge/community/rules | Planted bridge top-3; three findings cite inputs | M1 |
| T5 | Compare before/after snapshots | Only expected delta highlighted; two cases connect | M1 + M4 |
| T6 | Open every demo-visible edge | 100% returns source or derivation chain | M3 + M4 |
| T7 | Explain path; accept/reject lead | Evidence IDs in answer; status/audit update | M3 + M4 |
| T8 | Disable external AI/network | Deterministic explanation and fixture still work | M3 + M6 |
| T9 | Audit every slide claim | Claim has build hash + capture/test reference | M5 + M6 |

### Release-Candidate Checklist
- One-command or documented local startup; fixture reset completes without manual database edits.
- No secrets, real PII, government logos used as endorsements, or unsupported integration claims.
- All demo routes require the configured principal and material reads/decisions appear in the audit log.
- All visible counts, dates, labels, evidence IDs, and screenshots match the current build hash.
- Frontend has loading/error/offline states; backend errors are structured and do not expose stack traces.
- The three wow factors work in three consecutive rehearsals and in the offline fallback mode.
- M5 signs the claim register; M6 freezes the PPT, demo sequence, fallback video, and presenter cues.

### Cut Ladder If The Build Falls Behind
- **Never cut:** Entity Fusion decision, Network Diff, Evidence Drawer, one cross-case bridge lead, deterministic path explanation, golden reset.
- **Degrade safely:** Generic file upload → fixed demo-source buttons; free-text copilot → fixed grounded questions; time slider → Before/After toggle; three findings → bridge + communication burst.
- **Cut first:** Map/GIS, PDF export, saved boards, multilingual UI, advanced animations, generic schema mapper, external AI dependency, financial-cycle visualization.

---

## 11. PPT Track — M5 Vaishali and M6 Ananya

> **Deck law:** Nothing enters the final PPT because it sounds impressive. A modification appears only when the frozen build, test output, or demo capture proves it. No roadmap slide and no finals-level claims in the internal submission.

### M5 — Research, Validation, and Claim Ownership
- **Owns:** Problem framing, stakeholder workflow evidence, codebase-before audit, competitor/differentiation facts, metric definitions, benchmark execution, claim register, technical-owner sign-off.
- **Produces:** Approved slide copy pack, source/claim notes, `metrics.json`/CSV, before/after captures, test summary, judge-question evidence sheet.
- **Does not own:** Master deck layout, demo sequence, final submission, or rewriting technical claims without the coding owner's evidence.
- **Gate:** Each claim has claim text, evidence type, build hash, owner, file/test/capture reference, measured value, and approval status.

### M6 — Product Narrative, Demo, and Submission Ownership
- **Owns:** Prototype scope board, slide sequence, visual system, master PPT file, demo script, presenter handoffs, timing, recording, fallback package, submission checklist.
- **Produces:** Final deck, three-minute runbook, 60–90 second fallback capture, demo reset checklist, speaker cues, submission archive.
- **Does not own:** Research conclusions, metric calculation, source interpretation, or technical changes inside M1–M4 boundaries.
- **Gate:** M6 may compress wording but cannot alter a number, scope, causal claim, or security claim without M5 and the technical owner.

### PPT Production Workflow
1. M6 creates the slide shell and assigns one evidence slot per slide.
2. M5 supplies approved content blocks and marks them Draft / Verified / Remove.
3. Technical owner signs the relevant screenshot, payload, or test result.
4. M6 places only Verified blocks, updates the demo cue, and exports a review PDF.
5. M5 performs the final claim audit; M6 locks and submits the file.

---

## 12. Modification-Matched PPT Structure

Ten slides are enough. Slides 4–9 must be deleted if their implementation/evidence gate is not met; never replace a failed gate with a mockup presented as working.

### Slide 01 — The fragmented-data investigation gap
- **Owner:** M5 content; M6 layout/speaker
- **Only show:** The investigator task NEXUS addresses: finding a defensible connection across FIR, CDR, and transaction fragments.
- **Visual:** One simple fragmented-sources visual leading to a missed cross-case connection.
- **Evidence gate:** Problem statement text + concise workflow evidence; no invented crime statistics.

### Slide 02 — What we changed in CaseClock
- **Owner:** M5 content; M6 layout
- **Only show:** Honest baseline-to-prototype map: reused FastAPI/React/NetworkX/OCR/auth/audit; replaced deadline-centric demo story.
- **Visual:** Before/after architecture or route map, not a marketing feature cloud.
- **Evidence gate:** Repository path/commit audit signed by M1–M4.

### Slide 03 — NEXUS source-to-decision system design
- **Owner:** M5 technical copy; M6 visual
- **Only show:** M2 → M1 → M3 → M4 pipeline and the audited human loop; Fact/Derived/Hypothesis policy.
- **Visual:** The four-owner architecture diagram from this plan.
- **Evidence gate:** Contract examples exist and each coding owner approves their boundary.

### Slide 04 — Modification 1: trustworthy ingestion + Entity Fusion
- **Owner:** M6 story; M5 claim check
- **Only show:** Three controlled source types, raw-source preservation, candidate reasons/conflicts, confirm/reject/defer.
- **Visual:** Live/screenshot sequence: candidate before decision → confirmed identity.
- **Evidence gate:** Golden ingest and resolution tests pass; exact counts captured.

### Slide 05 — Modification 2: graph intelligence + Network Diff
- **Owner:** M6 story; M5 claim check
- **Only show:** First-class entities, person-only bridge/community analysis, cross-case bridge, Before/After replay.
- **Visual:** Two graph frames with added bridge highlighted.
- **Evidence gate:** Known bridge top-3; snapshot delta matches `truth.json`.

### Slide 06 — Modification 3: click-any-link evidence
- **Owner:** M6 story; M5 claim check
- **Only show:** One relationship's source rows/pages, time, confidence, and derivation chain.
- **Visual:** Network edge selected beside the open Evidence Drawer.
- **Evidence gate:** Traceability test covers every edge used in the demo.

### Slide 07 — Modification 4: lead, pathfinder, grounded explanation
- **Owner:** M6 story; M5 claim check
- **Only show:** One cross-case lead; cited connection path; deterministic fallback; accept/reject audit.
- **Visual:** Lead card → path → cited answer → decision status.
- **Evidence gate:** Lead/copy/audit golden test passes offline and online/provider-off modes.

### Slide 08 — Three-minute golden demo
- **Owner:** M6
- **Only show:** Only the exact eight-step path in Section 1; include presenter click cues and expected visible result.
- **Visual:** A horizontal 8-step demo strip with one screenshot per wow moment.
- **Evidence gate:** M6 completes three clean rehearsals under three minutes on the target laptop.

### Slide 09 — Measured prototype results
- **Owner:** M5
- **Only show:** Actual traceability, match confusion counts, bridge rank, path latency, demo time, and offline pass/fail.
- **Visual:** Small scorecard with numerator/denominator and build hash.
- **Evidence gate:** Metrics generated after feature freeze; targets replaced by actual values.

### Slide 10 — Why this prototype wins — and what it does not claim
- **Owner:** M6 close; M5 accuracy sign-off
- **Only show:** Evidence-first human control, inspectable intelligence, reusable code foundation; explicit prototype exclusions.
- **Visual:** Three proof pillars plus one scope guardrail line.
- **Evidence gate:** Every proof pillar demonstrated in slides 4–9; exclusions match the build/readme.

---

## 13. Claim-to-Code Traceability Matrix

| Claim | Code Proof | Demo / Test Proof | Sign-off | Slide |
|---|---|---|---|---|
| Entity Fusion works | M2 candidate + decision logic; M3 route; M4 workbench | Resolution test output + before/after screenshot | M2 / M3 / M4 | Slide 4 |
| Networks connect after review | M1 snapshot diff + bridge finding; M4 replay | `truth.json` delta + bridge rank + graph capture | M1 / M4 | Slide 5 |
| Every shown link is evidence-backed | M3 evidence service; M4 drawer | Traceability numerator/denominator + selected edge capture | M3 / M4 | Slide 6 |
| Copilot is grounded | M3 path/evidence composer + deterministic fallback; M4 panel | Response payload with evidence IDs + offline run | M3 / M4 | Slide 7 |
| Prototype is measurable | M3 metrics export; M5 validation protocol | Frozen metrics artifact with build hash | M3 / M5 | Slide 9 |

### Claims Forbidden Unless The Build Changes
- ❌ "Integrated with CCTNS/ICJS/NCRB" → ✅ "adapter-ready prototype using synthetic fixtures"
- ❌ "Production secure" or "DPDP compliant" → ✅ "prototype role checks and append-only audit scaffolding"
- ❌ "AI predicts criminals/masterminds" → ✅ "deterministic network metrics surface reviewable bridge entities"
- ❌ "Works on any document/CSV" → ✅ "controlled FIR, CDR, and transaction schemas for the prototype"
- ❌ "Real-time nationwide scale" → do not include scale claims in this internal deck.

### Screenshot Capture List
- **S1** — two disconnected case components before entity confirmation.
- **S2** — Entity Fusion candidate with reasons, conflict, and source links.
- **S3** — post-confirmation diff with the bridge highlighted.
- **S4** — Evidence Drawer for one communication/financial relationship.
- **S5** — cross-case lead and pathfinder output.
- **S6** — grounded explanation with evidence IDs and lead decision audit.
- **S7** — metrics scorecard showing actual counts, timing, build hash, and date.

---

## 14. Live Demo Runbook

| Time | Action | Visible Proof | Owner |
|---|---|---|---|
| 0:00–0:15 | Open Network Explorer | Two disconnected cases; state the investigation question. | M6 / presenter |
| 0:15–0:35 | Load three demo sources | Extraction summary and preserved source records. | M4 UI, M2 data |
| 0:35–0:55 | Open Entity Fusion | Show reasons/conflict; confirm the planted alias. | M4 UI, M2 logic |
| 0:55–1:20 | Replay Before → After | Bridge appears; cases join; added delta highlighted. | M1 + M4 |
| 1:20–1:40 | Open Evidence Drawer | Exact CDR/transaction locator, time, confidence, derivation class. | M3 + M4 |
| 1:40–2:05 | Open bridge lead | Explainable rule, connected cases, cited path. | M1 + M3 + M4 |
| 2:05–2:30 | Ask "How are these cases connected?" | Grounded path answer with evidence IDs. | M3 + M4 |
| 2:30–2:50 | Accept/reject lead | Decision state and audit entry update. | M3 + M4 |
| 2:50–3:00 | Close | Three proofs: trusted data, explainable network, human decision. | M6 |

### Presenter Language
- **Open:** "These two cases appear separate because their evidence lives in different records. NEXUS does not guess a criminal; it helps an investigator test a connection."
- **Fusion:** "The system proposes this alias match and shows both supporting evidence and a conflict. The investigator remains the decision-maker."
- **Evidence:** "This link is not a decorative line. It points to the exact source record and shows whether it is a fact, a derivation, or a hypothesis."
- **Close:** "Our prototype turns fragmented records into a reviewable lead while preserving provenance at every step."

### Failure-Safe Demo Modes

| Failure | Recovery | What To Say |
|---|---|---|
| External AI unavailable | Use deterministic path explanation. | "Grounding is the product; generation is optional." |
| Upload/OCR slow | Load pre-parsed golden batch with same source locators. | "The controlled fixture preserves the identical lineage contract." |
| Backend restart | Use Reset Demo; keep local services and fixture command ready. | "We are restoring the reproducible prototype state." |
| Live UI failure | Play 60–90 second capture, then answer from evidence screenshots. | "This capture is from the same frozen build hash." |

---

## 15. Judge-Question Preparation and Final Sign-off

**Q. Why is this not just a graph dashboard?**
A. Because the prototype includes source ingestion, explainable entity fusion, temporal network change, edge-level provenance, a human lead decision, and a grounded path answer — one audited workflow, not a visualization.

**Q. How do you avoid false accusations?**
A. Facts, derived findings, and hypotheses are separated. Entity matches and leads require human confirm/reject, every output cites source evidence, and we avoid guilt/prediction labels.

**Q. Where is AI genuinely used?**
A. NLP/entity extraction and candidate resolution can assist with unstructured records; the demo's critical bridge/path/pattern logic is deterministic and testable. Generation is optional and grounded.

**Q. Why not blockchain or a GNN?**
A. Neither is necessary to prove the core stakeholder value. Provenance, audit, and explainable graph algorithms solve the prototype requirement with lower risk and clearer verification.

**Q. Is the data real?**
A. No. The prototype uses labeled synthetic crime-like fixtures to stay legal, reproducible, and measurable. The architecture preserves source adapters for authorized future data.

**Q. Can it scale?**
A. This internal prototype does not claim nationwide scale. Its typed contracts, adapter boundaries, and stateless APIs are designed so storage and compute can be replaced later without rewriting the investigator workflow.

**Q. What is the standout innovation?**
A. The combination of human-reviewed entity fusion, before/after network diff, and click-any-link provenance. The insight changes visibly while its evidence remains inspectable.

**Q. What did each member build?**
A. M1 graph intelligence; M2 data trust/resolution; M3 evidence/decision APIs; M4 workspace; M5 proof/metrics; M6 product narrative/demo. The handoff contracts prevent overlap.

### Final Owner Sign-off

| Owner | Sign-off Scope | Ready |
|---|---|---|
| M1 Shriraj | Bridge rank, findings, snapshot diff | [ ] |
| M2 Vikram | Fixtures, raw lineage, resolution truth | [ ] |
| M3 Sujal | APIs, evidence, grounded answer, audit | [ ] |
| M4 Ram | Golden UI path, recovery states, laptop view | [ ] |
| M5 Vaishali | Claim register, metrics, slide accuracy | [ ] |
| M6 Ananya | Scope lock, deck, runbook, submission/fallback | [ ] |

> **Final release rule:** The submission is ready only when all six owners sign their row, the three wow factors pass three consecutive rehearsals, and every deck claim points to the frozen build or measured artifact.

---

*NEXUS prototype brief | Built to win by proving one defensible investigation workflow end to end.*
