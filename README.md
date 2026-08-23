# CaseClock

> Statutory-deadline-aware investigation tracking for Karnataka State Police  
> Built for KSP Datathon 2026 (PS1 — Intelligent Conversational AI)

[![CI](https://github.com/acchasujal/CaseClock/actions/workflows/ci.yml/badge.svg)](https://github.com/acchasujal/CaseClock/actions/workflows/ci.yml)

## KSP Datathon 2026

CaseClock is an Investigation Decision Intelligence Platform for Karnataka State Police that turns fragmented case data into timely, explainable action.

[Live Prototype](https://caseclock-frontend-zaruqrfp.onslate.in) · [Demo Video](https://drive.google.com/file/d/1zmdwMHbuCU8Pvqoz40mblGX8S9lQ7v5L/view?usp=sharing) · [Prototype Deck](https://storage.googleapis.com/vision-hack2skill-production/innovator/USER00953434/1785087100169-CaseClockPS1TeamBruh.pdf)

### The problem

Investigators must coordinate statutory deadlines, forensic and evidentiary blockers, case relationships and supervisory escalation across fragmented records. A missed deadline can become a legal failure, while a generic dashboard rarely explains what needs attention or why.

### Our solution

CaseClock combines deterministic BNSS deadline rules with a unified investigation graph and evidence-grounded assistance. It helps IOs, SHOs and SPs see urgent clocks, named blockers, connected cases and explainable escalation context while retaining human confirmation for consequential actions.

### Key capabilities

- Statutory clock calculation and autonomous deadline sweeps.
- Dependency/blocker tracking for FSL, CDR, statements and related evidence.
- Risk-ranked worklists and supervisor escalation routing.
- Case network, similar-case and pattern intelligence over one graph.
- Case Copilot intent parsing with refusal gates and audit trails.
- Role-aware IO/SHO/SP workflows using synthetic, non-PII demonstration data.

### Submission documentation

The concise final submission brief is in [`docs/datathon-2026-submission.md`](docs/datathon-2026-submission.md). Reproducible performance evidence is in [`docs/benchmark-report.md`](docs/benchmark-report.md) and [`docs/benchmark-results.json`](docs/benchmark-results.json).

### Prototype performance

Local synthetic measurements include 6,667 mixed-state statutory clocks at 97.0 ms p50 / 108.6 ms p95, a 4,000-case graph with 22,296 entities and 45,448 relationships, and a 29.4 ms p95 depth-2 graph query. These are prototype benchmarks—not production Catalyst SLOs.

### Zoho Catalyst integration status

| Integration | Repository-backed status | Workflow value |
|---|---|---|
| AppSail | Implemented/config-dependent; deployment URL documented | Hosts the FastAPI investigation services near the operational workflow. |
| Slate | Implemented/config-dependent; frontend build passes | Delivers the role-aware investigator and supervisor interface. |
| Data Store | Implemented/config-dependent; live provider not reverified in this run | Provides a durable adapter path for cases, graph records, clocks and audit state. |
| Job Scheduling | Cron sweep route/service implemented; scheduler configuration-dependent | Keeps statutory monitoring running when officers are offline. |
| ConvoKraft | Webhook integration implemented; Catalyst Action configuration required | Routes operational assistant actions to deterministic CaseClock worklist, clock, and case services. |
| QuickML | Optional client and controlled intent-routing path preserved; live provider not benchmarked | Future provider for constrained intent routing when explicitly enabled. |
| File Store + Zia OCR | Provider adapter implemented; live credentials/provider not verified | Supports evidence-document persistence and OCR when configured. |

External-provider features are reported as configuration-dependent unless a live call has been reproduced. See [`docs/datathon-2026-submission.md`](docs/datathon-2026-submission.md) for the evidence boundary.

---

## What This Is

One unified investigation graph. Every organizer-required capability (network analysis, pattern discovery, conversational query) is a different lens on the same graph, anchored by real statutory-deadline tracking under BNSS.

Read [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) for full context. Read [`docs/TASK.md`](docs/TASK.md) for what is actually built vs. not built — that file is the only source of truth on real progress.

---

## Repository Structure

```
CaseClock/
├── backend/
│   ├── app/
│   │   ├── api/            # Route handlers
│   │   ├── core/
│   │   │   ├── clock/      # Legal Clock Engine (LOAD BEARING)
│   │   │   ├── dependency/ # Dependency Tracker
│   │   │   ├── escalation/ # Escalation Rule Engine
│   │   │   ├── graph/      # Graph traversals, aggregation, similarity (Lane 3)
│   │   │   ├── copilot/    # NL grounding, refusal gate (Lane 4)
│   │   │   └── auth/
│   │   ├── db/             # Storage adapter (Catalyst Data Store)
│   │   ├── catalyst/       # Catalyst SDK wrappers — QuickML, SmartBrowz, Zia
│   │   └── main.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── refusal_testset/
├── frontend/               # Lane 2 — React app (Worklist, Case Detail, Escalation, Rollup)
├── shared/                 # Cross-lane contracts & constants
│   ├── contracts/          # API contract types (Python + TypeScript) — owned by Lane 4
│   └── constants/          # clock_types.py — offence-category → clock-type mapping (Lane 1)
├── tests/
│   └── scale/              # 1-2 lakh record load tests only
├── scripts/                # Seed data, refusal testset runner, deploy verifier
├── deployment/             # Catalyst AppSail + Slate configs
├── docs/                   # Consolidated project documentation
└── .github/                # CI workflows, issue templates, PR template, CODEOWNERS
```

---

## Lane Ownership

Lanes represent **ownership domains**, not Git branches. Development uses **GitHub Flow** with short-lived feature branches targeting `main` directly. Ownership boundaries remain lane-based regardless of branch names.

| Lane | Owns | Key Directories/Files |
|---|---|---|
| 1 — Backend Core | Clock/Dependency/Escalation, Auth, APIs, Constants | `backend/app/core/clock/`, `backend/app/core/dependency/`, `backend/app/core/escalation/`, `backend/app/core/auth/`, `shared/constants/` |
| 2 — Frontend | React UI, dashboard, timeline, charts, analytics | `frontend/` |
| 3 — Graph Intelligence | Aggregations, similarity, pattern/risk/forecasting | `backend/app/core/graph/` |
| 4 — AI + Architecture + Integration | Copilot, refusal gate, contracts, Catalyst deployment, CI/CD | `backend/app/core/copilot/`, `backend/app/catalyst/`, `shared/contracts/`, `deployment/`, `.github/`, `docs/` |

---

## Getting Started (Local)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### Backend
```bash
# From repo root — shared/ is importable alongside backend/
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Run tests
```bash
# Run all backend tests (from repo root)
pytest tests/ -v

# Skip large-scale load tests
pytest tests/ -v --ignore=tests/scale
```

---

## Key Rules

Before writing any code, read [`docs/EXECUTION_RULES.md`](docs/EXECUTION_RULES.md).

**Critical anti-hallucination rules (enforced in every PR):**
- Never invent a schema field, API endpoint, or table that doesn't exist
- Never label a rule engine as AI/ML
- Never generate free-text about a specific person's guilt or risk
- All BNSS citations marked `[VERIFIED]` or `[UNVERIFIED]`

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). All PRs must pass the checklist in [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

Contract changes (`shared/contracts/`) require Lane 4 (Sujal) review. Clock/escalation/graph schema changes require a `DECISION_LOG.md` entry before the PR.

---

## Deployment

Mandatory on Zoho Catalyst (AppSail + Slate) per organizer eligibility rules.

### Live Deployment (Development Environment)

| Component | URL |
|---|---|
| **Frontend (Slate)** | https://caseclock-frontend-zaruqrfp.onslate.in |
| **Backend (AppSail)** | https://caseclock-backend-50043773125.development.catalystappsail.in |
| **Catalyst Project** | 51441000000017001 (CaseClock, Datacenter: India) |

### Health Verification
```bash
# Backend health
curl https://caseclock-backend-50043773125.development.catalystappsail.in/health

# OpenAPI schema
curl https://caseclock-backend-50043773125.development.catalystappsail.in/openapi.json
```

### Environment Variables (AppSail — caseclock-backend)

Configured in Catalyst Console → AppSail → caseclock-backend → Configuration → Environment Variables:

| Variable | Value | Notes |
|---|---|---|
| `ENVIRONMENT` | `production` | Enables production auth gate |
| `CASECLOCK_REPOSITORY` | `local` | Use in-memory + synthetic data |
| `CORS_ORIGINS` | `http://localhost:5173,...,https://caseclock-frontend-zaruqrfp.onslate.in` | Comma-separated allowed origins |

> **Note:** `CORS_ORIGINS` is also set in `backend/app-config.json` `env_variables` for deployment tracking.

### Manual Deploy Commands
```bash
# Verify active project before deploying
catalyst project:list

# Deploy backend only (after code changes)
catalyst deploy --only appsail

# Deploy frontend only (after frontend build)
npm run build  # from frontend/
catalyst deploy --only slate

# Deploy both
catalyst deploy --only appsail,slate
```

### Pre-Deploy Checklist
1. `backend/shared/` must exist (copy of root `shared/` for AppSail PYTHONPATH)
2. Frontend must be rebuilt with `npm run build` for `.env.production` to take effect
3. Active Catalyst project must be `51441000000017001`

### Docker (Local Development)
```bash
# Build from repo root
docker build -t caseclock-backend -f backend/Dockerfile .

# Run with development variables
docker run --rm -p 8000:8000 \
  -e ENVIRONMENT=development \
  -e CORS_ORIGINS=http://localhost:5173 \
  caseclock-backend

# Verify
curl http://localhost:8000/health
```

---


## Docs

| Document | Purpose |
|---|---|
| [`PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) | Why the product exists |
| [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) | System architecture |
| [`TASK.md`](docs/TASK.md) | What is actually built (source of truth) |
| [`EXECUTION_RULES.md`](docs/EXECUTION_RULES.md) | How to work on this repo (ops + AI rules) |
| [`DECISION_LOG.md`](docs/DECISION_LOG.md) | Architecture decisions and trade-offs |
| [`FEATURE_REGISTRY.md`](docs/FEATURE_REGISTRY.md) | Feature status and scope labels |
| [`HACKATHON_MASTER_GUIDE.md`](docs/HACKATHON_MASTER_GUIDE.md) | Submission strategy (frozen) |
| [`PROTOTYPE_SUBMISSION_GUIDE.md`](docs/PROTOTYPE_SUBMISSION_GUIDE.md) | Deliverable list |
| [`docs/spikes/quickml.md`](docs/spikes/quickml.md) | QuickML capability spike results and architectural decision |
| [`docs/graph-intelligence/DATA_MODEL.md`](docs/graph-intelligence/DATA_MODEL.md) | Detailed graph entity catalog with planned fields |
| [`docs/graph-intelligence/EDGE_MODEL.md`](docs/graph-intelligence/EDGE_MODEL.md) | Stored and derived edge definitions |
| [`docs/graph-intelligence/DATASTORE_SPIKE.md`](docs/graph-intelligence/DATASTORE_SPIKE.md) | Catalyst Data Store spike validation plan |
| [`docs/graph-intelligence/MIGRATION_PLAN.md`](docs/graph-intelligence/MIGRATION_PLAN.md) | Adjacency-list mapping strategy for Catalyst |
| [`docs/graph-intelligence/SYNTHETIC_DATA_SPEC.md`](docs/graph-intelligence/SYNTHETIC_DATA_SPEC.md) | Synthetic dataset targets and repeat-entity strategy |
