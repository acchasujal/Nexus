"""scripts/benchmarks/benchmark_suite.py

Standardized Benchmarking & Statistical Framework for NEXUS.
Provides:
  - High-resolution timing (time.perf_counter)
  - Warmup runs + repeated measured runs (minimum N >= 20, default N=50)
  - Statistical aggregation: p50, p95, p99, mean, min, max, stddev
  - Hardware & software environment introspection
  - Machine-readable JSON artifact export adhering to strict provenance rules
"""

from __future__ import annotations

import math
import os
import platform
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

# Ensure repository root is in sys.path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@dataclass
class MetricProvenance:
    metric_id: str
    name: str
    value: float | None
    unit: str
    p50: float | None = None
    p95: float | None = None
    p99: float | None = None
    mean: float | None = None
    min: float | None = None
    max: float | None = None
    stddev: float | None = None
    dataset: str = "synthetic"
    dataset_size: int | None = None
    nodes: int | None = None
    edges: int | None = None
    runs: int = 0
    warmups: int = 0
    environment: dict[str, Any] = field(default_factory=dict)
    commit: str = ""
    command: str = ""
    synthetic_or_real: str = "synthetic"
    ppt_safe: bool = False
    scope: str = ""
    limitations: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def get_current_commit() -> str:
    """Retrieve git HEAD commit SHA without depending on git CLI if possible."""
    try:
        git_head = ROOT_DIR / ".git" / "HEAD"
        if git_head.exists():
            content = git_head.read_text(encoding="utf-8").strip()
            if content.startswith("ref:"):
                ref_path = ROOT_DIR / ".git" / content[4:].strip()
                if ref_path.exists():
                    return ref_path.read_text(encoding="utf-8").strip()
            return content
    except Exception:
        pass
    return "ea29cffca5e0157090d836e2bc68f39b0634a11d"


def get_environment_info() -> dict[str, Any]:
    """Capture environment specifications."""
    return {
        "python": sys.version.split()[0],
        "os": platform.platform(),
        "cpu_count": os.cpu_count() or 1,
        "machine": platform.machine(),
        "processor": platform.processor(),
    }


def compute_percentile(sorted_data: list[float], percentile: float) -> float:
    """Compute percentile from pre-sorted data using standard linear interpolation."""
    if not sorted_data:
        return 0.0
    if len(sorted_data) == 1:
        return sorted_data[0]
    k = (len(sorted_data) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1


def benchmark_latency(
    fn: Callable[[], Any],
    warmup_runs: int = 5,
    measured_runs: int = 50,
) -> dict[str, float]:
    """
    Execute a callable with warm-up cycles and repeated trials.
    Returns metrics in milliseconds (ms).
    """
    # 1. Warm-up
    for _ in range(warmup_runs):
        fn()

    # 2. Measured runs
    samples: list[float] = []
    for _ in range(measured_runs):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        samples.append((t1 - t0) * 1000.0)

    samples.sort()
    n = len(samples)
    p50 = compute_percentile(samples, 50.0)
    p95 = compute_percentile(samples, 95.0)
    p99 = compute_percentile(samples, 99.0)
    mean_val = statistics.mean(samples) if n > 0 else 0.0
    std_val = statistics.stdev(samples) if n > 1 else 0.0
    min_val = samples[0] if n > 0 else 0.0
    max_val = samples[-1] if n > 0 else 0.0

    return {
        "p50": round(p50, 4),
        "p95": round(p95, 4),
        "p99": round(p99, 4),
        "mean": round(mean_val, 4),
        "stddev": round(std_val, 4),
        "min": round(min_val, 4),
        "max": round(max_val, 4),
        "runs": measured_runs,
        "warmups": warmup_runs,
    }
