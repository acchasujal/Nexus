# NEXUS Public SIH Demo Deployment Guide (Vercel Frontend + Render Backend)

> **Hackathon Target:** Smart India Hackathon 2026 (Problem Statement ID: 26189)  
> **System:** NEXUS — Evidence-Grounded Criminal Network Intelligence Platform  
> **Client:** Ministry of Home Affairs (MHA) / National Crime Records Bureau (NCRB)  
> **Recommended Minimal Stack:** **Vercel** (React/Vite SPA) + **Render Free Web Service** (FastAPI)  

---

## 1. Minimal Public Deployment Architecture

```
                    INVESTIGATOR / JUDGE BROWSER
                                 │
                 ┌───────────────┴───────────────┐
                 │ HTTPS (Static UI)             │ HTTPS (API Calls)
                 ▼                               ▼
     ┌───────────────────────┐       ┌───────────────────────┐
     │        VERCEL         │       │        RENDER         │
     │  React 19 / Vite SPA  │       │    FastAPI Backend    │
     │  (Automatic Global    │       │ (Uvicorn on Free Tier │
     │   CDN & SPA Rewrites) │       │   $PORT & 0.0.0.0)    │
     └───────────────────────┘       └───────────┬───────────┘
                                                 │
                                 ┌───────────────┴───────────────┐
                                 ▼                               ▼
                 ┌───────────────────────────────┐ ┌───────────────────────────┐
                 │  In-Memory GraphStore         │ │  BSA Section 63 Proofs    │
                 │  445 Nodes, 530 Edges,        │ │  SHA-256 Provenance       │
                 │  50 Cases, 120 Suspects       │ │  Cryptographic Evidence   │
                 └───────────────────────────────┘ └───────────────────────────┘
```

> [!NOTE]
> **Blueprint is not required.** PostgreSQL, Neo4j, Redis, and Docker are **not required** for the public SIH demo. The backend automatically boots from the self-contained synthetic ground-truth dataset in `<6ms`.

---

## 2. Step-by-Step Deployment Protocol

### PART A: Deploy FastAPI Backend on Render (5 Minutes)

1. Log into [Render Dashboard](https://dashboard.render.com).
2. Click **New +** $\rightarrow$ **Web Service**.
3. Connect the GitHub repository: `https://github.com/acchasujal/Nexus` (or your fork).
4. Configure service parameters:
   - **Name:** `nexus-backend` (or your preferred name)
   - **Region:** Singapore / Frankfurt / Oregon (any available)
   - **Branch:** `main`
   - **Root Directory:** *(leave blank — repository root)*
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`
   - **Health Check Path:** `/health`
5. Configure Environment Variables under **Environment**:
   | Variable | Value | Notes |
   | :--- | :--- | :--- |
   | `ENVIRONMENT` | `production` | Enables production mode |
   | `AUTH_MODE` | `demo` | Enables role-based demo switching |
   | `JWT_SECRET_KEY` | *(Click "Generate" or type a 32+ char string)* | Tokens signing secret |
   | `CORS_ORIGINS` | `https://nexus.vercel.app,http://localhost:5173` | Replace `nexus.vercel.app` with your actual Vercel domain once deployed |
   | `ARTIFACT_PATH` | `artifacts/nexus_graph/nexus_graph.json` | Default synthetic graph path |
6. Click **Create Web Service**.
7. Wait for the build to complete. Note your backend URL (e.g. `https://nexus-backend.onrender.com`).

---

### PART B: Deploy Frontend on Vercel (3 Minutes)

1. Log into [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** $\rightarrow$ **Project**.
3. Import the `Nexus` GitHub repository.
4. Configure project settings:
   - **Framework Preset:** `Vite`
   - **Root Directory:** Click **Edit** $\rightarrow$ select `frontend` $\rightarrow$ click **Continue**.
   - **Build Command:** `npm run build` (or default `vite build`)
   - **Output Directory:** `dist`
5. Under **Environment Variables**, add:
   | Key | Value |
   | :--- | :--- |
   | `VITE_API_BASE_URL` | `https://nexus-backend.onrender.com` *(Use your actual Render backend URL from Part A)* |
6. Click **Deploy**.
7. Vercel will build the bundle and provide your public URL (e.g. `https://nexus-crime-intel.vercel.app`).
8. *(Important)* Copy your Vercel URL, go back to Render $\rightarrow$ `nexus-backend` $\rightarrow$ **Environment**, and add your Vercel URL to `CORS_ORIGINS`.

---

## 3. Verification & Smoke Test Checklist

Once both services are deployed, test the live deployment in under 60 seconds:

1. **Liveness Check:**
   ```bash
   curl https://nexus-backend.onrender.com/health
   # Response: {"status":"ok","service":"nexus-backend","version":"1.0.0","environment":"production"}
   ```
2. **Readiness & Graph Data Check:**
   ```bash
   curl https://nexus-backend.onrender.com/ready
   # Response: {"status":"ready","service":"nexus-backend","storage":"in_memory","total_nodes":445,"total_edges":530}
   ```
3. **Open Vercel Frontend in Browser:**
   - Open your Vercel URL (e.g. `https://nexus-crime-intel.vercel.app`).
   - Click **Login as Investigator**.
   - Search `9845011223` in Universal Search $\rightarrow$ confirms backend connectivity.
   - Navigate to **Entity Fusion** $\rightarrow$ confirms cross-case candidate resolution.
   - Navigate to **Network Explorer** $\rightarrow$ confirms D3 multi-hop graph canvas rendering.
   - Refresh on nested route `/fusion` or `/network` $\rightarrow$ confirms Vercel SPA rewrites work.

---

## 4. Resetting Demo Fixtures During Live Evaluation

If you need to reset all suspect merges, graph links, and lead triages back to the initial state during a live presentation:
- Navigate to **Settings** (`/settings`) in the UI.
- Click **Reset Demo Fixture**.
