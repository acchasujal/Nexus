# Catalyst Deployment Guide

Service-by-service decisions for Zoho Catalyst integration.
Moved from `ENGINEERING_OPERATING_MANUAL.md` Task 2.
**Never spike around Catalyst — always verify before building.**

---

## Final Stack Decision (Subject to Spike Verification)

```
Frontend    → React → Catalyst Slate / Web Client Hosting
Backend     → FastAPI (Python) → Catalyst AppSail  [SPIKE REQUIRED]
Database    → Catalyst Data Store (graph-as-adjacency-table)  [SPIKE REQUIRED]
Auth        → Catalyst Authentication (3-role: IO/SHO/SP)
LLM         → Catalyst QuickML  [SPIKE REQUIRED — compliance-critical]
PDF         → Catalyst SmartBrowz
Scheduling  → Catalyst Cron (staleness/escalation recomputation)
CI/CD       → Catalyst Pipelines (or GitHub Actions — whichever is verified first)
Finals-only → Zia Services (voice/Kannada), Catalyst Mail
Skipped     → NoSQL, Stratus, Cache, Signals, Circuits, Push, Connections, Zia AutoML/OCR
```

---

## Service-by-Service Decisions

| Service | Decision | Reason | Status |
|---|---|---|---|
| AppSail | **Use** | Runs FastAPI close to as-is — lowest-risk Catalyst-native backend path | 🔴 UNVERIFIED |
| Slate / Web Hosting | **Use** | React SPA — minimal learning curve | ✅ Straightforward |
| Data Store | **Use** | Hosts graph-as-adjacency-table. Must support recursive/multi-hop queries | 🔴 UNVERIFIED |
| Authentication | **Use** | Replaces custom auth skeleton — native, reduces Phase 1 build time | ✅ Likely |
| QuickML | **Use (cautious)** | Required path for LLM — using external LLM directly is a compliance risk per organizer language. Must support general grounded-completion, not just RAG | 🔴 UNVERIFIED (highest priority spike) |
| SmartBrowz | **Use** | Covers PDF export (Feature #13) with no custom renderer needed | ✅ Likely |
| Cron | **Use** | Periodic escalation recomputation — production-grade signal for judges | ✅ Likely |
| Pipelines | **Use (or GitHub Actions)** | CI/CD — whichever is confirmed first | 🟡 Evaluate |
| Zia (voice/Kannada) | **Use — Finals only** | Covers voice + Kannada requirements directly | Deferred |
| Mail | **Use — Finals only** | Escalation emails that actually send vs. on-screen only | Deferred |
| NoSQL | **Skip** | No need to run two data paradigms | — |
| Stratus | **Skip MVP** | No confirmed blob-storage need | — |
| Cache | **Skip until measured** | Speculative caching violates EXECUTION_RULES.md | — |
| Signals / Circuits | **Skip** | Overengineering for a sequential rule engine | — |
| Serverless Functions | **Fallback only** | If AppSail rejects Python/FastAPI, fall back here — worse option, still compliant | — |

---

## Three Mandatory Spikes (Block All Feature Work)

Run these before opening any feature branch. Time-box each to 4 hours.

### Spike 1 — AppSail: Python/FastAPI Support
**Question:** Does Catalyst AppSail support Python 3.11 + FastAPI without a rewrite to function-handler paradigm?  
**Owner:** Lane 4  
**If YES:** Proceed. Use AppSail.  
**If NO:** Fall back to Serverless Functions with Python runtime. Update ARCHITECTURE.md + DECISION_LOG.md.  
**Evidence needed:** A deployed FastAPI app with one endpoint, responding on an AppSail URL.  
**Status:** NOT STARTED

### Spike 2 — Data Store: Recursive Query Support
**Question:** Does Catalyst Data Store support recursive/multi-hop SQL queries (or CTEs) needed for co-accused graph traversal?  
**Owner:** Lane 1  
**If YES:** Proceed. Use Data Store as the graph-as-adjacency-table backend.  
**If NO:** Evaluate Data Store adjacency tables with application-level traversal (load edges, traverse in Python). Update ARCHITECTURE.md.  
**Evidence needed:** A query that walks N hops of a simulated adjacency table and returns results.  
**Status:** NOT STARTED

### Spike 3 — QuickML: General Grounded-Completion Support
**Question:** Does QuickML support general LLM completion calls (not just document-RAG) for our NL→query grounding pattern?  
**Owner:** Lane 4  
**If YES:** Proceed. QuickML is the LLM layer.  
**If NO:** Document the gap explicitly in DECISION_LOG.md. Accept the flagged compliance risk if using an external provider. Do NOT silently use an external LLM without logging this decision.  
**Evidence needed:** A QuickML call that takes a user query string and returns structured output (not a retrieved document chunk).  
**Status:** NOT STARTED — **HIGHEST COMPLIANCE RISK IN THE STACK**

---

## Spike Results (fill in after running)

| Spike | Result | Date | Logged in DECISION_LOG.md |
|---|---|---|---|
| AppSail Python/FastAPI | — | — | — |
| Data Store Recursive Queries | — | — | — |
| QuickML General Completion | — | — | — |
| SmartBrowz HTML→PDF | — | — | — |
| Zia STT/TTS (English + Kannada) | — | — | — |

---

## Environment Variables

All service credentials go in `.env` (gitignored). See `configs/.env.example` for the template.  
Never commit real credentials. If a teammate needs them, share out-of-band (Signal, encrypted message — not Slack or email).

---

## Fresh-Clone Deployment Verification

Run `scripts/verify_deployment.sh` after every release tag. Verify from a second machine that:
1. Backend endpoint responds at the AppSail URL
2. Frontend loads at the Slate URL
3. A database read succeeds (confirms Data Store connection)
4. Auth rejects an unauthenticated request
