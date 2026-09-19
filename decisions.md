# NEXUS Architectural & Product Decisions

This document is the **single source of truth** for material architectural, security, data model, and engineering decisions in NEXUS.

---

## DEC-001 — Polyglot Graph & In-Memory GraphStore Architecture
- **Date:** 2026-08-20
- **Status:** Accepted & Implemented
- **Decision:** Adopt a hybrid polyglot architecture combining:
  1. In-memory double-adjacency list `GraphStore` (`adj` and `radj`) indexed by entity and edge types for ultra-low-latency graph traversals (<0.025ms BFS expansions).
  2. Neo4j 5 Community / Cypher as persistent graph database for Cypher analytics, schema-constrained projections, and deep graph queries.
  3. Cloud PostgreSQL 16 for relational case registries, user authentication, and immutable audit logs.
- **Reason:** Real-time investigative UI workflows require sub-second response times for multi-hop BFS, betweenness centrality, and Louvain community detection across multi-relational graphs. Relational SQL recursive joins suffer latency degradation, while remote Neo4j calls alone introduce network roundtrip overhead for interactive visual canvas manipulations.
- **Alternatives Considered:**
  - *PostgreSQL only (recursive CTEs):* Inadequate performance on 3+ hop traversals and community clustering.
  - *Neo4j only:* Network latency overhead during high-frequency interactive canvas manipulations.
- **Consequences:** Provides sub-millisecond local graph operations while maintaining robust durable graph persistence in Neo4j. Requires initial in-memory graph synchronization upon backend startup (measured at ~6.05ms for baseline dataset).

---

## DEC-002 — Deterministic-Before-Generative & Ethical Refusal Gate
- **Date:** 2026-08-21
- **Status:** Accepted & Implemented
- **Decision:** Enforce a strict architectural boundary where:
  1. All entity resolution, similarity scoring, community clustering, and centrality computations execute strictly via deterministic algorithms (Double Metaphone, Jaccard multi-attribute weighting, Louvain modularity, Brandes betweenness).
  2. The AI Copilot incorporates an architectural refusal interceptor (`CopilotService`) that halts and refuses queries requesting predictive guilt scores, dangerousness ratings, or recidivism risk before any LLM prompt execution.
  3. Generative AI is limited strictly to natural language summarization of verified graph facts with mandatory grounded citations.
- **Reason:** In the Indian constitutional framework, the determination of criminal guilt or innocence is the exclusive prerogative of the judiciary. Predictive policing algorithms create severe bias, unconstitutional automation, and legal liabilities.
- **Alternatives Considered:**
  - *End-to-end LLM graph reasoning:* Unreliable, hallucination-prone, and violates Section 63 BSA admissibility standards.
- **Consequences:** Absolute adherence to legal ethics, elimination of predictive guilt bias, and verifiable trust for law enforcement agencies. Speculative queries are rejected by design.

---

## DEC-003 — Edge-Level Evidence Provenance & Section 63 BSA Compliance
- **Date:** 2026-08-22
- **Status:** Accepted & Implemented
- **Decision:** Every relationship edge in the NEXUS graph must carry an immutable `EvidenceProvenance` citation record containing:
  - `source_type`: Category of source document (`FIR`, `CDR`, `BANK_TXN`, `SEIZED_DEVICE`, `INTELLIGENCE_REPORT`).
  - `source_id`: Document identifier, UTR number, or call detail record ID.
  - `timestamp`: UTC event creation timestamp.
  - `extracted_fact`: Concrete verifiable factual assertion.
  - `derivation_method`: Algorithmic or forensic verification method (`OFFICIAL_RECORD`, `TELECOM_LOG`, `ALGORITHMIC_MATCH`).
  - `confidence`: Quantitative confidence score [0.0 - 1.0].
- **Reason:** Under Section 61 and Section 63 of the Bharatiya Sakshya Adhiniyam, 2023 (BSA), electronic evidence, link charts, and intelligence dossiers are admissible in court only with continuous provenance and verifiable source attribution.
- **Alternatives Considered:**
  - *Node-level citations only:* Fails to capture multi-relational facts between same entities across multiple independent cases.
- **Consequences:** Guarantees court admissibility and full auditability. Click-any-edge UX immediately surfaces the underlying forensic evidence. Small storage overhead per edge is negligible relative to evidentiary value.

---

## DEC-004 — Synthetic Multi-Modal Intelligence Corpus Strategy
- **Date:** 2026-08-23
- **Status:** Accepted & Implemented
- **Decision:** All development, testing, CI benchmarks, and demonstrations operate exclusively on a deterministic synthetic dataset generator (`synthetic_data/nexus_generator.py`) paired with planted ground-truth associations (`artifacts/nexus_graph/ground_truth.json`).
- **Reason:** Real police FIRs, CDRs, and bank transactions are classified under Indian statutory protections and the Digital Personal Data Protection Act, 2023. Using live citizen PII in development or public demonstrations is strictly prohibited.
- **Alternatives Considered:**
  - *Anonymized real data:* Masking is prone to re-identification attacks and lacks reproducible benchmark ground truth.
- **Consequences:** 100% reproducible testing and evaluation, zero privacy risk, while retaining full structural complexity of organized crime networks.

---

## DEC-005 — Durable Neo4j Graph Projection Layer
- **Date:** 2026-09-07
- **Status:** Accepted & Implemented
- **Decision:** Implement a bidirectional, durable Neo4j projection engine (`backend/app/db/neo4j.py`) with:
  1. Explicit schema constraints (`node_key` constraint on `Entity(id)` and `case_number` constraint on `Case(case_id)`).
  2. Parameterized batch Cypher synchronization (`sync_nodes` and `sync_edges` using `UNWIND`).
  3. Bidirectional projection reading (`read_projection` into memory `GraphStore`).
  4. Non-fatal graceful degradation: when Neo4j is offline or credentials unconfigured, the application logs a warning and cleanly falls back to the in-memory graph engine without crashing.
- **Reason:** Bridges the gap between fast in-memory execution and durable graph storage required for multi-analyst collaboration, persistent Cypher queries, and enterprise deployment.
- **Alternatives Considered:**
  - *Direct synchronous Cypher queries on every UI action:* Severe latency penalties.
  - *Strict fail-fast dependency:* Breaks standalone offline development and local quick-start demos.
- **Consequences:** Full durability, schema integrity, and zero downtime in environments where Neo4j is provisioned or temporarily unavailable.

---

## DEC-006 — SHA-256 Tamper-Evident Evidence Verification
- **Date:** 2026-09-12
- **Status:** Accepted & Implemented
- **Decision:** Implement SHA-256 cryptographic payload verification across all evidence records (`backend/app/services/evidence_service.py`):
  1. Hash calculation covers canonical JSON representation (`evidence_type`, `title`, `description`, `file_name`, `source_system`, `case_id`, `metadata`).
  2. Any unauthorized modification to an evidence record's underlying metadata or content produces an immediate verification failure, flagging the record as compromised.
  3. Automated tamper audit test suite (`tests/test_evidence_tamper_audit.py`) validates tamper detection across all fields.
- **Reason:** Mandatory compliance with Bharatiya Sakshya Adhiniyam, 2023 Section 63 requirements for electronic records authenticity.
- **Alternatives Considered:**
  - *External blockchain anchoring:* Higher complexity and latency for MVP; SHA-256 with immutable audit logs in PostgreSQL meets statutory standard.
- **Consequences:** Cryptographically guarantees data integrity from ingestion to PDF dossier export.

---

## DEC-007 — Temporal Graph Snapshots & Network Diff Engine
- **Date:** 2026-09-17
- **Status:** Accepted & Implemented in core algorithm, API/UI Promotion In Progress
- **Decision:** Establish `GraphSnapshot` and `NetworkChange` as first-class domain models, promoting the existing `backend/app/core/graph/algorithms/snapshot_diff.py` engine into the authoritative `NetworkDiffService`.
  1. The diff engine performs pure, non-mutating $O(N + E)$ comparisons across temporal intervals or explicit snapshot revisions.
  2. Evaluates structural additions/removals (`added_nodes`, `removed_nodes`, `added_relationships`, `removed_relationships`) and semantic property modifications without mutation.
  3. Identifies topological phase shifts: bridge emergence/loss, community splits/merges, and identifier drift events.
- **Reason:** Law enforcement networks are non-static; kingpins adapt phone numbers, vehicles, and intermediaries across time. Retrospective static graphs hide these operational adaptations.
- **Alternatives Considered:**
  - *Ad-hoc timestamp filters on every graph query:* Slow, non-deterministic, and cannot compare two discrete investigative states.
- **Consequences:** Enables investigators to scrub time windows and observe syndicate reorganization deterministically.

---

## DEC-008 — Network Pulse & Structural Significance Filtering
- **Date:** 2026-09-17
- **Status:** Accepted & Roadmap P0
- **Decision:** Implement `NetworkPulseService` to filter raw graph diffs into qualified `NetworkPulse` intelligence records:
  1. Raw edge additions (e.g. routine calls) do not trigger alarms; only high-significance structural changes (new bridge to a dormant syndicate, identifier transition, cross-jurisdiction transfer) generate a Pulse.
  2. Pulses are prioritized purely for investigator review priority (`CRITICAL_REVIEW`, `PRIORITY_REVIEW`, `ROUTINE_REVIEW`). Under no circumstances is priority converted into a "guilt" or "dangerousness" score.
  3. Every pulse carries explicit pointers to supporting evidence records, action windows, and uncertainty metrics.
- **Reason:** Prevents alert fatigue and information overload for investigating officers.
- **Alternatives Considered:**
  - *Alert on every added edge:* Generates hundreds of trivial notifications, diluting high-value intelligence.
- **Consequences:** High signal-to-noise ratio in the investigator worklist while upholding non-negotiable ethical boundaries.

---

## DEC-009 — Multi-State Evidence Sufficiency & Contradiction Model
- **Date:** 2026-09-17
- **Status:** Accepted & Roadmap P0
- **Decision:** Model evidence sufficiency through explicit discrete epistemic states:
  - `SUPPORTS`: Concrete official record directly substantiates the relationship.
  - `CONFLICTS`: Independent evidence contradicts the claimed fact (e.g., CDR tower in Delhi while FIR narrative claims presence in Bengaluru).
  - `MISSING`: Relationship is suspected or inferred but lacks mandatory corroborating documentation.
  - `INFERRED`: Derived via deterministic graph clustering or phonetic similarity; awaiting corroboration.
  - `VERIFIED`: Confirmed by an authorized investigating officer after reviewing primary documents.
- **Reason:** Legal prosecution requires evidentiary sufficiency, not just statistical likelihood. Contradictory evidence must be surfaced transparently rather than silently smoothed over.
- **Alternatives Considered:**
  - *Single floating-point confidence score (0.0 - 1.0):* Obscures whether a low score is due to missing data or active contradiction.
- **Consequences:** Absolute clarity in investigative dossiers; legal defensibility under scrutiny in judicial cross-examination.

---

## DEC-010 — Constrained Early-Warning Forecasting & Mandatory Abstention
- **Date:** 2026-09-17
- **Status:** Accepted & Roadmap P0
- **Decision:** Architect the `EarlyWarningService` with strictly constrained forecast targets and a mandatory abstention gate:
  1. **Permitted Targets:** Narrow operational state transitions:
     - `JURISDICTION_SHIFT` (activity moving to neighboring district/state)
     - `COMMUNICATION_PATTERN_SHIFT` (sudden radio silence or shift to encrypted/burner channels)
     - `FINANCIAL_ROUTE_TRANSITION` (re-routing through mule accounts after a freeze)
     - `IDENTIFIER_DRIFT` (phone/vehicle transition)
     - `NETWORK_RESTRUCTURING` (intermediary replacement)
  2. **Prohibited Targets:** Guilt, criminality propensity, future crime commission, dangerousness, or recidivism risk.
  3. **Mandatory Abstention:** If supporting evidence is below sufficiency thresholds, stale (>90 days), or conflicting, the service MUST output `INSUFFICIENT EVIDENCE / NO FORECAST`.
- **Reason:** Algorithmic bias and black-box crime prediction violate human rights and Indian constitutional norms. Forecasting must be strictly restricted to network topology and operational logistics.
- **Alternatives Considered:**
  - *Predictive recidivism scoring:* Unconstitutional, legally inadmissible, and ethically prohibited.
- **Consequences:** Provides actionable operational leads for law enforcement while ensuring strict legal compliance.

---

## DEC-011 — Role-Gated Cross-Branch Intelligence Pulse Routing
- **Date:** 2026-09-17
- **Status:** Accepted & Roadmap P1
- **Decision:** Structure inter-case and inter-jurisdictional intelligence propagation into `IntelligencePulse` packets:
  1. Automated bridge detection between independent cases (e.g. Case A in Bengaluru and Case B in Mumbai) generates an unrouted candidate pulse.
  2. Propagation is strictly governed by RBAC/ABAC: only supervisors/analysts with appropriate clearance can authorize transmission.
  3. Transmission and acknowledgement are logged in the immutable audit log with full actor provenance.
- **Reason:** Inter-unit rivalry and data siloing hinder coordinated action against multi-state syndicates, but unvetted sharing risks investigative compromise and leaks.
- **Alternatives Considered:**
  - *Global shared graph across all stations without access gating:* Violates operational security and need-to-know principles.
- **Consequences:** Controlled, audited, and secure cross-station collaboration.

---

## DEC-012 — Controlled SOCMINT & Digital Shadow Evidence Governance
- **Date:** 2026-09-17
- **Status:** Accepted & Roadmap P1
- **Decision:** Ingest digital signals (e.g. social media handles, marketplace postings, messaging identifiers) strictly as controlled evidence items under explicit governance:
  1. Only authorized, lawful, and publicly available or legally subpoenaed signals are ingested.
  2. Association states follow an explicit progression:
     $$\text{OBSERVED} \to \text{CANDIDATE LINK} \to \text{CORROBORATED} \to \text{INVESTIGATOR CONFIRMED}$$
  3. A digital handle or profile match is NEVER sufficient proof of legal identity by itself; it requires independent hard-identifier corroboration (phone, IMEI, Aadhaar token, banking).
- **Reason:** Unregulated digital scraping produces false positives, violates privacy rights, and fails statutory standards of evidence.
- **Alternatives Considered:**
  - *Full automated identity merging from social handles:* Severe risk of false citizen implication.
- **Consequences:** Preserves civil liberties, complies with DPDP Act 2023, and delivers verifiable digital corroboration.

---

## DEC-013 — Explicit Investigation Graph Depth Control & Deterministic Entity Provenance
- **Date:** 2026-09-18
- **Status:** Accepted & Implemented
- **Decision:**
  1. Default the Case Network endpoint (`/api/v1/network/cases/{case_id}`) and frontend Explorer to `depth=1` (direct case entities, accused, and direct evidence).
  2. Provide explicit investigator-controlled graph expansion via safe query parameter `depth: int = Query(1, ge=0, le=3)`:
     - `depth=0`: Root case entity only (strict isolate).
     - `depth=1`: Direct case entities (accused, complainants, direct evidence).
     - `depth=2`: Expanded multi-hop intelligence (syndicate operatives, financial conduits, CDR bridges).
     - `depth=3`: Extended intelligence network (secondary accounts, multi-tier criminal cells).
  3. Enrich all node responses with deterministic `NodeContextResponse` containing:
     - `presence_type` (`DIRECT_CASE`, `INTELLIGENCE_EXPANSION`, `CDR_CONNECTION`, `CROSS_CASE`, `EVIDENCE`, `OTHER`).
     - `reason`: Grounded natural language fact derived from edge evidentiary provenance.
     - `source_ids`: Underlying statutory records (FIRs, CDRs, bank statements, intelligence notes).
     - `relationship_types`: Direct or path relationship types.
     - `distance_from_case`: Exact topological hop distance from case root.
     - `path` & `readable_path`: Authoritative traversal breadcrumbs.
  4. Never generate or hallucinate context reasons via LLM; all reasons must be deterministically constructed from verifiable graph edge provenance.
- **Reason:** Defaulting to multi-hop depth=2 caused cases (e.g. `FIR-2026-495`) to show wider syndicate entities (e.g. `Pradeep Iyer`, `Ramesh Hegde`) without visual differentiation, risking confusion between direct accused persons and multi-hop intelligence entities.
- **Alternatives Considered:**
  - *Removing multi-hop capability:* Rejected; multi-hop syndicate detection is essential for dismantling criminal networks.
  - *LLM-generated context explanations:* Rejected; violates deterministic evidence grounding and introduces hallucination risk.
- **Consequences:** Investigators have full control over network scope; direct accused entities and multi-hop intelligence are clearly and visually distinguished; all presence is explainable with verifiable Section 63 BSA evidence citations.

---

## DEC-014 — Unstructured Document Ingestion Foundation & Tamper-Evident Fingerprinting (P1-A)
- **Date:** 2026-09-19
- **Status:** Accepted & Implemented (P1-A)
- **Decision:**
  1. Establish an unstructured document ingestion foundation for machine-readable `.pdf` and `.txt` files (FIRs, police memos, intelligence reports).
  2. Maintain a strict phase boundary:
     $$\text{DOCUMENT} \to \text{EXTRACTED TEXT} \to \text{VERIFIED DOCUMENT PROVENANCE}$$
     No automatic graph mutations, no node/relationship generation, and no LLM execution in this phase.
  3. Enforce deterministic SHA-256 cryptographic document integrity hashing on original bytes. Frame hashing accurately as cryptographic integrity and tamper-evident fingerprinting without making premature or unsupported statutory legal-admissibility claims.
  4. Preserve document and extracted text confidentiality strictly through existing RBAC (`EvidenceAuthorizationPolicy`). Documents tagged with a `case_id` are confidential and inaccessible/undiscoverable to unauthorized officers across upload, listing, metadata, and text endpoints.
  5. Employ deterministic text extraction: `pypdf` for machine-readable PDFs (with encryption detection and page-level fallback) and safe encoding decoding for plain text.
  6. Emit `DOCUMENT_UPLOADED`, `DOCUMENT_VIEWED`, and `DOCUMENT_EXTRACTION_FAILED` through the durable audit trail, avoiding duplicate events during internal service queries.
- **Reason:** Real-world criminal investigations receive voluminous unstructured filings (FIR PDFs, seizure memos, plain-text intelligence notes). Establishing an authoritative, tamper-evident document intake layer before downstream entity extraction prevents ungrounded graph corruption and ensures strict chain-of-custody tracking.
- **Alternatives Considered:**
  - *Direct LLM extraction directly into graph on upload:* Rejected; violates deterministic auditability and risks hallucinations mutating the authoritative graph.
  - *Storing multi-gigabyte raw binaries directly inside relational SQL columns:* Rejected; decoupled `DocumentService` operates via clean persistence abstraction allowing future blob/object storage backends.
- **Consequences:** Provides a secure, tamper-evident, RBAC-governed document extraction foundation. Existing CSV ingestion remains 100% unchanged.

---

## DEC-015 — Document Intelligence: Deterministic Candidate Entity & Relationship Extraction (P1-B)
- **Date:** 2026-09-19
- **Status:** Accepted & Implemented (P1-B)
- **Decision:**
  1. Establish Phase P1-B pipeline:
     $$\text{DOCUMENT} \to \text{EXTRACTED TEXT} \to \text{CANDIDATE ENTITIES} \to \text{CANDIDATE RESOLUTION} \to \text{CANDIDATE RELATIONSHIPS} \to \text{PROVENANCE} \to \text{STOP}$$
  2. **Absolute Zero-Mutation Invariant:** P1-B must never mutate the authoritative investigation graph. It has no authority to create, update, or delete nodes or edges, or merge/fuse entities. Enforced and validated via deep graph state equality assertions before and after extraction (`authoritative_graph_before == authoritative_graph_after`).
  3. **Deterministic Extraction Priority:** Deterministic high-precision candidate extraction operates completely independently. Optional LLM enrichment is strictly non-authoritative and every LLM output must be deterministically validated against source spans.
  4. **Strictly Read-Only Resolution:** Candidate resolution queries existing canonical graph entities via read-only inspection to identify candidate matches (`REVIEW_REQUIRED` / `NO_MATCH_FOUND`). It never outputs authoritative confirmation or "MATCHED" state.
  5. **Explicit Evidence Requirement for Relationships:** Candidate relationships are produced only where explicit textual connective evidence exists. Mere paragraph co-occurrence without relational predicates strictly yields zero relationships (unsupported inference guard).
  6. **Case RBAC & Auditability:** Candidate extraction and retrieval endpoints (`POST /documents/{id}/extract`, `GET /documents/{id}/candidates`, `GET /candidates/{id}`, `GET /candidates/{id}/resolution`) strictly enforce canonical case jurisdiction and record audit events (`DOCUMENT_EXTRACTION_STARTED`, `DOCUMENT_CANDIDATES_EXTRACTED`, `CANDIDATE_VIEWED`).
  7. **Strict Phase Boundary:** P1-B strictly stops before P1-C. No "Add to Graph", no candidate promotion, and no investigator accept/reject logic is implemented in this phase.
- **Reason:** Criminal intelligence cannot permit black-box ungrounded entity injection into the authoritative case graph. Establishing an isolated, verifiable candidate layer with explicit provenance and read-only resolution guarantees that human investigators retain constitutional sovereignty over what enters the court-admissible graph.
- **Alternatives Considered:**
  - *Direct graph ingestion from text:* Rejected; risks hallucinated or false nodes polluting the evidence network.
  - *Automated entity fusion during extraction:* Rejected; violates judicial and evidentiary standards under Indian law.
- **Consequences:** Provides an explainable, isolated candidate extraction layer with complete provenance grounding. Prepares the system for investigator-guided P1-C candidate review.
- **Technical Debt Resolved in P1-C:**
  - *Mutable-Repository vs. Read-Only Graph Interface:* Formally introduced `ReadOnlyGraphView` (`backend/app/core/graph/read_only_view.py`), which restricts graph queries to safe read-only operations (`get_node`, `get_all_nodes`, `get_neighbors`, `find_nodes_by_property`, `count_nodes`, `count_edges`). `DocumentExtractionService` now receives only `ReadOnlyGraphView` for entity resolution candidate lookups, eliminating architectural mutation exposure.

---

## DEC-016 — Investigator Confirmation → Authoritative Graph Mutation (P1-C)
- **Date:** 2026-09-19
- **Status:** Accepted & Implemented (P1-C)
- **Decision:**
  1. Establish Phase P1-C controlled promotion lifecycle:
     $$\text{P1B CANDIDATE} \to \text{INVESTIGATOR REVIEW} \to \text{ACCEPT / REJECT} \to \text{VALIDATION} \to \text{AUTHORITATIVE GRAPH MUTATION} \to \text{PROVENANCE} \to \text{AUDIT} \to \text{REVIEWABLE HISTORY}$$
  2. **Absolute Promotion Invariant:** No candidate entity or relationship may enter the authoritative case graph without an explicit, authorized, and authenticated investigator decision. Zero automatic promotion, zero automatic identity fusion, zero background ingestion bypass.
  3. **100% Deterministic Promotion Path:** Zero LLM calls are permitted anywhere in the promotion or mutation path. Candidate data from P1B is treated purely as candidate input; the final graph mutation payload is synthesized, validated, and persisted by deterministic application code.
  4. **Canonical ID Convention Consistency:** All newly created entities reuse existing canonical NEXUS prefix conventions (`person-XXXX`, `phone-XXXX`, `account-XXXX`, `vehicle-XXXX`, `org-XXXX`, `location-XXXX`). Secondary incompatible naming schemes are strictly barred, ensuring full downstream compatibility with `GraphStore`, Neo4j, graph projections, GraphRAG, and entity resolution.
  5. **Existing Graph Schema Compatibility:** Linking candidates to existing entities (`link_candidate_to_entity`) preserves canonical graph schemas without injecting arbitrary non-canonical node attributes. Candidate references are merged directly into canonical provenance arrays (`provenance.supporting_documents`).
  6. **Separation of Powers & Server-Side RBAC (`can_decide_candidate`):**
     - Anonymous callers are strictly rejected (401/403).
     - `ANALYST` role has analytical read-only access and is forbidden from executing graph mutations or candidate confirmations (403).
     - `INVESTIGATOR` / `IO` must be assigned directly to the case (403 if unassigned).
     - `SUPERVISOR` / `SP` / `ADMIN` have supervisory authority covering divisional/state cases.
  7. **Edge Deduplication & Evidence Corroboration:** Accepting a candidate relationship where a canonical edge already connects the source and target nodes does NOT create a redundant duplicate edge. It corroborates the existing edge by appending the new document citation and case ID to its provenance records.
  8. **Strict Transaction Failure & Atomicity Safeguard:** If a mutation fails (simulated graph/repository/Neo4j disk failure):
     - An HTTP 500 error is returned.
     - The candidate remains available for review/retry and is NOT marked `ACCEPTED`.
     - No false-success decision record is persisted.
     - No successful promotion audit event is emitted; instead, a failure event (`CANDIDATE_PROMOTION_FAILED`) is recorded.
     - In-flight mutations are safely rolled back, leaving zero partial corruption in the graph.
  9. **Idempotency & Conflicting Decisions Protection:** Re-submitting an identical decision returns the existing decision idempotently (200 OK). Attempting to accept a candidate that was already rejected (or vice versa) raises an HTTP 409 Conflict.
- **Reason:** Ensuring that the authoritative investigation graph remains strictly court-admissible, grounded in verifiable physical evidence under Indian law, and free from algorithmic or predictive guilt bias requires an airtight, human-in-the-loop promotion boundary.
---

## DEC-017 — Dedicated Surveillance Report Ingestion (P1-D)
- **Date:** 2026-09-19
- **Status:** Accepted & Implemented (P1-D)
- **Decision:**
  1. **Dedicated First-Class Source Type:** Introduce `SURVEILLANCE_REPORT = "SURVEILLANCE_REPORT"` into the authoritative `SourceType` enum, resolving the audit weakness where field observations were previously absorbed under generic intelligence reports (`INTEL_REPORT`). Existing ingestion behavior for FIR, CDR, BANK_TXN, and INTEL_REPORT remains completely unmodified.
  2. **Deterministic Data Contract & Normalization:** Implement structured surveillance ingestion (`backend/app/db/ingestion/parsers/surveillance.py` and `mappers/surveillance.py`) handling surveillance records containing `report_id`, `case_id`, `observation_id`, `observed_at`, `subject_name`, `observation_type`, `location`, `vehicle_plate`, `phone_number`, `organization_name`, `summary`, and `source_reference`. Enforce strict ISO-8601 UTC timestamp validation, phone number normalization, vehicle plate uppercase standardization, and required field checks.
  3. **Reuse of Existing Graph Semantics & Zero Unsupported Inference:**
     - Map observations strictly into existing Schema V2 node types (`Person`, `Location`, `Vehicle`, `Phone`, `Organization`) and relationship types (`SEEN_AT`, `USED_VEHICLE`, `USED_PHONE`, `ASSOCIATED_WITH`).
     - Strictly prohibit speculative inferences: observation at a location NEVER infers `OWNS`, `ACCUSED_IN`, `COMMITTED`, or implicit association with other subjects observed at the same location.
  4. **Multi-Attribute Entity Resolution:** Integrate with the existing deterministic multi-attribute entity registry (`IdentityClaim`). Match canonical entities when evidence permits (phone, vehicle, exact name); flag ambiguous matches as `REVIEW_REQUIRED` without arbitrary or speculative fusion; never use LLMs to decide identity.
  5. **Edge Deduplication & Evidence Corroboration:** Ingesting an observation connecting two entities that are already linked by an existing canonical edge (`(source_id, target_id, edge_type)`) does NOT create a redundant duplicate edge. The existing edge is corroborated by appending the observation's `EvidenceProvenance` to `corroborating_evidence` and incrementing `edges_reused`.
  6. **Authoritative Graph Mutation Boundary:** Surveillance ingestion uses the exact same authoritative graph mutation pipeline (`apply_bundle` / `GraphStore` / Neo4j projection). Direct database writes or parallel graph stores are strictly prohibited.
  7. **RBAC, Audit Trail & Idempotency:**
     - Ingestion requires authenticated officer principals and enforces existing case jurisdiction policies.
     - Emits dedicated audit events (`SURVEILLANCE_REPORT_UPLOADED`, `SURVEILLANCE_REPORT_INGESTED`, `SURVEILLANCE_REPORT_INGESTION_FAILED`) preserving officer identity, case ID, source record ID, and cryptographic payload integrity.
     - Repeated ingestion of the same report is idempotent: duplicate observations reuse existing nodes and corroborate existing edges without creating duplicate entities. Mutation failures cleanly abort with zero partial graph state and emit failure audit records.
- **Reason:** Field surveillance reports (stakeouts, physical sightings, vehicle tracking, rendezvous logs) provide critical time-stamped ground truth during active investigations. Establishing a dedicated, deterministic ingestion pipeline with full provenance and strict corroboration eliminates ambiguity while preventing speculative bias.
- **Consequences:** Provides a seamless, court-admissible surveillance ingestion path across backend and frontend, unified within the single authoritative investigation graph.

---

## DEC-018 — Unified IntelligenceEvent Domain Contract & Foundation (A3)
- **Date:** 2026-09-20
- **Status:** Accepted & Implemented (A3)
- **Decision:**
  1. **Unified Domain Event Contract:** Establish `IntelligenceEvent` as the foundational unified domain event contract for the NEXUS intelligence processing lifecycle, bridging document ingestion, graph mutations, network diffs, evidence assessments, intelligence pulses, verification tasks, investigator decisions, and cross-case routing.
  2. **Zero Predictive Guilt Constraint:** Exclude any `confidence`, `guilt`, or `predictive` scores from the `IntelligenceEvent` model. Intelligence events represent objective facts, actions, and detected operational state changes, never probabilistic guilt determinations.
  3. **Deterministic Canonical Identifier:** Introduce `make_intelligence_event_id` in `backend/app/db/ingestion/identifiers.py` producing `intevt-{hash12}` from case ID, event type, and payload content.
  4. **Cryptographic Payload Integrity:** Compute deterministic SHA-256 integrity hashes (`compute_payload_integrity_hash`) with sorted JSON keys, preserving evidentiary chain of custody under Section 63 BSA.
  5. **Clean Epistemic Separation:**
     - `IntelligenceEvent` represents domain events within the investigative analysis lifecycle.
     - `AuditEvent` represents administrative, security, and user action tracking for compliance. Recording an `IntelligenceEvent` emits an `AuditEventType.INTELLIGENCE_EVENT_RECORDED` audit entry.
     - Graph `Event` nodes represent real-world crime incidents or meetings within the entity network graph.
  6. **Strict Epistemic Isolation for Phase A3:**
     - Document ingestion is NOT wired to emit `IntelligenceEvent`s yet.
     - Closed-loop cascades (A7 verification workflows, A8 closed-loop graph updates, A14 cross-case routing) are deferred to their designated roadmap phases.
     - No external brokers (Kafka/RabbitMQ) introduced; persistence is managed via in-memory repository with case indexing.
  7. **Case-Level RBAC:** Endpoints `POST /nexus/intelligence/events`, `GET /nexus/intelligence/events/{event_id}`, and `GET /nexus/intelligence/events` strictly enforce case access authorization (`can_access_case`).
- **Reason:** Prior to A3, event representations across NEXUS were fragmented across disparate subsystem objects (`Event` graph nodes, `IntelligencePulsePacket`, `AuditEvent`). Unifying the event contract at the domain level provides the structural foundation for reactive intelligence propagation without introducing speculative predictive bias or untracked state transitions.
- **Consequences:** Provides a clean, typed, canonical event foundation across backend Python and frontend TypeScript contracts while maintaining 100% test passing rates.

---

## DEC-019 — Persistent Verification Tasks Workflow & Domain Contracts (A7)
- **Date:** 2026-09-20
- **Status:** Accepted & Implemented (A7)
- **Decision:**
  1. **Persistent Task Lifecycle:** Upgrade read-only recommendations (`VerificationActionItem` / `NetworkPulseItem.verification_plan`) into first-class, persistent `VerificationTask` entities governed by an explicit 7-state lifecycle:
     $$\text{CREATED} \to \text{ASSIGNED} \to \text{REQUESTED} \to \text{RECEIVED} \to \text{UNDER\_REVIEW} \to \text{VERIFIED} \mid \text{DISMISSED}$$
  2. **Zero Predictive Guilt Constraint:** Maintain strict exclusion of `confidence`, `guilt`, or `risk` scores. Verification tasks represent actionable investigative inquiries to address concrete evidentiary gaps, never automated guilt determinations.
  3. **Deterministic Canonical Identifier:** Introduce `make_verification_task_id(case_id, target_claim, requested_evidence_type, discriminator)` producing stable `vtask-{hash12}` identifiers.
  4. **Idempotent Pulse Conversion:** Converting pulse verification recommendations into tasks is strictly idempotent. Repeated calls to `/nexus/verification/tasks/from-pulse/{pulse_id}` reuse existing tasks without generating duplicates.
  5. **Terminal State Immutability:** Once a task reaches terminal state `VERIFIED` or `DISMISSED`, all subsequent state transitions, reassignments, and evidence attachments are strictly rejected with a domain error.
  6. **Authoritative Evidence References:** Verification tasks link directly to existing authoritative evidence objects (`requested_evidence_ids`, `received_evidence_ids`, `supporting_evidence_ids`, `conflicting_evidence_ids`). Attempting to attach non-existent evidence IDs is rejected.
  7. **Reuse Established Case Authorization Policy:** Enforce standard NEXUS case authorization (`can_access_case`) across all task endpoints without inventing ad-hoc role prohibitions.
  8. **Audit & Intelligence Event Integration:**
     - Emits Section 63 BSA audit events: `VERIFICATION_TASK_CREATED`, `VERIFICATION_TASK_ASSIGNED`, `VERIFICATION_TASK_TRANSITIONED`, `VERIFICATION_TASK_EVIDENCE_ATTACHED`, `VERIFICATION_TASK_DECIDED`.
     - Emits A3 `IntelligenceEvent`s: `VERIFICATION_TASK_CREATED` upon task creation and `VERIFICATION_COMPLETED` upon reaching terminal status.
  9. **Explicit Epistemic Isolation (Zero Graph Mutations):** A7 strictly ends at the verified/dismissed investigator decision. No graph mutation, no snapshot regeneration, no network diff recomputation, and no automated routing occurs in A7. Closed-loop propagation is strictly reserved for Phase A8.
- **Reason:** Real-world investigative operations require tracking, assigning, and corroborating missing evidence across jurisdictions. Read-only recommendations lacked accountability, audit history, and durable evidentiary linkage.
- **Consequences:** Empowers investigators with an immutable, verifiable action plan to bridge intelligence gaps while preserving court admissibility under Section 63 BSA.

---

## DEC-020 — First-Class Evidence Assessment Architecture & Pulse Compatibility Bridge (A5)
- **Date:** 2026-09-20
- **Status:** Accepted & Implemented (A5)
- **Decision:**
  1. **First-Class Domain Entity:** Elevate evidence assessment from an embedded sub-object inside `NetworkPulseItem` into a standalone, investigator-accessible `EvidenceAssessment` domain object:
     $$\text{Claim / Edge / Entity / Event} \to \text{Evidence Assessment} \to \text{Epistemic State} + \text{Rationale} \to \text{Verification Task / Decision}$$
  2. **Preservation of Epistemic State Semantics:** Strictly reuse existing `EpistemicState` enum (`SUPPORTS`, `CONFLICTS`, `MISSING`, `INFERRED`, `VERIFIED`). Complete exclusion of predictive confidence scores, numerical probabilities, risk metrics, or guilt determinations.
  3. **Deterministic Canonical Identifier:** Implement `make_evidence_assessment_id(case_id, claim, state, discriminator)` producing stable `evasmt-{hash12}` identifiers.
  4. **Append-Only Auditable Revision:** Assessments are immutable records; revisions do not destructively overwrite records. Revisions append to `history: list[AssessmentRevisionHistoryItem]` recording `revision_number`, `from_state`, `to_state`, `actor_id`, `timestamp`, `rationale`, and `evidence_ids`.
  5. **Authoritative Evidence Linkage:** Assessments link by reference to authoritative evidence (`evidence_ids`, `supporting_evidence_ids`, `conflicting_evidence_ids`, `missing_evidence_types`). Every referenced ID is validated against repository source records; non-existent evidence references are rejected.
  6. **Provenance Preservation:** Source IDs, source types, and observed timestamps are preserved directly from underlying evidence citations into assessment metadata.
  7. **Backward-Compatible Pulse Bridge:** `NetworkPulseItem.assessment: list[EvidenceAssessmentItem]` contract remains 100% intact. `EvidenceAssessment` provides `.to_pulse_item()` and `.from_pulse_item()` methods to allow seamless bidirectional projection without breaking existing pulse consumers or frontend components.
  8. **Audit & IntelligenceEvent Integration:**
     - Emits Section 63 BSA audit events: `EVIDENCE_ASSESSMENT_CREATED` and `EVIDENCE_ASSESSMENT_REVISED`.
     - Emits A3 `IntelligenceEvent`s with `event_type=IntelligenceEventType.EVIDENCE_ASSESSED`.
  9. **Strict Decoupling Invariants:** No graph mutations, no snapshot recalculations, no automated closed-loop propagation (A8), and no automated routing (A14) occur in A5.
- **Reason:** Investigators must independently evaluate evidentiary support, conflicts, and gaps for relationships, claims, and events across cases without requiring an active network pulse.
- **Consequences:** Enables standalone, explainable evidentiary assessment workflows while preserving complete compatibility with existing proactive pulse and verification features.


## DEC-016: Closed-Loop Propagation Architecture (A8)
- **Date:** 2026-09-20
- **Status:** Accepted & Implemented (A8)
- **Decision:**
  1. **Deterministic Closed-Loop Pipeline:** Connect authoritative investigator decisions to deterministic graph mutation, point-in-time snapshots, pure $O(N+E)$ network diffing, A3 operational domain events, and refreshed active network change pulses:
     $$\text{Investigator Decision} \to \text{Graph Mutation} \to \text{Snapshot Capture} \to \text{NetworkDiff} \to \text{IntelligenceEvents} \to \text{Pulse Refresh}$$
  2. **Strict A3 Enum Compatibility:** Restrict operational event types strictly to pre-existing members of `IntelligenceEventType`:
     - `INVESTIGATOR_DECISION`
     - `ENTITY_OBSERVED` / `RELATIONSHIP_OBSERVED`
     - `SNAPSHOT_CREATED`
     - `NETWORK_CHANGE_DETECTED`
     - `SIGNAL_GENERATED`
     Zero duplicate or ad-hoc event enums introduced.
  3. **Case-Scope Transparency:** Explicitly document that the underlying graph store (`repo.to_graph_store()`) is global; `case_scope` is recorded and transmitted strictly as investigative context/attribution metadata, never claimed as graph partitioning or case-isolated topology.
  4. **Dynamic Pulse Integrity:** Propagation filters pulses strictly from non-empty graph diffs via `_filter_network_pulses`. Under no circumstances is the static demonstration pulse `pulse-0082` emitted as dynamic intelligence or registered as a signal event.
  5. **Stable Decision ID Idempotency:** The propagation lifecycle is keyed on the stable `decision_id` (`dec-XXXX`) generated during candidate review. Subsequent invocations with the same `decision_id` return the cached completed propagation result without re-snapshotting or duplicate event emission.
  6. **Retryable & Recoverable Fault Handling:** If downstream snapshot, diff, or event emission fails after graph mutation, the valid graph mutation is NOT rolled back. Failure is tracked in the decision record, and propagation can be retried via `retry_propagation` or `POST /nexus/propagation/retry/{decision_id}`.
  7. **Human-in-the-Loop Verification Boundary:** Refreshed pulses provide `verification_plan` recommendations (`VerificationActionItem`), but A7 persistent `VerificationTask`s are NOT automatically instantiated, preserving intentional investigator review.
  8. **Strict Decoupling from A14:** Cross-jurisdiction inter-case pulse packet routing (`IntelligencePulsePacket` / A14) is completely decoupled from A8.
- **Reason:** Bridges the operational gap between investigator decisions, graph mutations, and proactive network change intelligence while adhering strictly to zero predictive guilt and deterministic audit requirements.
- **Consequences:** Enables investigators to see the immediate network consequences of verified facts in the form of refreshed pulses, diffs, and audit trails without manual snapshot orchestration.



