# ADR-003: Edge-Level Evidence Provenance and Section 63 BSA Compliance

## Status
**Accepted & Implemented**

## Context
Under Section 61 and Section 63 of the **Bharatiya Sakshya Adhiniyam, 2023 (BSA)**, electronic records, link charts, and intelligence dossiers are only admissible if accompanied by verifiable metadata, source identification, and cryptographic integrity verification. A generic graph that shows connections without provenance is legally useless in chargesheet preparation.

## Decision
Every graph relationship in NEXUS must carry an `EvidenceProvenance` data structure:
- **`source_type`:** Source document category (`FIR`, `CDR`, `BANK_TXN`, `SEIZED_DEVICE`, `INTELLIGENCE_REPORT`).
- **`source_id`:** Document serial, UTR, or call log identifier.
- **`timestamp`:** UTC record creation/event time.
- **`extracted_fact`:** Concise, verifiable fact statement.
- **`derivation_method`:** Verification mechanism (`OFFICIAL_RECORD`, `TELECOM_LOG`, `ALGORITHMIC_MATCH`).
- **`confidence`:** Quantitative match confidence score.

## Consequences
- **Positive:** Unbroken chain of custody; every visual edge on the graph can be clicked to inspect source court/police citations.
- **Trade-off:** Graph storage payload includes metadata overhead for every instantiated edge.
