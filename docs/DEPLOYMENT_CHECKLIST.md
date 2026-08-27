# NEXUS Production Deployment Readiness Checklist

> **Target:** Smart India Hackathon 2026 (PS 26189) — AI-Powered Criminal Network Analysis System  
> **Platform:** Render Static Site + Render FastAPI Web Service + PostgreSQL + Neo4j AuraDB  

---

## 1. Pre-Deployment Git & Repository Integrity
- [x] Working tree clean on `main` branch.
- [x] No sensitive credentials, private keys, or API tokens committed.
- [x] `.env` and local caches excluded in `.gitignore`.
- [x] `.env.example` provides explicit cloud deployment template variables.
- [x] `render.yaml` Infrastructure-as-Code blueprint valid and verified.

## 2. Backend & API Health
- [x] 509 automated pytest suite passing (`pytest`).
- [x] Linting passing with 0 errors (`python -m ruff check backend/ shared/ tests/`).
- [x] Ground truth evaluation achieves 100% precision, recall, and F1 (`python scripts/evaluate_ground_truth.py`).
- [x] Dynamic `$PORT` binding configured for Render web service.
- [x] Root `/health` liveness probe endpoint available.
- [x] Root `/ready` readiness probe endpoint available.
- [x] Dynamic production CORS origin parsing enabled.

## 3. Frontend & Client-Side SPA
- [x] 46 frontend vitest test suite passing (`npm run test:run`).
- [x] TypeScript type checking passing without errors (`tsc`).
- [x] Production build generated in `dist/` with optimized chunk sizes (`npm run build`).
- [x] `VITE_API_BASE_URL` properly parameterized without trailing slash collision.
- [x] SPA rewrite rules configured (`/*` $\rightarrow$ `/index.html`) to support nested deep links.

## 4. Graph & Intelligence Engine
- [x] In-memory graph index built deterministically (<6ms) on startup.
- [x] Multi-evidence duplicate edge warning resolution verified in `GraphLoader`.
- [x] Multi-candidate cross-case resolution verified.
- [x] Ethical Refusal Gate verified against predictive guilt queries.
- [x] Section 63 BSA evidence hash verification verified.

## 5. Demonstration & Remote Operation
- [x] Standalone production seed script verified (`python scripts/seed_production_demo.py`).
- [x] Live demo fixture reset button in UI Settings tested.
- [x] Zero citizen PII in all datasets.
- [x] Remote judge access does not depend on local laptop.
