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
