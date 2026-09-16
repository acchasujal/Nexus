# NEXUS Security, Governance & Evidence Integrity

This document outlines the security architecture, statutory compliance guardrails, role-based access control (RBAC), immutable audit logging, and cryptographic evidence verification implemented in NEXUS.

---

## 1. Statutory Boundaries & Responsible AI

NEXUS strictly complies with the Constitution of India, criminal procedure jurisprudence, the Digital Personal Data Protection (DPDP) Act 2023, and the Bharatiya Sakshya Adhiniyam (BSA) 2023.

### 1.1 Absolute Prohibition on Automated Guilt Scoring
- **Constitutional Principle:** Under the Indian legal system, determining criminal guilt, innocence, and penal culpability is the exclusive constitutional prerogative of the judiciary.
- **Architectural Firewall:** No algorithm, statistical model, or LLM in NEXUS is permitted to compute or display:
  - "Guilt Scores" or "Probability of Criminality"
  - "Future Crime / Offense Predictions"
  - "Recidivism Risk / Dangerousness Ratings"
  - "Credibility / Deception Ratings"
- **Refusal Gate Implementation:** The `CopilotService` inspects incoming queries and halts on prohibited terms (`guilty`, `culpable`, `reoffend`, `predict guilt`, `convict`, `dangerous`). Refused queries return an explicit explanation directing officers to primary evidentiary records.

### 1.2 Mandatory Epistemic Abstention
- When generating operational early-warning signals, if evidence is sparse, stale (>90 days old), or contradictory, the system must explicitly abstain:
  $$\text{Early Warning Result: } \mathbf{INSUFFICIENT\ EVIDENCE\ /\ NO\ FORECAST}$$
- The system never outputs speculative guesses to fill intelligence gaps.

---

## 2. Evidence Provenance & Section 63 BSA Compliance

Under Section 61 and Section 63 of the Bharatiya Sakshya Adhiniyam, 2023, digital evidence and intelligence dossiers are admissible in court only with verifiable, continuous chain-of-custody provenance:

1. **Edge-Level Attribution:** Every relationship carries an `EvidenceProvenance` citation record capturing:
   - `source_type`: Category of source document (`FIR`, `CDR`, `BANK_TXN`, `SEIZED_DEVICE`, `INTELLIGENCE_REPORT`, `SOCMINT`)
   - `source_id`: Unique identifier (FIR number, call detail record ID, bank transaction UTR)
   - `timestamp`: UTC event creation timestamp
   - `extracted_fact`: Concrete verifiable factual assertion
   - `derivation_method`: Algorithmic or forensic verification method (`OFFICIAL_RECORD`, `TELECOM_LOG`, `ALGORITHMIC_MATCH`)
   - `confidence`: Quantitative confidence score [0.0 - 1.0]
2. **Section 63 BSA Dossier Export:** Generates tamper-evident forensic intelligence packages with cryptographic hash chains and certificate metadata.

---

## 3. Cryptographic Evidence Integrity (SHA-256)

To guarantee that source records underpinning analytical graphs remain untampered:

### 3.1 Canonicalization & Hashing
1. **Source Record Hashing:** During ingestion, raw rows are canonicalized (keys sorted alphabetically, strict separators, deterministic JSON serialization) and hashed using SHA-256.
2. **Evidence Record Hashing:** `EvidenceService` hashes the canonical payload (`evidence_type`, `title`, `description`, `file_name`, `source_system`, `case_id`, `metadata`).

### 3.2 Dynamic Tamper Verification Flow
1. Investigators click **[Verify Integrity]** in the Evidence Drawer.
2. Backend endpoint `POST /api/v1/nexus/sources/{source_id}/verify` recomputes the SHA-256 digest from the canonical raw excerpt.
3. If the computed hash differs from the stored hash, an `INTEGRITY MISMATCH` alert is raised, and the event is recorded in the immutable audit trail.

---

## 4. Role-Based Access Control (RBAC) & Signal Authorization

NEXUS enforces least-privilege role boundaries across the law enforcement hierarchy:

| Role | Domain Scope | Analytical Permissions | Proactive Signal Permissions |
| :--- | :--- | :--- | :--- |
| **`INVESTIGATOR`** (IO) | Assigned Case Workspace | View assigned cases, run entity resolution, inspect multi-hop suspect networks, query copilot. | Review Network Pulses for assigned cases; execute suggested verification workflows. |
| **`ANALYST`** | Crime Branch / Special Cell | Cross-case syndicate clustering, bridge broker identification, temporal pattern queries. | Inspect network diffs across jurisdictions; prepare cross-branch Intelligence Pulses. |
| **`SUPERVISOR`** (SP / DCP) | District / Division Oversight | District-wide intelligence rollup, cross-station correlation, immutable audit review. | Authorize cross-jurisdiction Intelligence Pulse dispatches; review tamper alerts. |
| **`ADMIN`** | System Administration | User provisioning, role assignment, security telemetry, health monitoring. | System configuration, database synchronization, key rotation. |

---

## 5. Controlled SOCMINT & Digital Shadow Governance

When fusing digital signals (social media handles, forum identifiers, digital marketplace posts):
- **Lawful Sourcing:** Only publicly accessible, lawful, or officially subpoenaed digital data is ingested. Private account hacking or unverified automated scraping is prohibited.
- **Strict Association Lifecycle:** Digital connections follow a mandatory 4-stage progression:
  $$\text{OBSERVED} \to \text{CANDIDATE LINK} \to \text{CORROBORATED} \to \text{INVESTIGATOR CONFIRMED}$$
- **Non-Equivalence Rule:** A matching username or online handle is NEVER treated as legal proof of person identity by itself. It must be corroborated by a hard physical identifier (phone, IMEI, bank account, or Aadhaar token).

---

## 6. Immutable Audit Trail

Every analytical query, data export, and administrative action is immutably logged via `AuditService`:
- Entity resolution searches and candidate decisions (`CONFIRMED`, `REJECTED`, `DEFERRED`)
- Multi-hop graph expansion actions and BFS queries
- Copilot queries, grounded citations, and safety refusal events
- SHA-256 integrity verification results and tamper alerts
- Intelligence Pulse generation, transmission, and acknowledgement
- Exported case intelligence dossiers

Audit records include timestamp, actor user ID, role, client IP, case ID, and unique request ID.

---

## 7. Trust Fabric & Blockchain Strategy (Current vs. Target)

- **Current Implementation:** SHA-256 cryptographic hashing of canonical payloads, immutable append-only PostgreSQL audit trails, and Section 63 BSA evidence dossier generation.
- **Target Architecture (Vision):** Selective Merkle-tree anchoring on permissioned ledgers (Hyperledger Fabric or sovereign state node) for inter-agency audit non-repudiation.
- **Explicit Non-Goal:** Sensitive crime data (raw FIRs, CDRs, bank statements, victim details) will NEVER be stored on public blockchains.
