# Target Architecture

## Target flow

`SOURCE DATA → NORMALIZE / EXTRACT → ENTITY RESOLUTION → UNIFIED GRAPH → NETWORK + TEMPORAL ANALYTICS → CHANGE DETECTION → EARLY-WARNING ENGINE → EVIDENCE CHECK → INTELLIGENCE PULSE → NEXT BEST VERIFICATION → INVESTIGATOR → AUDIT`

## Layer 1 — Intelligence Fusion

Sources:
- FIR / reports
- CDR / telecom
- financial records
- intelligence reports
- criminal history
- authorized/public digital or SOCMINT signals

Output:
canonical, provenance-preserving evidence records.

## Layer 2 — Identity + Knowledge Graph

Reuse current 12-entity graph and extend only where necessary for:
- digital identifiers
- source/capture metadata
- temporal validity
- identity versions
- network snapshots

Core:
- deterministic entity resolution
- human confirmation/rejection/defer
- cross-case relationships
- communities
- paths
- influential/bridge positions

## Layer 3 — Change + Forecast

New analytical plane:

### Network Diff
Compare two graph snapshots or temporal windows.

Detect:
- added/removed entities
- added/removed relationships
- changed communities
- new bridges
- removed bridges
- new jurisdictions
- identifier transitions
- newly relevant evidence
- affected cases

### Network Pulse
Filter raw graph changes into meaningful structural/temporal changes.

### Identity Drift
Track transitions in:
- phone
- device
- account
- alias
- vehicle
- digital identifier
- jurisdiction

### Network Adaptation
Detect:
- intermediary replacement
- bridge replacement
- community merge/split
- network restructuring
- route rerouting

### Case DNA
Explainable structural retrieval across:
- graph shape
- communications topology
- financial paths
- locations/jurisdictions
- temporal sequence
- common identifiers/entities

## Layer 4 — Early-Warning Engine

This must forecast only narrowly defined investigation-relevant states.

Examples:
- jurisdiction transition
- communication-pattern shift
- financial-route transition
- network restructuring
- identifier drift

Never:
- guilt
- criminality probability
- future crime
- dangerousness

### Forecast object

Every signal should contain:
- signal
- time window
- exact supporting evidence
- forecast
- support level
- uncertainty/conflicts/missing evidence
- action window
- suggested verification

Abstention is valid:
`INSUFFICIENT EVIDENCE / NO FORECAST`

## Layer 5 — Evidence Sufficiency

For every important finding:
- SUPPORTS
- CONFLICTS
- MISSING
- INFERRED / DERIVED
- VERIFIED (only after human action where applicable)

## Layer 6 — Next Best Verification

Produce a verification plan, not an autonomous order.

Examples:
- review subscriber record
- inspect transaction chain
- verify cross-case timeline
- inspect independent location source

## Layer 7 — Intelligence Pulse

Structured packet:
- source branch/case
- affected investigations
- signal
- observed change
- evidence references
- action window
- suggested verification
- authorization context

Output to:
- relevant branch
- relevant investigation
- authorized analyst/investigator

## Layer 8 — Trust Fabric

Current/near-term:
- SHA-256 integrity
- evidence registry
- provenance
- RBAC/ABAC
- audit
- data masking

Target:
- Merkle/permissioned-ledger anchoring
- privacy-preserving deconfliction using vetted PSI/MPC

Raw FIR/CDR/bank/PII must remain off-chain.

## Layer 9 — Closed-loop learning

`NEW EVIDENCE / HUMAN DECISION → GRAPH UPDATE → NEW SNAPSHOT → NETWORK DIFF → PULSE`

The loop must be auditable.

## Deployment/scaling principle

Do not run unrestricted full-graph expensive analytics on every UI request.

Use:
- candidate blocking
- deterministic identifiers
- bounded 2–3 hop queries
- incremental graph updates
- targeted projections
- queue/stream only when volume requires it
