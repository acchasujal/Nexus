# NEXUS — Developer Setup & Contribution Guide

## 1. Prerequisites

- **Python:** Version 3.11+ (Python 3.13 tested and verified)
- **Node.js:** Version 20+ with `npm`
- **Docker & Docker Compose:** Optional for containerized multi-service deployment

---

## 2. Local Environment Setup

### 2.1 Backend Setup (FastAPI & Python)

```bash
# 1. Create and activate a virtual environment
python -m venv venv

# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate

# 2. Install backend dependencies
pip install -r backend/requirements.txt

# 3. Start the FastAPI development server
uvicorn backend.app.main:app --reload --port 8000
```
API Swagger documentation is live at: `http://localhost:8000/docs`

### 2.2 Frontend Setup (React & Vite)

```bash
# In a separate terminal:
cd frontend
npm install
npm run dev
```
Frontend UI is live at: `http://localhost:5173`

---

## 3. Containerized Deployment with Docker Compose

To launch the full local NEXUS stack (PostgreSQL 16, Neo4j 5 Community, FastAPI backend, Vite/Nginx frontend):

```bash
docker compose up --build
```

- **Frontend Application:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`
- **Neo4j Browser:** `http://localhost:7474` (User: `neo4j`, Password: `nexuspassword`)
- **PostgreSQL Port:** `localhost:5432`

---

## 4. Synthetic Intelligence Dataset Generation

To regenerate the synthetic criminal intelligence dataset and ground-truth validation files:

```bash
python -c "from synthetic_data.nexus_generator import export_nexus_synthetic_dataset; export_nexus_synthetic_dataset()"
```

Output files generated:
- `artifacts/nexus_graph/nexus_graph.json` (445 nodes, 530 relationships)
- `artifacts/nexus_graph/ground_truth.json` (Planted entity resolution and community ground truth)
