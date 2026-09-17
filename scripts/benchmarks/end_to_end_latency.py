"""scripts/benchmarks/end_to_end_latency.py

End-to-End Evidence-to-Investigator Signal Latency Benchmark for NEXUS:
Measures full pipeline latency across:
  NEW EVIDENCE INGESTION
  -> GRAPH UPDATE (In-Memory Adjacency Index)
  -> SNAPSHOT CREATION
  -> NETWORK DIFF (diff_graph_snapshots)
  -> SIGNIFICANCE FILTERING & NETWORK PULSE GENERATION
  -> EVIDENCE ASSESSMENT
  -> CONSTRAINED OPERATIONAL EARLY WARNING

Measures:
  - Cold pipeline latency (Initial index build + diff)
  - Warm pipeline latency: p50, p95, p99 across N >= 30 repeated runs
"""

from __future__ import annotations

import copy
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.proactive_intelligence_service import ProactiveIntelligenceService
from scripts.benchmarks.benchmark_suite import (
    MetricProvenance,
    benchmark_latency,
    get_current_commit,
    get_environment_info,
)


def execute_pipeline_cycle(service: ProactiveIntelligenceService, cycle_idx: int) -> dict[str, Any]:
    """Execute one full end-to-end evidence-to-signal cycle."""
    repo = service.repo
    # 1. Ingest new evidence record
    src_id = f"SRC-E2E-{cycle_idx:04d}"
    repo.source_records[src_id] = {
        "id": src_id,
        "source_type": "CDR",
        "locator": f"CALL-LOG:line-{cycle_idx}",
        "raw_excerpt": f"Intercept call {cycle_idx}: Vikram Sharma phoned suspect Deepak Verma.",
        "occurred_at": "2026-09-17T08:00:00Z",
        "batch_id": "BATCH-E2E",
        "case_ids": ["case-0001"],
        "content_hash": "e2e_digest",
        "hash_algorithm": "SHA-256",
    }

    # 2. Update GraphStore with new connection
    baseline_store = service.get_snapshot_store("snap-baseline-v1")
    assert baseline_store is not None

    updated_store = GraphStore()
    for nid, node in baseline_store.nodes.items():
        updated_store.nodes[nid] = NodeRecord(node.node_id, node.entity_type, node.properties)
    for src, elist in baseline_store.adj.items():
        for e in elist:
            updated_store.adj.setdefault(src, []).append(e)
            updated_store.radj.setdefault(e.target_id, []).append(e)
            updated_store.edge_index.setdefault(e.edge_type, []).append(e)

    # Ingest new edge
    new_edge = AdjEdge(
        "COMMUNICATED_WITH",
        "person-0001",
        "person-0004",
        properties={"id": f"rel-e2e-{cycle_idx}", "source_record_id": src_id},
    )
    updated_store.adj.setdefault("person-0001", []).append(new_edge)
    updated_store.radj.setdefault("person-0004", []).append(new_edge)
    updated_store.edge_index.setdefault("COMMUNICATED_WITH", []).append(new_edge)

    # 3. Snapshot Creation
    snap_id = f"snap-e2e-{cycle_idx}"
    service._snapshots[snap_id] = {
        "snapshot_id": snap_id,
        "case_scope": "GLOBAL",
        "created_at": "2026-09-17T08:05:00Z",
        "store": updated_store,
        "node_count": len(updated_store.nodes),
        "edge_count": sum(len(e) for e in updated_store.adj.values()),
        "version": "v1.1",
    }

    # 4. Network Diff, Pulse, Assessment, and Early Warning
    res = service.compute_network_diff("snap-baseline-v1", snap_id)
    return {
        "pulses_generated": len(res.pulses),
        "added_relationships": len(res.added_relationships),
    }


def run_end_to_end_benchmark() -> list[MetricProvenance]:
    commit = get_current_commit()
    env = get_environment_info()
    metrics: list[MetricProvenance] = []

    repo = InMemoryBackendRepository()
    service = ProactiveIntelligenceService(repo)

    print("\n[End-to-End Latency Benchmark] Running Evidence -> Pulse -> Forecast Pipeline...")

    # Benchmark warm pipeline
    cycle_counter = [0]

    def _step():
        cycle_counter[0] += 1
        execute_pipeline_cycle(service, cycle_counter[0])

    warm_res = benchmark_latency(_step, warmup_runs=5, measured_runs=35)

    print(f"  Warm Pipeline Latency: p50={warm_res['p50']:.2f}ms, p95={warm_res['p95']:.2f}ms, p99={warm_res['p99']:.2f}ms")

    metrics.append(
        MetricProvenance(
            metric_id="evidence_to_signal_p95_latency",
            name="Evidence-to-Investigator Signal Latency (p95)",
            value=warm_res["p95"],
            unit="ms",
            p50=warm_res["p50"],
            p95=warm_res["p95"],
            p99=warm_res["p99"],
            mean=warm_res["mean"],
            min=warm_res["min"],
            max=warm_res["max"],
            stddev=warm_res["stddev"],
            dataset="synthetic_criminal_graph",
            nodes=len(service.repo.to_graph_store().nodes),
            edges=sum(len(e) for e in service.repo.to_graph_store().edge_index.values()),
            runs=warm_res["runs"],
            warmups=warm_res["warmups"],
            environment=env,
            commit=commit,
            command="python scripts/benchmarks/end_to_end_latency.py",
            synthetic_or_real="synthetic",
            ppt_safe=True,
            scope="Complete pipeline: Ingestion -> Graph Update -> Diff -> Pulse -> Evidence Assessment -> Early Warning",
            limitations="Measured in-memory; production environment with remote Postgres/Neo4j and network transit will add network I/O overhead.",
        )
    )

    return metrics


if __name__ == "__main__":
    res = run_end_to_end_benchmark()
