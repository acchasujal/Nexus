# NEXUS Graph Data Model & Ontology

## 1. Core Graph Entities

The NEXUS knowledge graph models 12 distinct intelligence entities across law enforcement operations:

| Entity Type | Description | Key Attributes |
| :--- | :--- | :--- |
| **`Person`** | Suspect, co-accused, witness, or informant | `id`, `full_name`, `aliases`, `phone_numbers`, `vehicles`, `addresses`, `national_id`, `is_known_offender` |
| **`Case`** | First Information Report (FIR) or court case | `id`, `fir_number`, `title`, `station_name`, `district`, `offence_category`, `status`, `incident_date` |
| **`Phone`** | Monitored mobile phone or SIM | `id`, `phone_number`, `imei`, `imsi`, `telecom_circle`, `carrier`, `is_burner` |
| **`Vehicle`** | Seized or monitored vehicle | `id`, `registration_number`, `chassis_number`, `make_model`, `color`, `registered_owner` |
| **`Location`** | Incident scene, hideout, or meeting point | `id`, `name`, `address_text`, `city`, `district`, `latitude`, `longitude`, `location_type` |
| **`Organization`** | Front company, cartel, or gang | `id`, `name`, `org_type`, `registration_number`, `known_front`, `operating_districts` |
| **`Device`** | Seized digital device / burner hardware | `id`, `device_type`, `serial_number`, `mac_address`, `seized_from_person_id` |
| **`Account`** | Bank or wallet account | `id`, `account_number`, `bank_name`, `ifsc_code`, `account_type`, `is_flagged_mule` |
| **`Transaction`** | Financial wire transfer or Hawala ledger | `id`, `transaction_ref`, `amount`, `currency`, `timestamp`, `channel`, `is_suspicious` |
| **`Event`** | Temporal intelligence occurrence | `id`, `event_type`, `timestamp`, `description`, `participant_ids`, `location_id` |
| **`IntelligenceReport`** | Field intelligence briefing | `id`, `report_number`, `source_agency`, `classification`, `summary`, `target_person_ids` |
| **`Evidence`** | Physical or digital seized evidence item | `id`, `evidence_number`, `case_id`, `evidence_type`, `description`, `collected_at`, `provenance` |

---

## 2. Relationship Edge Types

| Edge Type | Source Entity | Target Entity | Semantics |
| :--- | :--- | :--- | :--- |
| **`ACCUSED_IN`** | `Person` | `Case` | Individual formally named as accused |
| **`VICTIM_IN`** | `Person` | `Case` | Individual registered as complainant/victim |
| **`WITNESS_IN`** | `Person` | `Case` | Individual providing testimony |
| **`CO_ACCUSED_WITH`** | `Person` | `Person` | Joint accused in shared criminal proceedings |
| **`COMMUNICATED_WITH`** | `Person` / `Phone` | `Person` / `Phone` | Telecommunication call or message record |
| **`ASSOCIATED_WITH`** | `Person` | `Person` / `Organization` | General syndicate or gang association |
| **`TRANSFERRED_MONEY_TO`**| `Account` | `Account` | Financial flow / Hawala transfer |
| **`OWNS_ACCOUNT`** | `Person` / `Organization` | `Account` | Ownership of banking/wallet node |
| **`USES_PHONE`** | `Person` | `Phone` | Subscriber or device user |
| **`DRIVES_VEHICLE`** | `Person` | `Vehicle` | Driver or registered owner of vehicle |
| **`LOCATED_AT`** | `Person` / `Event` | `Location` | Spatial presence or incident scene |
| **`MENTIONED_IN`** | `Person` / `Organization` | `IntelligenceReport` | Referenced in intelligence briefing |
| **`RESOLVED_TO`** | `Person` | `Person` | Cross-source entity resolution link |
| **`HAS_EVIDENCE`** | `Case` | `Evidence` | Evidence item tagged to investigation |

---

## 3. Evidence Provenance Model

Every edge and resolved entity retains structured evidentiary provenance:

```python
class EvidenceProvenance(BaseModel):
    source_type: str        # "FIR", "CDR", "BANK_TXN", "SEIZED_DEVICE", "INTELLIGENCE_REPORT"
    source_id: str          # Source document ID / Transaction reference
    timestamp: datetime     # Timestamp of extraction / collection
    extracted_fact: str     # Specific verifiable fact extracted
    derivation_method: str  # "OFFICIAL_RECORD", "TELECOM_LOG", "FINANCIAL_LEDGER", "ALGORITHMIC_MATCH"
    confidence: float       # Confidence score (0.0 to 1.0)
```
