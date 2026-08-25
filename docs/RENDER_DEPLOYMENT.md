# NEXUS Production Deployment Guide (Render & Cloud Architecture)

> **Platform:** Render (Frontend Static Site + FastAPI Web Service + PostgreSQL + Neo4j AuraDB)  
> **System:** NEXUS — Evidence-Grounded Criminal Network Intelligence Platform (SIH 2026 PS 26189)  

---

## 1. Architecture Overview

```
                          INVESTIGATOR (Browser)
                                    │
                  ┌─────────────────┴─────────────────┐
                  │ HTTPS                             │ HTTPS (API)
                  ▼                                   ▼
      ┌─────────────────────────┐         ┌─────────────────────────┐
      │   Render Static Site    │         │    Render Web Service   │
      │   (React 19 / Vite SPA) │         │     (FastAPI Backend)   │
      └─────────────────────────┘         └────────────┬────────────┘
                                                       │
                                     ┌─────────────────┴─────────────────┐
                                     ▼                                   ▼
                      ┌─────────────────────────────┐     ┌─────────────────────────────┐
                      │    PostgreSQL Database      │     │      Neo4j AuraDB           │
                      │  (Cases, Audit, Auth)       │     │ (Network Graph & Cypher)    │
                      └─────────────────────────────┘     └─────────────────────────────┘
```

---

## 2. Prerequisites
1. **GitHub Account** with access to [https://github.com/acchasujal/Nexus](https://github.com/acchasujal/Nexus).
2. **Render Account** ([render.com](https://render.com)).
3. *(Optional for Graph persistence)* **Neo4j AuraDB Account** ([neo4j.com/cloud/aura](https://neo4j.com/cloud/aura/)).

---

## 3. Option A: Blueprint Deployment (One-Click with `render.yaml`)

1. Log into your Render dashboard.
2. Click **New +** $\rightarrow$ **Blueprint**.
3. Connect the `acchasujal/Nexus` repository.
4. Render will read [`render.yaml`](file:///d:/Projects/CaseClock/render.yaml) and automatically configure:
   - **`nexus-backend`** (Python Web Service with `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`)
   - **`nexus-frontend`** (Static Site with SPA rewrite rules for `/network`, `/cases/:id`, etc.)
5. Click **Apply**.

---

## 4. Option B: Manual Service Setup on Render

### Step 4.1: Deploy Backend Web Service
1. In Render Dashboard, click **New +** $\rightarrow$ **Web Service**.
2. Select `acchasujal/Nexus` repository.
3. Configure settings:
   - **Name:** `nexus-backend`
   - **Region:** Singapore (or closest to India)
   - **Branch:** `main`
   - **Root Directory:** (leave empty)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
4. Add Environment Variables:
   - `ENVIRONMENT` = `production`
   - `CORS_ORIGINS` = `https://<your-frontend-subdomain>.onrender.com`
   - `JWT_SECRET_KEY` = `generate-a-strong-32-char-random-key`
   - `ARTIFACT_PATH` = `artifacts/nexus_graph/nexus_graph.json`
   - `AUTH_MODE` = `demo`
   - *(Optional)* `DATABASE_URL` = `postgresql://...`
   - *(Optional)* `NEO4J_URI` = `neo4j+s://xxxx.databases.neo4j.io`
   - *(Optional)* `NEO4J_USER` = `neo4j`
   - *(Optional)* `NEO4J_PASSWORD` = `<your-aura-password>`
5. Click **Create Web Service**. Note the deployed URL (e.g. `https://nexus-backend.onrender.com`).

---

### Step 4.2: Deploy Frontend Static Site
1. In Render Dashboard, click **New +** $\rightarrow$ **Static Site**.
2. Select `acchasujal/Nexus` repository.
3. Configure settings:
   - **Name:** `nexus-frontend`
   - **Branch:** `main`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm ci && npm run build`
   - **Publish Directory:** `dist`
4. Add Environment Variable:
   - `VITE_API_BASE_URL` = `https://nexus-backend.onrender.com` (use your actual backend URL)
5. Configure Redirect/Rewrite rule under **Redirects/Rewrites**:
   - **Type:** `Rewrite`
   - **Source:** `/*`
   - **Destination:** `/index.html`
6. Click **Create Static Site**.

---

## 5. PostgreSQL & Neo4j AuraDB Setup

### PostgreSQL on Render:
1. Click **New +** $\rightarrow$ **PostgreSQL**.
2. Set Database: `nexus_db`, User: `nexus`.
3. Copy the **Internal Database URL** into the backend's `DATABASE_URL` environment variable.

### Neo4j AuraDB:
1. Create a Free/Professional AuraDB Instance at [console.neo4j.io](https://console.neo4j.io).
2. Download credentials `.txt` file.
3. Set in Render Backend Environment:
   - `NEO4J_URI`: `neo4j+s://<dbid>.databases.neo4j.io`
   - `NEO4J_USER`: `neo4j`
   - `NEO4J_PASSWORD`: `<your-downloaded-password>`

---

## 6. Health & Readiness Verification

Once deployed, verify endpoints:
```bash
# 1. Process Liveness
curl -I https://nexus-backend.onrender.com/health
# Response: HTTP/2 200 {"status":"healthy","service":"nexus-backend",...}

# 2. Storage & Graph Readiness
curl https://nexus-backend.onrender.com/ready
# Response: {"status":"ready","total_nodes":445,"total_edges":530,...}
```

---

## 7. Demo Day Presentation Protocol (Judge Remote Access)

1. Share the deployed Frontend URL: `https://nexus-frontend.onrender.com`
2. The judge selects any role (`Investigator`, `Analyst`, `Supervisor`, `SP`) at login.
3. Standard demonstration sequence runs out-of-the-box without requiring local servers:
   - **Worklist:** Review live multi-jurisdictional FIRs.
   - **Universal Search:** Search `9845011223` or `Rafiq`.
   - **Entity Fusion:** Compare cross-case candidates (CASE-141 ↔ CASE-207) and confirm fusion.
   - **Global Network Canvas:** Explore D3-rendered multi-hop syndicate topology with Louvain clusters.
   - **Evidence & Chain of Custody:** Verify Section 63 BSA SHA-256 cryptographic hashes.
   - **Ethical Copilot:** Demonstrate real-time refusal of predictive guilt scoring vs grounded answers.
   - **Export:** Generate Section 63 BSA-compliant court dossier PDF.
