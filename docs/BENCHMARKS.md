# NEXUS — Performance & Latency Benchmarks

## 1. Executive Summary & Methodology

All performance benchmarks represent **actual local measurements** executed on synthetic criminal intelligence datasets using reproducible scripts. 

> **Important Discipline Note:** Historical CaseClock prototype benchmarks (e.g. statutory deadline cron jobs) are obsolete and have been purged. Only current NEXUS graph intelligence measurements are presented below.

---

## 2. Current NEXUS Benchmark Results

**Measured Environment:** Local development workstation (Python 3.13 / FastAPI / In-Memory `GraphStore` / NetworkX).  
**Dataset Scale:** 445 entities (120 suspects, 150 phones, 60 accounts, 50 cases) and 530 relationships.

| Benchmark Operation | Workload / Depth | Target SLA | Measured Latency | Result |
| :--- | :--- | :--- | :--- | :---: |
| **In-Memory Adjacency Index Build** | 445 nodes, 530 edges | $< 50\text{ ms}$ | **$6.05\text{ ms}$** | ✅ PASSED |
| **1-Hop Neighborhood Traversal (BFS)** | Direct incident connections | $< 5\text{ ms}$ | **$0.024\text{ ms}$** | ✅ PASSED |
| **2-Hop Subgraph Expansion (BFS)** | Co-accused & phone links | $< 10\text{ ms}$ | **$0.013\text{ ms}$** | ✅ PASSED |
| **3-Hop Extended Syndicate Traversal** | Deep network chains | $< 25\text{ ms}$ | **$0.018\text{ ms}$** | ✅ PASSED |
| **Louvain Community Detection** | 25 distinct modules | $< 200\text{ ms}$ | **$46.07\text{ ms}$** | ✅ PASSED |
| **Betweenness Centrality Bridge Discovery** | 149 articulation broker points | $< 500\text{ ms}$ | **$363.40\text{ ms}$** | ✅ PASSED |
| **Multi-Attribute Entity Resolution Query** | Phonetic + Jaccard + Phone + Vehicle | $< 50\text{ ms}$ | **$3.36\text{ ms}$** | ✅ PASSED |
| **Multi-Feature Case Similarity Search** | Feature vector distance | $< 20\text{ ms}$ | **$1.22\text{ ms}$** | ✅ PASSED |

---

## 3. Scale-Up Benchmark (1,800+ Nodes)

Tested via [`tests/scale/test_scale_performance.py`](file:///d:/Projects/CaseClock/tests/scale/test_scale_performance.py):
- **Graph Scale:** 1,815 nodes, 1,770 edges
- **Graph Index Construction:** `2.84 ms`
- **3-Hop BFS Traversal:** `0.06 ms`
- **Community Detection (152 modules):** `299.85 ms`
- **Entity Resolution Matching:** `50.04 ms`

---

## 4. How to Reproduce Benchmarks

Run the benchmark script directly from the project root:

```bash
python scripts/benchmark_nexus.py
```
