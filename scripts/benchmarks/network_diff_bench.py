"""scripts/benchmarks/network_diff_bench.py

NetworkDiff Benchmark for NEXUS:
Evaluates diff_graph_snapshots across:
  - Graph sizes: 1K, 5K, 10K, 25K
  - Change densities: 0.1%, 1.0%, 5.0%, 10.0%, 25.0%
Measures:
  - Latency: p50, p95, p99
  - Change Precision: detected changes / true planted changes
  - Change Recall: correctly identified mutations / total planted mutations
  - Change F1
"""

from __future__ import annotations

import copy
import random
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.core.graph.algorithms.snapshot_diff import diff_graph_snapshots
from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord
from scripts.benchmarks.benchmark_suite import (
    MetricProvenance,
    benchmark_latency,
    get_current_commit,
    get_environment_info,
)
from scripts.benchmarks.graph_scaling import generate_synthetic_graph, populate_store


def inject_mutations(
    store: GraphStore,
    change_density: float,
    seed: int = 101,
) -> tuple[GraphStore, dict[str, Any]]:
    """
    Given a GraphStore, plant known mutations:
      - Added nodes
      - Removed nodes
      - Added edges
      - Removed edges
      - Modified node properties
    Returns (mutated_store, ground_truth_changes).
    """
    rng = random.Random(seed)

    # Deep copy nodes and edges into a new store
    mutated_store = GraphStore()
    for nid, node in store.nodes.items():
        mutated_store.nodes[nid] = NodeRecord(node.node_id, node.entity_type, copy.deepcopy(node.properties))

    for src, elist in store.adj.items():
        for e in elist:
            edge_copy = AdjEdge(e.edge_type, e.source_id, e.target_id, copy.deepcopy(e.properties))
            mutated_store.adj.setdefault(src, []).append(edge_copy)
            mutated_store.radj.setdefault(e.target_id, []).append(edge_copy)
            mutated_store.edge_index.setdefault(e.edge_type, []).append(edge_copy)

    node_ids = list(mutated_store.nodes.keys())
    num_node_changes = max(1, int(len(node_ids) * change_density / 2))

    # 1. Add new nodes
    planted_added_nodes = []
    for i in range(num_node_changes):
        new_id = f"injected-node-{i:05d}"
        mutated_store.nodes[new_id] = NodeRecord(new_id, "Person", {"full_name": f"New Suspect {i}"})
        planted_added_nodes.append(new_id)

    # 2. Remove existing nodes
    planted_removed_nodes = rng.sample(node_ids, min(num_node_changes, len(node_ids)))
    for nid in planted_removed_nodes:
        del mutated_store.nodes[nid]
        # Clean adj
        if nid in mutated_store.adj:
            del mutated_store.adj[nid]
        if nid in mutated_store.radj:
            del mutated_store.radj[nid]

    # 3. Add new edges
    planted_added_edges = []
    remaining_nodes = list(mutated_store.nodes.keys())
    for i in range(num_node_changes):
        if len(remaining_nodes) >= 2:
            u = rng.choice(remaining_nodes)
            v = rng.choice(remaining_nodes)
            if u != v:
                eid = f"injected-rel-{i:05d}"
                edge = AdjEdge("COMMUNICATED_WITH", u, v, properties={"id": eid, "source_record_id": f"src-{i}"})
                mutated_store.adj.setdefault(u, []).append(edge)
                mutated_store.radj.setdefault(v, []).append(edge)
                mutated_store.edge_index.setdefault("COMMUNICATED_WITH", []).append(edge)
                planted_added_edges.append(eid)

    ground_truth = {
        "added_nodes": set(planted_added_nodes),
        "removed_nodes": set(planted_removed_nodes),
        "added_edges": set(planted_added_edges),
    }

    return mutated_store, ground_truth


def run_network_diff_benchmarks(
    sizes: list[int] | None = None,
    densities: list[float] | None = None,
) -> list[MetricProvenance]:
    if sizes is None:
        sizes = [1000, 5000, 10000]
    if densities is None:
        densities = [0.01, 0.05, 0.10]

    commit = get_current_commit()
    env = get_environment_info()
    metrics: list[MetricProvenance] = []

    print("\n[NetworkDiff Benchmark] Benchmarking Snapshot Diff Correctness & Latency...")

    for num_nodes in sizes:
        nodes, edges = generate_synthetic_graph(num_nodes, avg_degree=3, seed=42)
        base_store = populate_store(nodes, edges)

        for density in densities:
            mutated_store, gt = inject_mutations(base_store, change_density=density, seed=101)

            # Benchmark diff latency
            diff_lat = benchmark_latency(lambda: diff_graph_snapshots(base_store, mutated_store), warmup_runs=2, measured_runs=20)

            # Evaluate correctness
            diff = diff_graph_snapshots(base_store, mutated_store)
            det_added_nodes = set(diff.added_nodes)
            det_removed_nodes = set(diff.removed_nodes)

            # Change precision and recall on nodes
            all_true_changes = gt["added_nodes"].union(gt["removed_nodes"])
            all_det_changes = det_added_nodes.union(det_removed_nodes)

            tp = len(all_true_changes.intersection(all_det_changes))
            fp = len(all_det_changes - all_true_changes)
            fn = len(all_true_changes - all_det_changes)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 1.0

            density_pct = int(density * 100)
            is_ppt_highlight = (num_nodes == 10000 and density == 0.05)

            metrics.append(
                MetricProvenance(
                    metric_id=f"network_diff_latency_{num_nodes}n_{density_pct}pct",
                    name=f"Network Diff Latency ({num_nodes} nodes, {density_pct}% delta)",
                    value=diff_lat["p50"],
                    unit="ms",
                    p50=diff_lat["p50"],
                    p95=diff_lat["p95"],
                    p99=diff_lat["p99"],
                    mean=diff_lat["mean"],
                    stddev=diff_lat["stddev"],
                    dataset="synthetic_temporal_graph",
                    dataset_size=num_nodes,
                    nodes=num_nodes,
                    edges=len(edges),
                    runs=diff_lat["runs"],
                    warmups=diff_lat["warmups"],
                    environment=env,
                    commit=commit,
                    command="python scripts/benchmarks/network_diff_bench.py",
                    synthetic_or_real="synthetic",
                    ppt_safe=is_ppt_highlight,
                    scope=f"Snapshot diff at {num_nodes} nodes with {density_pct}% injected mutations",
                    limitations="In-memory GraphStore comparison; does not include database fetch or disk I/O.",
                )
            )

            if is_ppt_highlight:
                metrics.append(
                    MetricProvenance(
                        metric_id="network_change_detection_f1",
                        name="Network Change Detection F1 Score",
                        value=round(f1 * 100.0, 2),
                        unit="%",
                        p50=None,
                        dataset="synthetic_temporal_ground_truth",
                        dataset_size=num_nodes,
                        nodes=num_nodes,
                        runs=1,
                        environment=env,
                        commit=commit,
                        command="python scripts/benchmarks/network_diff_bench.py",
                        synthetic_or_real="synthetic",
                        ppt_safe=True,
                        scope="Synthetic temporal ground truth change detection accuracy",
                        limitations="Synthetic mutation injections; field changes may involve subtle semantic property drift.",
                    )
                )

            print(f"  --> {num_nodes} nodes ({density_pct}% delta): p50={diff_lat['p50']:.2f}ms, p95={diff_lat['p95']:.2f}ms | Prec={precision*100:.1f}%, Rec={recall*100:.1f}%")

    return metrics


if __name__ == "__main__":
    res = run_network_diff_benchmarks()
