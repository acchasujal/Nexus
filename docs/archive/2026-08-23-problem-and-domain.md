# NEXUS — Problem Analysis & Domain Grounding

> **SIH 2026 Problem Statement ID:** 26189  
> **Target Problem:** AI-Powered Criminal Network Analysis System  

---

## 1. Problem Statement Deconstruction & Reality Check

### The Surface vs. Real Underlying Problem

- **The Surface Problem:** Investigating officers face information overload when manually sifting through stacks of paper case files, CDR spreadsheets, and bank transaction sheets.
- **The True Underlying Bottleneck:** Indian law enforcement does not suffer from a lack of data digitization; it suffers from an **intelligence-extraction and relationship-synthesis bottleneck**. 
  
While CCTNS has digitized millions of FIRs across 17,798 police stations, and ICJS enables search across 88+ crore records, intelligence remains locked in:
1. **Unstructured Narrative Text:** FIR contents and witness statements with non-standardized phrasing.
2. **Siloed Relational Databases:** Telephony databases (CDRs) stored separately from banking feeds (IMPS/UPI) and court chargesheets.
3. **Vernacular & Alias Ambiguity:** Suspects intentionally utilizing aliases, misspelled names, and rotating burner devices across state borders.

---

## 2. The 5 Root Technical Bottlenecks

### 1. Data Heterogeneity
- **Challenge:** Police reports are narrative text; CDRs are structured timestamped telephony logs; banking files are transactional balance sheets; VAHAN records are vehicle registries.
- **NEXUS Resolution:** Implements a unified heterogeneous property graph ontology where diverse data types map into 12 core entity nodes and typed evidentiary edges.

### 2. Entity Ambiguity & Indian Vernacular Names
- **Challenge:** Variations like *"Ravi Kumar"*, *"R. Kumar"*, *"Ravikumar"*, or phonetic equivalents like *"Vikram Sharma"* ↔ *"Bikram Sarma"* lead to **False Fragmentation** (splitting one criminal across 5 profiles) or **False Merging** (merging distinct individuals).
- **NEXUS Resolution:** Multi-attribute entity resolution combining Indian phonetic normalization (`sh` ↔ `s`, `v` ↔ `b`, `ee` ↔ `i`, `ou` ↔ `u`), character-bigram Jaccard similarity, alias tracking, and corroborating hard identifiers (phone, IMEI, vehicle, national ID).

### 3. Implicit vs. Explicit Relationships
- **Challenge:** Criminal syndicates operate through decentralized cells rather than explicit hierarchical org charts.
- **NEXUS Resolution:** Uncovers latent associations through co-location, shared mobile devices/IMEIs, layered financial transfer chains, and communication bursts.

### 4. Graph Centrality Trap (Kingpins vs. Foot Soldiers)
- **Challenge:** Simple Degree Centrality (counting total calls or connections) disproportionately highlights low-level operatives who execute high call volumes.
- **NEXUS Resolution:** Applies **Betweenness Centrality** and **Louvain Modularity** to isolate hidden coordinators who make few direct calls but act as structural bridge brokers between separate criminal cells.

### 5. Evidentiary Provenance & Legal Defensibility
- **Challenge:** Under the **Bharatiya Sakshya Adhiniyam, 2023 (BSA Sections 61 & 63)**, digital intelligence must maintain an unbroken chain of custody with verifiable metadata and cryptographic integrity. Unexplainable LLM assertions are inadmissible in court.
- **NEXUS Resolution:** Every edge and insight in NEXUS maintains strict `EvidenceProvenance` with source document references, timestamps, derivation methods, and SHA-256 hash chains.

---

## 3. Fact vs. Inference vs. Design Decision Matrix

To ensure absolute transparency and domain fidelity, NEXUS distinguishes between verified facts, analytical inferences, and engineering design choices:

| Category | Item Description | Domain Classification | Handling in NEXUS |
| :--- | :--- | :--- | :--- |
| **FACT** | 17,798 police stations operational on CCTNS nationwide. | Verified Government Metric | Primary data source assumptions |
| **FACT** | Section 63 BSA 2023 mandates hash integrity for electronic records. | Statutory Law | Cryptographic hashing of evidence dossiers |
| **INFERENCE** | A person sharing an IMEI and hideout address with an accused is a potential co-conspirator. | Analytical Hypothesis | Surfaced as a lead with confidence score; human validation required |
| **INFERENCE** | A node with high betweenness centrality bridging two syndicates is an operational broker. | Topological Lead | Highlighted visually on graph; zero guilt inference attached |
| **DESIGN DECISION** | In-memory double-adjacency index for sub-millisecond graph traversals. | System Architecture | Sub-second query SLA without database roundtrips |
| **DESIGN DECISION** | Rejection of queries requesting guilt, innocence, or recidivism prediction. | Ethical Guardrail | Refusal gate interceptor built into Copilot service |
