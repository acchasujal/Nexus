# Benchmarks and evaluation

Measurements below are **historical, reproducible synthetic benchmarks**, not production service-level guarantees. Current regression results are recorded in [progress](../progress.md). Tests, performance experiments and deployment observations answer different questions.

## Recorded performance artifact

Source: [current_metrics.json](../artifacts/benchmarks/current_metrics.json), recorded on 2026-09-17 at commit `ea29cffca5e0157090d836e2bc68f39b0634a11d`, Python 3.13.1, Windows 11 AMD64, eight logical cores. The filename denotes the tracked artifact; it does not mean it was measured against today's working tree.

| Experiment | Synthetic workload | Measured runs | p50 | p95 |
| --- | --- | ---: | ---: | ---: |
| Temporal snapshot diff | 10,000 nodes, 14,997 edges; 5% changes | 20 | 73.75 ms | 85.04 ms |
| Three-hop BFS | 50,000 nodes, 74,999 edges | 30 | 0.0179 ms | 0.0188 ms |
| Evidence-to-signal pipeline | 445 nodes, 493 edges; warm pipeline | 35 | 10.46 ms | 33.49 ms |

These experiments use the in-memory graph. They exclude Render cold starts, browser rendering, network latency and PostgreSQL/Neo4j round trips. The pipeline includes prototype analytical stages; execution speed does not establish forecast validity.

## Quality measurements and limits

The artifact records 100% precision and recall for planted synthetic identity ground truth and 87.5% precision for its adversarial noise suite. The latter is a separate workload, not a contradictory estimate of the same population. Neither establishes accuracy on real police records.

The [calibrated synthetic comparison](../artifacts/benchmarks/ncrb_calibrated_comparison.json) records distribution-fit experiments. Matching aggregate reference distributions does not validate individual relationships, operational forecasts or real-world deployment suitability.

Evidence coverage, tamper detection and abstention experiments are scoped to the tested fixtures and injected changes. Do not present them as universal guarantees, statutory certification or zero-risk claims. **NEW PROTOTYPE:** rule-based early-warning demonstrations remain distinct from calibrated forecasting.

## Reproduction

From the repository root:

```bash
python scripts/evaluate_ground_truth.py
python scripts/verify_canonical_invariants.py
python scripts/benchmarks/run_all_benchmarks.py
```

The benchmark runner writes tracked artifacts. Review its diff before committing; include commit, environment, workload, warm-ups and run counts when reporting new results. Keep seeded quality, adversarial robustness, API latency and browser timing separate.

Use [development](DEVELOPMENT.md) for regression commands and [deployment](DEPLOYMENT.md) for readiness semantics. A passing health probe is not a latency measurement.
