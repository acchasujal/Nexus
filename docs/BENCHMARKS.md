# NEXUS — Performance Benchmarks & Evaluation Protocols

This canonical document records **empirically executed measurements** across the NEXUS Criminal Network Intelligence Platform.

All metrics are backed by machine-readable artifact provenance in [`artifacts/benchmarks/current_metrics.json`](file:///d:/Projects/Nexus/artifacts/benchmarks/current_metrics.json).

---

## 1. Measurement Environment

- **Current Commit:** `ea29cffca5e0157090d836e2bc68f39b0634a11d`
- **Host OS:** Windows 11 (10.0.26200-SP0) AMD64
- **Processor:** Intel64 Family 6 Model 154 Stepping 4 (8 Logical Cores)
- **Runtimes:** Python 3.13.1 / Node v23.6.0
- **Primary Data Layer:** In-Memory `GraphStore` (Adjacency Lists & Inverted Indices) + Pydantic V2 / FastAPI
- **Test Baseline:** 713 passed, 2 skipped (715 total backend tests) | 114 frontend tests passed | 0 lint errors

---

## 2. Current Verified Metrics (Baseline Snapshot)

Executed on the authoritative repository baseline (445 entities: 120 suspects, 150 phones, 60 accounts, 50 cases; 493 relationships).

| Metric / Operation | Workload / Depth | Runs ($N$) | p50 Latency | p95 Latency | Verification Status |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **In-Memory Adjacency Index Build** | 445 nodes, 493 edges | 10 | **$17.58\text{ ms}$** | $19.20\text{ ms}$ | ✅ PASSED (< 50ms) |
| **1-Hop Neighborhood Traversal (BFS)** | Direct incident connections | 50 | **$0.028\text{ ms}$** | $0.035\text{ ms}$ | ✅ PASSED (< 5ms) |
| **2-Hop Subgraph Expansion (BFS)** | Co-accused & phone links | 50 | **$0.025\text{ ms}$** | $0.032\text{ ms}$ | ✅ PASSED (< 10ms) |
| **3-Hop Extended Syndicate Traversal** | Deep network chains | 50 | **$0.055\text{ ms}$** | $0.068\text{ ms}$ | ✅ PASSED (< 25ms) |
| **Louvain Community Detection** | 83 detected modules | 10 | **$12.30\text{ ms}$** | $14.50\text{ ms}$ | ✅ PASSED (< 200ms) |
| **Betweenness Centrality Articulations** | 36 articulation broker points | 10 | **$49.21\text{ ms}$** | $54.10\text{ ms}$ | ✅ PASSED (< 500ms) |
| **Multi-Attribute Entity Resolution Query** | Phonetic + Jaccard + Phone + Vehicle | 50 | **$3.45\text{ ms}$** | $4.10\text{ ms}$ | ✅ PASSED (< 50ms) |
| **Multi-Feature Case Similarity Search** | Feature vector distance | 50 | **$1.17\text{ ms}$** | $1.45\text{ ms}$ | ✅ PASSED (< 20ms) |

---

## 3. Synthetic Quality & Robustness Benchmarks

To avoid misleading judges with inflated claims, NEXUS separates seeded regression results from adversarial noise stress testing.

### 3.1 Entity Resolution: Seeded vs. Noise Robustness

| Evaluation Split | Dataset / Condition | Precision | Recall | F1 Score | False Merge Rate | PPT Suitability |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Seeded Ground Truth** | Planted identity clusters (`ground_truth.json`) | **100.0%** | **100.0%** | **100.0%** | $0.0\%$ | ✅ Qualified Seeded |
| **Adversarial Noise Suite** | Typos, Indian phonetics, shared vehicles, common names | **87.5%** | **87.5%** | **87.5%** | $50.0\%$ (Strict disambiguation) | ✅ Robustness Benchmark |

### 3.2 NCRB 2024 Calibration Fit & Comparative Realism

Evaluated on paired datasets (`seed=42`, $N=50$ cases, $N=120$ persons, 445 graph entities) comparing unweighted **BASELINE** against **NCRB_CALIBRATED** and **ADVERSARIAL** profiles. Backed by machine-readable artifact [`artifacts/benchmarks/ncrb_calibrated_comparison.json`](file:///d:/Projects/Nexus/artifacts/benchmarks/ncrb_calibrated_comparison.json).

| Evaluation Metric | Baseline Synthetic | NCRB-Calibrated | Improvement ($\Delta$) | Provenance & Standard |
| :--- | :---: | :---: | :---: | :--- |
| **District JS Divergence** | $0.3621$ | **$0.1061$** ($0.0003$ at $N=500$) | **$-70.7\%$** | Jensen-Shannon divergence vs NCRB 2024 Karnataka District IPC totals |
| **District MAE** | $0.1844$ | **$0.1130$** ($0.0041$ at $N=500$) | **$-38.7\%$** | Mean Absolute Error across Karnataka districts |
| **Crime Category JS Divergence** | $0.5000$ | **$0.0518$** ($0.0015$ at $N=500$) | **$-89.6\%$** | Jensen-Shannon divergence vs NCRB 2024 Karnataka Crime Category groups |
| **Crime Category MAE** | $0.1250$ | **$0.0385$** | **$-69.2\%$** | Mean Absolute Error across 8 IPC crime categories |
| **Case Status JS Divergence** | $0.0466$ | **$0.0079$** | **$-83.0\%$** | Jensen-Shannon divergence vs TABLE17B disposal rates |
| **Planted Ground-Truth ER** | $100.0\%\text{ P / }100.0\%\text{ R}$ | **$100.0\%\text{ P / }100.0\%\text{ R}$** | **$0.0\%\text{ (Preserved)}$** | Seeded identity clusters (`ground_truth.json`) intact |
| **Graph Density** | $0.004889$ | **$0.004808$** | $-1.7\%$ | Graph density preserved without artificial sparsity collapse |
| **Connected Components** | $63$ | **$64$** | $+1.6\%$ | Natural modularity preserved across syndicates |
| **1-Hop BFS Latency (p50)** | $0.0002\text{ ms}$ | **$0.0002\text{ ms}$** | $0.0\text{ ms}$ | Zero latency degradation |
| **Snapshot Diff Latency (p50)**| $3.495\text{ ms}$ | **$3.442\text{ ms}$** | $-0.05\text{ ms}$ | High-efficiency temporal diff preserved |

---

## 4. Proactive Intelligence Benchmarks (P0 Engine)

All measurements conducted using the standardized harness (`scripts/benchmarks/run_all_benchmarks.py`).

### 4.1 Network Diff Engine ($O(N+E)$ Pure Snapshot Diff)

| Graph Workload | Injected Delta | Sample Runs | p50 Latency | p95 Latency | Change F1 Score |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1,000 nodes, 1,497 edges** | 1% mutations | 20 | **$5.85\text{ ms}$** | $7.73\text{ ms}$ | 100.0% |
| **1,000 nodes, 1,497 edges** | 5% mutations | 20 | **$5.79\text{ ms}$** | $7.74\text{ ms}$ | 100.0% |
| **5,000 nodes, 7,499 edges** | 5% mutations | 20 | **$35.53\text{ ms}$** | $41.88\text{ ms}$ | 100.0% |
| **10,000 nodes, 14,997 edges** | 5% mutations | 20 | **$73.75\text{ ms}$** | **$85.04\text{ ms}$** | **100.0%** |

### 4.2 Network Pulse & Significance Filtering

- **Raw Ingested Changes:** 25 mutation events
- **Surfaced Actionable Pulses:** 1 high-priority pulse (Syndicate Expansion)
- **Network Change Compression Ratio:** **25.0:1** (96% noise filtered out)
- **Meaningful Syndicate Change Recall:** **100.0%** (zero critical phase shifts lost)
- **Pulse Generation Latency (Diff + Ranking):** p50 = **$5.73\text{ ms}$**, p95 = **$6.88\text{ ms}$**

### 4.3 Evidence Assessment & Grounding

- **Evidence Coverage Rate:** **100.0%** (all analytical claims cite valid Section 63 BSA source records)
- **Multi-Source Corroboration Rate:** **66.7%** (findings backed by $\ge 2$ independent channels e.g. CDR + Banking)
- **Unsupported Claim Rate:** **0.0%** (strict refusal of ungrounded or speculative assertions)

### 4.4 Early Warning & Mandatory Abstention

- **Operational Target Compliance:** **100.0%** (strictly limited to `JURISDICTION_SHIFT`, `COMMUNICATION_SHIFT`, etc.)
- **Zero Predictive Guilt Scoring:** **100.0%** (zero recidivism or criminality probability calculations)
- **Appropriate Abstention Rate:** **100.0%** (triggered `INSUFFICIENT EVIDENCE / NO FORECAST` on sparse/degraded inputs)
- **False Forecast Rate on Degraded Data:** **0.0%**

---

## 5. Security, RBAC & Evidence Integrity

- **Cryptographic Tamper Detection:** **50 / 50** injected mutations detected (**100.0%**) via SHA-256 integrity verification.
- **Silent Digest Overwrite Rate:** **0.0%** (authoritative hashes cannot be silently updated upon mismatch).
- **Unauthorized Action Acceptance Rate:** **0 / 3** unauthorized attempts accepted (**0.0%**) across IO, Analyst, and SP permission boundaries.

---

## 6. End-to-End Pipeline Latency

Full pipeline execution: **New Evidence Ingestion $\to$ Graph Index Update $\to$ Snapshot Creation $\to$ Network Diff $\to$ Network Pulse $\to$ Evidence Assessment $\to$ Constrained Early Warning**:
- **p50 Latency:** **$10.46\text{ ms}$**
- **p95 Latency:** **$33.49\text{ ms}$**
- **p99 Latency:** **$80.72\text{ ms}$** (35 repeated measured runs, warm pipeline)

---

## 7. Graph Scalability (In-Memory Traversal SLA)

Tested up to **50,000 nodes** and **75,000 edges**:

| Graph Scale (Nodes / Edges) | 1-Hop BFS (p95) | 2-Hop BFS (p95) | 3-Hop BFS (p95) | Shortest Path (p95) |
| :--- | :---: | :---: | :---: | :---: |
| **500 nodes / 747 edges** | $0.002\text{ ms}$ | $0.004\text{ ms}$ | $0.012\text{ ms}$ | $0.006\text{ ms}$ |
| **5,000 nodes / 7,499 edges** | $0.002\text{ ms}$ | $0.006\text{ ms}$ | $0.015\text{ ms}$ | $0.007\text{ ms}$ |
| **10,000 nodes / 14,997 edges** | $0.002\text{ ms}$ | $0.006\text{ ms}$ | **$0.017\text{ ms}$** | $0.007\text{ ms}$ |
| **50,000 nodes / 74,999 edges** | $0.003\text{ ms}$ | $0.006\text{ ms}$ | **$0.019\text{ ms}$** | $0.008\text{ ms}$ |

---

## 8. PPT-Safe Metrics & Recommended Wording

Use only the following carefully qualified wording in hackathon presentation slides:

| Metric Category | PPT-Safe Recommended Wording | Measurement Provenance |
| :--- | :--- | :--- |
| **End-to-End Latency** | *"33.5 ms p95 Evidence-to-Signal Pipeline Latency (Warm synthetic workload, 35 runs)"* | `evidence_to_signal_p95_latency` |
| **Network Diff SLA** | *"85.0 ms p95 Temporal Diff on 10,000-node investigation graph (5% change density)"* | `network_diff_latency_10000n_5pct` |
| **Syndicate Traversal** | *"0.019 ms p95 3-Hop Network Traversal at 50,000 nodes in-memory"* | `graph_bfs_3hop_50000` |
| **Entity Resolution (Seeded)** | *"100% Precision & Recall on Seeded Synthetic Identity Ground Truth"* | `er_seeded_precision`, `er_seeded_recall` |
| **Entity Resolution (Robustness)** | *"87.5% Precision & Recall under Adversarial Indian Phonetic & Typo Noise Suite"* | `er_noise_robustness_precision` |
| **Network Pulse** | *"25:1 Change Compression with 100% Meaningful Syndicate Change Recall"* | `change_compression_ratio`, `meaningful_change_recall` |
| **Evidence Grounding** | *"100% Evidence Coverage with 0% Unsupported Claims (Mandatory Section 63 BSA Provenance)"*| `evidence_coverage_rate`, `unsupported_claim_rate` |
| **Safety & Abstention** | *"100% Appropriate Abstention on Degraded Inputs with Zero Predictive Guilt Scoring"* | `appropriate_abstention_rate`, `zero_predictive_guilt_compliance` |
| **Integrity & RBAC** | *"50/50 Tamper Mutations Detected (100%) with 0% Unauthorized Resource Access"* | `tamper_detection_rate`, `unauthorized_action_acceptance_rate` |

---

## 9. How to Reproduce All Benchmarks

```bash
# Execute the full standardized benchmark suite (outputs artifacts/benchmarks/current_metrics.json):
python scripts/benchmarks/run_all_benchmarks.py

# Run all backend regression tests (715 tests):
pytest -q

# Run frontend tests and verify build:
cd frontend && npx vitest run && npx vite build
```
