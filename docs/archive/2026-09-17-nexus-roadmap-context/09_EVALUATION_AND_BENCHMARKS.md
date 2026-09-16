# Evaluation & Benchmark Transformation

Current ER and graph-performance benchmarks must remain regression gates, but they are not sufficient for the new proactive layer.

## Preserve current gates

- 708 backend tests
- 114 frontend tests
- lint/build
- ER precision/recall
- GraphStore latency
- Neo4j projection tests
- evidence tamper tests
- Copilot refusal tests

## New evaluation suites

### Network Diff
Measure:
- change precision
- change recall
- false-change rate
- missed-change rate
- temporal detection latency

### Network Pulse
Measure:
- precision@K
- false alert rate
- useful-pulse rate
- lead time
- calibration/support-level reliability

### Early Warning
Measure:
- precision@K
- recall@K
- lead time
- abstention rate
- false-alert rate
- temporal holdout performance

### Evidence Assessment
Measure:
- evidence attribution correctness
- support/conflict classification
- unsupported-claim rate
- silent-overwrite rate

### Next Best Verification
Measure:
- expert usefulness
- uncertainty-resolution rate
- percentage of recommendations that resolve the missing evidence
- inappropriate recommendation rate

### Intelligence Pulse
Measure:
- routing correctness
- authorization failures
- acknowledgement latency
- duplicate propagation rate

### Case DNA
Measure:
- Top-K retrieval relevance
- component-level explanation consistency
- expert validation

### SOCMINT correlation
Measure:
- attribution precision
- independent corroboration rate
- source-quality stratification

## Dataset strategy

Current synthetic ground-truth data remains the regression fixture.

Add temporal scenarios with:
- known graph changes
- known irrelevant changes
- stale evidence
- contradictory evidence
- false entity matches
- false relationship candidates
- jurisdiction transitions
- identifier drift
- bridge emergence/replacement

Never present synthetic benchmark accuracy as real-world accuracy.

Use temporal holdouts for forecasting-like evaluation.

Always compare complex methods against simple baselines.
