"""tests/scale/test_scale_performance.py

Scale performance and latency benchmark for NEXUS.
Generates large synthetic criminal intelligence graphs in-memory and benchmarks:
  1. Adjacency indexing and GraphStore construction.
  2. Multi-hop BFS traversal latency.
  3. Modularity community detection & bridge node calculation.
  4. Multi-attribute Entity Resolution throughput.
"""

from __future__ import annotations

import time
import pytest

from backend.app.core.graph.algorithms.clustering import detect_communities
from backend.app.core.graph.algorithms.entity_resolution import resolve_entity
from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord, bfs
from synthetic_data.nexus_generator import generate_nexus_synthetic_dataset


@pytest.mark.large_scale
def test_nexus_graph_algorithms_at_scale():
    print("\n[SCALE BENCHMARK] Generating scaled NEXUS synthetic graph...")
    start_gen = time.perf_counter()
    res = generate_nexus_synthetic_dataset(
        num_cases=200,
        num_persons=500,
        num_phones=600,
        num_accounts=300,
    )
    nodes = res["dataset"]["nodes"]
    edges = res["dataset"]["edges"]
    gen_duration = time.perf_counter() - start_gen
    total_records = len(nodes) + len(edges)
    print(f"  Generated: {len(nodes)} nodes, {len(edges)} edges in {gen_duration:.2f}s")
    assert total_records >= 2000

    # 1. Build GraphStore in-memory index
    start_idx = time.perf_counter()
    store = GraphStore()
    for n in nodes:
        store.nodes[n["id"]] = NodeRecord(
            node_id=n["id"],
            entity_type=n["entity_type"],
            properties=n.get("properties", {}),
        )
    for e in edges:
        edge_obj = AdjEdge(
            source_id=e["source_id"],
            target_id=e["target_id"],
            edge_type=e["edge_type"],
            properties=e.get("provenance", {}),
        )
        store.adj.setdefault(e["source_id"], []).append(edge_obj)
        store.radj.setdefault(e["target_id"], []).append(edge_obj)
        store.edge_index.setdefault(e["edge_type"], []).append(edge_obj)
    idx_duration = time.perf_counter() - start_idx
    print(f"  GraphStore Index built in {idx_duration*1000:.2f}ms")
    assert idx_duration < 1.0

    # 2. Benchmark BFS traversal
    first_node = nodes[0]["id"]
    start_bfs = time.perf_counter()
    visited_nodes = bfs(store, start_id=first_node, direction="both", max_depth=3)
    bfs_duration = time.perf_counter() - start_bfs
    print(f"  3-Hop BFS traversal visited {len(visited_nodes)} nodes in {bfs_duration*1000:.2f}ms")
    assert bfs_duration < 0.05

    # 3. Benchmark Community Detection
    start_comm = time.perf_counter()
    communities = detect_communities(store)
    comm_duration = time.perf_counter() - start_comm
    print(f"  Community detection detected {len(communities)} communities in {comm_duration*1000:.2f}ms")
    assert comm_duration < 0.50

    # 4. Benchmark Entity Resolution throughput
    start_er = time.perf_counter()
    sample_query = {
        "full_name": "Vikram Sharma",
        "phone_number": "9845012345",
        "vehicle_number": "KA01AB1001",
    }
    matches = resolve_entity(store, sample_query, confidence_threshold=0.40)
    er_duration = time.perf_counter() - start_er
    print(f"  Entity Resolution matched {len(matches)} candidates in {er_duration*1000:.2f}ms")
    assert er_duration < 0.20
