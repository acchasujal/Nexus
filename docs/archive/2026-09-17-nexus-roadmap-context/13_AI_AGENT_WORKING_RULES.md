# AI Agent Working Rules for NEXUS Transformation

Read `00_START_HERE.md` before touching code/docs.

## Context hierarchy

1. Actual code/tests = implementation truth
2. `progress.md` = progress truth
3. `decisions.md` = accepted decision truth
4. This roadmap pack = target product direction
5. Historical docs = background only

When sources conflict, do not silently choose one. Investigate and update the canonical document/decision record.

## Mandatory behavior

Before changing code:
1. inspect current implementation
2. identify reusable services/models/APIs
3. map target capability to current architecture
4. define tests
5. define data-model/API/UI impact
6. implement minimally
7. run regression tests
8. update canonical docs
9. update `progress.md`
10. add `decisions.md` entry if a material architecture/security/data decision was made

## Never

- rewrite working subsystems without evidence
- silently change API semantics
- add mock/placeholder logic and call it implemented
- invent benchmark numbers
- present target vision as current
- introduce LLM reasoning where deterministic logic is required
- add generic features just because competitors have them
- add raw social-media scraping
- add public-chain storage of sensitive evidence
- create redundant markdown docs

## Required status labels

For every target feature use one:
- CURRENT
- EXTENSION
- NEW PROTOTYPE
- TARGET / FUTURE
- REJECTED

## Definition of done

A feature is not "done" until:
- code exists
- tests exist
- API contract is documented
- UI workflow is verified where applicable
- benchmark/quality evidence exists where applicable
- progress.md is updated
- security/provenance implications are handled
- deployment remains healthy

## Commit discipline

Use small coherent commits.
Do not bundle unrelated refactors.
Do not change the public deployment architecture without recording a decision.

## Final red-team checklist

Before marking work complete:
- Does this improve an investigator decision?
- What evidence supports it?
- What can be wrong?
- How is uncertainty shown?
- What happens when evidence is missing?
- Who can act?
- How is the action audited?
- Can the feature be evaluated?
