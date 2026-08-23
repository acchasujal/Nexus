# Synthetic Data Spec

This document defines a realistic synthetic dataset for the Graph Intelligence lane. It is designed to exercise graph traversal, pattern analysis, similarity, copilot grounding, dependency tracking, and clock behavior without introducing real PII.

## Dataset Targets

- 500 Cases
- 900 Persons
- 150 Officers
- 1000 Evidence records
- 150 Dependencies
- Multiple districts
- Multiple police stations
- Repeat offenders
- Shared phone numbers
- Shared vehicles
- Shared addresses
- Pending FSL and CDR reports
- Active legal clocks

## Coverage Targets By Feature

- Network Analysis: at least 60 repeated accused identities across 2+ cases, plus at least 25 shared phone-number clusters and 20 shared vehicle clusters.
- Pattern Detection: at least 8 recurring section combinations, 6 district clusters, and uneven station load so rollups have visible concentration.
- Similarity Search: at least 40 cases in repeated attribute bundles that share a section pair, a locality, and a month window.
- Copilot: at least 30 cases with enough connected context for grounded answers about person role, case stage, dependency status, or active clock state.
- Dependency Tracking: at least 60 cases with one or more pending dependencies, including FSL, CDR, witness statement, and sign-off items.
- Escalation Engine: at least 25 cases near threshold and at least 10 cases already past threshold with unresolved dependencies.
- Clock Engine: every case must have an active or explicitly overdue clock, with a small subset carrying multiple concurrent clocks.

## Design Goals

1. Give network analysis real signal by intentionally repeating a subset of people across multiple cases.
2. Give similarity and pattern detection repeated structured attributes to cluster on.
3. Give dependency and clock flows real stale and active states instead of clean, finished cases only.
4. Keep the dataset believable enough that downstream developers can test realistic graph queries without overfitting to toy data.

## Proposed Population Model

### Cases

- 500 total cases.
- Spread across 6 districts and 18 police stations.
- Each case should have at least one officer, one statutory classification path, and at least one person role edge.
- Roughly:
  - 260 routine investigation cases
  - 90 property/vehicle-linked cases
  - 80 assault or public-order cases
  - 70 mixed cases with multiple persons and multiple evidence items

### Persons

- 900 total person nodes.
- Suggested composition:
  - 360 unique accused identities
  - 180 repeat accused identities reused across 2 to 5 cases
  - 140 victims
  - 110 complainants
  - 110 witnesses
  - 0 to many people may appear in more than one role when the scenario justifies it, but the data should not make that common.

### Repeated Person Patterns

- Keep at least 60 accused identities attached to 3 or more cases.
- Keep at least 15 person records that recur with the same phone number across multiple cases.
- Keep at least 10 person records that recur with the same address across multiple cases.
- Keep at least 8 person records that recur with the same vehicle registration across multiple cases.

### Officers

- 150 officers across ranks.
- Distribute them across station, circle, subdivision, and district levels.
- At least some officers should appear in multiple cases so workload and escalation routing can be demonstrated.

### Units And Locations

- Use 6 districts and 18 police stations, with 2 to 4 stations per district.
- Assign each officer to one primary unit, and reuse a limited number of supervising officers so escalation routing is observable.
- Ensure location values repeat across related case clusters so the similarity view has real grouping signals.

### Evidence

- 1000 evidence records.
- Average of 2 evidence items per case, with some cases intentionally richer.
- Evidence should mix document, device, sample, and witness-note style items.

### Dependencies

- 150 dependency records.
- Suggested mix:
  - 60 FSL reports
  - 35 CDR reports
  - 25 witness statements
  - 15 supervisory sign-offs
  - 15 document retrieval items

### Clocks

- Every case should have at least one ClockInstance.
- Some cases should have a second clock instance to represent concurrent or later-stage deadlines.
- The dataset should include active, near-deadline, and overdue clocks so the clock UI and escalation logic can all be exercised.

Target mix:

- 220 green or comfortably active clocks
- 130 amber clocks
- 90 red clocks
- 60 overdue clocks

### Dependency And Clock Coupling

- At least 50 cases should combine an active clock with one unresolved dependency.
- At least 20 cases should combine an overdue clock with a pending FSL or CDR dependency.
- At least 10 cases should include two active clocks to prove the model can hold concurrent deadlines.

## Repeated Entity Strategy

The repeats below are intentional. Each one exists to unlock a specific downstream feature.

| Repeated entity             | How it repeats                                                                         | Why it exists                                                                                                | Feature enabled                                            |
| --------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| Repeat accused person       | Same accused reused across 2 to 5 cases                                                | Creates real cross-case identity reuse instead of isolated one-case graphs                                   | Network Analysis, Co-accused derivation, Copilot grounding |
| Shared phone number         | Same phone number attached to multiple person records or repeated across related cases | Gives a structured link that is strong enough to cluster but not so strong that every case becomes identical | Similarity, Network Analysis, Pattern Detection            |
| Shared vehicle registration | Same vehicle reused across vehicle-linked cases                                        | Produces a concrete artifact that ties multiple incidents together                                           | Network Analysis, Similarity, Crime Pattern Discovery      |
| Shared address              | Same address or locality reused across multiple persons and cases                      | Creates geographic clustering and station/district rollups                                                   | Pattern Detection, Similarity, Copilot grounding           |
| Shared station ownership    | Same station appears on multiple cases in the same district                            | Reflects how real case loads cluster in actual policing workflows                                            | Worklist, Pattern Detection, Escalation views              |
| Shared officer assignments  | Same officer handles multiple cases                                                    | Enables workload, escalation routing, and supervisor hierarchy views                                         | Escalation routing, Worklist, Copilot grounding            |
| Shared section bundles      | Same section or recurring section pair appears across related cases                    | Gives similarity search a deterministic legal-pattern anchor                                                 | Similarity, Pattern Detection, Copilot grounding           |
| Shared court context        | Same court context recurs for multiple cases                                           | Lets downstream audit and filing flows see repeated judicial context                                         | Copilot, Pattern Detection                                 |

## Why the Repeats Matter

- Repeat accused identities are required so `CO_ACCUSED_WITH` has real meaning and is not a self-contained same-case artifact.
- Shared phone numbers provide a weak but useful relationship for similarity and case linking.
- Shared vehicle numbers create a repeatable pattern for auto-surfacing potentially related incidents.
- Shared addresses let district and station rollups show a meaningful concentration of activity.
- Shared officers and stations let the graph support realistic operational oversight and escalation routing.
- Shared section bundles give similarity search a stable, explainable legal pattern to rank on.
- Shared court context keeps filing-related outputs from looking artificially disconnected.

## Case Archetypes

Use a mix of the following archetypes so the dataset exercises the full lane:

1. Single-accused case with one dependency and one active clock.
2. Multi-accused case with a repeat offender and shared evidence.
3. Vehicle-linked case with repeated vehicle registration across cases.
4. Address-linked cluster with several cases in the same locality.
5. Dependency-heavy case with pending FSL and CDR items.
6. Overdue case with unresolved dependency and escalation pressure.
7. Multi-cluster case group where the same accused, same phone number, and same location recur together, but not in every case, so the graph stays dense without collapsing into one cluster.

## Suggested Attribute Patterns

- Districts: 6 distinct district values.
- Police stations: 18 distinct stations distributed unevenly so some stations are busier than others.
- Offence categories: enough variety to exercise all legal clock mappings.
- Evidence mix: device-heavy for CDR-linked cases, document-heavy for FSL-heavy cases, and mixed for repeat-offender cases.
- Clock states: active, amber, red, and overdue states should all be present.
- Dependency states: pending, resolved, and escalated should all be represented.
- Section combinations: recurring bundles should appear often enough that the similarity feature can explain why cases were matched.

## Example Coverage Expectations

- Network analysis should find at least one non-trivial repeated accused path across multiple cases.
- Similarity should surface cases sharing phone number, vehicle, or address patterns.
- Pattern detection should show station and district concentration, not flat distributions.
- Copilot should be able to ground answers in repeated entities and active clocks.
- Escalation logic should have at least one case that is clearly near or past threshold.
- The graph should contain at least one cluster where a repeated accused, repeated phone number, and repeated address intersect, so downstream traversal is not dependent on a single pattern type.

## Notes For Future Generators

- Keep repeated entities deliberate, not random.
- Avoid perfectly clean data; some missing, pending, or stale dependencies are necessary.
- Avoid overusing the same repeat entity so the graph does not collapse into a single giant cluster.
- Preserve consistent identifiers for repeated synthetic identities so downstream queries remain stable.
- Do not introduce real personal data patterns that look like live records.
