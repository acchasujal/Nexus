# Security, Governance & Trust Transformation

## Preserve existing controls

- RBAC
- immutable audit
- SHA-256 evidence integrity
- evidence provenance
- Copilot refusal gate
- synthetic-data policy
- least privilege

## Extend RBAC to proactive intelligence

Authorization must apply to:
- who can see a Network Pulse
- who can inspect underlying evidence
- who can generate Intelligence Pulse
- which branches can receive propagated intelligence
- which digital/SOCMINT signals can be viewed
- who can execute/approve verification workflows

## Provenance

Every proactive signal must carry:
- source references
- timestamps
- derivation
- algorithm/service version
- support state
- uncertainty
- actor/role where human action occurred

## SOCMINT governance

Only authorized/public data.
Preserve:
- source URL/identifier where appropriate
- timestamp
- capture context
- authorization basis
- association state

Association states:
Observed → Candidate Link → Corroborated → Investigator Confirmed

A username/account match is never sufficient identity proof.

## Blockchain strategy

Current:
SHA-256 integrity + audit + evidence registry.

Target:
selective Merkle/permissioned ledger anchoring.

Do not store:
- raw FIRs
- CDRs
- financial records
- PII

on a public blockchain.

Never claim that hashing or blockchain itself creates legal admissibility.

## PSI/MPC

If implemented later:
- use vetted protocol
- explicit threat model
- authorized participants
- metadata minimization
- do not use naive hashes as production PSI

## Responsible forecasting

Allowed:
- network state
- jurisdiction transition
- communication shift
- financial route transition
- identifier drift
- network restructuring

Not allowed:
- guilt
- criminal propensity
- future crime
- dangerousness
- recidivism

Abstain if evidence is sparse, stale or contradictory.
