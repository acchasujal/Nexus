# NEXUS — Evidence-Grounded Criminal Network Intelligence Platform
> **SIH 2026 Problem Statement PS 26189**  
> AI-Powered Criminal Network Analysis, Multi-Source Entity Resolution, and Co-Accused Graph Intelligence.

---

## 1. Executive Summary & Problem Context

Modern law enforcement and intelligence agencies face immense challenges in uncovering complex, organized criminal syndicates. Critical intelligence is fragmented across disparate, siloed data sources:
- **First Information Reports (FIRs)** and court chargesheets with inconsistent naming, spelling mistakes, and alias variations.
- **Call Detail Records (CDRs)**, IMEI logs, and shared burner phones.
- **Banking, Hawala, and Financial Transaction Ledgers** with multi-hop layering and smurfing.
- **Vehicle Registrations & Fastag logs**.
- **Field Intelligence Reports** and seized physical/digital evidence.

**NEXUS** is an enterprise-grade, evidence-grounded criminal intelligence platform that integrates multi-source law enforcement data into a unified, high-performance graph database. It provides deterministic, explainable entity resolution, automated syndicate community detection, bridge broker discovery, temporal event sequencing, and an investigator copilot protected by strict ethical refusal guardrails against autonomous guilt or predictive criminal inference.

---

## 2. Core Capabilities

### 🔍 Explainable Entity Resolution (ER)
- **Multi-Attribute Matching:** Correlates suspects across name variations, Indian phonetic normalization (`sh` ↔ `s`, `v` ↔ `b`, `ee` ↔ `i`, `ou` ↔ `u`), character-bigram Jaccard similarity, alias lists, phone numbers, vehicle registrations, and national identifiers.
- **Deterministic Confidence Breakdown:** Categorizes resolution into clear status tiers (`MATCHED`, `PROBABLE_MATCH`, `REVIEW_REQUIRED`, `NOT_MATCHED`) with explicit mathematical contribution breakdown.
- **Zero Silent Merges:** Preserves source entity distinctness while establishing cross-case resolution links with full provenance.

### 🕸️ Graph Analytics & Syndicate Discovery
- **Community Detection:** Applies NetworkX Louvain/Modularity clustering to discover hidden syndicates and operational criminal cells.
- **Bridge Broker Identification:** Computes betweenness centrality and articulation points to highlight critical intermediary brokers connecting otherwise distinct criminal modules.
- **Multi-Hop Traversal:** Real-time sub-millisecond BFS expansion across suspect networks, financial layering chains, and co-accused links.
- **Repeat Accused & Shared Cluster Analysis:** Automatically detects cross-case recidivism and clusters of suspects sharing burner phones or getaway vehicles.

### 🤖 Grounded Investigator Copilot
- **Strict Ethical & Legal Guardrails:** Automated refusal gate strictly blocks queries asking for guilt/innocence determination, culpability, predictive dangerousness, or recidivism likelihood.
- **Verifiable Citations:** Every response includes direct citations linked to source FIRs, CDR logs, bank transactions, and graph analytics procedures.
- **Grounded Graph Context:** Returns suggested interactive graph actions and adjacent network structures.

### 🛡️ Local-First Architecture & Audit Compliance
- **Local Infrastructure:** Docker Compose configuration running PostgreSQL 16, Neo4j 5 Community, FastAPI backend, and React/Vite frontend.
- **Immutable Audit Trail:** Logs all queries, entity resolution executions, and graph expansions with actor identity and timestamp for judicial defensibility.

---

## 3. Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, React Flow, Lucide React, TanStack Query |
| **Backend** | Python 3.13 / FastAPI, Pydantic v2, SQLAlchemy, NetworkX, Uvicorn |
| **Graph & Storage** | Neo4j 5 Community (Cypher, APOC), PostgreSQL 16 (Relational/Audit), In-Memory Adjacency Index |
| **Testing & Quality** | Pytest (325 tests), Vitest (35 tests), Docker Compose, GitHub Actions |

---

## 4. Quick Start (Local Development)

### Prerequisites
- Python 3.11+ (or 3.13)
- Node.js 20+ & npm
- Docker & Docker Compose (Optional for containerized run)

### Running Locally

```bash
# 1. Clone the repository
git clone <NEXUS_REPOSITORY_URL>
cd nexus

# 2. Setup and Run Backend
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000

# 3. Setup and Run Frontend (in a new terminal)
cd frontend
npm install
npm run dev
```
Open your browser at `http://localhost:5173`.

### Running with Docker Compose

```bash
docker compose up --build
```
- **Frontend:** `http://localhost:5173`
- **Backend API Docs:** `http://localhost:8000/docs`
- **Neo4j Browser:** `http://localhost:7474` (Credentials: `neo4j` / `nexuspassword`)

---

## 5. Verification & Benchmarking

Execute the automated test suites and performance benchmarks:

```bash
# Run backend test suite (325 tests)
pytest

# Run frontend test suite (35 tests)
cd frontend && npm test -- --run

# Run Ground Truth Precision/Recall Evaluation
python scripts/evaluate_ground_truth.py

# Run Real-Time Graph Latency Benchmarks
python scripts/benchmark_nexus.py
```

---

## 6. Project Structure

```
├── artifacts/
│   └── nexus_graph/          # Synthetic intelligence graph & ground truth dataset
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI REST routers & error handlers
│   │   ├── auth/             # RBAC principal & token verifier
│   │   ├── core/graph/       # Graph schema, entities, edges, & algorithms (ER, clustering, similarity)
│   │   ├── db/               # In-memory repository & persistence adapters
│   │   ├── services/         # Case, Audit, and Grounded Copilot services
│   │   └── main.py           # Application entrypoint
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # UI shell, NetworkAnalysisPanel, similarity & copilot widgets
│   │   ├── pages/            # Overview, NetworkExplorer, Entities, Patterns, Timeline, Evidence, Copilot, Audit
│   │   ├── lib/apiClient.ts  # Typed API transport layer
│   │   └── routes/router.tsx # Application routing
│   └── package.json
├── shared/
│   └── contracts/            # Single source-of-truth API schemas (Python & TypeScript)
├── synthetic_data/
│   └── nexus_generator.py    # Multi-source intelligence graph & ground truth generator
├── scripts/
│   ├── evaluate_ground_truth.py
│   └── benchmark_nexus.py
└── docker-compose.yml
```

---

## 7. License & Compliance

Developed for SIH 2026 PS 26189. Designed in compliance with Indian criminal procedure, evidentiary chain-of-custody standards, and responsible AI fairness principles.
