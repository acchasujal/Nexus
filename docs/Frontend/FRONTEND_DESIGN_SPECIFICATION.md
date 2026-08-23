# CASECLOCK — DEFINITIVE FRONTEND DESIGN SPECIFICATION
**The absolute, final source of truth for AI coding agents. No placeholders. No decisions left to the agent.**

---

## SECTION 1: Design Philosophy

### Product Vision
CaseClock is an investigation command center, not a chatbot with a dashboard attached. It treats statutory deadlines and named evidentiary blockers as first-class objects. It feels like Palantir (density, purposefulness), Linear (speed, keyboard-first, motion), and Stripe (precision, polish)—specifically tailored for law enforcement.

### UX Philosophy
1.  **Deterministic over Generative:** The UI reflects facts computed by the backend. The AI layer is a query engine, not a magic oracle.
2.  **Two-Click Ceiling:** Any primary action is reachable in two clicks from the home screen.
3.  **Explainability is Visual:** Every number, risk badge, and AI response is one click away from its source rule or data trace.
4.  **Calm Under Pressure:** Refusals and errors are rendered with neutral, calm weight. Alarms are reserved strictly for breached statutory deadlines.

### Design Principles
1.  No status is color-only.
2.  The frontend computes nothing; it only renders backend state.
3.  Refusal is a success state, not an error.
4.  Motion communicates state change only; never decoration.
5.  Honest scope labeling (synthetic data is visually badged).

### Cognitive Load Strategy
Information is prioritized by urgency: Status (What happened?) -> Risk (What needs attention?) -> Action (What do I do next?). Tables are the default view to allow dense scanning without cognitive overload. AI path traces are collapsed by default.

### Why Judges Will Remember This UI
Judges see dozens of chatbots. They will remember CaseClock because of the **Signature Moment**: watching a risk badge flip, a table row re-sort, and an escalation fire simultaneously in under 300ms, followed by an AI query returning a traceable, structured answer. It proves the system is wired together, not just a UI over a static database.

---

## SECTION 2: Visual Identity

| Attribute | Specification | Why |
|---|---|---|
| **Typography** | Inter (sans-serif). Tabular numerals enabled for all metrics. | Unmatched legibility at small sizes; tabular numerals prevent jitter in data-dense tables. |
| **Spacing** | 8px base scale: 4, 8, 12, 16, 24, 32, 48, 64. | Systematic spacing creates rhythm; 8px aligns with standard screen resolutions. |
| **Grid** | 12-column. Max width 1440px. | 1440px maximizes the primary work surface without sprawling on ultra-wide monitors. |
| **Breakpoints** | `sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`. | Standard Tailwind breakpoints for predictable responsive behavior. |
| **Elevation** | Flat by default. Shadow-md on Dialogs, Drawers, Dropdowns. | Depth implies temporary context. The main canvas remains flat to keep data primary. |
| **Border Radius** | `4px` (inputs/buttons), `8px` (cards/tables), `12px` (dialogs). | Sharp enough for enterprise authority, soft enough to feel modern. |
| **Stroke Widths** | `1px` for all borders and dividers. | 1px prevents visual noise in dense table rows. |
| **Icon Style** | `lucide-react`. 1.5px stroke. Paired with text for status. | Clean, consistent, easily tree-shakeable. |
| **Illustrations** | None. | Illustrations waste space in enterprise tools and infantilize the user. |
| **Charts** | Recharts (Line, Bar, Heatmap). | Clean, React-native, easy to theme. |
| **Tables** | 40px row height (Dense default), 56px (Comfortable). | Dense mode allows IOs to scan 20+ cases without scrolling. |
| **Cards** | 8px radius, 1px border, no shadow. | Cards group discrete units without floating them unnecessarily. |
| **Motion** | 150ms (micro), 300ms (layout). `ease-out` standard. | Fast enough to feel instant, slow enough to register the state change. |
| **Loading** | Skeletons matching layout. Copilot: "Running query..." text. | Spinners obscure layout; skeletons prevent DOM shift. |
| **Errors** | Inline, red text, specific reason, Retry button. | "Something went wrong" is a banned phrase. |
| **Empty States** | Icon, 1 sentence reason, 1 primary action button. | Explains *why* it's empty, preventing false bug reports. |

---

## SECTION 3: Complete Design Token System

Agents must import these via Tailwind config. Do not hardcode.

### Colors
```css
/* Neutral Scale (Grays) */
--neutral-50: #F9FAFB;
--neutral-100: #F3F4F6;
--neutral-200: #E5E7EB;
--neutral-300: #D1D5DB;
--neutral-400: #9CA3AF;
--neutral-500: #6B7280;
--neutral-600: #4B5563;
--neutral-700: #374151;
--neutral-800: #1F2937;
--neutral-900: #111827;

/* Semantic (Status) */
--color-success: #059669; /* Green */
--color-warning: #D97706; /* Amber */
--color-danger: #DC2626;  /* Red */
--color-info: #2563EB;    /* Blue (Primary Action only) */
```

### Typography Scale
| Token | Size | Weight | Line Height | Usage |
|---|---|---|---|---|
| `display` | 2.5rem (40px) | 700 | 1.2 | Rollup Metric Cards |
| `h1` | 1.75rem (28px) | 600 | 1.3 | Page Titles |
| `h2` | 1.25rem (20px) | 600 | 1.4 | Section Headers |
| `body` | 0.9375rem (15px) | 400 | 1.5 | Default text, table cells |
| `small` | 0.8125rem (13px) | 400 | 1.5 | Metadata, timestamps |
| `caption` | 0.75rem (12px) | 500 | 1.4 | Badges, labels (Floor: never smaller) |

### Spacing & Radius
| Token | Value | Token | Value |
|---|---|---|---|
| `space-1` | 4px | `radius-sm` | 4px |
| `space-2` | 8px | `radius-md` | 8px |
| `space-3` | 12px | `radius-lg` | 12px |
| `space-4` | 16px | `radius-full` | 9999px |
| `space-6` | 24px | | |
| `space-8` | 32px | | |

### Animation
| Token | Duration | Curve | Usage |
|---|---|---|---|
| `fast` | 150ms | `ease-out` | Hover states, color changes |
| `normal` | 300ms | `ease-out` | Layout shifts, drawer open |
| `reduced` | 0ms | `linear` | `prefers-reduced-motion: reduce` |

---

## SECTION 4: Layout System

### Application Shell
*   **Left Sidebar:** Fixed `240px` width. Contains Wordmark, Role Badge, Primary Nav, Settings, Sign Out. Collapses to hamburger on `< lg`.
*   **Header:** Fixed `64px` height. Contains Global Search, Notifications Bell, Density Toggle.
*   **Content Area:** Fills remaining space. `32px` padding on `lg+`, `16px` on mobile.

### Panels & Drawers
*   **Drawer:** Slides in from right. `480px` width on desktop, `100%` on mobile. Used for quick edits (Add Dependency).
*   **Inspector:** None. Right-side panels are reserved exclusively for the docked Copilot in Case Detail.

### Navigation Hierarchy
1.  **Level 0 (Home):** Role-dependent (Worklist, Escalation Queue, Rollup).
2.  **Level 1 (Object):** Case Detail (`/case/:id`).
3.  **Level 2 (Tab):** Case sub-views (Clock, Network, Timeline). Persisted in URL.

---

## SECTION 5: Screen Specifications

### 1. Risk-Ranked Worklist (Home for IO/SHO)
*   **Purpose:** Sort cases by urgency, not FIR number.
*   **Layout:** Full-width `DataTable`. Sticky header. Action bar above table (Search, Filter, Density Toggle).
*   **Primary Action:** Click row -> Case Detail.
*   **Visual Hierarchy:** RiskBadge > ClockBadge > FIR No > Accused Name.
*   **Loading:** 15 skeleton rows.
*   **Empty:** "No active cases for this station." (Checks `isError` and `data.length === 0`).
*   **Keyboard:** Arrow keys navigate rows, Enter opens Case Detail.
*   **Required Data:** `Case[]` from `/worklist`.
*   **Judge Impression:** Immediate visual proof of the core thesis. Red badges at the top catch the eye.

### 2. Case Detail (Universal Object)
*   **Purpose:** The universal landing page for a specific case.
*   **Layout:** 3-column grid on desktop (Action Bar spanning top, Left: Clock & Dependencies, Right: Copilot docked). Tabbed interface for Network/Timeline/Similarity.
*   **Primary Actions (Top Bar):** Escalate, Add Dependency, Export PDF, Ask Copilot.
*   **Loading:** Skeleton matching 3-column layout.
*   **Required Data:** `Case` from `/cases/:id`.
*   **Judge Impression:** Density and clarity. The large Clock Countdown next to named blockers proves this isn't a generic dashboard.

### 3. Escalation Queue (Home for SHO/SP)
*   **Purpose:** Auto-generated notices when cases cross thresholds.
*   **Layout:** Full-width `DataTable`.
*   **Primary Action:** Click row -> Case Detail.
*   **Required Data:** `Escalation[]` from `/escalations`.
*   **Judge Impression:** The "wow" moment happens here when a new row appears live during the demo.

### 4. District Rollup (Home for SP/DCP)
*   **Purpose:** Exception-only district metrics.
*   **Layout:** Top row: 4 `MetricCards`. Below: Ranked Table of stations by overdue count.
*   **Required Data:** `Metrics` from `/rollup/:district`.
*   **Judge Impression:** Proves the system scales beyond a single station.

---

## SECTION 6: Component Specifications

### DataTable
*   **Props:** `columns: ColumnDef[]`, `data: T[]`, `isLoading: boolean`, `onRowClick: (row) => void`.
*   **States:** Loading (Skeletons), Empty (EmptyState component), Populated.
*   **Accessibility:** `role="grid"`. Arrow key navigation. `aria-sort` on headers.
*   **Responsive:** Horizontal scroll (`overflow-x-auto`) on `< lg`.

### ClockBadge
*   **Props:** `daysRemaining: number`, `status: 'HEALTHY' | 'WARNING' | 'DANGER' | 'UNDETERMINED'`.
*   **Variants:** `compact` (text only, e.g., "7d"), `detail` (horizontal progress bar + large number).
*   **A11y:** `aria-label="9 days remaining, status danger"`.

### RiskBadge
*   **Props:** `level: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNDETERMINED'`, `reasonUrl?: string`.
*   **Variants:** Default (Icon + Text + "Why?" link).
*   **A11y:** Icon is `aria-hidden`. Text conveys meaning. Link has `aria-describedby`.

### CopilotPanel
*   **Props:** `caseId?: string`.
*   **States:** Idle (Input focus), Loading ("Running query..."), Answer (Text + collapsed PathTrace), Refusal (Neutral gray box: "I cannot answer this.").
*   **A11y:** `role="log"`. `aria-live="polite"`. NO `assertive`.

### GraphViewer
*   **Props:** `nodes: GraphNode[]`, `edges: GraphEdge[]`.
*   **Library:** React Flow.
*   **A11y:** Hidden from screen readers (`aria-hidden="true"`). An adjacent "Table View" toggle provides the accessible alternative.

---

## SECTION 7: Interaction Design

### The Signature Escalation (The Wow Moment)
1.  User clicks "Mark Stale" on a Dependency in Case Detail.
2.  UI immediately shows dependency as stale (optimistic UI).
3.  Backend mutation succeeds.
4.  React Query invalidates `['worklist']`, `['case', id]`, `['escalations']`.
5.  **Simultaneously:** Worklist row moves up (re-sorted by backend), Case Detail clock turns red, Escalation Queue gets a new row.
6.  **Motion:** 300ms smooth transition on row background color and position.

### Dependency Update
*   **Trigger:** "Add Dependency" button -> Drawer opens -> Form submit.
*   **Optimistic Update:** Update cache immediately. Show Toast on success. Revert on error.

### Copilot Query
*   **Trigger:** Enter key in Copilot input.
*   **Flow:** Input locks -> "Running query..." -> Response renders. PathTrace is collapsed by default. 1-click expand.

---

## SECTION 8: Motion System

| Interaction | Duration | Curve | Purpose |
|---|---|---|---|
| Button Hover | 150ms | `ease-out` | Acknowledge interaction |
| Drawer Open | 300ms | `ease-out` | Establish temporary context |
| Risk Badge Color Change | 200ms | `linear` | Draw attention to state shift |
| Worklist Row Re-sort | 300ms | `ease-in-out` | Guide eye to new priority position |
| Copilot Response Fade-in | 150ms | `ease-out` | Prevent jarring pop-in |

**Reduced Motion:** All durations set to `0ms`. State changes are instant.

---

## SECTION 9: Accessibility Specification

1.  **Focus Rings:** 2px solid `--color-info` outline on every focusable element. Never `outline: none`.
2.  **Keyboard:** All actions reachable via keyboard. Tables support arrow keys. Dialogs trap focus.
3.  **Screen Readers:** `aria-live="polite"` for Copilot and Toasts. `aria-live="assertive"` ONLY for hard system errors.
4.  **Contrast:** Minimum 4.5:1 (text), 3:1 (UI elements/icons).
5.  **Graphs/Charts:** Never rely solely on color. Use patterns or text labels. Provide table fallbacks for complex graphs.

---

## SECTION 10: Responsive Rules

*   **Desktop (`>= 1024px`):** 3-column Case Detail. 240px Sidebar. 12-column grid.
*   **Tablet (`768px - 1023px`):** Sidebar collapses to hamburger. Case Detail stacks vertically (Copilot moves below). Tables scroll horizontally.
*   **Mobile (`< 768px`):** Single column. Action bar becomes sticky bottom bar. Drawers go full-screen.

---

## SECTION 11: Visual Consistency Rules (AI Agent Hard Laws)

1.  **NEVER** hardcode hex colors. Use Tailwind classes mapped to tokens.
2.  **NEVER** invent API response shapes. Import from `shared/contracts/api.ts`.
3.  **NEVER** compute business logic (e.g., `if (days < 20) setRisk('HIGH')`). The backend provides the status.
4.  **NEVER** use `assertive` `aria-live` for Copilot responses.
5.  **NEVER** build a custom force-directed graph. Use React Flow.
6.  **NEVER** use generic spinners for page loads. Use `LoadingSkeleton`.
7.  **NEVER** style a Copilot refusal as an error (red). It is a neutral state.

---

## SECTION 12: Frontend Architecture Rules

*   **Folder Structure:**
    *   `/src/components` (Global reusable UI)
    *   `/src/features` (Screen-specific components grouped by route)
    *   `/src/contexts` (AuthContext, UIContext)
    *   `/src/hooks` (Custom React Query hooks)
    *   `/src/lib` (Utils, MSW setup)
*   **State Ownership:** Context API owns UI state. React Query owns server state. `useState` owns local form state.
*   **API Ownership:** All data fetching via React Query hooks (`useWorklist`, `useCase`). No direct `fetch` in components.

---

## SECTION 13: Implementation Order

1.  **Phase 1: Foundation:** Tailwind tokens, Context API, React Query setup, MSW setup, AppShell (Sidebar/Header).
2.  **Phase 2: Core Data:** `DataTable`, `StatusChip`, `RiskBadge`, `ClockBadge`, `Worklist` screen.
3.  **Phase 3: Case Detail:** `Case Detail` layout, `DependencyTable`, `EscalationDialog`, React Query invalidation logic (Signature Interaction).
4.  **Phase 4: AI & Graphs:** `CopilotPanel`, `PathTrace`, `GraphViewer` (React Flow + Table fallback), Rollups.

---

## SECTION 14: Judge Psychology

*   **Worklist:** Judge sees immediate differentiation. "This sorts by legal urgency, not date."
*   **Case Detail:** Judge sees density and clarity. "The clock and the blockers are right next to each other."
*   **Signature Escalation:** Judge sees a live, deterministic system. "It caught the breach before the judge did."
*   **Copilot:** Judge sees explainability. "It refused to guess, and showed me the exact rule it used."
*   **Graph/Table Toggle:** Judge sees accessibility and scale. "It works for screen readers and 1 lakh rows."

---

## SECTION 15: Demo Story

1.  **0:00 - Land on Worklist:** Red badges at the top. "These cases are about to legally fail."
2.  **0:15 - Open Case 847:** Clock shows 9 days. Dependency shows FSL pending 21 days.
3.  **0:30 - The Trigger:** Click "Mark FSL as Stale".
4.  **0:32 - The Wow:** Case 847 moves to top of Worklist. Clock turns red. Escalation Queue (open in split-screen) instantly gets a new row.
5.  **1:00 - The Copilot:** Ask "Why is this case at risk?"
6.  **1:02 - The Answer:** Copilot replies: "Case 847 is at risk because the FSL report is 21 days stale and the 60-day clock has 9 days remaining." (Expand PathTrace).
7.  **1:30 - The Refusal:** Ask "Is the accused guilty?" Copilot replies calmly: "I cannot infer guilt or risk of reoffense."
8.  **2:00 - Scale:** Open Rollup. Show 5,000 rows in DataTable rendering flawlessly.

---

## SECTION 16: Critical Review

*   **Weak Decision Identified:** Previously allowed Choropleth Map for MVP.
    *   **Fix Applied:** Mapped to Table fallback only. Saves 2 days of dev time.
*   **Overengineering Identified:** Previously left WebSocket/SSE open for live updates.
    *   **Fix Applied:** Strict 3s polling + React Query invalidation. Reliable, deterministic, no backend spikes needed.
*   **Time Risk Identified:** Custom graph engine.
    *   **Fix Applied:** React Flow mandated.
*   **Accessibility Risk Identified:** Graph nodes unreadable by screen readers.
    *   **Fix Applied:** Graph hidden from ARIA, Table view is the accessible primary path.