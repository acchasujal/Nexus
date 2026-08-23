# NEXUS REST API Reference

All endpoints are served with prefix `/api/v1` (or root where configured) and return JSON payloads.

---

## 1. Investigations & Cases

### `GET /api/v1/investigations`
List all active criminal network investigations with summary counts.
- **Query Parameters:**
  - `district` *(optional)*: Filter by district name (e.g. `Bengaluru Urban`)
  - `category` *(optional)*: Filter by crime category (e.g. `Narcotics & Drug Trafficking`)
  - `status` *(optional)*: Filter by case status (`OPEN`, `UNDER_INVESTIGATION`, `CHARGESHEETED`)
- **Response:** `list[InvestigationSummaryResponse]`

### `GET /api/v1/investigations/{case_id}`
Retrieve deep details of an investigation, including accused entities, evidence items, and timestamps.
- **Response:** `InvestigationDetailResponse`

---

## 2. Network Explorer & Graph Analytics

### `GET /api/v1/network/cases/{case_id}?depth=2`
Execute a multi-hop BFS expansion centered on a case node or suspect entity.
- **Query Parameters:** `depth` (integer, 1 to 3)
- **Response:** `NetworkGraphResponse` (`nodes`, `edges`, `centrality_scores`)

### `GET /api/v1/communities`
Retrieve detected criminal syndicates and community modules.
- **Response:** `list[CommunitySummaryResponse]`

### `GET /api/v1/influence/bridges`
Identify critical bridge nodes and articulation points connecting separate syndicates.
- **Response:** `list[BridgeNodeResponse]`

### `GET /api/v1/influence/rankings`
Retrieve high-influence network nodes ranked by betweenness and degree centrality.
- **Response:** `list[InfluenceRankingResponse]`

---

## 3. Explainable Entity Resolution

### `POST /api/v1/entity-resolution/resolve`
Resolve a suspect record against the intelligence graph.
- **Request Body:**
  ```json
  {
    "full_name": "Vikram Sharma",
    "phone_number": "9845012345",
    "vehicle_number": "KA01AB1001",
    "address_text": "MG Road, Bengaluru",
    "confidence_threshold": 0.45,
    "candidate_limit": 10
  }
  ```
- **Response:**
  ```json
  {
    "query": { ... },
    "matches": [
      {
        "matched_node_id": "person-0002",
        "confidence": 0.95,
        "status": "MATCHED",
        "matched_fields": ["full_name_phonetic", "phone_number"],
        "reason": "Phonetic name match 'Bikram Sarma'; Matching phone (9845012345)",
        "evidence_breakdown": {
          "phone_number": 1.0,
          "name_score": 1.0
        },
        "properties": { ... }
      }
    ]
  }
  ```

---

## 4. Patterns & Temporal Intelligence

### `GET /api/v1/patterns/repeat-offenders`
List suspects appearing as accused in multiple distinct investigations.

### `GET /api/v1/patterns/shared-clusters`
Detect clusters of persons sharing phone numbers, vehicles, or hideout locations.

### `GET /api/v1/timeline?case_id={case_id}`
Retrieve a chronological sequence of suspect meetings, communication bursts, and transactions.

---

## 5. Grounded Investigator Copilot

### `POST /api/v1/copilot/query`
Query the evidence-grounded intelligence copilot.
- **Request Body:**
  ```json
  {
    "query": "Show phone and syndicate links connected to case-0001",
    "case_id": "case-0001"
  }
  ```
- **Response:** `CopilotQueryResponse` (includes `answer`, `grounded_citations`, `is_refusal`, `suggested_actions`)

---

## 6. Audit & System Telemetry

### `GET /api/v1/audit?limit=50`
Retrieve the immutable audit trail (Requires `SUPERVISOR` or `ADMIN` role).

### `GET /api/v1/system/status`
Retrieve real-time graph size, node counts, and operational health metrics.
