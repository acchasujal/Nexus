"""scripts/benchmarks/graph_scaling.py

Graph scaling benchmark for NEXUS GraphStore:
  - Sizes: 500, 1000, 2500, 5000, 10000, 25000, 50000 nodes
  - Operations:
      1. GraphStore construction
      2. 1-hop BFS traversal
      3. 2-hop BFS traversal
      4. 3-hop BFS traversal
      5. Bounded shortest pathfinding
      6. Entity lookup by ID
  - Measures p50, p95, p99 across repeated runs.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.core.graph.algorithms.utils import (
    AdjEdge,
    GraphStore,
    NodeRecord,
    bfs,
)
from collections import deque

def find_shortest_path(store: GraphStore, src: str, tgt: str, max_depth: int = 6) -> list[str] | None:
    if src not in store.nodes or tgt not in store.nodes:
        return None
    if src == tgt:
        return [src]
    queue = deque([(src, [src])])
    visited = {src}
    while queue:
        curr, path = queue.popleft()
        if len(path) - 1 >= max_depth:
            continue
        # Neighbors
        neighbors = []
        for e in store.adj.get(curr, []):
            neighbors.append(e.target_id)
        for e in store.radj.get(curr, []):
            neighbors.append(e.source_id)
        for nbr in neighbors:
            if nbr == tgt:
                return path + [nbr]
            if nbr not in visited and nbr in store.nodes:
                visited.add(nbr)
                queue.append((nbr, path + [nbr]))
    return None
from scripts.benchmarks.benchmark_suite import (
    MetricProvenance,
    benchmark_latency,
    get_current_commit,
    get_environment_info,
)


def generate_synthetic_graph(num_nodes: int, avg_degree: int = 3, seed: int = 42) -> tuple[list[NodeRecord], list[AdjEdge]]:
    rng = random.Random(seed)
    nodes: list[NodeRecord] = []
    edges: list[AdjEdge] = []

    entity_types = ["Person", "Phone", "Account", "Vehicle", "Case"]
    for i in range(num_nodes):
        nid = f"n-{i:06d}"
        etype = entity_types[i % len(entity_types)]
        nodes.append(NodeRecord(node_id=nid, entity_type=etype, properties={"idx": i, "label": f"Node-{i}"}))

    # Generate random edges with roughly avg_degree
    edge_types = ["COMMUNICATED_WITH", "USED_PHONE", "TRANSFERRED_FUNDS", "ASSOCIATED_WITH"]
    num_edges = int(num_nodes * avg_degree / 2)
    edge_set: set[tuple[str, str]] = set()

    for i in range(num_edges):
        u_idx = rng.randint(0, num_nodes - 1)
        v_idx = rng.randint(0, num_nodes - 1)
        if u_idx != v_idx:
            pair = (f"n-{min(u_idx, v_idx):06d}", f"n-{max(u_idx, v_idx):06d}")
            if pair not in edge_set:
                edge_set.add(pair)
                edges.append(
                    AdjEdge(
                        source_id=pair[0],
                        target_id=pair[1],
                        edge_type=edge_types[i % len(edge_types)],
                        properties={"id": f"e-{i:07d}", "source_record_id": f"rec-{i:07d}"},
                    )
                )

    return nodes, edges


def populate_store(nodes: list[NodeRecord], edges: list[AdjEdge]) -> GraphStore:
    store = GraphStore()
    for n in nodes:
        store.nodes[n.node_id] = n
    for e in edges:
        store.adj.setdefault(e.source_id, []).append(e)
        store.radj.setdefault(e.target_id, []).append(e)
        store.edge_index.setdefault(e.edge_type, []).append(e)
    return store


def run_graph_scaling_benchmarks(
    sizes: list[int] | None = None,
    runs: int = 30,
    warmup: int = 5,
) -> list[MetricProvenance]:
    if sizes is None:
        sizes = [500, 1000, 2500, 5000, 10000, 25000, 50000]

    commit = get_current_commit()
    env = get_environment_info()
    metrics: list[MetricProvenance] = []

    print(f"\n[Graph Scaling Benchmark] Testing graph sizes: {sizes}")
    for num_nodes in sizes:
        nodes, edges = generate_synthetic_graph(num_nodes, avg_degree=3, seed=42)
        num_edges = len(edges)
        print(f"  --> Graph size: {num_nodes:,} nodes | {num_edges:,} edges")

        # 1. GraphStore Construction Latency
        construct_res = benchmark_latency(lambda: populate_store(nodes, edges), warmup_runs=2, measured_runs=max(5, runs // 3))
        metrics.append(
            MetricProvenance(
                metric_id=f"graph_construct_{num_nodes}",
                name="GraphStore Construction Latency",
                value=construct_res["p50"],
                unit="ms",
                p50=construct_res["p50"],
                p95=construct_res["p95"],
                p99=construct_res["p99"],
                mean=construct_res["mean"],
                min=construct_res["min"],
                max=construct_res["max"],
                stddev=construct_res["stddev"],
                dataset="synthetic_random_graph",
                dataset_size=num_nodes,
                nodes=num_nodes,
                edges=num_edges,
                runs=construct_res["runs"],
                warmups=construct_res["warmups"],
                environment=env,
                commit=commit,
                command="python scripts/benchmarks/graph_scaling.py",
                synthetic_or_real="synthetic",
                ppt_safe=False,
                scope=f"In-memory GraphStore indexing at {num_nodes} nodes",
                limitations="In-memory Python dictionary and adjacency lists; single-threaded.",
            )
        )

        store = populate_store(nodes, edges)
        root_node = nodes[0].node_id
        target_node = nodes[min(10, num_nodes - 1)].node_id

        # 2. 1-Hop BFS
        bfs1_res = benchmark_latency(lambda: bfs(store, start_id=root_node, direction="both", max_depth=1), warmup_runs=warmup, measured_runs=runs)
        metrics.append(
            MetricProvenance(
                metric_id=f"graph_bfs_1hop_{num_nodes}",
                name="1-Hop Traversal Latency",
                value=bfs1_res["p50"],
                unit="ms",
                p50=bfs1_res["p50"],
                p95=bfs1_res["p95"],
                p99=bfs1_res["p99"],
                mean=bfs1_res["mean"],
                min=bfs1_res["min"],
                max=bfs1_res["max"],
                stddev=bfs1_res["stddev"],
                dataset="synthetic_random_graph",
                nodes=num_nodes,
                edges=num_edges,
                runs=bfs1_res["runs"],
                warmups=bfs1_res["warmups"],
                environment=env,
                commit=commit,
                command="python scripts/benchmarks/graph_scaling.py",
                synthetic_or_real="synthetic",
                ppt_safe=False,
                scope=f"1-hop traversal on {num_nodes}-node graph",
            )
        )

        # 3. 2-Hop BFS
        bfs2_res = benchmark_latency(lambda: bfs(store, start_id=root_node, direction="both", max_depth=2), warmup_runs=warmup, measured_runs=runs)
        metrics.append(
            MetricProvenance(
                metric_id=f"graph_bfs_2hop_{num_nodes}",
                name="2-Hop Traversal Latency",
                value=bfs2_res["p50"],
                unit="ms",
                p50=bfs2_res["p50"],
                p95=bfs2_res["p95"],
                p99=bfs2_res["p99"],
                mean=bfs2_res["mean"],
                min=bfs2_res["min"],
                max=bfs2_res["max"],
                stddev=bfs2_res["stddev"],
                dataset="synthetic_random_graph",
                nodes=num_nodes,
                edges=num_edges,
                runs=bfs2_res["runs"],
                warmups=bfs2_res["warmups"],
                environment=env,
                commit=commit,
                command="python scripts/benchmarks/graph_scaling.py",
                synthetic_or_real="synthetic",
                ppt_safe=False,
                scope=f"2-hop traversal on {num_nodes}-node graph",
            )
        )

        # 4. 3-Hop BFS
        bfs3_res = benchmark_latency(lambda: bfs(store, start_id=root_node, direction="both", max_depth=3), warmup_runs=warmup, measured_runs=runs)
        metrics.append(
            MetricProvenance(
                metric_id=f"graph_bfs_3hop_{num_nodes}",
                name="3-Hop Traversal Latency",
                value=bfs3_res["p50"],
                unit="ms",
                p50=bfs3_res["p50"],
                p95=bfs3_res["p95"],
                p99=bfs3_res["p99"],
                mean=bfs3_res["mean"],
                min=bfs3_res["min"],
                max=bfs3_res["max"],
                stddev=bfs3_res["stddev"],
                dataset="synthetic_random_graph",
                nodes=num_nodes,
                edges=num_edges,
                runs=bfs3_res["runs"],
                warmups=bfs3_res["warmups"],
                environment=env,
                commit=commit,
                command="python scripts/benchmarks/graph_scaling.py",
                synthetic_or_real="synthetic",
                ppt_safe=(num_nodes in (10000, 50000)),
                scope=f"3-hop syndicate traversal on {num_nodes}-node graph",
                limitations="Measured in-memory; real-world Neo4j traversals will have bolt connection overhead.",
            )
        )

        # 5. Shortest Path
        sp_res = benchmark_latency(lambda: find_shortest_path(store, src=root_node, tgt=target_node, max_depth=6), warmup_runs=warmup, measured_runs=runs)
        metrics.append(
            MetricProvenance(
                metric_id=f"graph_shortest_path_{num_nodes}",
                name="Bounded Shortest Path Latency",
                value=sp_res["p50"],
                unit="ms",
                p50=sp_res["p50"],
                p95=sp_res["p95"],
                p99=sp_res["p99"],
                mean=sp_res["mean"],
                min=sp_res["min"],
                max=sp_res["max"],
                stddev=sp_res["stddev"],
                dataset="synthetic_random_graph",
                nodes=num_nodes,
                edges=num_edges,
                runs=sp_res["runs"],
                warmups=sp_res["warmups"],
                environment=env,
                commit=commit,
                command="python scripts/benchmarks/graph_scaling.py",
                synthetic_or_real="synthetic",
                ppt_safe=False,
                scope=f"Shortest path search on {num_nodes}-node graph",
            )
        )

    return metrics


if __name__ == "__main__":
    res = run_graph_scaling_benchmarks(sizes=[500, 1000, 2500, 5000, 10000, 25000, 50000])
    for m in res:
        if "bfs_3hop" in m.metric_id:
            print(f"[{m.nodes} nodes] 3-Hop BFS: p50={m.p50}ms, p95={m.p95}ms")
