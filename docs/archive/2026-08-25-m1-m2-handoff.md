# NEXUS M1 → M2 Technical Handoff
## Graph Intelligence Contract & Data Ingestion Requirements

> **Target Platform:** NEXUS — Evidence-Grounded Criminal Network Intelligence Platform  
> **Problem Statement:** SIH 2026 PS 26189 (Ministry of Home Affairs / National Crime Records Bureau)  
> **Author:** M1 (Graph & Network Intelligence Workstream)  
> **Target Audience:** Vikram (M2: Data Ingestion & Processing Workstream)  
> **Date:** August 24, 2026  
> **Repository Commit:** `8926c5f` (`origin/develop`)  

---

## 1. Executive Summary

M1 has finalized the **Graph Intelligence Layer** for NEXUS. This includes canonical graph projection, degree/betweenness centrality, Louvain community detection, articulation point bridge discovery, deterministic pattern detection rules, cross-case bridge identification, and temporal snapshot diffing.

M2 (Data Ingestion / Processing) is responsible for parsing raw intelligence sources (FIR text logs, CDR call logs, bank transaction ledgers, intel reports) and mapping them into canonical **Graph Schema V2** objects (`GraphStore`).

```
  ┌──────────────────┐
  │  Raw Data Logs   │ (FIRs, CDRs, Bank Ledgers, Intel Reports)
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ M2 Ingestion &   │ (Parser, Entity Resolution, Canonicalization)
  │ Entity Resolution│
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │ Graph Schema V2  │ (Nodes, Relationships, SourceRecord Lineage)
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │    GraphStore    │ (Unified In-Memory Investigation Graph)
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │   M1 Graph       │ (Centrality, Bridges, Louvain, Patterns,
  │  Intelligence    │  Cross-Case Bridges, Snapshot Diff)
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────┐
  │  Investigation   │ (Evidence-Grounded Intelligence Workspace)
  │     Insights     │
  └──────────────────┘
```

> [!IMPORTANT]
> **Strict Non-Negotiable Contract:** M2 MUST strictly adhere to the canonical Graph Schema V2 definitions documented in this specification. M2 MUST NOT invent ad-hoc node fields, unlisted relationship types, or arbitrary risk scores.

---

## 2. M1 Completion Status

All M1 graph algorithms and intelligence modules are implemented, 100% deterministic, evidence-grounded, and validated by unit tests.

| Module | Implementation File | Purpose | M2 Dependency |
| :--- | :--- | :--- | :--- |
| **Graph Schema V2** | [`graph_schema.py`](file:///c:/Users/dyara/Nexus/backend/app/core/graph/graph_schema.py) | Declarative schema contract for nodes, edges, enums, and provenance. | Strict compliance with node/edge structures and enums. |
| **Person Projection** | [`projection.py`](file:///c:/Users/dyara/Nexus/backend/app/core/graph/algorithms/projection.py) | Projects heterogeneous graph into Person-Only graph via shared phones, bank transfers, events, etc. | Must emit valid `USED_PHONE`, `OWNS_ACCOUNT`, `TRANSFERRED_TO`, `PRESENT_AT`, `COMMUNICATED_WITH` edges. |
| **Centrality** | [`centrality.py`](file:///c:/Users/dyara/Nexus/backend/app/core/graph/algorithms/centrality.py) | Computes normalized Degree Centrality and Betweenness Centrality on Person-Only projection. | Requires accurate Person node linkage and edge connectivity. |
| **Bridge Intelligence** | [`bridges.py`](file:///c:/Users/dyara/Nexus/backend/app/core/graph/algorithms/bridges.py) | Identifies graph articulation points connecting disconnected network components. | Requires structural integrity of Person projection. |
| **Louvain Communities** | [`communities.py`](file:///c:/Users/dyara/Nexus/backend/app/core/graph/algorithms/communities.py) | Detects dense criminal clusters using modularity optimization with deterministic ties. | Requires accurate edge weights and network topologies. |
| **Pattern Rules** | [`pattern_rules.py`](file:///c:/Users/dyara/Nexus/backend/app/core/graph/algorithms/pattern_rules.py) | Detects shared devices, communication bursts near events, and circular/repeated financial flows. | Requires timestamps, phone usage edges, account transfers, and event records with provenance. |
| **Cross-Case Bridges** | [`cross_case.py`](file:///c:/Users/dyara/Nexus/backend/app/core/graph/algorithms/cross_case.py) | Discovers entities connecting $\ge 2$ distinct investigation cases with source evidence. | Requires stable canonical entity IDs across cases and valid Case relationship/provenance links. |
| **Snapshot Diff** | [`snapshot_diff.py`](file:///c:/Users/dyara/Nexus/backend/app/core/graph/algorithms/snapshot_diff.py) | Computes $O(N+E)$ temporal graph diffs between snapshot states. | Requires **stable Node.id** and **stable Relationship.id** across ingestion runs. |

---

## 3. Graph Schema V2 — Canonical Contract

### 3.1 Base Node Model (`GraphEntityBase` / `Node`)
Defined in [`backend/app/core/graph/entities.py`](file:///c:/Users/dyara/Nexus/backend/app/core/graph/entities.py).

```python
class GraphEntityBase(BaseModel):
    id: str
    entity_type: GraphEntityType = GraphEntityType.PERSON
    canonical_label: str = ""
    aliases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    source_id: Optional[str] = None        # Internal / Legacy backward-compatibility ONLY
    source_type: Optional[str] = None      # Internal / Legacy backward-compatibility ONLY
    properties: dict[str, Any] = Field(default_factory=dict) # Synced with attributes
```

#### Field Specifications

| Field Name | Type | Required/Optional | Constraints & Semantics | Canonical vs Legacy |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `str` | **Required** | Non-empty string. Must be stable across ingestion runs. | **CANONICAL V2** |
| `entity_type` | `GraphEntityType` | **Required** | Enum value from `GraphEntityType` (e.g. `"Person"`, `"Phone"`). | **CANONICAL V2** |
| `canonical_label` | `str` | **Required** | Human-readable primary label (e.g. `"Rahul Kumar"`, `"9876543210"`). | **CANONICAL V2** |
| `aliases` | `list[str]` | Optional | List of alias strings. Default: `[]`. | **CANONICAL V2** |
| `attributes` | `dict[str, Any]` | Optional | Arbitrary structured metadata dictionary. Automatically synced with `properties`. | **CANONICAL V2** |
| `confidence` | `float` | **Required** | Float between `0.0` and `1.0`. Default: `1.0`. | **CANONICAL V2** |
| `created_at` | `datetime` | Optional | ISO-8601 UTC timestamp. Default: current UTC time. | **CANONICAL V2** |
| `updated_at` | `datetime` | Optional | ISO-8601 UTC timestamp. Default: current UTC time. | **CANONICAL V2** |
| `source_id` | `Optional[str]` | Optional | Pointer to legacy source record string. | *LEGACY / INTERNAL* |
| `source_type` | `Optional[str]` | Optional | Pointer to legacy source type. | *LEGACY / INTERNAL* |
| `properties` | `dict[str, Any]` | Optional | Property dictionary (kept in 1:1 sync with `attributes`). | *LEGACY / INTERNAL* |

> [!CAUTION]
> **Canonical Handoff Rule:** `source_id` and `source_type` on node objects exist strictly for legacy backward compatibility. In Graph Schema V2, provenance MUST be represented through `SourceRecord` nodes and `source_record_id` attributes on relationships.

---

## 4. Relationship V2 Contract

Defined in [`backend/app/core/graph/edges.py`](file:///c:/Users/dyara/Nexus/backend/app/core/graph/edges.py).

```python
class GraphEdge(BaseModel):
    id: Optional[str] = None
    source_id: str
    target_id: str
    edge_type: GraphRelationshipType
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    derivation_class: DerivationClass = DerivationClass.FACT
    source_record_id: Optional[str] = None
    storage_mode: EdgeStorageMode = EdgeStorageMode.STORED
    weight: float = 1.0
    created_at: datetime = Field(default_factory=_utcnow)
    provenance: EvidenceProvenance = Field(default_factory=EvidenceProvenance)
    properties: dict[str, Any] = Field(default_factory=dict)
```

#### Field Specifications

| Field Name | Type | Required/Optional | Constraints & Semantics |
| :--- | :--- | :--- | :--- |
| `id` | `str` | **Required** | Stable relationship identifier. If omitted, auto-generated as `rel_{source_id}_{edge_type}_{target_id}`. |
| `source_id` | `str` | **Required** | Non-empty Node ID of the source entity. |
| `target_id` | `str` | **Required** | Non-empty Node ID of the target entity. |
| `edge_type` | `GraphRelationshipType` | **Required** | Valid enum value (e.g. `"COMMUNICATED_WITH"`, `"USED_PHONE"`). |
| `start_time` | `Optional[datetime]` | Optional | ISO-8601 UTC timestamp for start of relationship or call/transaction time. |
| `end_time` | `Optional[datetime]` | Optional | ISO-8601 UTC timestamp for end of relationship. Must be $\ge$ `start_time`. |
| `confidence` | `float` | **Required** | Float between `0.0` and `1.0`. Default: `1.0`. |
| `derivation_class` | `DerivationClass` | **Required** | Enum: `"FACT"` (from source data), `"DERIVED"` (algorithm output), `"HYPOTHESIS"`. |
| `source_record_id` | `Optional[str]` | **Required for Facts** | Node ID of the backing `SourceRecord` node (e.g., `"src_fir_001"`). |
| `storage_mode` | `EdgeStorageMode` | Optional | `"STORED"` (persisted fact) or `"COMPUTED"` (virtual/derived). |
| `weight` | `float` | Optional | Numeric edge weight score (default `1.0`). |
| `provenance` | `EvidenceProvenance` | Optional | Nested citation object synced automatically with `source_record_id` and `confidence`. |
| `properties` | `dict[str, Any]` | Optional | Arbitrary metadata (e.g. `amount`, `call_duration_seconds`, `utr`). |

---

## 5. Canonical Enums

Defined in [`backend/app/core/graph/enums.py`](file:///c:/Users/dyara/Nexus/backend/app/core/graph/enums.py).

### 5.1 `GraphEntityType` (20 Enum Values)

```python
class GraphEntityType(str, Enum):
    # Core Investigation Entities
    PERSON = "Person"
    CASE = "Case"
    PHONE = "Phone"
    VEHICLE = "Vehicle"
    LOCATION = "Location"
    ORGANIZATION = "Organization"
    DEVICE = "Device"
    ACCOUNT = "Account"
    TRANSACTION = "Transaction"
    EVENT = "Event"
    INTELLIGENCE_REPORT = "IntelligenceReport"
    EVIDENCE = "Evidence"
    SOURCE_RECORD = "SourceRecord"
    
    # Supporting Domain Entities
    OFFICER = "Officer"
    UNIT = "Unit"
    COURT = "Court"
    ACT = "Act"
    SECTION = "Section"
    CRIME_HEAD = "CrimeHead"
    CRIME_SUB_HEAD = "CrimeSubHead"
```

### 5.2 `GraphRelationshipType` (30 Enum Values)

```python
class GraphRelationshipType(str, Enum):
    # Case participations
    INVOLVED_IN = "INVOLVED_IN"
    ACCUSED_IN = "ACCUSED_IN"
    VICTIM_IN = "VICTIM_IN"
    COMPLAINANT_IN = "COMPLAINANT_IN"
    WITNESS_IN = "WITNESS_IN"

    # Direct entity associations
    USED_PHONE = "USED_PHONE"
    USED_VEHICLE = "USED_VEHICLE"
    OWNS_VEHICLE = "OWNS_VEHICLE"
    SEEN_AT = "SEEN_AT"
    PRESENT_AT = "PRESENT_AT"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    CONNECTED_TO = "CONNECTED_TO"
    OWNS_ACCOUNT = "OWNS_ACCOUNT"
    TRANSFERRED_TO = "TRANSFERRED_TO"
    TRANSFERRED_FUNDS = "TRANSFERRED_FUNDS"
    COMMUNICATED_WITH = "COMMUNICATED_WITH"
    SHARED_PHONE = "SHARED_PHONE"
    OCCURRED_AT = "OCCURRED_AT"
    OCCURRED_IN = "OCCURRED_IN"
    PARTICIPATED_IN = "PARTICIPATED_IN"
    MENTIONED_IN = "MENTIONED_IN"
    HAS_EVIDENCE = "HAS_EVIDENCE"
    SUPPORTED_BY = "SUPPORTED_BY"
    CHARGED_UNDER = "CHARGED_UNDER"
    INVESTIGATED_BY = "INVESTIGATED_BY"
    BELONGS_TO_UNIT = "BELONGS_TO_UNIT"
    CO_ACCUSED_WITH = "CO_ACCUSED_WITH"
    LINKED_TO = "LINKED_TO"
    CITES_SOURCE = "CITES_SOURCE"
```

### 5.3 `DerivationClass` (3 Enum Values)

```python
class DerivationClass(str, Enum):
    FACT = "FACT"          # Directly extracted from an imported source document/record
    DERIVED = "DERIVED"    # Computed deterministically by M1 algorithms/rules
    HYPOTHESIS = "HYPOTHESIS" # Human-entered investigative lead or hypothesis
```

---

## 6. Source Record & Provenance Contract

### 6.1 `SourceRecord` Node Specification
Every imported data payload (FIR document, CDR CSV row, Bank ledger transaction, Intel PDF) MUST produce a first-class `SourceRecord` node in `GraphStore`:

```python
class SourceRecord(GraphEntityBase):
    entity_type: GraphEntityType = GraphEntityType.SOURCE_RECORD
    id: str                  # e.g., "src_fir_2026_001" or "src_cdr_line_1042"
    batch_id: str = ""       # Ingestion batch identifier
    source_type: str = ""    # "FIR", "CDR", "BANK_TXN", "INTEL_REPORT"
    locator: str = ""        # File path, line number, FIR #, or UTR
    raw_excerpt: str = ""    # Original raw text log snippet or raw JSON payload
    hash: Optional[str] = None # SHA-256 hash of the raw record
    occurred_at: datetime = Field(default_factory=_utcnow)
```

### 6.2 Lineage Chain Architecture

```
┌─────────────────────────────────────────────────────────┐
│              SourceRecord Node ("src_001")               │
│ (source_type="CDR", locator="cdr_log_20260824.csv:L42") │
└────────────────────────────┬────────────────────────────┘
                             │
                             │ (source_record_id = "src_001")
                             ▼
┌─────────────────────────────────────────────────────────┐
│     GraphEdge ("rel_phone1_COMMUNICATED_WITH_phone2")   │
│  edge_type="COMMUNICATED_WITH", derivation_class="FACT" │
└────────────────────────────┬────────────────────────────┘
                             │
                             │ (consumed by M1 Scanner)
                             ▼
┌─────────────────────────────────────────────────────────┐
│                   M1 Derived Finding                    │
│ rule_id="communication_burst_near_event"                │
│ evidence_ids=["src_001"], derivation_class="DERIVED"    │
└─────────────────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Provenance Refusal Rule:** Every derived M1 finding checks for backing `evidence_ids` via `source_record_id` on relationships or `CITES_SOURCE` edges. If M2 emits edges without `source_record_id`, M1 algorithms will **suppress** pattern rules and cross-case bridge findings.

---

## 7. Confidence & Temporal Contracts

### 7.1 Confidence Contract
- **Type:** `float`
- **Range:** $0.0 \le \text{confidence} \le 1.0$
- **Default:** `1.0`
- **Forbidden:** Percentage integers (e.g. `95` or `100`).
- **Semantics:** Represents data extraction or entity-resolution certainty. It is **NOT** a risk, guilt, or criminality score.

### 7.2 Temporal Contract
- **Type:** ISO-8601 UTC `datetime` strings or standard Python `datetime` objects.
- **Fields:** `start_time`, `end_time` (on relationships), `timestamp` / `occurred_at` (on nodes/records).
- **Temporal Window Rules:**
  - `communication_burst_near_event`: Requires `Event.timestamp` and `COMMUNICATED_WITH` edge `start_time` / `timestamp`. The M1 default burst window is **$\pm 15$ minutes** around event time, requiring $\ge 3$ communications.
  - `snapshot_diff`: Compares graph states across two points in time.
  - `circular_repeated_financial_flow`: Evaluates repeated transfers and timestamp sequences.

---

## 8. M1 → M2 Data Dependency Matrix

| M1 Algorithm Module | Required Entity Types | Required Relationships | Required Fields | Provenance Required? | Timestamp Required? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Person Projection** | `Person`, `Phone`, `Account`, `Vehicle`, `Location`, `Event` | `USED_PHONE`, `OWNS_ACCOUNT`, `TRANSFERRED_TO`, `TRANSFERRED_FUNDS`, `COMMUNICATED_WITH`, `PRESENT_AT` | Node `id`, `entity_type`, Edge `source_id`, `target_id` | Optional | Optional |
| **Degree & Betweenness Centrality** | Derived Person Projection | Projected Person edges | Node `id`, `canonical_label` | Optional | No |
| **Bridge Intelligence** | Derived Person Projection | Projected Person edges | Node `id`, `canonical_label` | Optional | No |
| **Louvain Communities** | Derived Person Projection | Projected Person edges | Node `id`, Edge `weight` | Optional | No |
| **Shared Phone / Device Rule** | `Person`, `Phone`, `Device` | `USED_PHONE`, `USED_DEVICE` | `source_record_id` | **YES** | No |
| **Communication Burst Rule** | `Phone`, `Person`, `Event` | `COMMUNICATED_WITH`, `USED_PHONE`, `PARTICIPATED_IN` | `start_time` / `timestamp`, `source_record_id` | **YES** | **YES** ($\pm 15$ min) |
| **Repeated Financial Flow Rule** | `Account`, `Person` | `TRANSFERRED_FUNDS`, `TRANSFERRED_TO`, `OWNS_ACCOUNT` | `amount`, `source_record_id`, `timestamp` | **YES** | Optional ($\ge 3$ transfers) |
| **Cross-Case Bridge Rule** | Any entity type, `Case`, `SourceRecord` | `ACCUSED_IN`, `INVOLVED_IN`, `VICTIM_IN`, `COMPLAINANT_IN`, `WITNESS_IN`, `INVESTIGATED_BY`, `PARTICIPATED_IN`, `MENTIONED_IN`, `HAS_EVIDENCE`, `CITES_SOURCE` | Stable canonical Entity `id`, `Case.id`, `source_record_id` | **YES** | No |
| **Temporal Snapshot Diff** | Any canonical entity / relationship | Any canonical relationship | Stable `Node.id`, Stable `Relationship.id`, `properties` | Optional | Optional |

---

## 9. Specific Pattern Requirements for Ingestion

### 9.1 Shared Phone / Device Pattern
M2 must ingest raw CDR/owner records and produce:
- `Person A` node (`id="p1"`)
- `Person B` node (`id="p2"`)
- `Phone X` node (`id="ph1"`)
- Edge 1: `p1 ──USED_PHONE──> ph1` (`source_record_id="src_cdr_1"`)
- Edge 2: `p2 ──USED_PHONE──> ph1` (`source_record_id="src_cdr_2"`)

> [!NOTE]
> M2 should **NOT** create a direct `p1 ──SHARED_PHONE──> p2` edge. M1's `detect_shared_phone_device()` rule scans for shared intermediate `Phone` / `Device` nodes and projects the explainable finding deterministically. `Vehicle` entities are strictly excluded from device sharing rules.

### 9.2 Communication Burst Near Event Pattern
M2 must produce:
- `Event` node (`id="ev_001"`, `timestamp="2026-08-24T14:00:00Z"`)
- `Phone P1` and `Phone P2` connected via $\ge 3$ `COMMUNICATED_WITH` edges with `start_time` within `13:45:00Z` to `14:15:00Z`.
- Edges MUST contain valid `source_record_id` pointers.

### 9.3 Circular / Repeated Financial Flow Pattern
M2 must produce:
- `Account A`, `Account B`, `Account C`
- `TRANSFERRED_FUNDS` or `TRANSFERRED_TO` edges carrying `amount`, `timestamp`, and `source_record_id`.
- Repeated flow requires $\ge 3$ transfers between the same ordered account pair (`Account A → Account B`).

---

## 10. Cross-Case Bridge Requirements

For M1 to detect that an entity (Person, Phone, Vehicle, Account, etc.) forms a cross-case bridge between Case A and Case B:
1. M2 must resolve the entity to the **SAME canonical Node ID** across both cases.
2. The entity must have valid, evidence-backed case membership relationships in both cases:
   - Direct: `Entity ──ACCUSED_IN / INVOLVED_IN / ...──> Case` (with `source_record_id`).
   - Indirect: `Entity ──LINKED_TO──> SourceRecord ──INVOLVED_IN / case_id metadata──> Case`.
3. If distinct node IDs are generated (`person_001` "Rahul Kumar" in Case A and `person_002` "Rahul Kumar" in Case B), M1 will treat them as two separate individuals and **will not** merge them. Entity resolution MUST be performed during M2 ingestion.

---

## 11. Snapshot Diff Requirements & ID Stability

M1's `diff_graph_snapshots(before, after)` compares graph snapshots in $O(N+E)$ time using exact ID matching:
- Node Identity: `Node.id`
- Relationship Identity: `Relationship.id`

> [!CAUTION]
> **Random ID Hazard:** If M2 generates random UUIDs (`uuid4()`) for nodes or relationships on every re-ingestion pass of the same dataset, `snapshot_diff` will report every single entity as `removed` and `re-added`, producing false diff output. Node IDs and Relationship IDs emitted by M2 MUST be deterministic and stable (e.g., hashed from natural keys: `hash(phone_number)`, `hash(fir_number + suspect_name)`, or `rel_{src}_{type}_{tgt}`).

---

## 12. What Vikram Must NOT Do

```
❌ DO NOT invent new entity types not present in GraphEntityType enum.
❌ DO NOT invent new relationship types not present in GraphRelationshipType enum.
❌ DO NOT use percentage integers for confidence (e.g. 95). Use floats (0.0 to 1.0).
❌ DO NOT generate random UUIDs on every ingestion run for stable entities.
❌ DO NOT merge distinct entity IDs based solely on identical canonical_label strings.
❌ DO NOT fabricate fake SourceRecord nodes or fake evidence IDs.
❌ DO NOT omit source_record_id on factual edges where provenance exists.
❌ DO NOT collapse shared phone relationships into direct Person->Person edges.
❌ DO NOT treat Vehicle entities as Phone/Device entities.
❌ DO NOT output guilt scores, probability of criminality, or mastermind scores.
❌ DO NOT modify M1 core algorithm files to bypass schema validation.
```

---

## 13. Required M2 Output Examples (JSON)

### 13.1 Canonical Person Node
```json
{
  "id": "person_rahul_sharma_101",
  "entity_type": "Person",
  "canonical_label": "Rahul Sharma",
  "aliases": ["Rahul", "Sharmaji"],
  "confidence": 0.95,
  "created_at": "2026-08-24T10:00:00Z",
  "updated_at": "2026-08-24T10:00:00Z",
  "attributes": {
    "full_name": "Rahul Sharma",
    "phone_numbers": ["9876543210"],
    "national_id": "ABCPB1234K",
    "addresses": ["Sector 17, Chandigarh"]
  }
}
```

### 13.2 Canonical Phone Node
```json
{
  "id": "phone_9876543210",
  "entity_type": "Phone",
  "canonical_label": "9876543210",
  "confidence": 1.0,
  "attributes": {
    "phone_number": "9876543210",
    "imei": "864201040506070",
    "carrier": "Airtel"
  }
}
```

### 13.3 Canonical Account Node
```json
{
  "id": "acc_sbi_998877",
  "entity_type": "Account",
  "canonical_label": "SBI-998877",
  "confidence": 1.0,
  "attributes": {
    "account_number": "998877665544",
    "bank_name": "State Bank of India",
    "ifsc_code": "SBIN0001234"
  }
}
```

### 13.4 Canonical Vehicle Node
```json
{
  "id": "veh_ch01ab1234",
  "entity_type": "Vehicle",
  "canonical_label": "CH01AB1234",
  "confidence": 1.0,
  "attributes": {
    "registration_number": "CH01AB1234",
    "vehicle_type": "Car",
    "make": "Hyundai",
    "model": "Creta"
  }
}
```

### 13.5 Canonical Event Node
```json
{
  "id": "evt_robbery_meeting_01",
  "entity_type": "Event",
  "canonical_label": "Pre-Incident Meeting",
  "confidence": 0.90,
  "attributes": {
    "event_type": "MEETING",
    "description": "Suspected coordination meeting",
    "timestamp": "2026-08-24T14:00:00Z"
  }
}
```

### 13.6 Canonical SourceRecord Node
```json
{
  "id": "src_fir_2026_099",
  "entity_type": "SourceRecord",
  "canonical_label": "FIR No. 99/2026",
  "confidence": 1.0,
  "attributes": {
    "batch_id": "batch_20260824_01",
    "source_type": "FIR",
    "locator": "PS_Sector_17/FIR_99_2026.pdf",
    "raw_excerpt": "Complainant reported theft of vehicle CH01AB1234...",
    "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "occurred_at": "2026-08-24T08:30:00Z"
  }
}
```

### 13.7 Communication Relationship
```json
{
  "id": "rel_cdr_call_8899",
  "source_id": "phone_9876543210",
  "target_id": "phone_9123456789",
  "edge_type": "COMMUNICATED_WITH",
  "start_time": "2026-08-24T14:05:00Z",
  "end_time": "2026-08-24T14:08:30Z",
  "confidence": 1.0,
  "derivation_class": "FACT",
  "source_record_id": "src_cdr_batch_44",
  "properties": {
    "duration_seconds": 210,
    "call_type": "OUTGOING"
  }
}
```

### 13.8 Financial Transfer Relationship
```json
{
  "id": "rel_txn_utr_998877",
  "source_id": "acc_sbi_998877",
  "target_id": "acc_hdfc_112233",
  "edge_type": "TRANSFERRED_FUNDS",
  "start_time": "2026-08-24T11:15:00Z",
  "confidence": 1.0,
  "derivation_class": "FACT",
  "source_record_id": "src_bank_stmt_01",
  "properties": {
    "amount": 150000.0,
    "currency": "INR",
    "utr": "UTR9988776655"
  }
}
```

### 13.9 Case Association Relationship
```json
{
  "id": "rel_accused_case_99",
  "source_id": "person_rahul_sharma_101",
  "target_id": "case_fir_99_2026",
  "edge_type": "ACCUSED_IN",
  "confidence": 1.0,
  "derivation_class": "FACT",
  "source_record_id": "src_fir_2026_099",
  "properties": {
    "role": "PRIMARY_ACCUSED"
  }
}
```

### 13.10 Provenance Citation Relationship
```json
{
  "id": "rel_cites_source_001",
  "source_id": "evidence_cctv_01",
  "target_id": "src_fir_2026_099",
  "edge_type": "CITES_SOURCE",
  "confidence": 1.0,
  "derivation_class": "FACT",
  "source_record_id": "src_fir_2026_099"
}
```

---

## 14. M2 Ingestion Acceptance Checklist

Before handing ingestion output over to M1 integration testing, Vikram must verify:

### Schema Validation
- [ ] Every node instantiates clean without Pydantic validation errors.
- [ ] Every relationship instantiates clean without Pydantic validation errors.
- [ ] `entity_type` values match `GraphEntityType` enum exact casing.
- [ ] `edge_type` values match `GraphRelationshipType` enum exact casing.

### Identity & Determinism
- [ ] Node `id` strings are non-empty and stable across re-ingestion.
- [ ] Relationship `id` strings are non-empty and stable across re-ingestion.
- [ ] Multiple calls between the same two phones contain distinct relationship IDs.

### Provenance
- [ ] Every imported document creates a corresponding `SourceRecord` node.
- [ ] Factual edges contain valid `source_record_id` pointers matching an existing `SourceRecord.id`.
- [ ] `derivation_class` is set to `"FACT"` for raw imported edges.

### Confidence & Time
- [ ] `confidence` values are floats between `0.0` and `1.0`.
- [ ] `start_time` and `end_time` are ISO-8601 UTC strings.
- [ ] `start_time` $\le$ `end_time`.

### M1 Compatibility Verification
- [ ] Shared phone scenarios generate intermediate `Phone` nodes connected via `USED_PHONE`.
- [ ] Communication burst scenarios generate `COMMUNICATED_WITH` edges with valid timestamps.
- [ ] Financial flow scenarios generate `TRANSFERRED_FUNDS` edges with `amount` properties.
- [ ] Cross-case bridging entities use unified canonical Node IDs across cases.

---

## 15. Test & Handoff Verification Procedure

1. **Run Ingestion:** Execute M2 parser on synthetic dataset (`synthetic_data/nexus_generator.py`).
2. **Build GraphStore:** Construct `GraphStore` via `build_graph_store(nodes, edges)`.
3. **Run M1 Test Suite:**
   ```bash
   python -m pytest
   ```
   All **428 Pytest unit tests** MUST continue to pass 100% clean.
4. **Run Ground Truth Evaluator:**
   ```bash
   python scripts/evaluate_ground_truth.py
   ```
   Must achieve **100% Precision / Recall** on synthetic ground-truth benchmarks.

---

## 16. Current Test Status

- **Total Test Suite:** 428 unit tests
- **Passed:** **428** (100% Pass Rate)
- **Failed:** **0**
- **Branch:** `origin/develop` (Commit: `8926c5f`)

---

## 17. Contract Ambiguities Requiring Team Decision

During the M1 codebase audit, the following structural dualities were identified:

1. **`attributes` vs `properties` Dual Storage:**  
   `GraphEntityBase` keeps `attributes` and `properties` in sync via a Pydantic model validator. M2 should populate `attributes`, but can read from either.
2. **Person Phone Numbers (`Person.phone_numbers` vs `Phone` Nodes):**  
   `Person` nodes support an internal `phone_numbers` list attribute. However, M1 pattern rules (like `shared_phone_device`) require explicit `Phone` nodes connected via `USED_PHONE` edges. M2 must emit explicit `Phone` nodes for network algorithms.
3. **Direct Case Links vs `SourceRecord` Case Metadata:**  
   Cross-case bridging evaluates both direct `Entity ──ACCUSED_IN──> Case` edges and `Entity ──> SourceRecord` edges where `SourceRecord.properties` has `case_id` or `fir_number`. Emitting explicit direct `Case` relationships is recommended for maximum performance.

---

## 18. What Vikram Needs to Do Next

1. Review this document ([`docs/M1_M2_HANDOFF.md`](file:///c:/Users/dyara/Nexus/docs/M1_M2_HANDOFF.md)).
2. Update M2 ingestion parsers (`backend/app/db/` or `synthetic_data/`) to output Graph Schema V2 nodes and edges matching the JSON examples in Section 13.
3. Ensure deterministic ID generation for nodes and edges.
4. Ensure `SourceRecord` nodes and `source_record_id` provenance attributes are populated on all raw facts.
5. Verify M2 ingestion output by passing the generated `GraphStore` into `detect_all_suspicious_patterns()` and `detect_cross_case_bridges()`.
6. Run `python -m pytest` to confirm all 428 tests pass clean.
7. Coordinate with the M1 team before making any changes to `GraphEntityType` or `GraphRelationshipType` enums.
