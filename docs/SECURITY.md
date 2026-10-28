# Security, evidence integrity, and responsible use

> Reviewed 2026-10-28. This is an implementation and limitations guide, not a compliance certification or legal opinion.

## Scope and data policy

NEXUS is an evaluation prototype using synthetic records. The MHA/NCRB problem context does not imply official deployment, accreditation, or access to police systems.

Do not put real citizen records, credentials, or private case material into development fixtures, public issues, screenshots, logs, or public ledgers. Hashes are not anonymization by themselves.

## Authentication: important prototype boundary

**CURRENT:** The frontend separates a local read-only demo from a server-issued session. The local role never creates a JWT or an authenticated AuthContext identity. Its controls do not expose backend mutations.

The backend login handler resolves demo roles and issues signed demo tokens. It does **not** validate credentials against a production officer directory. The current `DevelopmentVerifier` supports signed JWTs as well as demonstration shortcuts, including role headers/query parameters and legacy base64 tokens. Changing `AUTH_MODE` alone is not a replacement for a hardened identity integration.

Relevant code:

- [Login handler](../backend/app/api/core_routes.py)
- [Verifier](../backend/app/auth/verifier.py)
- [Principal resolution](../backend/app/auth/principal.py)
- [Authorization policy](../backend/app/auth/policy.py)
- [Frontend session context](../frontend/src/contexts/AuthContext.tsx)

**TARGET / FUTURE:** A production identity provider, verified credential exchange, robust expiry/revocation, stronger session lifecycle, restricted CORS, and operational access auditing require a separate security review before any real-data deployment. Do not describe the demo credential form as production authentication.

## Authorization and role semantics

Policy code and service-level checks—not visible frontend buttons—define backend access. Roles include IO/INVESTIGATOR, SHO/ANALYST, SP/SUPERVISOR, and ADMIN; specific actions and case/station/district scopes differ by policy. Do not assume aliases imply identical permissions for every endpoint.

Representative boundaries include scoped case/evidence access, investigator review decisions, audit/dossier permissions, and graph-readiness gates. Tests exercise these boundaries but do not constitute an independent penetration test.

Frontend logout clears stored role/token/demo selection and query cache. Obsolete login responses are rejected after logout, a new session attempt, or cancellation. If session storage cannot be written and verified, the frontend does not claim a usable stored server session.

## Responsible analysis

**CURRENT policy / tested refusal behavior:**

- No guilt, criminal-propensity, recidivism, dangerousness, or credibility scoring.
- Deterministic graph computation before generative explanation.
- Evidence attribution and explicit distinction between facts, derived associations, hypotheses, and decisions.
- Prohibited-query checks in the copilot.

**NEW PROTOTYPE:** Forecast/abstention cards illustrate constrained operational targets. They are not calibrated probabilities or blanket guarantees that every weak-data case is detected. See [pipeline scope](INTELLIGENCE_PIPELINE.md).

## Integrity mechanisms

| Mechanism | What it establishes | What it does not establish |
| --- | --- | --- |
| Source/evidence digest | Whether canonicalized content matches an expected digest | Whether the original statement is true |
| Audit hash chain | Detectable inconsistencies in chained records | Protection from every privileged/storage attack |
| Merkle proof and local permissioned ledger | Inclusion/integrity evidence within the implemented local structure | Deployed cross-agency consensus |
| PDF/dossier hashing | Whether exported bytes match a recorded hash | Automatic court admissibility or legal certification |
| Private content-addressed objects | Controlled source-byte storage and checked retrieval | A complete retention/incident-response program |

The source-record digest, evidence metadata digest, audit-chain hash, Merkle root, and PDF digest have separate scopes. A “recorded” hash must not be labelled “verified” without the corresponding verification operation.

Dossier formats reference the Section 63 BSA workflow. Their existence is not a legal finding that a particular record meets every evidentiary requirement. Human/legal review remains necessary.

## Digital identifier corroboration

**NEW PROTOTYPE:** Digital Shadow works with authorized structured/public identifiers and explicit association states. A handle match does not establish identity. Do not add covert scraping, account intrusion, or automatic promotion of an unverified association.

Production source authorization, minimization, retention, and legal review remain requirements—not accomplishments inferred from a demo screen.

## Secrets and deployment configuration

- Use ignored local environment files and hosting-provider secrets.
- Never put secrets in Vite variables; they become public bundle contents.
- Production configuration validates a private JWT secret, but a strong secret does not harden the demo login/verifier.
- Inspect actual CORS behavior; the current middleware includes broad preview-origin patterns and is not a certified least-privilege production policy.
- Keep raw exception/provider details and connection credentials out of diagnostics.
- Do not store FIRs, CDRs, accounts, or citizen PII on public blockchains. Naive `SHA256(phone)` is not production private-set intersection.

## Availability is not authorization

Read-only snapshots remain usable during service outages. Live reads require the selected flow's server session, and full-workspace mutations retain their backend checks. Graph operations remain gated until schema/sync/durable read complete. Never bypass those gates merely to produce a successful demo response.

See [deployment](DEPLOYMENT.md) for liveness versus readiness and bounded recovery.

## Reporting a concern

Report the affected revision and a synthetic reproduction through a private maintainer channel when details are sensitive. Do not post credentials, real records, exploit tokens, or private service dumps in public issues. A formal vulnerability disclosure program and response SLA have not been established.
