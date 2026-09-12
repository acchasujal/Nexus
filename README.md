# NEXUS — Evidence-Grounded Criminal Network Intelligence System

> **Smart India Hackathon (SIH) 2026** — Problem Statement ID: 26189  
> **Client Organization:** Ministry of Home Affairs (MHA) / National Crime Records Bureau (NCRB)  
> **Division:** Women Safety Division | **Theme:** Blockchain & Cybersecurity  

[![Pytest Tests](https://img.shields.io/badge/Pytest-708%20Passed-emerald.svg)](docs/DEVELOPMENT.md)
[![Vitest Tests](https://img.shields.io/badge/Vitest-114%20Passed-blue.svg)](docs/DEVELOPMENT.md)
[![ER Precision](https://img.shields.io/badge/ER%20Precision-100%25-green.svg)](docs/BENCHMARKS.md)
[![Docker Ready](https://img.shields.io/badge/Docker-Postgres%20%7C%20Neo4j%20%7C%20FastAPI%20%7C%20Vite-blueviolet.svg)](docker-compose.yml)

---

## 1. What is NEXUS?
NEXUS is an **evidence-grounded criminal network intelligence platform** that transforms fragmented First Information Reports (FIRs), Call Detail Records (CDRs), and banking transaction ledgers into an explainable, graph-native investigative workspace for Indian law enforcement, resolving suspect aliases and uncovering hidden kingpin brokers without black-box predictive bias.

## 2. Problem & Solution
- **The Bottleneck:** Investigating officers face intelligence fragmentation across siloed FIR narratives, telecom CDR spreadsheets, and bank transaction ledgers. Suspects deliberately use phonetic aliases, rotating burner phones, and cross-district jurisdictions.
- **The Solution:** NEXUS applies deterministic phonetic and multi-attribute entity resolution, constructs an in-memory heterogeneous property graph with durable Neo4j projection, identifies criminal syndicates via Louvain modularity, isolates hidden kingpins via Betweenness Centrality, and powers an evidence-grounded AI Copilot gated by an ethical refusal firewall.

## 3. Architecture Summary
NEXUS adopts a hybrid polyglot persistence architecture:
- **In-Memory `GraphStore`:** Dual adjacency lists (`adj` and `radj`) indexed by entity and edge type for sub-millisecond BFS traversals (<0.025ms).
- **Neo4j 5 Community / AuraDB:** Persistent graph projection with parameterized batch Cypher synchronization (`UNWIND ... MERGE`) and schema constraints.
- **Cloud PostgreSQL 16:** Relational state, case metadata, RBAC, and append-only audit trail.
- **Presentation:** React 19 / Vite SPA featuring React Flow canvas, interactive Pathfinder, and Evidence Drawer.

```
React 19 / Vite SPA  ──►  FastAPI Backend (REST / Copilot)
                                │
          ┌─────────────────────┴─────────────────────┐
          ▼                                           ▼
In-Memory GraphStore                       PostgreSQL 16 & Neo4j
(Sub-ms BFS & Analytics)                  (Relational & Graph State)
```

## 4. Repository Structure
```
/
├── README.md               # Primary entry point & project summary
├── AGENTS.md               # AI coding governance & development rules
├── progress.md             # Single source of truth for ongoing progress
├── decisions.md            # Single source of truth for ADRs
├── docs/                   # Canonical documentation set
│   ├── ARCHITECTURE.md     # Polyglot persistence, graph engine, subsystems
│   ├── DEPLOYMENT.md       # Render, Vercel, Docker, pre-flight checklist
│   ├── DEVELOPMENT.md      # Setup, test commands, lint, benchmark verification
│   ├── SECURITY.md         # Responsible AI, Section 63 BSA, SHA-256 integrity
│   ├── API.md              # Core REST endpoints & request contracts
│   ├── DATA_MODEL.md       # 12 graph entities, typed edges, provenance
│   ├── INTELLIGENCE_PIPELINE.md # 7-stage ingestion & analysis pipeline
│   ├── BENCHMARKS.md       # SLA measurements & scale benchmarks
│   ├── DEMO.md             # 3-minute judge demonstration script
│   └── archive/            # Historical milestone reports & audit handoffs
├── backend/                # FastAPI application, core graph, db, services
├── frontend/               # React 19, TypeScript, Tailwind, React Flow
├── shared/                 # Canonical schemas & contracts
├── synthetic_data/         # Deterministic synthetic intelligence generator
├── scripts/                # Benchmarking, evaluation, and seeding scripts
└── tests/                  # Pytest backend & scale test suites
```

## 5. Local Quick-Start

### Using Docker Compose:
```bash
docker compose up --build
```
- Frontend UI: `http://localhost:5173`
- Backend Swagger API: `http://localhost:8000/docs`
- Neo4j Browser: `http://localhost:7474` (User: `neo4j`, Password: `nexuspassword`)

### Using Local Virtual Environment:
```bash
# 1. Backend
python -m venv venv
.\venv\Scripts\Activate.ps1   # or source venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --port 8000

# 2. Frontend (in separate terminal)
cd frontend
npm install
npm run dev
```

## 6. Testing & Quality Gates
```bash
# Backend unit & integration tests (708 passing)
pytest

# Backend linting (0 errors)
python -m ruff check backend/ shared/ tests/

# Frontend tests & build (114 passing, 0 build errors)
cd frontend && npm test -- --run && npm run build

# Ground-truth entity resolution benchmark (100% Precision / Recall)
python scripts/evaluate_ground_truth.py
```

## 7. Key Limitations
- Global betweenness centrality across >100,000 nodes requires Neo4j GDS projections.
- Ingestion of non-text scanned image PDFs currently requires upstream OCR extraction.
- Determination of legal guilt or innocence is excluded by design under Indian constitutional law.

---

## 8. Central Documentation Links
- **[Progress & Status Board](progress.md)** — Active workstreams, completed milestones, verification matrix.
- **[Architectural Decisions](decisions.md)** — Record of accepted ADRs (Graph engine, Refusal gate, SHA-256, Neo4j).
- **[System Architecture](docs/ARCHITECTURE.md)** — Detailed subsystem architecture and data flows.
- **[Deployment Guide](docs/DEPLOYMENT.md)** — Production hosting on Render & Vercel.
- **[Security & Governance](docs/SECURITY.md)** — Ethical AI firewall and Section 63 BSA compliance.
- **[Developer Guide](docs/DEVELOPMENT.md)** — Environment setup, tests, and synthetic data generation.
- **[API Reference](docs/API.md)** — REST API contracts and parameters.
