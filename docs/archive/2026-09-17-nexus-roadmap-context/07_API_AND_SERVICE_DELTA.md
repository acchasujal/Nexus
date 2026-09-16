# API & Service Transformation

Keep existing endpoint contracts backward compatible where practical.

## New service boundaries

### NetworkDiffService
Responsibilities:
- construct temporal snapshots
- compare snapshots
- emit raw NetworkChange records
- deterministic diffing

### NetworkPulseService
Responsibilities:
- filter/aggregate NetworkChange
- calculate structural significance
- attach evidence
- produce NetworkPulse
- support abstention

### EvidenceAssessmentService
Responsibilities:
- support/conflict/missing states
- evidence freshness/quality
- sufficiency decision
- provenance traversal

### EarlyWarningService
Responsibilities:
- generate constrained Forecast objects
- enforce forecast scope
- calculate uncertainty
- abstain when evidence is insufficient

### VerificationPlanner
Responsibilities:
- map missing evidence to suggested verification actions
- role/authorization aware
- never execute enforcement

### IntelligencePulseService
Responsibilities:
- determine affected investigations
- generate structured information packet
- RBAC/ABAC enforcement
- acknowledgement/audit

### IdentityDriftService
Responsibilities:
- correlate identifier transitions over time
- produce IdentityDriftEvent
- never infer intent solely from drift

### CaseDNAService
Responsibilities:
- explainable structural retrieval
- component-level similarity breakdown

## Suggested API families

`GET /api/v1/nexus/snapshots`
`GET /api/v1/nexus/diff?before=...&after=...`
`GET /api/v1/nexus/pulses`
`GET /api/v1/nexus/pulses/{pulse_id}`
`POST /api/v1/nexus/pulses/{pulse_id}/assess-evidence`
`GET /api/v1/nexus/forecasts`
`GET /api/v1/nexus/verification/{pulse_id}`
`POST /api/v1/nexus/verification/{id}/resolve`
`GET /api/v1/nexus/intelligence-pulses`
`POST /api/v1/nexus/intelligence-pulses`
`POST /api/v1/nexus/intelligence-pulses/{id}/ack`
`GET /api/v1/nexus/identity-drift`
`GET /api/v1/nexus/case-dna`
`GET /api/v1/nexus/digital-shadow`

Exact names are implementation suggestions, not mandatory. Inspect the current router/service conventions before choosing final paths.

## Backward compatibility

Do not break:
- existing case APIs
- entity-resolution APIs
- graph/path APIs
- Copilot
- evidence endpoints
- audit endpoints

Add adapters or versioned endpoints where needed.
