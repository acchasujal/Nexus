# NEXUS — Security, Governance & Responsible AI

## 1. Responsible AI Principles & Statutory Boundaries

NEXUS enforces strict architectural guardrails to guarantee compliance with Indian constitutional principles, criminal procedure, and data protection statutes.

### 1.1 Strict Prohibition on Automated Guilt Inference
- **Legal Principle:** Under Indian jurisprudence, determination of criminal liability, guilt, innocence, and dangerousness is the **sole constitutional prerogative of the judiciary** based on evidence presented at trial.
- **Architectural Firewall:** No algorithm, ML model, or LLM in NEXUS is permitted to output:
  - *"Guilt Scores"* or *"Probability of Criminality"*
  - *"Reoffending Risk"* or *"Recidivism Predictions"*
  - *"Credibility / Lie Detection Ratings"*
- **Refusal Gate Implementation:** The `CopilotService` inspects incoming queries and rejects prohibited terms (`guilty`, `culpable`, `reoffend`, `predict guilt`, `convict`, `criminal mindset`). Refused queries return an explicit explanation and direct the officer to verifiable factual evidence.

---

## 2. Evidence Provenance & Section 63 BSA 2023 Compliance

Under Section 61 and Section 63 of the **Bharatiya Sakshya Adhiniyam (BSA), 2023**, electronic records and digital intelligence must maintain an unbroken chain of custody:

1. **Edge-Level Attribution:** Every relationship in the knowledge graph is bound to an `EvidenceProvenance` object capturing:
   - Source document type (`FIR`, `CDR`, `BANK_TXN`, `SEIZED_DEVICE`, `INTELLIGENCE_REPORT`)
   - Unique source identifier (e.g. FIR number, CDR call log ID, IMPS UTR)
   - Timestamp of record creation and ingestion
   - Explicit derivation method (`OFFICIAL_RECORD`, `TELECOM_LOG`, `ALGORITHMIC_MATCH`)
2. **Cryptographic Integrity:** Designed to support SHA-256 hash chains for exported intelligence dossiers to guarantee tamper-evidence upon submission to prosecuting authorities.

---

## 3. Role-Based Access Control (RBAC)

NEXUS enforces granular, least-privilege role boundaries across the investigative hierarchy:

| Role | Domain Scope | Permissions |
| :--- | :--- | :--- |
| **`INVESTIGATOR`** (IO) | Case-Level Workspace | View assigned cases, execute entity resolution queries, inspect multi-hop suspect networks, query copilot. |
| **`ANALYST`** | Crime Branch / Special Cell | Cross-jurisdictional syndicate clustering, bridge broker identification, pattern and temporal hotspot analysis. |
| **`SUPERVISOR`** (SHO / SP / DCP) | District & Hierarchy Oversight | Complete district rollup visibility, cross-station intelligence correlation, immutable audit log review. |
| **`ADMIN`** | System Administration | User provisioning, role assignment, system health monitoring, security telemetry. |

---

## 4. Immutable Audit Trail & Telemetry

Every interaction within NEXUS is immutably recorded via `AuditService`:
- Entity resolution queries and matching results
- Multi-hop graph expansion actions
- Copilot queries, grounded citations, and safety refusals
- Exported case intelligence dossiers

Audit records include timestamp, actor user ID, role, client IP, case ID, and request ID to guarantee complete evidentiary accountability.

---

## 5. Data Privacy & Synthetic Data Strategy

- **DPDP Act, 2023 Alignment:** In compliance with Indian data privacy mandates, development, testing, and live demonstrations of NEXUS operate exclusively on a **high-fidelity synthetic dataset**.
- **Zero Real PII:** No live citizen PII or actual classified police records are bundled in the repository or exposed in demonstration environments.
