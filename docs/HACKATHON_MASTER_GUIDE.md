# HACKATHON_MASTER_GUIDE.md

> STATUS: FROZEN as of 2026-07-08. Update only if submission strategy changes.

A new team member should be able to read only this document and understand the hackathon, the judges, the problem, the product, and how to win. This is a strategy document, not an engineering document — see `PROJECT_CONTEXT.md`, `ARCHITECTURE.md`, and `IMPLEMENTATION_PLAN.md` for the technical layer.

**Honesty note, upfront:** Some sections below (screenshots, exact demo screen recordings) describe what to build once real screens exist — they are specifications, not evidence of a finished product. Do not present anything in this document as "already built" unless `TASK.md` says it's DONE.

---

# 1. Hackathon Overview

**What it is:** Datathon 2026, organized by Karnataka State Police (KSP) with Hack2skill. ₹10 lakh prize pool across two problem statements (PS1 and PS2). We are building for **PS1 only**: Intelligent Conversational AI for the KSP Crime Database.

**Timeline (verify against the live participant dashboard before relying on any date — organizer timelines have shifted between phases of this project's planning):**
- Registration deadline and prototype submission deadline are both live-tracked on the organizer dashboard.
- Initial shortlist → prototype refinement window → mentor connects → final shortlist → in-person Grand Finale demo day in Bengaluru.

**Deliverables required at submission (per `PROTOTYPE_SUBMISSION_GUIDE.md`):** Prototype Brief, public GitHub repo, Catalyst deployment, demo video, prototype deck (14-section organizer format).

**Judging flow:** Submission → initial screening (likely mechanical, checking stated capability coverage against the brief) → shortlist → refinement period with mentor access → final shortlist → live demo day in front of a jury.

**What organizers repeatedly emphasized (from the webinar, not guessed):**
- No "quick and dirty, throwaway" prototypes — they want production-grade thinking.
- Solutions must handle roughly 1–2 lakh (100,000–200,000) records without breaking.
- "Agentic AI" handling complex queries, not simple static Q&A.
- Bilingual (English + Kannada), voice-enabled interaction.
- Mandatory deployment on Zoho Catalyst — non-negotiable for eligibility.
- Explainability and audit trails are a named judging pillar, not a nice-to-have.

**Catalyst requirement:** Every submission must actually run on Zoho Catalyst. This is a hard eligibility gate, not a suggestion — a brilliant idea that isn't deployed there does not qualify.

---

# 2. Problem Statement, Explained Simply

**What KSP actually has today:** Crime records from 1,100+ police stations sit in static systems. An investigator who wants to ask "which of my cases are close to missing a deadline" or "does this accused show up in any other case" has to do it manually — no existing tool answers that in plain language.

**What they're asking for:** A chatbot-like interface where an investigator types (or speaks) a question in English or Kannada, and the system answers using the real crime data — while also being able to show networks between people, spot patterns across crimes, describe socio-demographic trends, profile repeat offenders, and warn about emerging problems before they escalate.

**What they explicitly do NOT want:** A static dashboard. A "quick and dirty" prototype that would break under real data volume. A system that just retrieves data without deeper analysis. Anything that isn't deployed and demonstrable.

**Hidden expectation (not written directly, but strongly implied by the phrase "agentic AI" and the emphasis on "beyond simple Q&A"):** They want to see a system that reasons across the data, not one that just runs a lookup and prints a result.

**Success criteria, in plain terms:** A judge should be able to ask a real investigator-style question, in English or Kannada, and get a correct, explainable answer — or a clear "I'm not confident enough to answer that" instead of a made-up answer.

---

# 3. Dataset Guide

**Source:** Organizer-provided ER schema (not raw data — synthetic data only, per DPDP-compliance policy).

**Central table:** `CaseMaster` — every FIR is a case, and everything else connects back to it.

**Connected tables:** Victim, Accused, ComplainantDetails, ArrestSurrender, ChargesheetDetails, Act, Section, CrimeHead, CrimeSubHead, Employee, Unit, Court, District, State.

**Key relationships:** One case can have many victims, many accused, many complainants, many arrests. Cases link to Section/Act (what law was broken) and to Location/Unit (where, and which police unit is handling it).

**What this schema supports well, in plain terms:** Conversational queries about a case, network analysis between people who share a case, pattern analysis across crime type/location/time, basic offender history look-ups.

**What this schema does NOT support (say this honestly, don't pretend otherwise):**
- No unique person-identifier across different cases — if the same person appears in two FIRs with a slightly different name spelling, the system can't automatically know it's the same person. This is a real, hard, unsolved problem, not a bug we forgot to fix.
- No financial/transaction data at all — if we build a "financial crime link" feature, it must run on invented demo data and be labeled as such.
- No rich socio-economic fields (income, education, migration) — only basic demographic fields like age and gender exist, so "socio-demographic insight" will honestly be shallow.
- No built-in investigation-deadline or dependency-tracking data — this is our own addition (Case Clock), not something already in the schema.

**Opportunity:** The schema is clean enough to support everything we're building without needing invented tables, except for the two gaps above (financial, deep socio-economic) — which is exactly why our product design labels those honestly instead of faking them.

---

# 4. Judge Psychology

**What judges will actually reward:**
- A system that clearly ties back to the *official brief's* stated capabilities (network analysis, patterns, profiling), not just our own invented differentiator.
- Visible honesty about limitations — a team that says "we didn't build X because the data doesn't support it" reads as more credible than one that claims everything works.
- A live moment that's memorable and clearly demonstrates the product's real logic, not just a slide claim.
- Explainability shown structurally (the system shows its reasoning path), not just asserted in a sentence.

**What instantly reduces credibility:**
- Claiming "real-time," "production-grade," or "AI-powered" for something that's actually a simple rule or a hardcoded value.
- Being unable to explain, when asked directly, where a specific piece of demo data actually came from.
- A live demo failing and the team having no fallback.
- Vague or evasive answers to a direct technical question.

**Common overclaims to avoid (we have a documented history of these — see `DECISION_LOG.md` D9 — so this is a real risk for us specifically):**
- Calling a rule-based threshold check "predictive AI" or "forecasting."
- Calling a relational database with adjacency queries a "graph database" if it isn't actually one.
- Implying bilingual support is deep when it's a translation wrapper.
- Implying financial-crime detection works on real KSP data when it's actually synthetic demo-only data.

**Common AI buzzword traps:** Saying "agentic," "autonomous," or "self-learning" without being able to explain, concretely, what decision the AI is making versus what a deterministic rule is making. Judges at a technical hackathon will ask "what does agentic actually mean here" — have a real, specific answer.

---

# 5. Our Product — Case Clock

**Core idea:** One unified investigation graph. Every organizer-required capability (network analysis, pattern discovery, profiling, conversational query) is a different way of looking at the *same* graph — not five separate systems bolted together.

**Why it exists:** Most competing PS1 teams will build a generic chatbot over the crime database. That's easy to imitate. Our actual moat is something harder to research and copy: tracking real statutory deadlines under BNSS (the 60/90-day chargesheet clock, and the other clocks that run alongside it), tied to named, specific evidentiary blockers (FSL, CDR, witness statements) rather than a vague "risk score."

**Our moat, specifically:**
1. Real legal research most teams won't do (multiple concurrent BNSS clocks, not just the one everyone cites).
2. A single graph architecture that makes every other required capability cheap and internally consistent, instead of five disconnected demos that can contradict each other.
3. A conversational layer that refuses to guess when it's not confident — a trust signal, tested with a real question set, not just claimed.

**Why this beats a generic chatbot:** A chatbot alone answers questions. Our system also tells an investigator what to actually do next (which case needs attention, why, and what specifically is blocking it) — and every answer, including refusals, can be traced back to real data, not a black box.

---

# 6. Product Walkthrough

**Users:** Investigating Officer (IO) — daily user. SHO — station oversight. SP/DCP — exception-only district rollup.

**Screens:**
- **Risk-Ranked Worklist** (IO's home screen) — cases sorted by urgency, not FIR number.
- **Case Detail** (the core screen everyone lands on) — clock badges, named dependency panel, Network tab (co-accused links), Similarity tab (comparable past cases), Copilot box.
- **District/Pattern Rollup** (SP/DCP) — exception-only view plus crime-pattern aggregation.
- **Escalation Queue** — auto-generated notices when a case crosses a risk threshold.

**Expected user journey:** IO opens worklist → sees the riskiest case at the top → opens it → sees exactly what's blocking it (e.g., FSL report pending, 9 days left) → asks the copilot a follow-up question → gets an answer with its reasoning path shown, or an honest refusal if the question is out of scope.

---

# 7. Demo Guide

**Order and timing (5 minutes total):**
1. 0:00–0:20 — Hook: explain the legal stakes of a missed deadline, plainly, no dramatization.
2. 0:20–0:50 — Baseline: today's plain FIR-sorted list.
3. 0:50–1:30 — Risk-ranked view: same data, reframed by urgency.
4. 1:30–2:15 — **The wow moment:** live, on-stage threshold-crossing — a case flips to critical, auto-escalation fires, addressed to the correct supervisor.
5. 2:15–2:45 — Same case: copilot answers a real question with its reasoning path shown.
6. 2:45–3:15 — Same box: copilot declines a deliberately unanswerable question rather than guessing.
7. 3:15–3:45 — Network tab: a shared accused surfaces across two cases.
8. 3:45–4:15 — Pattern/rollup view, brief.
9. 4:15–5:00 — Close on the real metric ("we're measuring how many cases never had to turn red") and the honesty line ("the clock doesn't lie, neither does the system").

**Fallback demo (if live escalation fails):** Have a pre-recorded 20-second screen capture of the exact same escalation moment ready to cut to instantly — never attempt to debug live in front of judges.

**Offline backup:** A fully recorded version of the entire 5-minute demo, downloaded locally, playable with zero internet dependency, in case venue Wi-Fi fails during Catalyst-hosted access.

---

# 8. PPT Guide (organizer's 14-section format)

For each slide: goal, story, key message, layout, what to put where, and speaker notes. Actual screenshots/diagrams get inserted once the real screens exist — placeholders are marked `[SCREENSHOT: ...]` below and must not be faked with mockup images presented as real.

**1. Team Details** — Goal: establish credibility fast. Layout: names, roles (Sujal — frontend/product, Shriraj/Vikram/Dhiren — backend/AI/data), college, one-line relevant experience each. Speaker note: keep to 15 seconds, don't over-explain.

**2. Solution** — Goal: state the one-sentence pitch clearly. Key message: "One investigation graph. Every required AI capability is a lens on it, anchored by real statutory-deadline tracking." Layout: one big sentence, not a paragraph. Common mistake: burying the differentiator under a list of features.

**3. Opportunities** — Goal: show you understand the real problem, not just the brief. Key message: default bail is a hard legal failure with no current system-level visibility. Layout: one workflow diagram (FIR → investigation → clock → filing), the clock highlighted in red.

**4. Features** — Goal: map directly onto the organizer's 10 stated capabilities from the official framework, showing coverage honestly (✓ / △ / labeled-stub) rather than claiming full depth on all 10. Layout: a table, exactly like the checklist in `FEATURE_REGISTRY.md`.

**5. Process Flow** — Goal: show the FIR-to-chargesheet lifecycle with the product's intervention points marked. `[DIAGRAM: reuse the Stage 0–8 investigation workflow already documented in this project's research]`.

**6. Wireframes** — Goal: show the screen layout intent. `[WIREFRAME: Case Detail — clock badges top, dependency panel left, tabs (Network/Similarity/Copilot) right]`. Build from actual Figma/hand-sketch once frontend work starts — do not present AI-generated mockups as final screens.

**7. Architecture** — Goal: show the single-graph principle visually. `[DIAGRAM: reuse the architecture diagram from ARCHITECTURE.md]`. Key message: "one graph, many lenses" stated explicitly on the slide, not just implied.

**8. Technologies** — Goal: list actual stack (React, FastAPI, Python, the LLM provider actually used, Zoho Catalyst). Common mistake: listing a technology that isn't actually integrated yet (e.g., don't claim Neo4j unless Catalyst confirms and it's actually wired in — see `TASK.md`).

**9. Catalyst Services** — Goal: name the actual Catalyst services used (verify against real deployment, not assumption — see `IMPLEMENTATION_PLAN.md` step 009). Do not write this slide until step 009 is actually done.

**10. Cost** — Goal: a real, computed order-of-magnitude estimate for district-scale deployment, not an asserted number. This has been flagged as missing in every prior planning round — compute it before finalizing this slide.

**11. Screenshots** — Goal: show the real, working product. Only insert real screenshots once `TASK.md` shows the relevant screens as DONE.

**12. Benchmarking** — Goal: compare against CCTNS and a hypothetical generic-chatbot competitor. Key message: "CCTNS stores that a case exists; we compute how close it is to legally failing." Layout: simple 3-column comparison table.

**13. Links** — GitHub repo, Catalyst deployment URL, demo video link.

**14. Future Roadmap** — Goal: honestly show what's next (real Kannada NLU, real entity resolution, prosecutor workflow, mobile/offline) — labeled clearly as post-hackathon, not implied as already built.

---

# 9. Demo Video Guide

**Sequence:** Mirror the live demo flow exactly (Section 7 above) — consistency between video and live demo matters; judges may watch both.

**Camera/screen flow:** Screen recording only for product footage; a brief (5–10 second) talking-head opening to establish the human presenter and stakes, then cut to screen for the rest.

**Voiceover:** Calm, plain language — avoid a "dramatic documentary" tone given the seriousness of the subject matter (real legal consequences for real people). Match the tone used in the live demo script.

**Timing:** Match the 5-minute live demo length, or shorter (2–3 minutes) if the organizer's video guidelines specify a shorter cap — verify actual video length requirement from the submission guide before finalizing.

**Editing:** Minimal — clean cuts between screens, no distracting transitions. A government-facing product demo should look calm and trustworthy, not flashy.

**Music:** None, or very subtle/ambient — avoid anything that could read as trivializing the subject matter (crime, legal deadlines, real consequences).

---

# 10. Q&A Preparation

Real highest-yield questions (not padded to an arbitrary count) — these collapse most of the 50-question space judges are likely to draw from, based on the brief-alignment, technical, and legal risks already identified across this project's planning:

1. **"Where's your network-analysis / financial-link data actually from?"** → "The network links come from the real organizer schema — shared accused across cases. The financial-link view is synthetic demo data, since the organizer's schema has no financial entities — we built the extension point and labeled it clearly."
2. **"Is this really forecasting, or just an alert?"** → "A rule-based threshold alert, deliberately — we didn't want to ship an unaudited prediction model given the well-documented bias risks in predictive policing."
3. **"How do you avoid the AI hallucinating a wrong answer?"** → "A deterministic grounding gate checks the query against real schema before execution; if confidence is low, the system refuses rather than guesses. We tested this against a held-out question set before this demo." (Only say this if the test has actually been run — see `TASK.md`.)
4. **"Does this scale to KSP's real data volume?"** → State the actual measured latency number from the scale test (see `IMPLEMENTATION_PLAN.md` step 051) — never an estimate.
5. **"How is this different from a generic chatbot every other team is building?"** → "The legal-deadline research and the single-graph architecture — every other capability reuses the same data instead of being a separate bolted-on demo."
6. **"What happens if two people are the same person but spelled differently across FIRs?"** → "That's a real, unsolved problem — entity resolution across messy real-world data. We don't claim to solve it; our synthetic demo deliberately includes exact-match repeat entities to demonstrate the mechanism, and full fuzzy-matching is roadmap, not MVP."
7. **"Is this actually 'agentic,' or is it just a chatbot with a rule engine bolted on?"** → Be honest: "Most of the system is deterministic by design — that's a feature, not a limitation, because it makes every decision auditable. The generative layer is scoped narrowly to language understanding and refusal, not autonomous decision-making."
8. **"Would officers actually use this, given documented low digital literacy?"** → "That's a real adoption risk we don't dismiss — the product design tries to minimize friction (a worklist, not a query language), but full adoption depends on training and change management beyond what software alone solves."
9. **"Where does the BNSS section number for default bail come from — is it verified?"** → State honestly whether this has been checked against bare statute text by demo day (per `TASK.md`); if not verified, say so rather than assert a number with false confidence.
10. **"Why should we trust a risk-score for an offender isn't biased?"** → "It's not a risk-of-reoffending score — it only reflects this specific person's own prior FIR involvement, never demographic attributes, specifically to avoid that exact bias risk."

---

# 11. Evaluation Against Judging Criteria (honest self-scoring)

Per prior judging-panel simulation in this project's planning (see `DECISION_LOG.md` context), our most recent honest estimate:

| Dimension | Score /100 | Why |
|---|---|---|
| Problem Alignment | 75 | Improved from an earlier 35 after adding network/pattern/profiling coverage |
| Explainability | 80 | Structural, not just claimed |
| Scalability | 55 | **Still pending an actual executed scale test — do not raise this score until `TASK.md` shows it DONE** |
| Innovation | 65 | Real differentiator, but "confidence scoring" style trust signals are learnable by competitors |
| Government Readiness / Honesty | 75 | Directly tied to how disciplined we stay about labeling stubs |
| Judge Memorability | 75 | Contingent on rehearsal quality of the live escalation moment |

**Weaknesses:** Two unexecuted mandatory tests (refusal-gate, scale) as of this writing. Thin sociological/financial coverage inherent to the schema, not our engineering. **Improvements:** Execute both outstanding tests before finalizing any score claims in the deck.

---

# 12. Risks

**Technical:** Entity resolution failure making network analysis look trivial or wrong. Catalyst not supporting the assumed storage/graph pattern (unverified as of this writing).
**Legal:** Wrong or unverified BNSS section number asserted confidently in front of a legally literate judge.
**AI:** Refusal gate under-refusing (answering confidently when it shouldn't) — more dangerous than over-refusing.
**Deployment:** First real deployment discovered to be broken close to submission — mitigated by `IMPLEMENTATION_PLAN.md`'s Phase 0 early-deploy rule.
**Demo:** Live escalation moment failing in front of judges with no fallback ready.
**Data:** Synthetic dataset too "clean," producing an artificially good-looking demo that doesn't reflect real messiness.
**Presentation:** Overclaiming any stub (financial, forecasting) as fully real — single highest-consequence risk given this team's documented pattern (`DECISION_LOG.md` D9).

---

# 13. Roadmap

**Prototype (this submission):** Clock + Dependency + Escalation (core), Network (co-accused), Pattern/Trend, Copilot with tested refusal, PDF export, 3-role stub.
**Finals refinement:** Kannada wrapper, voice I/O, financial stub (labeled), rule-based forecasting alert (labeled), risk-scoring view.
**Real deployment (aspirational, multi-year, institutionally contingent):** Real Kannada NLU, real entity resolution, prosecutor workflow, mobile/offline, full ABAC, real financial-intelligence integration requiring actual KSP data-sharing agreements.

---

# 14. Final Submission Checklist

- [ ] Prototype Brief written and reviewed against `PROJECT_CONTEXT.md` for consistency
- [ ] GitHub repo public, README.md accurate and followable from a clean clone
- [ ] Catalyst deployment live, verified from a clean/second machine
- [ ] Demo video recorded, matches live demo script, correct length per submission guide
- [ ] Deck complete, all 14 organizer sections present, no unlabeled stub presented as real
- [ ] Refusal-gate test executed and scored (`TASK.md` shows DONE)
- [ ] Scale test executed and scored (`TASK.md` shows DONE)
- [ ] BNSS section numbers verified or explicitly marked unverified
- [ ] Cost estimate slide actually computed, not asserted
- [ ] Fallback/offline demo recording ready

---

## Brutal Self-Review of This Guide

**Weakness found:** The PPT section originally risked implying screenshots and wireframes exist — corrected by marking every visual placeholder explicitly rather than describing invented content as if real.

**Weakness found:** A first pass at Section 10 was heading toward padding to 50 distinct questions by rephrasing the same 5–6 underlying risks repeatedly. Corrected by giving the real, distinct highest-yield set instead — a shorter, non-redundant list is more useful to a team member than a longer, repetitive one.

**Weakness found:** Section 11's scores were at risk of being copy-pasted from a much earlier planning round without flagging that two of the underlying tests (refusal-gate, scale) remain unexecuted as of this writing — corrected by explicitly tying the Scalability score to `TASK.md` status rather than presenting it as settled.

**Remaining, unresolved weakness this guide cannot fix by itself:** Every section here describes intent and plan. None of it is evidence the product works. The single highest-leverage action after reading this document is still what `IMPLEMENTATION_PLAN.md` already says: execute steps 001–010, then keep moving down that list. A perfect strategy guide with no working software behind it does not get shortlisted.

**VERDICT:** This guide is complete as a strategy document, but its usefulness is entirely contingent on the two outstanding mandatory tests and the actual build progress in `TASK.md` — treat this as the map, not the territory.
**KEY INSIGHT:** The organizer's own judging pillars reward honesty about limitations as much as they reward capability — this guide's discipline about labeling stubs is not caution for its own sake, it's a scoring strategy specific to this panel.
**MOST LIKELY MISTAKE:** Treating this document, or any of the prior planning documents, as evidence of progress. They are not. Progress is measured only by `TASK.md`'s status table changing from NOT STARTED to DONE.
**BIGGEST RISK:** Time. Every round of this project's planning has reached correct, sound strategic conclusions; none has yet been checked against a line of running code.
**BEST ALTERNATIVE:** Stop producing new documents. Open `IMPLEMENTATION_PLAN.md`, execute step 001.
**NEXT BEST ACTION:** Report back with `TASK.md`'s actual status after a real work session — that is the only input that should change any of the scores or claims in this guide going forward.
**CONFIDENCE:** High on the strategic content. Zero confidence that any of it survives contact with the two unexecuted mandatory tests until they're actually run.
