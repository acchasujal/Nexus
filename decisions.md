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

