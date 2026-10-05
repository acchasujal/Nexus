# NEXUS REST API Documentation

All API endpoints are served with prefix `/api/v1` (or root where configured) and communicate via JSON payloads.

---

## 1. Current Implemented APIs (Verified Baseline)

### 1.1 Investigations & Case Management
- **`GET /api/v1/investigations`**
  - Query parameters: `district`, `category`, `status`
  - Returns: `list[InvestigationSummaryResponse]`
- **`GET /api/v1/investigations/{case_id}`**
  - Returns comprehensive case details, accused persons, evidence items, and timestamps.
- **`GET /api/v1/cases/{case_id}/overview`**
  - Returns quick executive dashboard metrics for a specific FIR.

### 1.2 Network Explorer & Graph Analytics
- **`GET /api/v1/network/cases/{case_id}?depth=2`**
  - Executes multi-hop BFS neighborhood expansion centered on a case node or suspect entity.
- **`GET /api/v1/communities`**
  - Returns Louvain modularity clusters identifying criminal syndicates.
- **`GET /api/v1/influence/bridges`**
  - Identifies critical articulation points bridging distinct syndicate cells.
- **`GET /api/v1/influence/rankings`**
  - Returns betweenness and degree centrality rankings.
- **`GET /api/v1/nexus/network/path`**
  - Pathfinder endpoint finding shortest paths and financial routes between two entities with edge citations.

### 1.3 Explainable Entity Resolution
- **`POST /api/v1/entity-resolution/resolve`**
  - Resolves suspect candidate records against the knowledge graph using Indian phonetic matching and multi-attribute corroboration.
  - Returns match confidence, matched fields, and mathematical contribution breakdowns.
- **`GET /api/v1/nexus/entity-resolution/candidates`**
  - Returns flagged cross-case resolution candidate pairs for human review.
- **`POST /api/v1/nexus/entity-resolution/decide`**
  - Records an investigator's decision (`CONFIRMED`, `REJECTED`, `DEFERRED`) on a candidate match.

### 1.4 Patterns & Temporal Intelligence
- **`GET /api/v1/patterns/repeat-offenders`**
  - Lists repeat accused appearing across multiple FIRs.
- **`GET /api/v1/patterns/shared-clusters`**
  - Detects clusters of persons sharing phone numbers, vehicles, or addresses.
- **`GET /api/v1/timeline?case_id={case_id}`**
  - Returns chronological sequences of calls, transactions, and meetings.

### 1.5 Grounded Investigator Copilot
- **`POST /api/v1/copilot/query`**
  - Translates natural language investigative inquiries into verified graph facts with clickable Section 63 BSA evidence citations.
  - Gated by an architectural **Ethical Refusal Gate** that halts queries requesting guilt, dangerousness, or recidivism predictions.

### 1.6 Evidence Provenance & Cryptographic Integrity
- **`GET /api/v1/evidence/{evidence_id}`**
  - Returns evidence item details and chain-of-custody provenance.
- **`POST /api/v1/nexus/sources/{source_id}/verify`**
  - Verifies raw evidence payload against stored SHA-256 digest, raising an audit alert if tampered.

### 1.7 Audit & System Telemetry
- **`GET /api/v1/audit?limit=50`**
  - Returns immutable append-only audit trail logs (Requires `SUPERVISOR` or `ADMIN` role).
- **`GET /api/v1/system/status`**
  - Returns real-time graph size, node counts, index build latencies, and Neo4j connection status.
- **`GET /health`** & **`GET /ready`**
  - Liveness and readiness probes for cloud container orchestration.

---

## 2. Target API Contracts (Proactive Network Change Plane)

The following endpoints represent the target interface for upcoming P0 and P1 capabilities:

### 2.1 Graph Snapshots & Network Diff (P0)
- **`GET /api/v1/nexus/snapshots`**
  - List available point-in-time graph snapshots for an investigation.
- **`GET /api/v1/nexus/diff?before={snapshot_id}&after={snapshot_id}`**
  - Executes deterministic snapshot comparison using `NetworkDiffService`.
  - Returns: Added/removed nodes, added/removed relationships, bridge transitions, community splits/merges, and identifier drift records.

### 2.2 Network Pulse Queue (P0)
- **`GET /api/v1/nexus/pulses?priority={CRITICAL_REVIEW}`**
  - Retrieve filtered high-significance network change events.
- **`GET /api/v1/nexus/pulses/{pulse_id}`**
  - Inspect detailed pulse metrics, supporting evidence, and action windows.

### 2.3 Evidence Sufficiency & Early Warning (P0)
- **`POST /api/v1/nexus/pulses/{pulse_id}/assess-evidence`**
  - Evaluates evidence state (`SUPPORTS`, `CONFLICTS`, `MISSING`) for claims in a pulse.
- **`GET /api/v1/nexus/forecasts?case_id={case_id}`**
  - Returns constrained operational state forecasts (`JURISDICTION_SHIFT`, `IDENTIFIER_DRIFT`) with explicit uncertainty and abstention status.
- **`GET /api/v1/nexus/verification/{pulse_id}`**
  - Returns suggested next-best verification actions.

### 2.4 Cross-Branch Intelligence Pulse (P1)
- **`GET /api/v1/nexus/intelligence-pulses`**
  - Retrieve inbound cross-case intelligence packets affecting the investigator's assigned cases.
- **`POST /api/v1/nexus/intelligence-pulses/{pulse_id}/acknowledge`**
  - Acknowledge or reject receipt of routed intelligence, recorded in the audit log.

### 2.5 Explainable Case DNA (P2)
- **`GET /api/v1/nexus/case-dna/{case_id}`**
  - Returns structural and topological similarity breakdown against historical syndicates.


### Staged startup availability (2026-10-05)
With NEO4J_BACKGROUND_STARTUP=true, repository-backed bootstrap/pulses and authentication are available before graph projection completes. Live graph traversals and graph-changing operations return 503 until both sync and durable graph read finish. /health remains process liveness; /ready retains the required dependency policy. No payload contract changes. Bootstrap KPIs derive from the same active pulse assessments as the queue; they are not static historical demo counts.

Readiness also reports `startup.factory_to_http_ready_ms` (excludes earlier imports/platform scheduling) and `graph_initialization` status, stage, elapsed_ms and sanitized exception type if initialization fails. These diagnostics contain no credential or exception-message data and do not replace operational graph readiness.
