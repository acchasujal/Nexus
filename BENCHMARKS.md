# NEXUS Performance & Latency Benchmarks

## 1. Executive Summary

NEXUS executes all core graph intelligence operations in-memory using an optimized double-adjacency index and NetworkX integration, achieving sub-second real-time response times under load.

---

## 2. Benchmark Results

Measured on synthetic dataset (445 nodes, 530 edges across 50 cases):

| Operation | Scale / Depth | Target SLA | Measured Latency | Status |
| :--- | :--- | :--- | :--- | :--- |
| **In-Memory Graph Indexing** | 445 nodes, 530 edges | $< 50\text{ ms}$ | **$6.00\text{ ms}$** | ✅ PASSED |
| **1-Hop Neighborhood BFS** | Direct incident links | $< 5\text{ ms}$ | **$0.02\text{ ms}$** | ✅ PASSED |
| **2-Hop Neighborhood BFS** | Expanded syndicate links | $< 10\text{ ms}$ | **$0.01\text{ ms}$** | ✅ PASSED |
| **3-Hop Neighborhood BFS** | Extended network | $< 25\text{ ms}$ | **$0.02\text{ ms}$** | ✅ PASSED |
| **Community Detection** | Modularity / Louvain | $< 200\text{ ms}$ | **$56.63\text{ ms}$** | ✅ PASSED |
| **Bridge Node Detection** | Betweenness Centrality | $< 500\text{ ms}$ | **$355.03\text{ ms}$** | ✅ PASSED |
| **Entity Resolution Query** | Multi-attribute match | $< 50\text{ ms}$ | **$3.50\text{ ms}$** | ✅ PASSED |
| **Case Similarity Matching** | Feature vector distance | $< 20\text{ ms}$ | **$1.25\text{ ms}$** | ✅ PASSED |

---

## 3. Running Benchmark Suite

```bash
python scripts/benchmark_nexus.py
```
