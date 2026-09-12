# NEXUS Security, Governance & Evidence Integrity

This document outlines the security controls, statutory compliance boundaries, role-based access control (RBAC), immutable auditing, and cryptographic evidence verification implemented in NEXUS.

---

## 1. Statutory Boundaries & Responsible AI

NEXUS complies strictly with Indian constitutional principles, criminal procedure, and data protection mandates.

### 1.1 Prohibition on Automated Guilt Scoring
- **Constitutional Principle:** In the Indian legal system, determining criminal guilt, innocence, and culpability is the exclusive constitutional prerogative of the judiciary.
- **Architectural Firewall:** No algorithm, ML model, or LLM in NEXUS is permitted to output:
  - "Guilt Scores" or "Probability of Criminality"
  - "Reoffending Risk" or "Recidivism Predictions"
  - "Credibility / Lie Detection Ratings"
- **Refusal Gate Implementation:** The `CopilotService` inspects incoming queries and rejects prohibited terms (`guilty`, `culpable`, `reoffend`, `predict guilt`, `convict`). Refused queries return an explicit explanation directing investigators to factual evidentiary records.

---

## 2. Evidence Provenance & Bharatiya Sakshya Adhiniyam (BSA) 2023

Under Section 61 and Section 63 of the BSA 2023, digital intelligence and electronic link charts are admissible in court only with continuous chain-of-custody provenance:

1. **Edge-Level Attribution:** Every relationship carries an `EvidenceProvenance` citation capturing:
   - Source document type (`FIR`, `CDR`, `BANK_TXN`, `SEIZED_DEVICE`, `INTELLIGENCE_REPORT`)
   - Unique identifier (e.g., FIR number, call record ID, bank transaction UTR)
   - Ingestion and creation timestamps
   - Derivation method (`OFFICIAL_RECORD`, `TELECOM_LOG`, `ALGORITHMIC_MATCH`)
2. **Section 63 BSA Dossier Export:** Generates tamper-evident forensic intelligence packages with cryptographic hash chains.

---

## 3. Cryptographic Evidence Integrity (SHA-256)

To guarantee that source records underpinning analytical graphs remain untampered:

### 3.1 Canonicalization & Hashing
1. **Source Record Hashing:** During ingestion, raw rows are canonicalized (keys sorted alphabetically, strict separators, deterministic JSON serialization) and hashed using SHA-256.
2. **Evidence Record Hashing:** `EvidenceService` hashes the canonical payload (`evidence_type`, `title`, `description`, `file_name`, `source_system`, `case_id`, `metadata`).

### 3.2 Dynamic Tamper Verification Flow
1. Investigators click **[Verify Integrity]** in the Evidence Drawer.
2. Backend endpoint `POST /api/v1/nexus/sources/{source_id}/verify` recomputes the SHA-256 digest from the canonical raw excerpt.
3. If the computed hash differs from the stored hash, an `INTEGRITY MISMATCH` alert is raised, and the event is recorded in the audit trail.

---

## 4. Role-Based Access Control (RBAC)

NEXUS enforces least-privilege role boundaries across the investigative hierarchy:

| Role | Domain Scope | Permissions |
| :--- | :--- | :--- |
| **`INVESTIGATOR`** (IO) | Case-Level Workspace | View assigned cases, run entity resolution, inspect multi-hop suspect networks, query copilot. |
| **`ANALYST`** | Crime Branch / Special Cell | Cross-case syndicate clustering, bridge broker identification, temporal hotspot analysis. |
| **`SUPERVISOR`** (SP / DCP) | District Oversight | District-wide intelligence rollup, cross-station correlation, immutable audit review. |
| **`ADMIN`** | System Administration | User provisioning, role assignment, security telemetry, health monitoring. |

---

## 5. Immutable Audit Trail

Every state modification and analytical access is immutably logged via `AuditService`:
- Entity resolution queries and matching results
- Multi-hop graph expansion actions
- Copilot queries, grounded citations, and safety refusals
- Exported case intelligence dossiers
- Integrity verification results and tamper alerts

Audit records include timestamp, actor user ID, role, client IP, case ID, and request ID.

---

## 6. Synthetic Data Protection
- **DPDP Act 2023 Alignment:** All development, testing, CI benchmarks, and live demonstrations operate exclusively on synthetic datasets generated via `synthetic_data/nexus_generator.py`.
- **Zero Real PII:** No live citizen PII or actual classified police records are ever stored in the repository.
