# NEXUS Deployment Guide

This guide covers deployment architectures, cloud hosting instructions, configuration parameters, and verification procedures for NEXUS.

---

## 1. Minimal Public SIH Demo Architecture

For public hackathon demonstrations, NEXUS supports an ultra-lightweight deployment topology:

```
                    INVESTIGATOR / JUDGE BROWSER
                                 │
                 ┌───────────────┴───────────────┐
                 │ HTTPS (Static UI)             │ HTTPS (API Calls)
                 ▼                               ▼
     ┌───────────────────────┐       ┌───────────────────────┐
     │        VERCEL         │       │        RENDER         │
     │  React 19 / Vite SPA  │       │    FastAPI Backend    │
     │  (Global CDN & SPA    │       │ (Uvicorn on Free Tier │
     │   Rewrite Routing)    │       │   $PORT & 0.0.0.0)    │
     └───────────────────────┘       └───────────┬───────────┘
                                                 │
                                 ┌───────────────┴───────────────┐
                                 ▼                               ▼
                 ┌───────────────────────────────┐ ┌───────────────────────────┐
                 │  In-Memory GraphStore         │ │  BSA Section 63 Proofs    │
                 │  445 Nodes, 530 Edges         │ │  SHA-256 Provenance       │
                 │  Zero Cloud DB Required       │ │  Cryptographic Evidence   │
                 └───────────────────────────────┘ └───────────────────────────┘
```

> **Note:** Standalone demo mode boots completely in `<6ms` from the bundled synthetic dataset without mandatory external PostgreSQL or Neo4j instances.

---

## 2. Enterprise Cloud Architecture

In full production or multi-station enterprise setups:
- **Relational Storage:** PostgreSQL 16 on Render or Neon for case registries, RBAC, and audit trails.
- **Graph Storage:** Neo4j AuraDB or containerized Neo4j 5 Community for durable Cypher projection.
- **Backend Service:** Render Docker Web Service or Kubernetes cluster.
- **Frontend SPA:** Vercel edge deployment with global CDN caching.

---

## 3. Step-by-Step Deployment Protocol

### Part A: Deploy FastAPI Backend on Render
1. Log into [Render Dashboard](https://dashboard.render.com).
2. Click **New +** $\rightarrow$ **Web Service**.
3. Connect repository: `https://github.com/acchasujal/Nexus` (or fork).
4. Configure parameters:
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/health`
5. Configure Environment Variables:
   | Variable | Recommended Value | Description |
   | :--- | :--- | :--- |
   | `ENVIRONMENT` | `production` | Enables production settings |
   | `AUTH_MODE` | `demo` | Enables role-switching in demonstration mode |
   | `CORS_ORIGINS` | `https://your-nexus.vercel.app` | Comma-separated allowed frontend domains |
   | `NEO4J_URI` | *(optional)* `neo4j+s://...` | Neo4j AuraDB URI |
   | `NEO4J_USERNAME` | *(optional)* `neo4j` | Neo4j user |
   | `NEO4J_PASSWORD` | *(optional)* `secret` | Neo4j password |

### Part B: Deploy React Frontend on Vercel
1. Log into [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** $\rightarrow$ **Project**.
3. Import the repository and configure:
   - **Framework Preset:** `Vite`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Environment Variables:
   | Variable | Value | Description |
   | :--- | :--- | :--- |
   | `VITE_API_BASE_URL` | `https://nexus-backend.onrender.com` | Base URL of deployed Render backend |

---

## 4. Pre-Flight Readiness Checklist

- [x] Clean working tree on `main` branch.
- [x] Zero hardcoded secrets, API tokens, or `.env` files committed.
- [x] Root `/health` liveness probe endpoint returns `200 OK`.
- [x] Root `/ready` readiness probe endpoint operational.
- [x] Frontend SPA rewrite rule (`/*` $\rightarrow$ `/index.html`) enabled via `vercel.json`.
- [x] Dynamic production CORS origin parsing verified.
- [x] Ground-truth precision/recall benchmark verified at 100%.
