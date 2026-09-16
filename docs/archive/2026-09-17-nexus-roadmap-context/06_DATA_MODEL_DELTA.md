# Data Model Delta

Do not replace the existing graph ontology unnecessarily.

## Preserve

Existing entity types:
Person, Case, Phone, Vehicle, Location, Organization, Device, Account, Transaction, Event, IntelligenceReport, Evidence.

Existing evidence provenance contract remains authoritative.

## Add/extend concepts

### GraphSnapshot
- snapshot_id
- case_scope / investigation_scope
- created_at
- source_revision
- node_count
- edge_count
- version/status

### NetworkChange
Represents a meaningful difference between two states.
- change_id
- before_snapshot
- after_snapshot
- change_type
- affected_entities
- affected_relationships
- affected_cases
- significance
- observed_at
- evidence_refs
- support_state
- status

Change types:
- EDGE_ADDED
- EDGE_REMOVED
- NODE_ADDED
- NODE_REMOVED
- BRIDGE_EMERGED
- BRIDGE_LOST
- COMMUNITY_MERGED
- COMMUNITY_SPLIT
- JURISDICTION_SHIFT
- IDENTIFIER_DRIFT
- ROUTE_CHANGE
- OTHER

### NetworkPulse
A filtered/qualified NetworkChange worth investigator review.
- pulse_id
- change_ids
- signal
- severity/priority only for review workflow, never guilt
- time_window
- evidence_refs
- support_level
- uncertainty
- action_window
- abstained
- generated_at
- status

### EvidenceAssessment
- claim_id
- evidence_ref
- state: SUPPORTS / CONFLICTS / MISSING / INFERRED / VERIFIED
- rationale
- source_quality
- freshness

### Forecast
- forecast_id
- pulse_id
- target_state
- time_window
- support_level
- uncertainty
- action_window
- suggested_verification
- abstention_reason

### VerificationPlan
- verification_id
- target_claim
- missing_evidence
- recommended_check
- responsible_role
- status
- result
- linked_evidence

### IntelligencePulse
- pulse_id
- source_branch/case
- affected_investigations
- signal
- observed_change
- evidence_refs
- action_window
- verification
- authorization
- acknowledgement
- status

### IdentityDriftEvent
- identity_id
- identifier_type
- previous_value/reference
- new_value/reference
- detected_at
- corroborating_context
- evidence_refs
- human_status

### CaseDNA
Explainable similarity record:
- case_pair
- structure_similarity
- communication_similarity
- financial_similarity
- location_similarity
- temporal_similarity
- shared_entities
- evidence_refs
- explanation
- retrieval_score

## Critical epistemic separation

Do not collapse these states:
1. observed fact
2. derived relationship
3. hypothesis/forecast
4. investigator decision

Every API/UI model must preserve that distinction.
