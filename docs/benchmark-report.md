# CaseClock Prototype Performance Report

## Environment

- Commit: `0a5589c` (`git status` clean except pre-existing untracked `backend/` dependency folders).
- OS: Windows 11 (`10.0.26200`)
- Python: 3.13.1; pytest 8.4.2
- Node/Vite: Node version was not emitted by the build command; Vite 6.4.3
- Measurements are local prototype measurements, not production SLOs.
- `git fetch origin` / `git pull --rebase origin main` were attempted but could not write `.git/FETCH_HEAD` because of local permission restrictions; the branch was already up to date.

## Dataset / Workload

- Deterministic synthetic graph generated with `SyntheticDataConfig(seed=42)`.
- Deadline benchmark sizes: 100, 500, 1,000 and 5,000 cases. The generator produces multiple clock records per case.
- Existing scale test: 4,000 cases, 22,296 nodes and 45,448 edges (67,744 records total).
- No genuine labelled entity-resolution or retrieval ground truth was found. Precision, recall, F1, Precision@K, Recall@K and MRR are therefore not reported.
- Catalyst/QuickML/Zia provider calls were not benchmarked; repository tests use mocks/stubs for external integrations.

## Methodology

- `scripts/benchmark_caseclock.py` generates data in memory, warms the clock path once, then performs 7 timed runs per workload. It reports p50, p95, mean and throughput.
- Clock correctness is checked through the deterministic engine and existing expected-output tests; the scale benchmark validates graph loading and traversal invariants.
- The existing `tests/scale/test_scale_performance.py` runs 100 depth-2 network queries and reports average latency.
- Frontend evidence comes from `npm.cmd run build`; gzip sizes are emitted by Vite.

## Results

### Before vs after optimization

The safe optimization adds a per-node incident-edge index to the in-memory repository. It leaves response contents and graph semantics unchanged.

| Metric | Before | After | Change |
|---|---:|---:|---:|
| 4,000-case depth-2 graph query mean | 26.61 ms | 21.523 ms | 19.1% lower |
| 4,000-case depth-2 graph query p95 | not measured | 29.431 ms | baseline unavailable |
| 5,000-case mixed-state deadline p50 | not measured | 97.017 ms | new representative workload |

The before/after graph comparison uses the same 4,000-case synthetic configuration and fixed seed. Deadline results are not presented as an improvement because the new mixed-state workload is intentionally different from the historical all-green baseline.

### Statutory deadline engine — synthetic performance benchmark

| Cases | Clocks | p50 runtime | p95 runtime | p50 throughput |
|---:|---:|---:|---:|---:|
| 100 | 134 | 0.512 ms | 0.742 ms | 261,514 clocks/s |
| 500 | 667 | 4.618 ms | 6.270 ms | 144,435 clocks/s |
| 1,000 | 1,334 | 10.234 ms | 14.100 ms | 130,346 clocks/s |
| 5,000 | 6,667 | 91.931 ms | 233.739 ms | 72,522 clocks/s |

All generated clock responses in this run were deterministic `green` statuses for the fixed reference date. This is a correctness/throughput result for the local pure-Python calculation path, not a claim about Catalyst or end-to-end API latency.

### Graph / network intelligence — synthetic scale test

- 4,000 cases; 22,296 nodes; 45,448 edges; 67,744 total records.
- GraphLoader load: 0.316 s; graph validation: 0.115 s.
- 100 depth-2 `get_case_network` traversals: 2.661 s total; 26.61 ms average/query.
- Entity-resolution smoke benchmark: 10 queries over the scale graph in 1.413 s. No labelled accuracy metric is claimed.

### Frontend production build

- Build: passed (`tsc && vite build`); Vite reported 2,657 transformed modules.
- Largest emitted JS chunk: `vendor-recharts` 423.95 kB / 114.55 kB gzip.
- Main application JS chunk: 238.67 kB / 72.70 kB gzip.
- Main CSS chunk: 32.82 kB / 6.70 kB gzip.

### Local API benchmark

Using the real FastAPI application, in-memory repository path, development role header, 100 requests per endpoint after warm-up:

| Endpoint | Success | p50 | p95 |
|---|---:|---:|---:|
| `/worklist` | 100% | 11.341 ms | 18.670 ms |
| `/cases/{id}` | 100% | 1.715 ms | 4.931 ms |
| similar cases | 100% | 19.140 ms | 29.739 ms |
| network analysis | 100% | 30.267 ms | 84.422 ms |
| deadline monitor | 100% | 1.256 ms | 3.510 ms |

## Correctness Evidence

- Relevant deterministic/backend correctness suites: **146/146 passed** in 18.31 s, covering graph foundation, phases 1–4, authentication/audit, system status, Catalyst repository fallback, clock engine, cron sweep, document intelligence contracts, and backend core API.
- The current repository collects 517 tests. The aggregate full-suite invocation progressed through 96% but did not emit a final summary in this Windows runner. No assertion failure was observed in the completed runs, so this report does not claim 517/517 until the runner produces a complete summary.
- Final targeted backend gate: 50/50 passed, including the repository-index equivalence test. Frontend tests: 35/35 passed; production build passed.
- Tests are regression/correctness evidence, not AI accuracy evidence.

## Scalability

The mixed-state clock benchmark remains below 100 ms p50 for 5,000 cases / 6,667 clocks; the historical all-green run was 131.713 ms p50 in the latest capture. The graph scale test demonstrates 67,744 in-memory records and 21.523 ms mean depth-2 network traversal after indexing. These are synthetic local measurements and should not be extrapolated to production data volume.

## Limitations

- The local API benchmark exercises the real FastAPI application with the in-memory repository fixture; it is not live AppSail/Catalyst latency.
- No live Catalyst deadline sweep evidence was available; the sweep is covered functionally by tests but not benchmarked against a live provider.
- No real labelled entity-resolution or similar-case ground truth exists in the repository; do not claim accuracy, precision, recall, F1, Precision@K, Recall@K or MRR.
- QuickML, Zia OCR and other external services were not benchmarked: external provider/configuration availability was not established.
- Browser performance/Core Web Vitals, users saved, investigation time saved and production scale were not measured.

## Reproduction Commands

```powershell
$env:PYTHONPATH='.'
python scripts\benchmark_caseclock.py
pytest -q --disable-warnings --basetemp .pytest-run tests\test_graph_foundation.py tests\test_phase1_foundation.py tests\test_phase2_schema_seed.py tests\test_phase3_auth_audit.py tests\test_phase4_services.py tests\test_system_status.py tests\test_catalyst_env_fallback.py tests\test_catalyst_repository.py tests\test_clock_engine.py tests\test_cron_job.py tests\test_document_intelligence.py tests\test_backend_core_api.py
pytest -q tests\scale\test_scale_performance.py -s --disable-warnings
cd frontend
npm.cmd run build
```
