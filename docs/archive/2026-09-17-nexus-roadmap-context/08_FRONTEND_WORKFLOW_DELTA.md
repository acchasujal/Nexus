# Frontend Workflow Delta

The current UI should evolve rather than be replaced.

## New investigator workflow

1. Worklist / Investigation
2. Network Pulse
3. Current Network
4. Entity Fusion
5. Evidence Assessment
6. Network Diff
7. Early Warning
8. Uncertainty / action window
9. Next Best Verification
10. Optional Intelligence Pulse
11. Digital Shadow
12. Copilot explanation
13. Human decision
14. Audit
15. Graph refresh/update

## New primary UI concepts

### Network Pulse
A review queue showing meaningful network changes:
- what changed
- when
- affected entities/cases
- evidence count
- support/conflict/missing state
- action window

### Network Diff
Before/after graph comparison:
- added nodes/edges
- removed nodes/edges
- changed communities
- new bridge
- jurisdiction movement
- evidence overlays

### Early Warning
Show the forecast object, not a generic risk score:
- signal
- time window
- evidence
- support
- uncertainty
- action window
- suggested verification
- abstention if necessary

### Evidence Assessment
Every claim should visually separate:
- supports
- conflicts
- missing
- verified

### Next Best Verification
Show suggested verification steps with role restrictions.

### Intelligence Pulse
Show:
- source case/branch
- affected investigations
- observed change
- evidence
- action window
- verification
- acknowledgement status

### Digital Shadow
Do not build a social-media dashboard.
Use a provenance-preserving evidence lane:
Observed → Candidate Link → Corroborated → Investigator Confirmed.

### Human decision
The final action should remain:
- confirm
- reject
- defer
- record reason

### Graph
Use the current Graph Explorer / Pathfinder foundations.
Make temporal diff and evidence overlays the major new visual capability.

## UX rules

- No "guilty", "dangerous", "criminal probability" labels.
- Do not turn Network Pulse into a red-alert wall.
- Use review-priority semantics.
- Make uncertainty visible.
- Make provenance one click away.
- Never hide whether a result is observed, derived, inferred or investigator-confirmed.
