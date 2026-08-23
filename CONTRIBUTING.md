# Contributing to CaseClock

**Read [`docs/EXECUTION_RULES.md`](docs/EXECUTION_RULES.md) first.** Everything below is a summary.

---

## Mandatory Context (paste at start of every AI coding session)

```
Read PROJECT_CONTEXT.md, EXECUTION_RULES.md, ARCHITECTURE.md, and TASK.md before responding.
Follow EXECUTION_RULES.md's anti-hallucination rules strictly.
Search existing code before writing new code — do not duplicate.
If this task requires a schema or API contract change, stop and flag it — do not proceed silently.
```

---

## Lane Ownership

Lanes represent **ownership domains**, not Git branches. Work only on code within your assigned lane's functional domain. Cross-lane changes require explicit approval from the other lane's owner, and any contract-boundary change (`shared/contracts/`, graph schema) requires Lane 4 (Sujal) sign-off.

| Lane | Ownership Domain | Key Directories/Files |
|---|---|---|
| 1 — Backend Core | Clock/Dependency/Escalation, Auth, APIs, Constants | `backend/app/core/clock/`, `backend/app/core/dependency/`, `backend/app/core/escalation/`, `backend/app/core/auth/`, `shared/constants/` |
| 2 — Frontend | React UI, dashboard, timeline, charts, analytics | `frontend/` |
| 3 — Graph Intelligence | Aggregations, similarity, pattern/risk/forecasting | `backend/app/core/graph/` |
| 4 — AI + Architecture + Integration | Copilot, refusal gate, contracts, Catalyst deployment, CI/CD | `backend/app/core/copilot/`, `backend/app/catalyst/`, `shared/contracts/`, `deployment/`, `.github/`, `docs/` |

---

## Branch Naming & Workflow

Development uses **GitHub Flow** with short-lived feature branches targeting `main` directly.

```
lane{N}/{imperative-noun}
```

Examples: `lane1/clock-engine`, `lane2/worklist`, `lane3/synthetic-data`, `lane4/refusal-gate`

---

## Commit Style

```
scope: imperative description
```

Examples:
- `clock: add BNSS offence-category mapping table [UNVERIFIED]`
- `contracts: add CaseSummaryResponse type`
- `frontend: implement risk-ranked worklist`

---

## Pull Requests

Every merge to `main` goes through a PR. Use the template at [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md). Do not skip the self-review checklist.

---

## Merge Strategy

- Task branch → `main`: squash merge, 1 approval (+ Lane 4 for contract-boundary PRs)
- Never force-push to `main`
- Branches are deleted automatically on merge

---

## Definition of Done

Code merged to `main`, tests pass, `TASK.md` updated, and — if architecture changed — `ARCHITECTURE.md` + `DECISION_LOG.md` updated in the same session.
