# Implementation Sequence

Do not rewrite the entire application.

## Phase 0 — Freeze baseline
- preserve current working branch
- run full backend/frontend tests
- capture current API/UI smoke state
- tag/branch baseline

## Phase 1 — Temporal foundation
- GraphSnapshot model
- snapshot IDs/versioning
- temporal state utilities
- deterministic graph serialization
- snapshot tests

## Phase 2 — Network Diff
- NetworkDiffService
- added/removed nodes and edges
- bridge/community/jurisdiction/identifier changes
- API
- frontend before/after view
- tests

## Phase 3 — Network Pulse
- significance filtering
- evidence attachment
- review priority
- Pulse API
- Pulse worklist UI
- tests

## Phase 4 — Evidence Assessment
- support/conflict/missing model
- stale/conflicting evidence
- evidence sufficiency
- provenance UI
- tests

## Phase 5 — Early Warning + Abstention
- constrained forecast object
- explicit uncertainty
- action window
- abstention gate
- deterministic benchmark fixtures
- tests

## Phase 6 — Next Best Verification
- verification planner
- role-aware suggestions
- resolution workflow
- feedback capture
- tests

## Phase 7 — Intelligence Pulse
- affected-investigation discovery
- structured packet
- RBAC routing
- acknowledgement
- audit
- tests

## Phase 8 — Identity Drift / Network Adaptation
- identifier transition events
- intermediary replacement
- bridge/community adaptation
- visualization
- tests

## Phase 9 — Digital Shadow / SOCMINT schema
- controlled evidence type
- source/capture metadata
- association-state workflow
- synthetic examples only
- tests

## Phase 10 — Case DNA
- component similarity
- explanations
- retrieval benchmarks

## Phase 11 — Trust UX
- SHA-256 verification visibility
- provenance chain
- optional trust anchor abstraction (future)

## Phase 12 — Integration
- closed-loop update
- investigator decision → audit → graph refresh
- deployment smoke tests

## Phase 13 — Documentation migration
- update all canonical docs
- remove obsolete claims
- clearly mark current vs target
- update demo/PPT-facing docs

## Phase 14 — Final red-team
Ask:
- Is any unsupported capability presented as working?
- Are forecasts actually constrained?
- Can every pulse be traced to evidence?
- Can the system abstain?
- Can unauthorized users receive cross-branch intelligence?
- Are benchmark claims correctly scoped?
