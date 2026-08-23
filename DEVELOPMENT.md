# NEXUS Development & Contribution Guide

## 1. Local Environment Setup

### 1.1 Python Virtual Environment
```bash
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux/macOS:
source venv/bin/activate

pip install -r backend/requirements.txt
```

### 1.2 Frontend Setup
```bash
cd frontend
npm install
```

---

## 2. Running Services

### Start Backend Development Server
```bash
uvicorn backend.app.main:app --reload --port 8000
```
API Documentation will be live at `http://localhost:8000/docs`.

### Start Frontend Development Server
```bash
cd frontend
npm run dev
```
UI will be live at `http://localhost:5173`.

---

## 3. Regenerating Synthetic Intelligence Data

To regenerate the multi-source synthetic intelligence dataset and ground truth:
```bash
python -c "from synthetic_data.nexus_generator import export_nexus_synthetic_dataset; export_nexus_synthetic_dataset()"
```
This produces `artifacts/nexus_graph/nexus_graph.json` and `artifacts/nexus_graph/ground_truth.json`.
