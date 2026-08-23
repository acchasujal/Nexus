# NEXUS — Intelligence Processing Pipeline

The NEXUS intelligence pipeline transforms heterogeneous, unstructured, and noisy crime records into an evidence-grounded graph intelligence workspace.

```mermaid
flowchart LR
    S1[1. Multi-Source Ingestion] --> S2[2. Normalization & NER]
    S2 --> S3[3. Entity Resolution]
    S3 --> S4[4. Graph Construction]
    S4 --> S5[5. Modularity & Centrality]
    S5 --> S6[6. Temporal Sequencing]
    S6 --> S7[7. Provenance & Copilot]
```

---

## Pipeline Stage Breakdown

### 1. Multi-Source Ingestion
- **Purpose:** Ingest unstructured crime reports and structured telemetry logs.
- **Input:** PDF/TXT FIR narratives, CSV CDR phone logs, IMPS/NEFT/UPI bank transaction files.
- **Output:** Canonical JSON document records.
- **Status:** **Implemented** (local file readers & synthetic generator).
- **Technology:** Python `json`, standard CSV/text parsers.
- **Known Limitations:** Ingestion of proprietary scanned TIFF/OCR formats currently requires pre-processing into text.

### 2. Entity Normalization & Extraction
- **Purpose:** Extract standardized entities and clean noisy Indian vernacular text.
- **Input:** Raw textual narratives and structured records.
- **Output:** Normalized name tokens, phone numbers (10-digit MSISDN), vehicle registrations (e.g. `KA01AB1001`), and UTC timestamps.
- **Status:** **Implemented**.
- **Technology:** Python regex normalizers, custom Indian phonetic normalizer (`phonetic_normalize`).
- **Known Limitations:** Custom domain spaCy fine-tuning is planned for Phase 2.

### 3. Explainable Entity Resolution (Disambiguation)
- **Purpose:** Resolve whether multiple suspect records represent the same individual without manual merging.
- **Input:** Suspect candidate query vs. Graph person profiles.
- **Output:** Match score ($0.0 - 1.0$), confidence tier (`MATCHED`, `PROBABLE_MATCH`, `REVIEW_REQUIRED`, `NOT_MATCHED`), and exact evidence breakdown.
- **Status:** **Implemented & Benchmarked** (100% Precision / Recall on ground-truth dataset).
- **Technology:** Character-bigram Jaccard, Double Metaphone-style phonetic clustering, alias lookups, and hard-ID corroboration.
- **Known Limitations:** Full multi-attribute clustering runs in memory; large-scale distributed clustering (e.g. Apache Spark) is roadmap for 10M+ nodes.

### 4. Knowledge Graph Construction
- **Purpose:** Build unified in-memory property graph.
- **Input:** Normalized entities and typed relationships.
- **Output:** Indexed `GraphStore` with bidirectional adjacency lists (`adj` and `radj`).
- **Status:** **Implemented & Benchmarked** (Index build time: 6.05 ms for 445 nodes / 530 edges).
- **Technology:** In-memory Python data structures, Neo4j 5 Cypher integration.
- **Known Limitations:** Currently loads complete graph in memory; Neo4j server provides disk-backed persistence.

### 5. Syndicate Modularity & Bridge Centrality Analysis
- **Purpose:** Discover criminal syndicate structures and isolate hidden kingpin brokers.
- **Input:** `GraphStore` network topology.
- **Output:** Community partition IDs, betweenness centrality scores, and articulation bridge nodes.
- **Status:** **Implemented & Benchmarked** (Community detection: 46.07 ms; Bridge detection: 363.40 ms).
- **Technology:** NetworkX Louvain modularity algorithm, betweenness centrality.
- **Known Limitations:** Centrality on graphs exceeding 100,000 nodes requires approximate sampling or Neo4j GDS projection.

### 6. Temporal & Pattern Intelligence
- **Purpose:** Reveal chronological communication spikes, fund layering paths, and shared burner phones.
- **Input:** Timestamped event edges and entity attributes.
- **Output:** Chronological timeline events, repeat accused lists, and shared attribute clusters.
- **Status:** **Implemented**.
- **Technology:** Temporal interval queries, reverse edge index scans.
- **Known Limitations:** Visual timeline handles up to 10,000 events before requiring client-side virtualized scrolling.

### 7. Evidence Provenance & Grounded Copilot
- **Purpose:** Answer natural-language investigative questions with citations, while refusing unethical guilt predictions.
- **Input:** Officer natural language query + active case context.
- **Output:** Grounded answer, structured `GroundedCitation` list, refusal status, and suggested graph actions.
- **Status:** **Implemented & Benchmarked** (100% refusal gate accuracy across canonical test suite).
- **Technology:** `CopilotService`, deterministic intent parser, safety refusal gate.
- **Known Limitations:** Local quantized LLM for zero-shot natural language Cypher generation is scheduled for Phase 2.
