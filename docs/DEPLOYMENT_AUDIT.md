# NEXUS Deployment Audit & Production Gap Analysis

> **Target Platform:** Render (Frontend Static Site + FastAPI Web Service + PostgreSQL + Neo4j AuraDB)  
> **System:** NEXUS — Evidence-Grounded Criminal Network Intelligence Platform  
> **Client:** Ministry of Home Affairs (MHA) / NCRB (SIH 2026 PS 26189)  
> **Status:** Authoritative Production Readiness Assessment  

---

## 1. Current Architecture

```
                    INVESTIGATOR BROWSER
                             │
            ┌────────────────┴────────────────┐
            │                                 │
     Static UI (Vite)                   API Requests
     (Port 5173 / CDN)                  (HTTPS / JSON)
            │                                 │
            ▼                                 ▼
┌─────────────────────────┐       ┌───────────────────────────────┐
│     React 19 SPA        │       │       FastAPI Backend         │
│ (D3.js / Tailwind / MSW)│       │ (Uvicorn ASGI Process $PORT)  │
└─────────────────────────┘       └──────────────┬────────────────┘
                                                 │
                               ┌─────────────────┴─────────────────┐
                               ▼                                   ▼
                ┌───────────────────────────┐       ┌───────────────────────────┐
                │   In-Memory GraphStore    │       │    PostgreSQL / Neo4j     │
                │ (Python Dual Adjacency)   │       │ (Relational & Graph Persist)│
                └───────────────────────────┘       └───────────────────────────┘
```

The NEXUS system uses a hybrid persistence architecture:
1. **Frontend:** React 19 SPA bundled with Vite, D3.js custom network canvas, TanStack React Query, and Tailwind CSS.
2. **Backend:** FastAPI with dependency injection, Pydantic data schemas, structured error handlers, and REST endpoints for case intelligence, cross-case entity resolution, Louvain communities, and BSA Section 63 cryptographic evidence verification.
3. **Core Intelligence Engine:** Dual in-memory adjacency store (`adj`/`radj`) for `<0.025ms` BFS traversals, bridge centrality, and deterministic pattern rules, with optional polyglot persistence to PostgreSQL and Neo4j.

---

## 2. Current Local Development Architecture

- **Backend:** `uvicorn backend.app.main:app --reload --port 8000`
- **Frontend:** `vite` development server on `http://localhost:5173` with proxy and optional mock service worker (MSW).
- **Databases:** Local `docker-compose.yml` running `postgres:16-alpine` on port 5432 and `neo4j:5.20-community` on ports 7474/7687.
- **Environment:** Local `.env` configuration file.

---

## 3. Current Production Readiness Summary

| Component | Status | Readiness Level |
| :--- | :---: | :--- |
| **Frontend Static Build** | ✅ Ready | `npm run build` generates optimized `dist/` (<180 kB gzip initial payload). |
| **API Base URL Config** | ⚠️ Fix Needed | `apiClient.ts` falls back to `window.location.origin` if `VITE_API_BASE_URL` is unset, which breaks cross-origin separation on Render unless explicitly configured. |
| **FastAPI Root Health Check** | ⚠️ Fix Needed | `/api/v1/system/status` exists, but standard top-level `/health` and `/ready` are missing at root. |
| **Render Port Binding** | ⚠️ Fix Needed | `backend/Dockerfile` and startup defaults use hardcoded `8000` rather than dynamic `$PORT`. |
| **CORS Configuration** | ⚠️ Fix Needed | `backend/app/config.py` defaults to localhost URLs; needs wildcard support in dev or dynamic origin matching in production. |
| **SPA Route Rewrites** | ⚠️ Fix Needed | Render Static Site requires rewrite rule to redirect `/*` to `/index.html` for deep linking (`/cases/:id`, `/network`). |
| **Production Demo Seeding** | ✅ Ready | Graph loader self-initializes from synthetic artifacts on startup without laptop dependencies. |

---

## 4. Frontend Deployment Readiness

- **Status:** ⚠️ Ready with minor environment & routing adjustments.
- **Evidence:** `frontend/src/lib/apiClient.ts` reads `import.meta.env.VITE_API_BASE_URL`.
- **Impact:** When deployed to Render Static Sites, navigating directly to `/cases/case-0001` or `/network` will return a 404 error without a rewrite rule (`/*` $\rightarrow$ `/index.html`).
- **Fix:** 
  1. Add `render.yaml` with static site routes configured: `source: /*`, `destination: /index.html`.
  2. Document `VITE_API_BASE_URL` pointing to the Render backend URL (e.g., `https://nexus-backend.onrender.com`).

---

## 5. FastAPI Deployment Readiness

- **Status:** ⚠️ Ready with entrypoint & health check fixes.
- **Evidence:** `backend/app/main.py` defines `app = create_app()`.
- **Impact:** Render assigns a dynamic port via `$PORT`. Hardcoding `8000` in the CMD will cause Render port-scan timeouts.
- **Fix:**
  1. Add a standard `/health` and `/ready` endpoint returning JSON status.
  2. Configure `uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}`.

---

## 6. PostgreSQL Readiness

- **Status:** ✅ Ready for cloud persistence.
- **Evidence:** `DATABASE_URL` is parsed via Pydantic `Settings` in `backend/app/config.py`.
- **Impact:** In-memory fallback allows the application to boot immediately even if PostgreSQL connection string is pending, ensuring zero downtime during demonstration setup.
- **Fix:** Ensure `DATABASE_URL` supports SQLAlchemy/psycopg connection formatting (e.g. `postgresql://...`).

---

## 7. Neo4j AuraDB Readiness

- **Status:** ✅ Ready.
- **Evidence:** `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` environment variables are supported.
- **Impact:** Supports `neo4j+s://` protocol required by Neo4j AuraDB cloud instances.
- **Fix:** Document AuraDB connection string format in `docs/RENDER_DEPLOYMENT.md`.

---

## 8. Authentication & Security Readiness

- **Status:** ✅ Production Hardened.
- **Evidence:**
  - `backend/app/config.py` emits an explicit warning if the default JWT secret is used in production.
  - Ethical Refusal Interceptor guarantees zero predictive guilt scoring at the architectural level.
  - Zero citizen PII in synthetic datasets.
- **Fix:** Set a strong `JWT_SECRET_KEY` in Render environment variables.

---

## 9. Environment Configuration

### Required Backend Variables (Render Web Service)
```bash
ENVIRONMENT=production
PORT=10000
CORS_ORIGINS=https://nexus-frontend.onrender.com
JWT_SECRET_KEY=generate-a-strong-random-secret-key-32-chars-min
DATABASE_URL=postgresql://nexus:password@dpg-xxxx.render.com/nexus_db
NEO4J_URI=neo4j+s://xxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-auradb-password
```

### Required Frontend Variables (Render Static Site)
```bash
VITE_API_BASE_URL=https://nexus-backend.onrender.com
```

---

## 10. CI/CD Readiness

- **Status:** ✅ Comprehensive.
- **Evidence:** `.github/workflows/ci.yml` runs full backend ruff lint, 509 pytest suite, ground truth evaluation, frontend ESLint, 46 vitest suite, and `vite build`.
- **Fix:** Add deployment verification script and `render.yaml` infrastructure-as-code manifest.

---

## 11. Observability & Health Checks

- **Root Liveness:** `GET /health` $\rightarrow$ Process alive status, timestamp, version.
- **Readiness:** `GET /ready` $\rightarrow$ Storage, GraphStore node/edge counts, repository health.
- **Telemetry:** `GET /api/v1/system/status` $\rightarrow$ Comprehensive node, edge, and case breakdown.

---

## 12. Deployment Checklist

- [x] Repository clean on `main` branch.
- [x] All 509 backend tests passing.
- [x] All 46 frontend tests passing.
- [x] Ground truth evaluation passing at 100% precision & recall.
- [x] Production build generated without errors.
- [ ] Root `/health` and `/ready` endpoints added to FastAPI.
- [ ] `render.yaml` blueprint authored.
- [ ] `docs/RENDER_DEPLOYMENT.md` deployment guide created.
- [ ] Production seed script `scripts/seed_production_demo.py` created.
- [ ] `docs/PRODUCTION_DEMO_DATA.md` authored.
- [ ] `.env.example` updated with cloud production templates.
