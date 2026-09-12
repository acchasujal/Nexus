# NEXUS Neo4j Architecture & Durable Graph Projection Specification

**System:** NEXUS — Evidence-Grounded Criminal Network Intelligence Platform  
**Target:** Smart India Hackathon 2026 — Problem Statement ID: 26189  
**Client Organization:** Ministry of Home Affairs (MHA) / National Crime Records Bureau (NCRB)  
**Theme:** Blockchain & Cybersecurity | **Division:** Women Safety Division  

---

## 1. Architectural Overview & System of Record Separation

NEXUS maintains a strict separation of database responsibilities:

1. **PostgreSQL (System of Record & Relational State)**
   - Authoritative state for user accounts, role definitions, audit event logs, investigation case metadata, raw source records, file locators, and human investigator review decisions.
   - Guaranteed ACID transactions for entity fusion confirmations, audit event appending, and ingestion batch bookkeeping.

2. **Neo4j (Authoritative Graph Backend & Traversal Engine)**
   - High-performance, explainable graph database storing canonical entities, multi-source relationship edges, case associations, and evidentiary provenance.
   - Executes multi-hop graph traversals, entity neighborhood queries, cross-case bridge identification, and network analytics without black-box predictive bias.

```
       ┌────────────────────────────────────────────────────────┐
       │               FastAPI Ingestion / Mutation             │
       └──────────────┬──────────────────────────┬──────────────┘
                      │                          │
                      ▼                          ▼
       ┌──────────────────────────────┐  ┌──────────────────────────────┐
       │          PostgreSQL          │  │       Neo4j Projection       │
       │   - Application State        │  │   - (:NexusNode {id})        │
       │   - Authoritative Sources    │  │   - [:CONNECTED_TO]          │
       │   - Immutable Audit Log      │  │   - Multi-Hop Traversals     │
       │   - Review Candidate States  │  │   - Pathfinding & Bridges    │
       └──────────────────────────────┘  └──────────────────────────────┘
```

---

## 2. Graph Schema & Idempotent Cypher Operations

### 2A. Node Schema
- Primary Label: `:NexusNode`
- Dynamic Entity Label: Matching `entity_type` (e.g. `:Person`, `:Phone`, `:Vehicle`, `:Location`, `:Organization`, `:Account`, `:Case`, `:Event`).
- Unique Identifier: `id` (Deterministic string identifier).
- Properties: `label`, `case_ids`, `badges`, and `properties_json` (preserving all arbitrary attributes losslessly).

### 2B. Schema Constraints & Indexes
Created idempotently on application startup via `Neo4jConnection.ensure_schema()`:
```cypher
CREATE CONSTRAINT nexus_node_id IF NOT EXISTS
FOR (n:NexusNode) REQUIRE n.id IS UNIQUE;

CREATE INDEX nexus_node_entity_type IF NOT EXISTS
FOR (n:NexusNode) ON (n.entity_type);
```

### 2C. Parameterized Batch Writes (UNWIND MERGE)
Idempotent batch operations ensure safe synchronization without duplicate nodes or parallel edge collisions:

**Node Upsert:**
```cypher
UNWIND $batch AS row
MERGE (n:NexusNode {id: row.id})
SET n.entity_type = row.entity_type,
    n.label = row.label,
    n.case_ids = row.case_ids,
    n.badges = row.badges,
    n.properties_json = row.properties_json
```

**Edge Upsert:**
```cypher
UNWIND $batch AS row
MATCH (src:NexusNode {id: row.source_id})
MATCH (tgt:NexusNode {id: row.target_id})
MERGE (src)-[r:CONNECTED_TO {id: row.id}]->(tgt)
SET r.edge_type = row.edge_type,
    r.weight = row.weight,
    r.confidence = row.confidence,
    r.derivation_class = row.derivation_class,
    r.start_time = row.start_time,
    r.end_time = row.end_time,
    r.source_record_id = row.source_record_id,
    r.properties_json = row.properties_json
```

---

## 3. Operational Gating & Failure Policy

NEXUS enforces a fail-closed architecture to prevent silent data fallback:

1. **No Silent Fallback to Memory:**
   When `GRAPH_BACKEND=neo4j`, the platform never serves an in-memory graph.
2. **Readiness Probe (`/ready`):**
   - Active Bolt connectivity check.
   - Validates that graph projection is synchronized (`graph.operational: true`, `graph.projection: "synced"`).
   - If Neo4j is offline or un-synced:
     - Under `NEO4J_FAILURE_POLICY=required`: Returns HTTP 503 `not_ready`.
     - Under `NEO4J_FAILURE_POLICY=degraded`: Returns HTTP 200 `degraded` with `dependencies_ready: false`.
3. **Data Operation Gating:**
   `require_graph_projection` intercepts incoming API requests and raises `ExternalServiceUnavailableError` (HTTP 503) if Neo4j is not yet operational.

---

## 4. Evidence Integrity & Cryptographic Auditing

1. **Deterministic SHA-256 Hashing:**
   - Every forensic record (FIR excerpt, CDR record, Bank transaction) generates a deterministic SHA-256 hash across canonical fields (`source_type`, `locator`, `occurred_at`, `raw_excerpt`).
2. **On-Demand Verification:**
   - Endpoint `POST /api/v1/nexus/sources/{source_id}/verify` recomputes the hash from the stored verbatim excerpt and compares against `stored_hash`.
   - Result:
     - Verified: Logs `EVIDENCE_INTEGRITY_VERIFIED`.
     - Tampered / Mismatched: Logs `EVIDENCE_INTEGRITY_MISMATCH` with expected vs. computed hash.
3. **Clickable Provenance Citations:**
   - All Copilot responses and graph inspection drawers provide clickable citations directly opening the underlying source records with forensic locators and SHA-256 signatures.

---

## 5. Deployment Environment Configuration

### Render Backend Environment Variables
```ini
ENVIRONMENT=production
GRAPH_BACKEND=neo4j
NEO4J_URI=neo4j+s://<your-cluster-id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=<secure-neo4j-password>
NEO4J_DATABASE=neo4j
NEO4J_FAILURE_POLICY=required
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<dbname>
JWT_SECRET_KEY=<32-byte-random-secret>
CORS_ORIGINS=https://nexus-eight-weld-33.vercel.app,https://nexus-frontend.onrender.com
```

### Vercel Frontend Environment Variables
```ini
VITE_API_BASE_URL=https://nexus-backend.onrender.com
```
