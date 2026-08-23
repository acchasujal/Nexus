# NEXUS Security & Responsible AI Architecture

## 1. Responsible AI & Legal Guardrails

NEXUS implements strict guardrails to prevent harmful, biased, or unconstitutional use of artificial intelligence in law enforcement contexts.

### 1.1 Automated Guilt and Recidivism Refusal
- **Statutory Compliance:** Under Indian criminal jurisprudence, determination of guilt, innocence, and culpability is strictly the exclusive prerogative of the judiciary based on evidence presented at trial.
- **Refusal Gate:** The NEXUS Copilot service intercepts all queries before LLM or knowledge retrieval occurs. Any prompt seeking:
  - Predictive criminal assessment ("Is X likely to commit crimes again?")
  - Guilt/innocence judgments ("Is the suspect guilty?")
  - Subjective credibility assessments ("Is the suspect lying?")
  is immediately refused with an explicit explanation and guidance towards factual, verifiable records (e.g. CDR logs, bank statements).

---

## 2. Authentication & Role-Based Access Control (RBAC)

1. **Investigator (`INVESTIGATOR` / `IO`):** View assigned cases, run entity resolution, query copilot, and explore multi-hop suspect networks.
2. **Intelligence Analyst (`ANALYST`):** Cross-case syndicate clustering, bridge broker identification, and pattern analysis.
3. **Supervisor (`SUPERVISOR` / `SHO` / `SP`):** Full investigation visibility, cross-district aggregations, and immutable audit log review.
4. **Administrator (`ADMIN`):** System configuration and user administration.

---

## 3. Evidentiary Traceability & Chain of Custody

All graph associations, entity resolution matches, and Copilot citations maintain full provenance linking back to:
- Specific First Information Report (FIR) numbers
- Verified CDR logs and telecom circle data
- Financial ledger entries and transaction references
- Field intelligence report serials

No relationship is asserted or merged without traceable evidentiary derivation.
