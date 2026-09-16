# NEXUS — Performance Benchmarks & Evaluation Protocols

This document separates **current measured performance benchmarks** from **target evaluation protocols** for the proactive network change plane.

---

## 1. Current Verified Performance Benchmarks

All performance figures below represent **actual local measurements** executed on synthetic criminal intelligence datasets using reproducible benchmark scripts.

**Measured Environment:** Local development workstation (Python 3.13 / FastAPI / In-Memory `GraphStore` / NetworkX / Neo4j 5).  
**Dataset Scale:** 445 entities (120 suspects, 150 phones, 60 accounts, 50 cases) and 530 relationships.

| Benchmark Operation | Workload / Depth | Target SLA | Measured Latency | Verification Status |
| :--- | :--- | :--- | :--- | :---: |
| **In-Memory Adjacency Index Build** | 445 nodes, 530 edges | $< 50\text{ ms}$ | **$6.05\text{ ms}$** | ✅ PASSED |
| **1-Hop Neighborhood Traversal (BFS)** | Direct incident connections | $< 5\text{ ms}$ | **$0.024\text{ ms}$** | ✅ PASSED |
| **2-Hop Subgraph Expansion (BFS)** | Co-accused & phone links | $< 10\text{ ms}$ | **$0.013\text{ ms}$** | ✅ PASSED |
| **3-Hop Extended Syndicate Traversal** | Deep network chains | $< 25\text{ ms}$ | **$0.018\text{ ms}$** | ✅ PASSED |
| **Louvain Community Detection** | 25 distinct modules | $< 200\text{ ms}$ | **$46.07\text{ ms}$** | ✅ PASSED |
| **Betweenness Centrality Bridge Discovery** | 149 articulation broker points | $< 500\text{ ms}$ | **$363.40\text{ ms}$** | ✅ PASSED |
| **Multi-Attribute Entity Resolution Query** | Phonetic + Jaccard + Phone + Vehicle | $< 50\text{ ms}$ | **$3.36\text{ ms}$** | ✅ PASSED |
| **Multi-Feature Case Similarity Search** | Feature vector distance | $< 20\text{ ms}$ | **$1.22\text{ ms}$** | ✅ PASSED |

### 1.1 Scale-Up Benchmark (1,800+ Nodes)
Tested via `tests/scale/test_scale_performance.py`:
- **Graph Scale:** 1,815 nodes, 1,770 edges
- **Graph Index Construction:** `2.84 ms`
- **3-Hop BFS Traversal:** `0.06 ms`
- **Community Detection (152 modules):** `299.85 ms`
- **Entity Resolution Matching:** `50.04 ms`

### 1.2 Ground-Truth Entity Resolution Accuracy
Tested via `python scripts/evaluate_ground_truth.py`:
- **True Positives:** 2
- **False Positives:** 0
- **False Negatives:** 0
- **Precision:** **100.00%**
- **Recall:** **100.00%**
- **F1 Score:** **100.00%**

---

## 2. Target Evaluation Protocols (Proactive Network Change Plane)

The following metrics and protocols define the evaluation harness for upcoming P0/P1 capabilities. Synthetic dataset accuracy must never be presented as field operational accuracy.

### 2.1 Network Diff Engine Evaluation
- **Change Precision:** Percentage of detected node/edge changes that represent true ground-truth graph state modifications.
- **Change Recall:** Percentage of actual graph mutations correctly captured in the diff.
- **False-Change Rate:** Rate of spurious change signals caused by dictionary reordering or non-semantic field updates (Target: $< 0.1\%$).
- **Diff Latency SLA:** $O(N + E)$ execution completed in $< 100\text{ ms}$ for 10,000 nodes.

### 2.2 Network Pulse Evaluation
- **Precision@K:** Proportion of top-$K$ surfaced pulses confirmed as operationally meaningful by investigators.
- **Useful-Pulse Rate:** Percentage of generated pulses leading to an active investigative step.
- **Alert Fatigue Metric (False Alert Rate):** Suppression of routine call volume changes (Target: $> 95\%$ routine noise filtered out).

### 2.3 Early-Warning & Abstention Evaluation
- **Precision@K & Lead Time:** Accuracy of forecasting operational transitions (e.g. `JURISDICTION_SHIFT`) and lead time provided before occurrence.
- **Abstention Rate & Calibration:** Reliability of triggering `INSUFFICIENT EVIDENCE / NO FORECAST` when data is sparse or contradictory (Target: 100% abstention on artificially degraded evaluation splits).
- **Zero Hallucination Gate:** Zero permitted generation of ungrounded or speculative forecasts.

### 2.4 Evidence Assessment Evaluation
- **Attribution Correctness:** Verification that every claim points to a valid, untampered source document.
- **Support / Conflict Accuracy:** Accuracy in categorizing corroborating vs. contradictory records.
- **Unsupported Claim Rate:** Strict requirement of 0% unsupported claims displayed without clear `MISSING` or `INFERRED` badges.

### 2.5 Next Best Verification Evaluation
- **Uncertainty Resolution Rate:** Percentage of suggested verification actions that successfully resolve an ambiguous or missing evidence link.
- **Role Appropriateness Rate:** Percentage of suggestions accurately targeted to the authorized investigator or analyst role.

### 2.6 Cross-Branch Intelligence Pulse Evaluation
- **Routing Correctness:** Verification that pulses are delivered exclusively to authorized officers handling affected cases.
- **Duplicate Suppression Rate:** Elimination of repeated notifications for the same cross-case link.
- **Acknowledgement Latency:** Tracking time from dispatch to investigating officer acknowledgement.

---

## 3. How to Reproduce Benchmarks

Execute the automated test and benchmark suites from the repository root:

```bash
# 1. Run all backend tests (708 passing)
pytest

# 2. Run ground-truth entity resolution benchmark
python scripts/evaluate_ground_truth.py

# 3. Run scale and latency benchmarks
python -m pytest tests/scale/test_scale_performance.py
```
