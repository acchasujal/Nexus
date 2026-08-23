# NEXUS — Evidence-Grounded Criminal Network Intelligence System

> **Smart India Hackathon (SIH) 2026**  
> **Problem Statement ID:** 26189  
> **Problem Title:** AI-Powered Criminal Network Analysis System  
> **Organization:** Ministry of Home Affairs (MHA) / National Crime Records Bureau (NCRB)  
> **Department:** Women Safety Division | **Theme:** Blockchain & Cybersecurity  

[![Pytest Tests](https://img.shields.io/badge/Pytest-296%20Passed-emerald.svg)](docs/TESTING.md)
[![Vitest Tests](https://img.shields.io/badge/Vitest-35%20Passed-blue.svg)](docs/TESTING.md)
[![ER Precision](https://img.shields.io/badge/ER%20Precision-100%25-green.svg)](docs/BENCHMARKS.md)
[![Docker Ready](https://img.shields.io/badge/Docker-Postgres%20%7C%20Neo4j%20%7C%20FastAPI%20%7C%20Vite-blueviolet.svg)](docker-compose.yml)

---

## 1. What is NEXUS?
**NEXUS** is an **evidence-grounded criminal network intelligence system** that transforms fragmented, multi-source criminal records into an explainable, graph-native investigative workspace for law enforcement agencies.

## 2. What Problem Does it Solve?
Police investigators face severe **intelligence-extraction bottlenecks** when analyzing cross-jurisdictional criminal syndicates. Critical connections between suspect aliases, shared burner phones (CDRs), and mule bank accounts remain trapped in disparate spreadsheets, PDF FIRs, and isolated departmental databases.

## 3. Why Does This Problem Matter?
Organized criminal rings (cyber fraud, extortion, narcotics trafficking, human trafficking) operate across state boundaries using multiple aliases and rotating burner SIMs. In manual investigations, identifying the true mastermind takes weeks or months of manual cross-referencing, while low-level operatives are often mistaken for kingpins simply due to call volume.

## 4. Who is the User?
- **Investigating Officers (IOs):** Discover cross-case suspect links, resolve aliases, and trace evidence chains.
- **Intelligence Analysts:** Partition complex networks into criminal syndicates and isolate bridge brokers.
- **Supervisory Officers (SHO / SP / DCP):** Review district intelligence rollups and immutable audit logs.

## 5. How Does NEXUS Work?
NEXUS ingests multi-source data (FIRs, CDR telephony dumps, bank ledgers), normalizes Indian vernacular text and aliases, resolves duplicate entities using multi-factor phonetic and hard-identifier corroboration, builds an in-memory heterogeneous knowledge graph, executes network modularity and centrality algorithms, and surfaces evidence-backed leads through an interactive visual workspace and grounded copilot.

## 6. What Are Its Core Modules?
1. **Multi-Source Ingestion & NLP Normalization:** Standardizes unstructured FIRs, CDR logs, and financial records.
2. **Explainable Entity Resolution:** Multi-attribute disambiguation matching Indian names, aliases, phones, and vehicles.
3. **Unified Knowledge Graph:** Heterogeneous property graph connecting 12 core entity types.
4. **Syndicate Modularity & Community Detection:** Partitions graphs into operational criminal cells (Louvain algorithm).
5. **Kingpin & Broker Isolation:** Computes Betweenness Centrality and PageRank to isolate hidden coordinators.
6. **Temporal & Pattern Intelligence:** Sequences communication bursts, fund layering loops, and shared burner clusters.
7. **Evidence Provenance & Grounded Copilot:** Clickable legal citations, Section 63 BSA compliance, and an ethical refusal gate.

## 7. What is Genuinely Different?
| Dimension | Traditional Tools | Typical Hackathon Projects | NEXUS Approach |
| :--- | :--- | :--- | :--- |
| **System Focus** | Manual desktop link charts | Generic 2D dot-and-line graphs | **Investigator Decision-Intelligence Layer** |
| **Entity Resolution** | Manual profile merging | Exact string match (fails on Indian names) | **Deterministic Phonetic + Hard ID Corroboration** |
| **Centrality Analysis** | Degree centrality (flags foot soldiers) | None | **Betweenness Centrality isolates hidden kingpins** |
| **Explainability** | Manual annotation | Hallucinated text from LLMs | **Clickable Evidence Provenance for every link** |
| **Legal Rigor** | Proprietary closed format | Unverified claims | **Section 63 BSA 2023 Tamper-Evident Hash Audit** |

## 8. What Technology Does It Use?
- **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, React Flow, Lucide React, TanStack Query
- **Backend:** Python 3.13 / FastAPI, Pydantic v2, SQLAlchemy, NetworkX, Uvicorn
- **Graph & Database:** Neo4j 5 Community (Cypher, APOC), PostgreSQL 16, In-Memory Double-Adjacency Index
- **Containerization:** Docker, Docker Compose, Nginx

## 9. How Do I Run It Locally?

### Option A: Docker Compose (Recommended)
```bash
docker compose up --build
```
- Frontend: `http://localhost:5173`
- Backend Swagger: `http://localhost:8000/docs`
- Neo4j Browser: `http://localhost:7474` (User: `neo4j`, Password: `nexuspassword`)

### Option B: Local Virtual Environment
```bash
# 1. Backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # or source venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000

# 2. Frontend (in a new terminal)
cd frontend
npm install
npm run dev
```

## 10. What Data Does It Use?
NEXUS uses a **high-fidelity deterministic synthetic dataset** ([`synthetic_data/nexus_generator.py`](synthetic_data/nexus_generator.py)) containing 50 cases, 120 persons, 150 phones, 60 bank accounts, 445 nodes, and 530 relationships with planted ground-truth clusters. **No real citizen PII or classified police data is bundled.**

## 11. How is AI Constrained?
NEXUS operates under a strict **Deterministic-Before-Generative** principle. AI models are **strictly prohibited** from outputting scores labeled "Guilt", "Probability of Criminality", or "Recidivism Risk". The Copilot features an architectural **Refusal Gate** that intercepts and blocks all unethical/illegal inference queries.

## 12. How is Evidence & Provenance Handled?
Every visual edge on the graph maintains an `EvidenceProvenance` object capturing the source document type (`FIR`, `CDR`, `BANK_TXN`), source ID, extraction timestamp, and derivation method, ensuring an unbroken evidentiary chain of custody under Section 63 of Bharatiya Sakshya Adhiniyam, 2023.

## 13. What Has Actually Been Benchmarked?
- **In-Memory Graph Index Build:** `6.05 ms` (Target: < 50ms)
- **1-Hop / 2-Hop / 3-Hop BFS:** `0.013 – 0.024 ms` (Target: < 25ms)
- **Louvain Community Detection:** `46.07 ms` (Target: < 200ms)
- **Betweenness Centrality Bridge Discovery:** `363.40 ms` (Target: < 500ms)
- **Entity Resolution Matching:** `3.36 ms` (Target: < 50ms)
- **Entity Resolution Accuracy:** **100% Precision, 100% Recall, 100% F1** on planted ground truth.

## 14. What Are the Limitations?
- Full global graph centrality algorithms currently run in-memory; scaling beyond 100,000 nodes requires Neo4j GDS projections.
- Ingestion of non-text scanned image PDFs currently requires OCR pre-processing.

## 15. What is Planned Next?
- Custom fine-tuned spaCy Indian Legal NER model integration.
- On-premise quantized local LLM (vLLM / Ollama) for zero-shot natural language Cypher querying.
- 1-Click Section 63 BSA cryptographically signed PDF Case Intelligence Dossier export.

---

## Documentation Directory

| Document | Purpose |
| :--- | :--- |
| [**Project Overview**](docs/PROJECT_OVERVIEW.md) | Problem Statement 26189 context, ecosystem, and non-goals |
| [**Problem & Domain**](docs/PROBLEM_AND_DOMAIN.md) | CCTNS/ICJS reality check and 5 technical bottlenecks |
| [**System Architecture**](docs/ARCHITECTURE.md) | Subsystems, hybrid persistence, and status matrix |
| [**Data Model & Ontology**](docs/DATA_MODEL.md) | 12 graph entities, typed edges, and provenance schemas |
| [**Intelligence Pipeline**](docs/INTELLIGENCE_PIPELINE.md) | 7-stage processing pipeline specifications |
| [**Security & Governance**](docs/SECURITY_AND_GOVERNANCE.md) | Responsible AI, ethical refusal gate, and BSA 2023 compliance |
| [**Development Guide**](docs/DEVELOPMENT.md) | Local environment setup and synthetic data generation |
| [**Testing Guide**](docs/TESTING.md) | Pytest, Vitest, and ground-truth evaluation instructions |
| [**Benchmarks & SLA**](docs/BENCHMARKS.md) | Latency SLA measurements and scale benchmarks |
| [**API Reference**](docs/API.md) | Complete REST API endpoint documentation |
| [**Live Demo Script**](docs/DEMO.md) | 3-minute judge demonstration script |
| [**Architectural Decisions**](docs/decisions/) | Accepted ADRs (Graph Architecture, Refusal Gate, Provenance) |
