# AI_CODING_GUIDE.md
**Written exclusively for AI coding agents (Claude, Codex, GPT, Gemini, Copilot, GLM, Antigravity, or any future model) working on the CaseClock frontend.**

This document does not redesign anything, does not change architecture, does not invent APIs or components. It operationalizes decisions already made in `CASECLOCK_FRONTEND_DESIGN_BIBLE.md`, `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md`, `ARCHITECTURE.md`, `FEATURE_REGISTRY.md`, and `EXECUTION_RULES.md`. Where this guide and those documents ever appear to disagree, those documents win — file a note in the session output, don't silently pick one.

---

## SECTION 1 — Purpose

This document exists because AI coding agents, unlike a persistent human engineer, have no memory between sessions. Every new session starts from zero context. Without a document like this, each session independently reinvents component names, re-derives design tokens from scratch, guesses at API shapes, and silently drifts from whatever the previous session built — producing exactly the "duplicate components, duplicate APIs, inconsistent Tailwind" failure mode this guide is built to prevent.

**Read this document at the start of every frontend coding session, before writing any code, after the four files `EXECUTION_RULES.md` already mandates (`PROJECT_CONTEXT.md`, `EXECUTION_RULES.md`, `ARCHITECTURE.md`, `TASK.md`).**

**Relationship to other documents:**
- `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` — the *why* and *what it should look like*. Design tokens, visual identity, component semantics, accessibility philosophy, judge-psychology reasoning. This guide does not repeat that reasoning; it points to it.
- `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md` — the *build sequence*. Phases, component inventory, routing map, state management decisions, API integration plan, mock data plan. This guide does not repeat that plan; it points to it.
- `AI_CODING_GUIDE.md` (this document) — the *session discipline*. What an AI agent must do before, during, and after writing code, so ten sequential sessions produce one coherent codebase instead of ten incompatible ones.

If you are about to write a design opinion ("I think risk badges should be circular") or a build-sequencing opinion ("I think we should build the graph before the worklist") — stop. Those decisions are already made. This guide only governs *how you execute them without drift*.

---

## SECTION 2 — Immutable Engineering Laws

1. **The frontend never computes business logic.** No risk calculation, no sorting, no date math, no clock arithmetic. If you find yourself writing `if (daysRemaining < 20)`, stop — that value should already be a string like `"HIGH"` from the API.
2. **Backend owns truth.** The frontend renders what the API returns and nothing else. If the API response looks wrong, that is a backend bug, not a frontend problem to compensate for.
3. **Never invent API contracts.** All request/response types come from `shared/contracts/api.ts`. If a field you need doesn't exist there, stop and say so — do not guess a shape and proceed.
4. **Never create a duplicate component.** Search the existing codebase (`frontend/src/components/`) before writing anything. If something close exists, extend it with a prop, don't fork it.
5. **Always search existing code first**, every session, before implementing anything — this is non-negotiable per `EXECUTION_RULES.md` and applies identically to frontend work.
6. **Accessibility is a correctness requirement, not a polish step.** WCAG 2.1 AA is the floor. A screen that fails a contrast or keyboard check is not "done, needs polish" — it is not done.
7. **Semantic colors only.** Green/Amber/Red/Blue map to fixed meanings (Bible §4.4) and are never reused decoratively. No new colors are introduced without a Bible update.
8. **No hardcoded values.** Colors, spacing, and typography come from design tokens (Bible §4.1–4.5). A raw hex code or an arbitrary `px` value in a component is a defect.
9. **No unnecessary abstractions.** Don't build a generic `<DataDisplay>` when `<DataTable>` is what's needed. This team's documented failure mode is overbuilt, disconnected pipelines — the same applies to frontend abstraction layers.
10. **Reuse before creating.** If a pattern appears twice, extract it. If it appears once, don't pre-extract it speculatively.
11. **Everything TypeScript strict.** No `any`, no implicit `any`, no `// @ts-ignore` without a comment explaining why and a linked issue.
12. **No status is ever color-only.** Every status indicator pairs color with an icon and a text label (Bible Principle 1).
13. **Refusal is calm, not an error.** A copilot refusal renders with neutral styling, never red/alarming (Bible Principle 4).
14. **No AI chrome.** No sparkle icons, no gradient borders on copilot output, no "AI is thinking" copy. Use "Running query" (Bible §1.4).
15. **Synthetic/stub features are visibly labeled.** Anything `FEATURE_REGISTRY.md` marks as synthetic or shallow gets a visible badge in the UI — never presented as equivalent to a verified feature.
16. **The demo path is the real path.** No separate "demo mode," no scripted animations, no hardcoded fake state changes. The signature interaction (Bible §8) must work through real mutation + query invalidation.
17. **Query invalidation over polling where both are viable**, but the escalation queue's 3-second poll (Build Guide v2 Task 7) is an intentional, approved exception — do not "optimize" it away without checking why it exists first.
18. **Never refactor and add a feature in the same change** — this applies to frontend components exactly as it does to backend engines per `EXECUTION_RULES.md`.
19. **Every architectural or contract-affecting frontend decision gets logged in `DECISION_LOG.md` in the same session** — not deferred, not assumed someone else will do it.
20. **If a task touches `shared/contracts/`, routing structure, or global state shape — stop and flag it** before proceeding, per the same CODEOWNERS/Lane-4-approval rule that governs backend contract changes.

---

## SECTION 3 — Repository Reading Order

Before writing any frontend code, read in this order:

1. **`PROJECT_CONTEXT.md`** — why the product exists. Skipping this produces technically-correct code that solves the wrong problem (e.g., building a generic dashboard instead of a deadline-first tool).
2. **`EXECUTION_RULES.md`** — the anti-hallucination rules and lane ownership apply to frontend work exactly as they do to backend. This is where "never invent an API field" comes from.
3. **`ARCHITECTURE.md`** — establishes that the frontend renders, never computes, and that Case Detail is the universal landing object. Skipping this is how a session ends up building risk-calculation logic client-side.
4. **`TASK.md`** — what's actually built right now, not what a deck implies. If `TASK.md` says the frontend shell is `NOT STARTED`, don't assume components from a hypothetical prior session exist.
5. **`CASECLOCK_FRONTEND_DESIGN_BIBLE.md`** — the visual/interaction rules. Skipping this is how a session invents its own color system or reintroduces a circular clock dial the Bible explicitly rejected.
6. **`CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md`** — the concrete phase you're building in, the component inventory, the routing map, the state management decisions already made (Context API, not Zustand; `staleTime: 0`; 3s escalation polling). Skipping this is how a session re-litigates a settled decision (Bible §9 already flagged some things as open — everything else is closed).
7. **`shared/contracts/api.ts`** — the actual type definitions. This is the ground truth for every request/response shape. Read this before writing a single `fetch` or `useQuery` call.
8. **The actual `frontend/` directory** — grep for existing components before building anything. Documentation describes intent; the code is what actually exists.

**Why this order specifically:** context (why) before rules (how to behave) before architecture (how it's shaped) before status (what's real) before design (how it should look) before build sequence (what to build now) before contracts (exact shapes) before code (what already exists). Reversing this order is how an agent ends up building a beautiful, well-typed component against an invented contract for a feature that's actually Roadmap-only.

---

## SECTION 4 — Session Startup Checklist

Before writing any code, verify:

- [ ] **Current branch** — confirm you're on a fresh `lane2/task-name` branch cut from latest `main`, not stacking on stale work.
- [ ] **Current phase** — check `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md` Task 4/Task 10 to confirm which phase/session number you're in. Do not build Phase 3 components if Phase 1 isn't merged.
- [ ] **Existing components** — `ls frontend/src/components/` and grep for anything matching what you're about to build.
- [ ] **Contracts** — open `shared/contracts/api.ts` and confirm the exact type you need exists. If it doesn't, stop and flag it — don't invent one.
- [ ] **Routing** — check `frontend/src/routes/` (or equivalent) against the Build Guide's routing map (Task 6) to confirm you're not creating a duplicate route.
- [ ] **Tailwind config** — confirm the design tokens (Bible §4.1–4.5) are actually present in `tailwind.config.js` as semantic classes, not being reinvented per-component.
- [ ] **Context providers** — confirm `AuthContext` and `UIContext` (Build Guide Task 7) exist before consuming them; don't create a second competing context.
- [ ] **React Query setup** — confirm `QueryClientProvider` exists and check the actual configured `staleTime`/`retry`/`refetchInterval` values in code match what's documented, not what you assume.
- [ ] **Existing hooks** — grep `frontend/src/hooks/` for anything that already wraps the API call you're about to make.
- [ ] **`TASK.md` status** — re-confirm the specific feature you're building is marked MVP in `FEATURE_REGISTRY.md`, not Finals/Roadmap.

If any checkbox reveals a mismatch between documentation and actual repository state, **stop and surface the mismatch explicitly in your session output** before proceeding — do not silently reconcile it by picking one version.

---

## SECTION 5 — Reusable Prompt Templates

Each template references project docs by name instead of restating requirements, so the agent reading it is forced back to the source of truth rather than working from a possibly-stale paraphrase.

**Build Component**
> Read `AI_CODING_GUIDE.md` Sections 2–4, `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` §4, and the component's row in `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md` Task 5. Search `frontend/src/components/` first — do not duplicate. Build `[Component Name]` in TypeScript strict mode, importing all types from `shared/contracts/api.ts`. No business logic, no hardcoded tokens, no invented props beyond what Task 5 specifies.

**Build Screen**
> Read `AI_CODING_GUIDE.md` Sections 2–4 and the screen's entry in `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md` Task 4 (phase) and Task 6 (route). Reuse existing components — list which ones you searched for and found/didn't find. Wire to the endpoint in Task 8. Handle loading (Bible §4.21), empty (§4.20), and error (§4.22) states explicitly — do not ship a happy-path-only screen.

**Build Hook**
> Read `AI_CODING_GUIDE.md` Section 4 and `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md` Task 7 (state management) and Task 8 (API plan). Confirm no existing hook in `frontend/src/hooks/` already covers this. New hooks wrap exactly one concern (one query, one mutation) — do not build a hook that both fetches and computes derived state beyond simple formatting.

**Build Layout**
> Read `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` §3 (Information Architecture) and §4.5 (Layout). Confirm against `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md` Task 6 routing map which layout wraps which route. Do not introduce a new layout shell if `AppShell` already covers this case.

**Build Table**
> Read `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` §4.7 and §5. Use the existing `DataTable` component — do not build a new table component. Server-side pagination only; confirm the endpoint in `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md` Task 8 supports the pagination params you're sending.

**Build Dialog**
> Read `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` §4.9. Dialogs are reserved for irreversible/consequential actions only (Component Usage Rules §4.25) — confirm this action qualifies before building a Dialog instead of a Toast or inline confirmation.

**Build Form**
> Read `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` §4.8. Single-column only. Inline validation on blur. Every field has a real `<label>`, not a placeholder standing in for one (§4.24).

**Accessibility Review**
> Read `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` §4.24 and Section 9 of this guide. Check color-only indicators, 44×44px touch targets, ARIA roles per component type, visible focus rings, and `aria-live="polite"` (never `assertive`) on copilot responses. Output a violation list and fixed code — do not silently patch without reporting what was wrong.

**Performance Review**
> Read `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md` Task 9 (mock data) and Task 12 (quality gates). Test against the 5,000-row mock dataset, not the small demo dataset. Confirm server-side pagination is real, not client-side pagination pretending to paginate a fully-loaded array.

**Refactor**
> Read `AI_CODING_GUIDE.md` Section 13 (Anti-patterns) and `EXECUTION_RULES.md`'s refactoring rule: never refactor and add a feature in the same change. State explicitly what behavior is preserved and what test (manual or automated) confirms it.

**Bug Fix**
> Read `EXECUTION_RULES.md`'s Debugging Methodology and Error Recovery Process. Revert first, diagnose second. Determine whether this is a frontend rendering bug or a backend contract mismatch before writing a fix — per Law 2, never add frontend logic to compensate for bad backend data.

**Responsive Design**
> Read `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` §4.5 and §3. Content padding becomes 16px under 768px; sidebar collapses to hamburger. Tables remain readable — horizontal scroll is acceptable, silently hiding columns is not.

**Animation**
> Read `CASECLOCK_FRONTEND_DESIGN_BIBLE.md` §1.2. 200ms micro / 300ms layout ceiling. Motion communicates a real state change only — if you can't name which state change this animates, remove it.

**Code Review**
> Read `AI_CODING_GUIDE.md` Section 10 (Review Checklist) and Section 13 (Anti-patterns) in full. Go through every checklist item explicitly, not just the ones that seem relevant — the ones that seem irrelevant are often where drift hides.

**Testing**
> Read `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md` Task 12 (Quality Gates). Write tests for: renders with real mock data, empty state, error state, and — for anything status-related — confirm a refusal/neutral state does NOT render with error styling (Law 13).

**Documentation Update**
> If this change affects a contract, route, or component inventory, update `CASECLOCK_FRONTEND_BUILD_GUIDE_v2.md` Task 5/6/8 in the same session, and log any architectural implication in `DECISION_LOG.md` — per `EXECUTION_RULES.md`'s Documentation Update Rules, this is not deferred.

---

## SECTION 6 — Coding Rules

**React:** Functional components only. No class components anywhere in this codebase.
**TypeScript:** Strict mode. No `any`. All API-shaped data typed from `shared/contracts/api.ts`, never re-declared locally.
**Tailwind:** Semantic utility classes mapped to design tokens only (Section 8). No arbitrary values (`w-[137px]`) unless there is a genuinely one-off layout need, and even then, comment why.
**Folder naming:** `kebab-case` for folders, `PascalCase.tsx` for component files, `camelCase.ts` for hooks/utils. One component per file; co-locate its test file (`ComponentName.test.tsx`) alongside it.
**Imports:** Absolute imports from `src/` root (`@/components/DataTable`), not relative chains (`../../../components/DataTable`).
**Exports:** Named exports for components (not default exports) — this makes renames and refactors traceable across the codebase and prevents the "duplicate component under a different name" failure mode this guide exists to prevent.
**Hooks:** One concern per hook. Prefix with `use`. Custom hooks live in `frontend/src/hooks/`, never inline-defined inside a component file if they're reused anywhere else.
**Composition:** Prefer composition (children, render props, slots) over configuration-object props with many optional flags — a component with 15 boolean props is a sign it should be two components.
**State:** Server state → React Query. Global UI state → Context (`AuthContext`, `UIContext`). Local/form state → `useState`. Never mirror server state into local `useState` "for convenience" — this is the single most common way frontend and backend state silently diverge.
**Forms:** Controlled inputs, inline validation on blur, single column (Section 5, Build Form template).
**Errors:** `isError` from React Query → `<ErrorState />`. Never swallow an error silently or log-and-continue without surfacing it to the user.
**Loading:** `isLoading` → `<LoadingSkeleton layout="..." />` matching the actual target layout, never a generic spinner for a full-page load.
**Empty states:** Icon + reason + action, per Bible §4.20 — never a bare "No data."
**Accessibility:** See Section 9 below — non-negotiable, checked every session.
**Performance:** Server-side pagination past 50 rows. Memoize expensive derived values (`useMemo`) only where profiling shows it matters — don't memoize reflexively.
**Animations:** Section 5's Animation template — 200/300ms ceiling, state-change-only.

---

## SECTION 7 — React Rules

- **Functional components only.** No exceptions.
- **Strict typing.** Every prop interface explicit and exported if the component is reused; no inferred `any` props.
- **Composition over inheritance/configuration sprawl.** If a component needs a `variant` prop with more than ~4 values, reconsider whether it should be multiple components.
- **Memoization rules:** `React.memo` only on components that re-render measurably often with unchanged props (e.g., table rows in a 500+ row list). Don't wrap every component in `memo` defensively — that's premature optimization that adds noise without proven benefit.
- **Hooks rules:** Obey the Rules of Hooks strictly (no conditional hooks, no hooks in loops). Custom hooks always start with `use` and are unit-testable independent of any component.
- **Custom hooks rules:** A custom hook wraps exactly one React Query call, one mutation, or one piece of derived local logic — never a bundle of unrelated concerns "for convenience."
- **Context rules:** Only two contexts exist per the Build Guide: `AuthContext` (role) and `UIContext` (drawer/dialog open state, table density). Do not create a third global context without checking Section 4's checklist first and flagging the addition explicitly.
- **React Query rules:** Query keys are structured and predictable (`['case', caseId]`, `['worklist', role]`) so invalidation (Build Guide Task 7) actually targets the right cache entries. Never invalidate `['all']` broadly when a specific key will do — broad invalidation defeats the caching strategy's purpose.

---

## SECTION 8 — Tailwind Rules

- **Semantic tokens only.** Colors referenced as `bg-status-red`, `text-status-amber`, `bg-brand-blue` — never raw Tailwind palette classes like `bg-red-500` directly in component code. Map raw palette to semantic names once, in `tailwind.config.js`, per Bible §4.4.
- **Spacing rules:** 8px-based scale only (Bible §4.2) — `p-2, p-3, p-4, p-6, p-8` etc. mapped to the 4/8/12/16/24/32/48/64 scale. No arbitrary spacing values.
- **Typography rules:** Font sizes come from the type scale in Bible §4.1, mapped to Tailwind's `text-*` utilities via config — never an arbitrary `text-[15px]`.
- **Responsive rules:** Mobile-first breakpoints (`sm:`, `md:`, `lg:`) matching Bible §4.5's stated breakpoints (768px, 1200px+). Sidebar collapse behavior is a fixed pattern, not re-derived per screen.
- **Dark mode policy:** Not in MVP scope per any project document — do not build dark-mode variants speculatively. If asked, flag that this is Roadmap-equivalent scope creep, matching how Kannada/voice are handled.
- **Hover rules:** Hover states exist only on genuinely interactive elements (buttons, table rows, links) — never on static informational elements, which implies false interactivity.
- **Focus rules:** 2px visible focus ring on every focusable element, never `outline-none` without an explicit visible replacement (Bible §4.24, Law 6).
- **Animation rules:** `transition-*` utilities capped at the durations in Section 5's Animation template — no custom keyframe animations beyond what's needed for the signature interaction's state-change transitions.

---

## SECTION 9 — Accessibility Rules

- **WCAG AA is the floor**, checked every session, not deferred to a "polish pass."
- **ARIA:** Use semantic HTML first (`<button>`, `<nav>`, `<table>`) and ARIA roles only to fill genuine gaps — don't add `role="button"` to a `<div>` when a `<button>` would just work.
- **Keyboard:** Every interactive element reachable via Tab, activated via Enter/Space. Table rows navigable via arrow keys + Enter (Build Guide component inventory, `DataTable`).
- **Focus:** Focus trapped inside open Dialogs/Drawers; focus returns to the triggering element on close.
- **Reduced motion:** Respect `prefers-reduced-motion` — disable non-essential transitions for users who've set this OS-level preference. This isn't in the Bible explicitly; it's a baseline WCAG expectation and Law 6 ("accessibility is a correctness requirement") covers it by extension.
- **Contrast:** 4.5:1 body text, 3:1 large text/icons, checked against the actual rendered semantic colors, not assumed.
- **Tables:** `role="grid"` with proper header association (`scope="col"`), sortable columns announce their sort state to screen readers.
- **Dialogs:** `role="alertdialog"` for consequential confirmations, `role="dialog"` otherwise, always with a labeled heading.
- **Forms:** Every input has an associated `<label>`, error messages linked via `aria-describedby`, `aria-invalid` set on validation failure.
- **Charts:** `role="img"` with a genuinely descriptive `aria-label` summarizing the data trend, not just the chart type. For anything interactive/drillable, provide the underlying data as an accessible table alternative (Bible §4.13's stored/derived edge accessibility fix extends here).
- **React Flow (GraphViewer):** `role="img"` alone is insufficient for an interactive graph per the prior review — the table-fallback view (already required at 500+ nodes for performance) is the accessible primary alternative at any node count, exposed via a visible toggle, not buried in a fallback-only code path.

---

## SECTION 10 — Review Checklist

Before considering any session's work finished, verify every item — not just the ones that feel relevant:

- [ ] No duplicate component was created (grep confirms nothing equivalent already existed).
- [ ] No duplicated logic (a helper/hook wasn't reinvented that already exists elsewhere).
- [ ] No API shape was invented — every type traces to `shared/contracts/api.ts`.
- [ ] No frontend business logic — grep your own diff for `if (days`, `.sort(`, date-math patterns, and risk-computation patterns.
- [ ] No hardcoded colors — grep for raw hex values or non-semantic Tailwind color classes.
- [ ] No hardcoded spacing — grep for arbitrary `px`/`rem` values outside the token scale.
- [ ] No accessibility regression — re-run the Accessibility Review prompt template (Section 5) against your own diff.
- [ ] No TypeScript errors — `tsc` compiles clean.
- [ ] No lint errors.
- [ ] No broken imports (absolute imports resolve correctly).

---

## SECTION 11 — Quality Gates

**Before Commit**
- [ ] `tsc` compiles with zero errors.
- [ ] Lint passes.
- [ ] Section 10's Review Checklist is complete.

**Before PR**
- [ ] Section 4's Session Startup Checklist mismatches (if any) are documented in the PR description, not silently resolved.
- [ ] Every new/changed screen handles loading, empty, and error states explicitly.
- [ ] Any contract, route, or state-shape change is flagged per Law 20 and, if it touches `shared/contracts/`, CODEOWNERS/Lane 4 approval is requested.

**Before Merge**
- [ ] Required CI (`ci.yml`) is green.
- [ ] At least one teammate approval, per `EXECUTION_RULES.md`'s merge gates.
- [ ] `TASK.md` is updated to reflect the new state — not deferred to "later."

**Before Demo**
- [ ] The signature interaction (Bible §8, Build Guide v2 Task 12's "Demo Readiness" gate) is verified live, end-to-end, with a real mutation and real query invalidation — not asserted from memory of it having worked once.
- [ ] `DataTable` is verified against the 5,000-row mock dataset, not just the small demo dataset.
- [ ] Every synthetic/stub feature visible in the demo path carries its visible label (Law 15).
- [ ] No console errors in the browser dev tools during the full demo walkthrough.

---

## SECTION 12 — Common Mistakes

1. **Computing risk/status client-side "just to make the UI feel more responsive."** This is Law 1's exact violation, and it's the single most common way an AI agent quietly reintroduces the rejected composite-risk-score pattern (`ARCHITECTURE.md`'s Rejected Approaches) through the frontend instead of the backend.
2. **Inventing a field on an API response type because the UI "needs" it.** If the design calls for something the contract doesn't provide, that's a signal to flag the gap, not silently extend the local type definition.
3. **Treating documentation as optional context instead of binding constraint.** An agent that skims the Bible and builds a circular clock dial anyway (explicitly rejected in favor of a horizontal bar, Bible §4.16) has produced work that will be rejected in review — wasted effort that a 10-second read would have prevented.
4. **Building a new component instead of extending an existing one with a prop.** This is how codebases end up with three near-identical badge components.
5. **Skipping empty/error/loading states because the happy path "works in the demo."** The organizer's own scale target (1–2 lakh records) guarantees error and loading states will be seen in real usage even if they're never seen in a scripted demo.
6. **Over-memoizing or over-abstracting defensively.** This team's documented failure mode is overbuilt, disconnected pipelines — the same instinct that produces a backend microservice nobody needed produces a frontend `useSuperGenericDataFetcher` hook nobody needed.
7. **Silently "fixing" a backend data problem in the frontend** (e.g., defaulting a missing field to a plausible-looking placeholder) instead of surfacing it as an honest empty/undetermined state — this is Law 2 and the Anti-Hallucination Rules applied to rendering, not just to data generation.

---

## SECTION 13 — Frontend Anti-patterns (explicitly forbidden)

- **Business logic in UI** — risk calculation, sorting, date math, clock arithmetic. Backend-only, always.
- **Component duplication** — a second `RiskChip` next to `RiskBadge` because the first one "didn't quite fit."
- **Inline styles** — `style={{ color: '#ff0000' }}` anywhere in the codebase. Tailwind semantic classes only.
- **Magic numbers** — an unexplained `20` or `50` threshold hardcoded in a component when it should be a named constant or, more likely, a value that should come from the backend response entirely.
- **Copy-paste components** — duplicating `DataTable` with three lines changed instead of adding a prop.
- **Prop drilling when Context exists** — passing `role` through five layers of props when `AuthContext` already holds it.
- **Inventing API fields** — see Section 12, item 2.
- **Inventing backend behavior** — assuming the escalation endpoint auto-retries, or that the copilot endpoint streams, without verifying against `shared/contracts/api.ts` and the QuickML spike findings first.
- **AI chrome** — sparkles, gradient borders, "AI is thinking" copy, anything that visually performs confidence the deterministic-first architecture doesn't claim to have (Law 14).
- **Fake interactivity** — a kanban-style dependency board that doesn't actually support drag-and-drop reordering the data model supports (Bible §4.15's explicit rejection).

---

## SECTION 14 — Implementation Principles (Immutable)

1. Backend owns truth; frontend renders it.
2. No invented contracts, no invented components, no invented behavior.
3. Search before building, every time, no exceptions.
4. Accessibility is correctness, not decoration.
5. Semantic tokens only — colors, spacing, typography.
6. Reuse before creating; extend before forking.
7. TypeScript strict, always.
8. Composition over configuration sprawl.
9. Context for global UI state, React Query for server state, `useState` for local/form state — and nothing blurs those lines.
10. Every screen handles loading, empty, and error explicitly.
11. Refusal is calm, never styled as an error.
12. The demo path is the real path — no scripted fakes.
13. Synthetic/stub features are always visibly labeled.
14. Every architecture-relevant decision gets logged in `DECISION_LOG.md` in the same session.
15. When documentation and reality disagree, surface the disagreement — never silently resolve it by guessing.
