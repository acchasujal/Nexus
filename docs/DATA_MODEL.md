# NEXUS Knowledge Graph Data Model & Ontology

This document is the **authoritative single source of truth** for the NEXUS graph ontology, relationship semantics, evidence provenance contracts, and target domain models.

---

## 1. Core Graph Entities (12 Entity Types)

NEXUS models 12 distinct intelligence entities representing physical, digital, and legal objects in law enforcement investigations:

| Entity Type | Description | Key Attributes (Verified in Code) | Status |
| :--- | :--- | :--- | :--- |
| **`Person`** | Suspect, co-accused, witness, victim, or informant | `id`, `full_name`, `first_name`, `last_name`, `aliases`, `phone_numbers`, `vehicle_numbers`, `address_text`, `national_id`, `is_known_offender` | CURRENT |
| **`Case`** | First Information Report (FIR) or court proceeding | `id`, `fir_number`, `title`, `station_name`, `district`, `offence_category`, `status`, `incident_date` | CURRENT |
| **`Phone`** | Monitored mobile phone or SIM identity | `id`, `phone_number`, `imei`, `imsi`, `telecom_circle`, `carrier`, `is_burner` | CURRENT |
| **`Vehicle`** | Seized or monitored vehicle | `id`, `registration_number`, `chassis_number`, `make_model`, `color`, `registered_owner` | CURRENT |
| **`Location`** | Incident scene, hideout, or meeting point | `id`, `name`, `address_text`, `city`, `district`, `latitude`, `longitude`, `location_type` | CURRENT |
| **`Organization`** | Front company, cartel, or gang | `id`, `name`, `org_type`, `registration_number`, `known_front`, `operating_districts` | CURRENT |
| **`Device`** | Seized digital device / burner hardware | `id`, `device_type`, `serial_number`, `mac_address`, `seized_from_person_id` | CURRENT |
| **`Account`** | Bank account or digital wallet | `id`, `account_number`, `bank_name`, `ifsc_code`, `account_type`, `is_flagged_mule` | CURRENT |
| **`Transaction`** | Financial wire transfer or Hawala ledger | `id`, `transaction_ref`, `amount`, `currency`, `timestamp`, `channel`, `is_suspicious` | CURRENT |
| **`Event`** | Temporal intelligence occurrence | `id`, `event_type`, `timestamp`, `description`, `participant_ids`, `location_id` | CURRENT |
| **`IntelligenceReport`** | Field intelligence briefing note | `id`, `report_number`, `source_agency`, `classification`, `summary`, `target_person_ids` | CURRENT |
| **`Evidence`** | Physical or digital seized evidence item | `id`, `evidence_number`, `case_id`, `evidence_type`, `description`, `collected_at`, `provenance` | CURRENT |

---

## 2. Relationship Edge Types

| Edge Type | Source Entity | Target Entity | Semantics | Status |
| :--- | :--- | :--- | :--- | :--- |
| **`ACCUSED_IN`** | `Person` | `Case` | Individual formally named as accused in FIR chargesheet | CURRENT |
| **`VICTIM_IN`** | `Person` | `Case` | Individual registered as complainant or victim | CURRENT |
| **`WITNESS_IN`** | `Person` | `Case` | Individual providing recorded witness statement | CURRENT |
| **`CO_ACCUSED_WITH`** | `Person` | `Person` | Joint accused named in shared criminal proceeding | CURRENT |
| **`COMMUNICATED_WITH`** | `Person` / `Phone` | `Person` / `Phone` | Telecommunication call or SMS interaction from CDR | CURRENT |
| **`ASSOCIATED_WITH`** | `Person` | `Person` / `Organization` | Syndicate, gang, or commercial affiliation | CURRENT |
| **`TRANSFERRED_MONEY_TO`**| `Account` | `Account` | Financial flow, bank transfer, or Hawala ledger entry | CURRENT |
| **`OWNS_ACCOUNT`** | `Person` / `Organization` | `Account` | Beneficial ownership of banking or wallet node | CURRENT |
| **`USES_PHONE`** | `Person` | `Phone` | Subscriber or confirmed device user | CURRENT |
| **`DRIVES_VEHICLE`** | `Person` | `Vehicle` | Driver or registered owner of vehicle | CURRENT |
| **`LOCATED_AT`** | `Person` / `Event` | `Location` | Spatial presence, tower ping, or incident scene | CURRENT |
| **`MENTIONED_IN`** | `Person` / `Organization` | `IntelligenceReport` | Referenced in intelligence briefing memo | CURRENT |
| **`RESOLVED_TO`** | `Person` | `Person` | Cross-source entity resolution link with match confidence | CURRENT |
| **`HAS_EVIDENCE`** | `Case` | `Evidence` | Evidence item tagged to specific investigation | CURRENT |

---

## 3. Evidence Provenance Contract (Section 63 BSA Compliant)

Every edge and derived intelligence relationship retains an unbroken chain of custody:

```python
class EvidenceProvenance(BaseModel):
    source_type: str        # "FIR", "CDR", "BANK_TXN", "SEIZED_DEVICE", "INTELLIGENCE_REPORT", "SOCMINT"
    source_id: str          # Source document ID / Transaction UTR / Call log ID
    timestamp: datetime     # Timestamp of extraction or collection
    extracted_fact: str     # Specific verifiable fact extracted
    derivation_method: str  # "OFFICIAL_RECORD", "TELECOM_LOG", "FINANCIAL_LEDGER", "ALGORITHMIC_MATCH"
    confidence: float       # Confidence score (0.0 to 1.0)
```

---

## 4. Target Domain Models (Proactive Network Change Plane)

The following domain models represent the target capabilities of the proactive change intelligence plane:

### 4.1 `GraphSnapshot`
Represents an immutable, point-in-time state of an investigative graph.
```python
class GraphSnapshot(BaseModel):
    snapshot_id: str
    case_scope: str | None       # Specific case ID or "GLOBAL"
    created_at: datetime
    source_revision: str        # Hash or sequence revision of source data
    node_count: int
    edge_count: int
    version: str = "v1"
```

### 4.2 `NetworkChange`
Represents a deterministic structural difference between two snapshots.
```python
class NetworkChangeType(str, Enum):
    EDGE_ADDED = "EDGE_ADDED"
    EDGE_REMOVED = "EDGE_REMOVED"
    NODE_ADDED = "NODE_ADDED"
    NODE_REMOVED = "NODE_REMOVED"
    BRIDGE_EMERGED = "BRIDGE_EMERGED"
    BRIDGE_LOST = "BRIDGE_LOST"
    COMMUNITY_MERGED = "COMMUNITY_MERGED"
    COMMUNITY_SPLIT = "COMMUNITY_SPLIT"
    JURISDICTION_SHIFT = "JURISDICTION_SHIFT"
    IDENTIFIER_DRIFT = "IDENTIFIER_DRIFT"
    ROUTE_CHANGE = "ROUTE_CHANGE"
    OTHER = "OTHER"

class NetworkChange(BaseModel):
    change_id: str
    before_snapshot_id: str
    after_snapshot_id: str
    change_type: NetworkChangeType
    affected_entities: list[str]
    affected_relationships: list[str]
    affected_cases: list[str]
    significance_score: float    # 0.0 to 1.0 (structural importance)
    observed_at: datetime
    evidence_refs: list[str]
```

### 4.3 `NetworkPulse`
A filtered, high-significance change qualified for investigator review.
```python
class ReviewPriority(str, Enum):
    CRITICAL_REVIEW = "CRITICAL_REVIEW"
    PRIORITY_REVIEW = "PRIORITY_REVIEW"
    ROUTINE_REVIEW = "ROUTINE_REVIEW"

class NetworkPulse(BaseModel):
    pulse_id: str
    change_ids: list[str]
    signal_headline: str
    review_priority: ReviewPriority  # For investigator queue priority only — NEVER guilt
    time_window: tuple[datetime, datetime]
    evidence_refs: list[str]
    support_level: float             # Evidence sufficiency score
    uncertainty: float
    action_window: str               # e.g. "Within 48 hours"
    abstained: bool = False
    generated_at: datetime
```

### 4.4 `EvidenceAssessment`
Models the epistemic state of evidence supporting an investigative claim.
```python
class EpistemicState(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONFLICTS = "CONFLICTS"
    MISSING = "MISSING"
    INFERRED = "INFERRED"
    VERIFIED = "VERIFIED"

class EvidenceAssessment(BaseModel):
    claim_id: str
    target_relationship_id: str
    evidence_ref: str
    state: EpistemicState
    rationale: str
    source_quality: float            # 0.0 to 1.0 based on official verification
    freshness_days: int
```

### 4.5 `Forecast`
Constrained operational forecast with mandatory abstention support.
```python
class ForecastTarget(str, Enum):
    JURISDICTION_SHIFT = "JURISDICTION_SHIFT"
    COMMUNICATION_PATTERN_SHIFT = "COMMUNICATION_PATTERN_SHIFT"
    FINANCIAL_ROUTE_TRANSITION = "FINANCIAL_ROUTE_TRANSITION"
    IDENTIFIER_DRIFT = "IDENTIFIER_DRIFT"
    NETWORK_RESTRUCTURING = "NETWORK_RESTRUCTURING"

class Forecast(BaseModel):
    forecast_id: str
    pulse_id: str
    target_state: ForecastTarget
    time_window: tuple[datetime, datetime]
    support_level: float
    uncertainty: float
    action_window: str
    suggested_verification: str
    abstained: bool
    abstention_reason: str | None    # e.g. "INSUFFICIENT EVIDENCE / NO FORECAST"
```

### 4.6 `VerificationPlan`
Actionable suggestions to resolve missing or conflicting evidence.
```python
class VerificationPlan(BaseModel):
    verification_id: str
    target_claim: str
    missing_evidence_type: str
    recommended_action: str          # e.g. "Obtain Section 91 CrPC telecom subscriber record"
    responsible_role: str            # "INVESTIGATOR" or "ANALYST"
    status: str = "PENDING"
    result: str | None = None
```

### 4.7 `IntelligencePulse`
Structured cross-branch/jurisdiction intelligence propagation packet.
```python
class IntelligencePulse(BaseModel):
    pulse_id: str
    source_case_id: str
    affected_case_ids: list[str]
    signal_summary: str
    observed_change: str
    evidence_refs: list[str]
    action_window: str
    authorization_role: str
    acknowledged_by: str | None = None
    status: str = "UNROUTED"         # "UNROUTED", "DISPATCHED", "ACKNOWLEDGED", "REJECTED"
```

### 4.8 `CaseDNA`
Explainable structural case similarity record.
```python
class CaseDNA(BaseModel):
    case_pair: tuple[str, str]
    structure_similarity: float      # Graph topology & modularity similarity
    communication_similarity: float  # CDR burst & frequency profile
    financial_similarity: float      # Peeling chain & transaction flow similarity
    location_similarity: float       # Geographic spatial overlap
    temporal_similarity: float       # Modus operandi timing match
    shared_entities: list[str]
    explanation: str
    retrieval_score: float
```

---

## 5. Critical Epistemic Separation

To preserve judicial credibility and Section 63 BSA compliance, NEXUS maintains an absolute architectural boundary across four tiers of data:

$$\text{OBSERVED FACT} \ne \text{DERIVED RELATIONSHIP} \ne \text{HYPOTHESIS / FORECAST} \ne \text{INVESTIGATOR DECISION}$$

1. **Observed Fact:** Ground-truth records from official filings (FIR registration, CDR log, bank transaction UTR).
2. **Derived Relationship:** Algorithmically computed graph edges (Louvain syndicate module, BFS path, Double Metaphone match).
3. **Hypothesis / Forecast:** Constrained operational predictions (`JURISDICTION_SHIFT`) with explicit uncertainty and abstention.
4. **Investigator Decision:** Legal determinations recorded by an authorized human investigating officer (accused arrest, charge confirmation, match acceptance).
