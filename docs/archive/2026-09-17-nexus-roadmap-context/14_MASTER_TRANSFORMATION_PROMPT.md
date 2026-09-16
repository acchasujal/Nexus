# MASTER PROMPT — NEXUS ROADMAP TRANSFORMATION

You are transforming the existing NEXUS repository into the target architecture/product defined in the accompanying context pack.

READ THESE FILES FIRST, IN ORDER:
1. 00_START_HERE.md
2. 01_CURRENT_STATE.md
3. 02_TARGET_ROADMAP.md
4. 03_TRANSFORMATION_PRINCIPLES.md
5. 04_TARGET_ARCHITECTURE.md
6. 05_CAPABILITY_MATRIX.md
7. 06_DATA_MODEL_DELTA.md
8. 07_API_AND_SERVICE_DELTA.md
9. 08_FRONTEND_WORKFLOW_DELTA.md
10. 09_EVALUATION_AND_BENCHMARKS.md
11. 10_SECURITY_GOVERNANCE_DELTA.md
12. 11_IMPLEMENTATION_SEQUENCE.md
13. 12_DOCUMENTATION_MIGRATION.md
14. 13_AI_AGENT_WORKING_RULES.md

Then inspect the real repository, tests, and current canonical docs.

## OBJECTIVE

Transform NEXUS from its current retrospective graph-intelligence workflow into:

observe → connect → detect change → forecast only what is justified → alert → verify → act → learn

The central product idea is:

> Network Change Intelligence: detect meaningful changes in an observed investigative network, ground every signal in evidence, identify what is missing, suggest what should be verified next, and route trusted intelligence to the investigation that needs it.

## NON-NEGOTIABLE PRODUCT PRINCIPLES

1. Preserve the existing working foundation.
2. Do not rewrite the entire architecture.
3. Extend existing GraphStore/Neo4j/PostgreSQL/ER/provenance/audit/RBAC systems.
4. Deterministic-before-generative.
5. Evidence before forecast.
6. Abstention is a valid outcome.
7. Human investigators remain responsible for decisions.
8. No guilt/criminality/future-crime prediction.
9. No raw sensitive evidence on public blockchains.
10. No naive phone-hash PSI.
11. Do not present target vision as implemented.
12. Do not add features only for feature-count parity.

## PRIMARY CAPABILITIES TO DELIVER

P0:
- GraphSnapshot
- Network Diff
- Network Pulse
- Evidence Gap / contradiction engine
- Early-Warning Signal framework
- abstention
- Next Best Verification

P1:
- Intelligence Pulse / affected-investigation routing
- Identity Drift
- Network Adaptation
- controlled Digital Shadow/SOCMINT schema
- SHA-256 integrity UX

P2:
- Case DNA
- selective Merkle/permissioned-ledger anchoring

Future:
- PSI/MPC
- advanced temporal GNN/crypto intelligence/biometrics

## IMPLEMENTATION METHOD

For each capability:

A. inspect current implementation
B. find reusable code
C. define minimal data-model delta
D. add service/module
E. add API
F. add frontend workflow
G. add deterministic synthetic scenarios
H. add tests
I. add benchmarks
J. update canonical docs
K. update progress.md
L. record material architecture/security choices in decisions.md

Do not proceed to the next major phase until regression gates pass.

## DATA MODEL

Introduce the objects in `06_DATA_MODEL_DELTA.md`, preserving existing entities and provenance.

Critical epistemic separation:
- OBSERVED FACT
- DERIVED RELATIONSHIP
- HYPOTHESIS/FORECAST
- INVESTIGATOR DECISION

Never collapse them.

## NETWORK CHANGE

The graph must become temporal.

Implement deterministic snapshots and a diff engine.

Network Diff must detect:
- added/removed nodes
- added/removed edges
- bridge emergence/loss
- community merge/split
- jurisdiction shifts
- identifier drift
- affected cases
- supporting evidence

## NETWORK PULSE

Do not alert on every graph change.

Aggregate/filter meaningful changes.

Every Pulse must contain:
- what changed
- when
- affected entities
- affected investigations
- evidence
- support/conflict/missing state
- uncertainty
- action window
- status

## EARLY WARNING

Forecast only narrow operational/investigative states:
- jurisdiction transition
- communication shift
- financial-route transition
- network restructuring
- identifier drift

Never forecast criminal intent.

Implement abstention:
if evidence is sparse/stale/contradictory → `INSUFFICIENT EVIDENCE / NO FORECAST`.

## EVIDENCE ASSESSMENT

For every important finding:
SUPPORTS / CONFLICTS / MISSING / INFERRED / VERIFIED.

Include source provenance and freshness.

## NEXT BEST VERIFICATION

Recommend evidence checks only.
Do not autonomously perform enforcement actions.

## INTELLIGENCE PULSE

Generate an RBAC-governed structured packet for affected investigations:
source case, affected cases, signal, observed change, evidence, action window, verification.

Audit:
creation, sending, receipt/acknowledgement, rejection.

## DIGITAL SHADOW

Use only authorized/public synthetic/demo signals.
Preserve:
source, timestamp, capture context, authorization, association state.

Association state:
Observed → Candidate Link → Corroborated → Investigator Confirmed.

Do not equate username/profile/account match with identity proof.

## TRUST

Keep current SHA-256 integrity.

Improve UX so investigators can verify evidence integrity.

Keep Merkle/ledger anchoring as target unless actually implemented.

Keep PSI/MPC as future/research unless a vetted implementation is added.

## EVALUATION

Every new proactive capability gets:
- unit/integration tests
- temporal fixtures
- synthetic ground truth
- baseline comparison
- false-positive/false-negative measurement
- uncertainty/abstention measurement

Never report synthetic metrics as field accuracy.

## UI

Make the new workflow visible:

Worklist
→ Network Pulse
→ Network Diff
→ Evidence Assessment
→ Early Warning
→ Next Best Verification
→ Intelligence Pulse
→ Human Decision
→ Audit
→ Graph Update

Do not turn the UI into a dashboard full of red alerts.

## DOCUMENTATION

Update existing canonical docs; do not create duplicate docs.

Clearly mark CURRENT vs TARGET.

## DEPLOYMENT

Preserve Render/Vercel compatibility unless a material architectural decision explicitly changes deployment.

## FINAL VERIFICATION

Before completing:
- run all backend tests
- run all frontend tests
- run lint
- run build
- run current ER benchmark
- run new change/pulse/forecast/verification benchmarks
- verify API contracts
- verify deployment health
- inspect generated docs for contradictions
- update progress.md
- update decisions.md if needed

## OUTPUT EXPECTATION

Do not merely describe what should be done.

Inspect, implement, test, document, and verify in dependency order while minimizing regressions.

When a roadmap capability cannot safely be implemented, preserve the architecture and documentation as TARGET/FUTURE rather than fabricating functionality.
