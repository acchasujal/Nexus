# CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md

## TASK 1: Audit of v1 vs. Claude's Review

*   **Caching vs. Signature Interaction:** **Mandatory**. The 5m/30s cache directly breaks the 300ms live cross-screen demo requirement. Invalidation contracts and fast-polling are required.
*   **Copilot Streaming:** **Mandatory**. Streaming was invented. Must be request/response only until backend verifies otherwise.
*   **GraphViewer / ChoroplethMap Complexity:** **Mandatory**. Over-investment risk. Must use React Flow; Map must fall back to Table for MVP.
*   **Contract Source of Truth:** **Mandatory**. Frontend cannot invent API shapes. Must strictly import from `shared/contracts/api.ts`.
*   **Command Palette Priority:** **Mandatory**. Must be P2 and explicitly cut-first.
*   **GraphViewer Accessibility:** **Mandatory**. `role="img"` is insufficient. Table fallback must be the accessible primary view.
*   **State Management Ambiguity:** **Mandatory**. Must resolve "Context vs Zustand". Context API is sufficient and mandated.
*   **Parallel Dev Reality:** **Mandatory**. Team is 1 frontend dev. "3 agents" must mean sequential AI coding sessions, not 3 engineers.
*   **Login Stub:** **Recommended**. Clarify as a 3-button role selector to prevent AI from building auth forms.
*   **Missing Escalation Component:** **Recommended**. Added `EscalationDialog`.
*   **MSW Dependency:** **Recommended**. Explicitly mark disabled in Catalyst production build.
*   **Scale Mock Data:** **Recommended**. Add 5,000+ row dataset for DataTable perf testing.
*   **`aria-live` Specification:** **Recommended**. Specify `polite` for Copilot responses.

---

## TASK 4: Implementation Roadmap (Smallest Path to Demo)

### Phase 1: Foundation & App Shell
*   **Goal:** Establish layout, routing, global state, and API infrastructure.
*   **Deliverables:** Context API (Auth/Role), React Query setup, AppShell (240px sidebar), Router with role guards, Design Tokens.
*   **Usable App:** User can select a role (stub login) and view an empty AppShell with navigation.

### Phase 2: MVP Critical Path (Worklist & Case Detail)
*   **Goal:** The core IO workflow.
*   **Deliverables:** `Worklist` (DataTable), `Case Detail` base layout, `ClockBar`, `DependencyTable`.
*   **Usable App:** IO can log in, see a mocked risk-sorted worklist, click a case, and see its clock and dependencies.

### Phase 3: Escalation & Copilot (The Wow Moment)
*   **Goal:** The signature interaction and AI layer.
*   **Deliverables:** `EscalationDialog`, `EscalationQueue`, `CopilotPanel` (Request/Response), `PathTrace`.
*   **Usable App:** User can trigger an escalation, see it appear in the queue via query invalidation, and ask the Copilot a question with a refusal fallback.

### Phase 4: Intelligence & Rollups (Post-MVP Visuals)
*   **Goal:** Graph and analytics views.
*   **Deliverables:** `NetworkTab` (React Flow + Table fallback), `Pattern & Trends` (Charts/Tables), `District Rollup` (MetricCards + Table fallback).

---

## TASK 5: Component Inventory

| Component Name | Purpose | Props | Variants | Accessibility | Dependencies | Priority | Owner |
|---|---|---|---|---|---|---|---|
| **AppShell** | Global layout | `children`, `role` | Desktop, Mobile | ARIA landmarks, Keyboard nav | Sidebar, Header | P0 | Lane 2 |
| **Sidebar** | Primary nav | `role`, `activeRoute` | Default | `nav` role, `aria-current` | None | P0 | Lane 2 |
| **Header** | Search, role | `role` | Default | `role="banner"` | SearchBar | P0 | Lane 2 |
| **SearchBar** | Global search | `onChange` | Default | `role="searchbox"` | Input | P0 | Lane 2 |
| **CommandPalette** | Quick nav | `open`, `onClose` | Default | Focus trap | SearchBar | P2 | Lane 2 |
| **DataTable** | Display lists | `columns`, `data` | Dense, Comfortable | Arrow key nav, `role="grid"` | StatusChip | P0 | Lane 2 |
| **ClockBadge** | Days remaining | `days`, `status` | Table, Detail | `aria-label` | None | P0 | Lane 2 |
| **RiskBadge** | HIGH/MED/LOW | `level` | Default | Icon + Text | None | P0 | Lane 2 |
| **DependencyTable** | Blocker tracking | `dependencies[]` | Default | `role="list"` | StatusChip | P0 | Lane 2 |
| **Timeline** | Chronological events | `events[]` | Vertical | `role="list"` | Icons | P1 | Lane 2 |
| **GraphViewer** | Network visualization | `nodes[]`, `edges[]` | Graph, Table | `role="grid"` (Table mode) | React Flow | P1 | Lane 2 |
| **MetricCard** | Rollup stats | `label`, `value` | Default | `aria-label` | None | P1 | Lane 2 |
| **Drawer** | Quick edits | `open`, `children` | Right | Focus trap, Esc | None | P0 | Lane 2 |
| **EscalationDialog** | Confirm escalation | `open`, `onConfirm` | Alert | `role="alertdialog"` | Button | P0 | Lane 2 |
| **Toast** | Action confirmation | `message` | Success, Error | `role="status"` | None | P0 | Lane 2 |
| **CopilotPanel** | AI query interface | `caseId?` | Docked, Global | `role="log"`, `aria-live="polite"` | PathTrace | P1 | Lane 2 |
| **PathTrace** | Explainability tree | `trace[]` | Collapsed | `aria-expanded` | None | P1 | Lane 2 |
| **LoadingSkeleton** | Perceived perf | `layout` | Table, Detail | `aria-busy="true"` | None | P0 | Lane 2 |
| **EmptyState** | No data state | `message`, `action` | Default | `role="status"` | Button | P0 | Lane 2 |
| **ErrorState** | Failure state | `message`, `onRetry` | System, Refusal | `role="alert"` | Button | P0 | Lane 2 |
| **StatusChip** | Healthy/Approaching | `status` | Default | Icon + Text | None | P0 | Lane 2 |
| **Button** | Primary actions | `variant`, `size` | Primary, Ghost | `focus-ring` | None | P0 | Lane 2 |
| **Input** | Forms/search | `label`, `value` | Text | `aria-invalid` | None | P0 | Lane 2 |

---

## TASK 6: Routing Map

*   **Strategy:** React Router v6. Protected routes wrap role-specific layouts.
*   **Login Stub:** `/login` is a 3-button role selector (IO/SHO/SP), NOT a credential form.

```text
/login (Public, role-selector stub)

# Protected Routes (AppShell)
/worklist (IO, SHO)
/escalations (SHO, SP)
/rollup (SP, DCP) -> Renders Table MVP
/patterns (All roles) -> Renders Table MVP
/copilot (All roles)
/audit (All roles, read-only)

/case/:id (All roles)
  /case/:id?tab=clock (Default)
  /case/:id?tab=timeline
  /case/:id?tab=network
  /case/:id?tab=similarity
  /case/:id?tab=copilot
  /case/:id?tab=audit

# Future Work (Do NOT build for MVP)
/settings
```

---

## TASK 7: State Management

**Rule:** The frontend *never* computes risk, sorting, or escalation logic. It only renders backend state.

*   **Global UI State (Context API):**
    *   `AuthContext`: `role` (IO/SHO/SP). Drives nav visibility and route guards.
    *   `UIContext`: `isEscalateDrawerOpen`, `tableDensity` (Dense/Comfortable).
*   **Server State (React Query):**
    *   *Caching:* `staleTime: 0` globally to prevent stale UI during demo. The backend is fast enough for synthetic data.
    *   *Escalations Polling:* `refetchInterval: 3000` (3 seconds) to simulate live cross-screen updates without WebSockets.
    *   *Retry:* `retry: 1` to prevent hanging load states on failure.
    *   *Error Handling:* `isError` -> `<ErrorState />`.
*   **Local State (useState):**
    *   Form inputs, Copilot text box.
*   **Optimistic Updates & Invalidation:**
    *   *Dependency Status Change:* Use `useMutation`.
    *   *On Success:* Call `queryClient.invalidateQueries(['worklist'])`, `queryClient.invalidateQueries(['case', caseId])`, and `queryClient.invalidateQueries(['escalations'])`. This guarantees the 300ms cross-screen signature interaction works deterministically.

---

## TASK 8: API Integration Plan

**Rule:** Never redefine contracts. All types are imported from `shared/contracts/api.ts`.

| Screen | Endpoint | Request Model | Response Model (from `api.ts`) | Strategy |
|---|---|---|---|---|
| **Worklist** | `GET /worklist` | `?role=IO` | `Case[]` | `staleTime: 0` |
| **Case Detail** | `GET /cases/:id` | `:id` | `Case` | `staleTime: 0` |
| **Network** | `GET /cases/:id/network` | `:id` | `GraphData` | `staleTime: 0` |
| **Rollup** | `GET /rollup/:district` | `:district` | `Metrics` | `staleTime: 0` |
| **Copilot** | `POST /copilot/query` | `{ query, caseId? }` | `CopilotResponse` | No cache, No stream |
| **Escalations** | `GET /escalations` | `?status=active` | `Escalation[]` | Poll 3s |
| **Update Dep** | `PATCH /deps/:id` | `{ status }` | `Dependency` | Invalidate `['worklist', 'case', 'escalations']` |

---

## TASK 9: Mock Data Plan

To unblock frontend development before backend APIs are stable. Uses MSW (Mock Service Worker). **MSW MUST be disabled in the Catalyst production build.**

*   **Folder Structure:** `/frontend/src/mocks/data/`
*   **Datasets:**
    1.  **Demo Dataset:** `mock_case_847.json` (Hero case. Clock: 9 days. Deps: FSL stale 21 days).
    2.  **Large Dataset:** `mock_worklist_5000.json` (5,000 rows to stress-test DataTable virtualization & pagination).
    3.  **Accessibility Dataset:** `mock_a11y.json` (Cases with "Undetermined" clocks, missing dependencies, empty states for every tab).
    4.  **Failure Dataset:** `mock_failure.json` (500 errors and timeouts to test `<ErrorState />`).
    5.  **Copilot Refusal Dataset:** `mock_copilot_refusal.json` (Returns `refused: true` for "Is he guilty?").
*   **Synthetic Labels:** Any mock data representing a stub feature (e.g., financial links) must include a `is_synthetic: true` flag so the UI can render the "Synthetic" badge.

---

## TASK 10: Parallel Development (1 Developer, Multiple AI Sessions)

**Strategy:** One frontend developer running sequential, isolated AI coding sessions to prevent merge conflicts and context rot.

*   **Session 1: Foundation & Shell (v0)**
    *   *Scope:* Tokens, AppShell, Context API, React Query setup, Routing.
    *   *Output:* A mergeable PR with a navigable skeleton.
*   **Session 2: Core Data Components (v1)**
    *   *Scope:* `DataTable`, `ClockBadge`, `RiskBadge`, `Worklist` screen.
    *   *Input:* Must read v0 codebase.
    *   *Output:* A mergeable PR with a working Worklist.
*   **Session 3: Case Detail & Mutation (v2)**
    *   *Scope:* `Case Detail` layout, `DependencyTable`, `EscalationDialog`, React Query invalidation logic.
    *   *Input:* Must read v1 codebase.
    *   *Output:* A mergeable PR with the signature interaction working.
*   **Session 4: AI & Intelligence (v3)**
    *   *Scope:* `CopilotPanel`, `PathTrace`, `GraphViewer` (React Flow + Table), Rollups.
    *   *Input:* Must read v2 codebase.

---

## TASK 11: AI Coding Strategy (Prompt Templates)

*(To be used by AI coding sessions)*

**Build Component:**
> "Read `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` and `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md`. Build the `[Component Name]` React component using TypeScript. Import all types from `shared/contracts/api.ts`. Do not invent API shapes. Do not compute business logic (risk, sorting, dates). Adhere to ARIA rules in Bible §4.24. Return only the component file and its CSS module."

**Build Screen:**
> "Read `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` and `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md`. Build the `[Screen Name]` screen. Use existing components from the codebase. Do not create duplicate components. Wire it to the `[Endpoint Name]` API using React Query. Handle loading, empty, and error states. Do not modify unrelated files."

**Accessibility Review:**
> "Audit this React code against `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` §4.24. Verify: color-only indicators, 44x44px targets, proper ARIA roles, focus rings. Provide fixed code."

**Bug Fix:**
> "Analyze this `[Component]` bug. Per `EXECUTION_RULES.md`, revert-first, diagnose-second. Do not add frontend logic to 'fix' bad backend data. Output the root cause and the minimal fix."

---

## TASK 12: Quality Gates

**Before moving forward from any phase, these must pass:**

*   **Contract Compliance:** `tsc` compiles with zero errors. No types invented in the frontend.
*   **Backend Ownership:** Search frontend code for `if (days < 20)` or `sort(...)`. Results must be zero.
*   **Accessibility:** All interactive elements pass keyboard nav. All status indicators have icons + text.
*   **Performance (Scale):** `DataTable` renders 5,000 rows via mock data at 60fps (virtualization works).
*   **Visual Consistency:** No hardcoded colors. All colors use semantic tokens.
*   **Demo Readiness (Signature Interaction):** Updating a dependency via mutation causes `Worklist`, `Case Detail`, and `Escalations` to refetch and update within 500ms without a page reload.

---

## TASK 13: Implementation Principles (Immutable Frontend Laws)

1.  **Backend owns truth.** The frontend never computes risk, priority, clocks, or status.
2.  **No duplicated contracts.** All API types come from `shared/contracts/api.ts`.
3.  **No duplicated components.** Check the codebase before building.
4.  **Context API for UI state.** React Query for server state.
5.  **Accessibility first.** WCAG 2.1 AA is the floor, not a polish step.
6.  **No status is color-only.** Always pair color with an icon and text.
7.  **Every animation has purpose.** Motion communicates state change only.
8.  **Everything reusable.** If it appears twice, it is a component.
9.  **Refusal is calm.** Copilot refusals are neutral states, not errors.
10. **No AI chrome.** No sparkles, no "AI is thinking", no gradients.
11. **Query invalidation over polling.** Mutations must invalidate related queries.
12. **Tables for scale.** Cards are exceptions, not the rule.
13. **Honesty in UI.** Synthetic features must be visibly labeled.
14. **The demo path is the real path.** No scripted animations or hardcoded demo states.
15. **React Flow for graphs.** Never build a custom graph engine.

---

## TASK 14: Consistency Audit

*   **Contradictions:** None. Removed streaming mandate. Removed 5m cache. Removed Zustand option.
*   **Duplicated Information:** Removed inline API response models; directed to `shared/contracts/api.ts`.
*   **Architecture Drift:** None. Strictly adheres to Context API + React Query + Backend logic.
*   **Invented APIs:** None. Copilot is request/response.
*   **Unsupported Catalyst Assumptions:** None. Relies on standard HTTP request/response and fast-polling, avoiding unverified WebSockets/SSE.
*   **Frontend Business Logic:** None. Explicitly banned in Principle 1 and Quality Gates.
*   **Hidden Dependencies:** None. MSW explicitly flagged for dev-only. React Flow mandated for graphs.