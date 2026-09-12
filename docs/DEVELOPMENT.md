# NEXUS Developer Setup & Testing Guide

This guide covers local environment setup, dependencies, running the application stack, automated test suites, code quality tooling, and ground-truth benchmark verification.

---

## 1. Prerequisites
- **Python:** Version 3.11+ (Python 3.13 tested and verified)
- **Node.js:** Version 20+ with `npm`
- **Docker & Docker Compose:** *(Optional)* For running containerized PostgreSQL 16 and Neo4j 5 Community.

---

## 2. Local Environment Setup

### 2.1 Backend Setup (FastAPI)
```bash
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows PowerShell
source venv/bin/activate       # Linux / macOS

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Start development server
uvicorn backend.app.main:app --reload --port 8000
```
API Swagger documentation is live at: `http://localhost:8000/docs`

### 2.2 Frontend Setup (React & Vite)
```bash
cd frontend
npm install
npm run dev
```
Frontend development server is live at: `http://localhost:5173`

---

## 3. Full Stack Docker Compose (Optional)
To run the complete integrated stack locally (PostgreSQL 16, Neo4j 5 Community, FastAPI, Vite):
```bash
docker compose up --build
```
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Neo4j Browser: `http://localhost:7474` (User: `neo4j`, Password: `nexuspassword`)

---

## 4. Testing & Verification Suite

NEXUS maintains comprehensive automated test coverage across all subsystems:

### 4.1 Backend Test Suite (Pytest)
```bash
# Run all 708 automated backend tests
pytest

# Run tests with execution timing breakdown
pytest -v --durations=10

# Run specific functional suites
pytest tests/test_neo4j_projection.py
pytest tests/test_evidence_tamper_audit.py
pytest tests/test_copilot_refusal_gate.py
pytest tests/test_nexus_entity_resolution.py
```

### 4.2 Frontend Test Suite (Vitest)
```bash
cd frontend

# Run all 114 Vitest unit and integration tests
npm test -- --run

# Run TypeScript compilation and production bundle build
npm run build
```

### 4.3 Linting & Code Quality
```bash
# Backend lint check (0 errors required)
python -m ruff check backend/ shared/ tests/

# Frontend lint check (0 errors required)
cd frontend && npm run lint
```

### 4.4 Ground-Truth Benchmark Evaluation
Validate the Entity Resolution engine against planted criminal syndicate ground truth:
```bash
python scripts/evaluate_ground_truth.py
```
**Expected Output:** 100% Precision, 100% Recall, 100% F1 score.

---

## 5. Synthetic Dataset Generation
To regenerate the deterministic synthetic dataset and ground-truth validation fixtures:
```bash
python -c "from synthetic_data.nexus_generator import export_nexus_synthetic_dataset; export_nexus_synthetic_dataset()"
```
- Generated graph: `artifacts/nexus_graph/nexus_graph.json` (445 nodes, 530 relationships)
- Planted ground truth: `artifacts/nexus_graph/ground_truth.json`
