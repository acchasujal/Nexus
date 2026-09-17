"""scripts/benchmarks/run_all_benchmarks.py

Master benchmark orchestrator for NEXUS.
Executes all benchmark modules:
  1. Graph Scaling (500 to 50,000 nodes)
  2. ER Robustness (Seeded Ground Truth + Adversarial Noise Suite)
  3. Network Diff (Correctness + Latency matrix across scales and densities)
  4. Network Pulse (Compression ratio, meaningful recall, latency)
  5. Evidence Assessment (Traceable coverage, multi-source corroboration, zero unsupported claims)
  6. Early Warning & Mandatory Abstention (Zero guilt compliance, 100% abstention on degraded signals)
  7. Evidence Integrity & RBAC (SHA-256 tamper detection, 0 unauthorized acceptance)
  8. End-to-End Pipeline Latency (Evidence -> Signal p50/p95)

Exports consolidated machine-readable results to:
  artifacts/benchmarks/baseline.json
  artifacts/benchmarks/current_metrics.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.benchmarks.benchmark_suite import MetricProvenance
from scripts.benchmarks.early_warning_bench import run_early_warning_benchmark
from scripts.benchmarks.end_to_end_latency import run_end_to_end_benchmark
from scripts.benchmarks.er_robustness import run_er_robustness_benchmark
from scripts.benchmarks.evidence_assessment_bench import run_evidence_assessment_benchmark
from scripts.benchmarks.graph_scaling import run_graph_scaling_benchmarks
from scripts.benchmarks.integrity_rbac_bench import run_integrity_and_rbac_benchmark
from scripts.benchmarks.network_diff_bench import run_network_diff_benchmarks
from scripts.benchmarks.network_pulse_bench import run_network_pulse_benchmark


def main() -> int:
    print("=" * 80)
    print("  NEXUS MASTER BENCHMARK & EVALUATION SUITE (SIH 2026 PS 26189)")
    print("=" * 80)

    all_metrics: list[MetricProvenance] = []

    # Phase 2: Graph Scaling
    graph_metrics = run_graph_scaling_benchmarks(sizes=[500, 1000, 2500, 5000, 10000, 25000, 50000])
    all_metrics.extend(graph_metrics)

    # Phase 3: ER Robustness
    er_metrics = run_er_robustness_benchmark()
    all_metrics.extend(er_metrics)

    # Phase 4: Network Diff
    diff_metrics = run_network_diff_benchmarks(sizes=[1000, 5000, 10000], densities=[0.01, 0.05, 0.10])
    all_metrics.extend(diff_metrics)

    # Phase 5: Network Pulse
    pulse_metrics = run_network_pulse_benchmark()
    all_metrics.extend(pulse_metrics)

    # Phase 6: Evidence Assessment
    evidence_metrics = run_evidence_assessment_benchmark()
    all_metrics.extend(evidence_metrics)

    # Phase 7: Early Warning & Abstention
    ew_metrics = run_early_warning_benchmark()
    all_metrics.extend(ew_metrics)

    # Phase 9: Integrity & RBAC
    sec_metrics = run_integrity_and_rbac_benchmark()
    all_metrics.extend(sec_metrics)

    # Phase 10: End-to-End Latency
    e2e_metrics = run_end_to_end_benchmark()
    all_metrics.extend(e2e_metrics)

    # Format JSON payload
    out_dir = ROOT_DIR / "artifacts" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).isoformat()
    payload = {
        "timestamp": timestamp,
        "total_metrics_recorded": len(all_metrics),
        "ppt_safe_count": len([m for m in all_metrics if m.ppt_safe]),
        "metrics": [m.to_dict() for m in all_metrics],
    }

    # Write both baseline and current_metrics
    current_metrics_path = out_dir / "current_metrics.json"
    baseline_path = out_dir / "baseline.json"

    with open(current_metrics_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print("\n" + "=" * 80)
    print(f"  ALL BENCHMARKS COMPLETED: {len(all_metrics)} metrics recorded.")
    print(f"  PPT-Safe Metrics: {payload['ppt_safe_count']}")
    print("  Saved artifacts to:")
    print(f"    - {current_metrics_path}")
    print(f"    - {baseline_path}")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
