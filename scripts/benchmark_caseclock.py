"""Reproducible local benchmarks for deterministic CaseClock prototype code.

Uses only in-memory synthetic data and does not touch production persistence.
"""
from __future__ import annotations

import json
import platform
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from collections import Counter

from backend.app.core.clock.engine import ClockEngine
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditService
from backend.app.services.cron_service import CronService
from backend.app.core.graph.algorithms.utils import AdjEdge, NodeRecord
from backend.app.core.graph.graph_loader import GraphLoader
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.graph_service import GraphService
from fastapi.testclient import TestClient
from backend.app.main import create_app
from synthetic_data.configs import SyntheticDataConfig
from synthetic_data.generator import generate_synthetic_graph
from shared.constants.clock_types import get_clock_rule


def pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((p / 100) * (len(ordered) - 1))))
    return ordered[index]


def _mixed_clock_properties(assembly, reference_time: datetime) -> list[dict[str, object]]:
    """Create a fixed-date mixed-state workload without changing production data."""
    state_offsets = (30, 10, 3, -5, 0)
    properties: list[dict[str, object]] = []
    for index, record in enumerate(assembly.clock_records):
        node_properties = dict(record.node.properties)
        days_remaining = state_offsets[index % len(state_offsets)]
        clock_type = str(node_properties.get("clock_type", ""))
        rule_key = "document_supply" if "DOCUMENT" in clock_type else "further_investigation" if "FURTHER" in clock_type else str(node_properties.get("offence_category", "theft"))
        duration_days = get_clock_rule(rule_key).duration_days
        deadline = reference_time + timedelta(days=days_remaining)
        node_properties["deadline_date"] = deadline
        node_properties["start_date"] = deadline - timedelta(days=duration_days)
        properties.append(node_properties)
    return properties


def run_size(case_count: int, repeats: int = 7, mixed: bool = False) -> dict[str, object]:
    assembly = generate_synthetic_graph(SyntheticDataConfig(seed=42, case_count=case_count))
    clock_nodes = [record.node for record in assembly.clock_records]
    reference_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    engine = ClockEngine(reference_time)
    properties = (
        _mixed_clock_properties(assembly, reference_time)
        if mixed
        else [node.properties for node in clock_nodes]
    )

    for node, node_properties in zip(clock_nodes, properties):
        engine.from_clock_node(str(node.id), node_properties)

    timings: list[float] = []
    last_statuses: list[str] = []
    last_responses = []
    for _ in range(repeats):
        start = time.perf_counter()
        responses = [engine.from_clock_node(str(node.id), node_properties) for node, node_properties in zip(clock_nodes, properties)]
        timings.append((time.perf_counter() - start) * 1000)
        last_statuses = [response.status.value for response in responses]
        last_responses = responses

    verification = [engine.from_clock_node(str(node.id), node_properties) for node, node_properties in zip(clock_nodes, properties)]

    return {
        "cases": len(assembly.case_blueprints),
        "clocks": len(clock_nodes),
        "runs": repeats,
        "runtime_ms_p50": round(pct(timings, 50), 3),
        "runtime_ms_p95": round(pct(timings, 95), 3),
        "runtime_ms_mean": round(statistics.mean(timings), 3),
        "runtime_ms_min": round(min(timings), 3),
        "runtime_ms_max": round(max(timings), 3),
        "clocks_per_sec_p50": round(len(clock_nodes) / (pct(timings, 50) / 1000), 1),
        "workload": "mixed-state" if mixed else "historical-all-green",
        "status_counts": dict(Counter(last_statuses)),
        "deterministic_output_match": [response.model_dump(mode="json") for response in last_responses] == [response.model_dump(mode="json") for response in verification],
    }


def run_sweep() -> dict[str, object]:
    """Measure the real local CronService sweep over the repository fixture."""
    repo = InMemoryBackendRepository(reference_time=datetime(2026, 1, 1, tzinfo=timezone.utc))
    service = CronService(repo, AuditService(repo))
    service.run_deadline_sweep()  # warm-up; it also proves the path is callable
    start = time.perf_counter()
    result = service.run_deadline_sweep()
    result["cases_per_sec"] = round(result["cases_scanned"] / (result["duration_ms"] / 1000), 1) if result["duration_ms"] else 0
    result["clocks_per_sec"] = round(result["clocks_evaluated"] / (result["duration_ms"] / 1000), 1) if result["duration_ms"] else 0
    result["wall_runtime_ms"] = round((time.perf_counter() - start) * 1000, 3)
    return result


def run_local_api(repeats: int = 100) -> dict[str, object]:
    """Measure the real FastAPI app against its in-memory repository fixture."""
    repo = InMemoryBackendRepository(reference_time=datetime(2026, 1, 1, tzinfo=timezone.utc))
    case_id = repo.case_ids[0]
    app = create_app(repository=repo)
    requests = {
        "worklist": ("/worklist", {"X-Dev-Role": "IO"}),
        "case_detail": (f"/cases/{case_id}", {"X-Dev-Role": "IO"}),
        "similar_cases": (f"/api/v1/graph/cases/{case_id}/similar", {"X-Dev-Role": "IO"}),
        "network": (f"/api/v1/graph/cases/{case_id}/network", {"X-Dev-Role": "IO"}),
        "deadline_monitor": ("/api/v1/system/deadline-monitor/status", {"X-Dev-Role": "IO"}),
    }
    results: dict[str, object] = {}
    with TestClient(app, raise_server_exceptions=False) as client:
        for name, (path, headers) in requests.items():
            for _ in range(5):
                client.get(path, headers=headers)
            timings: list[float] = []
            successes = 0
            for _ in range(repeats):
                start = time.perf_counter()
                response = client.get(path, headers=headers)
                timings.append((time.perf_counter() - start) * 1000)
                successes += response.is_success
            results[name] = {
                "requests": repeats,
                "success_rate": round(successes / repeats, 4),
                "p50_ms": round(pct(timings, 50), 3),
                "p95_ms": round(pct(timings, 95), 3),
                "mean_ms": round(statistics.mean(timings), 3),
                "min_ms": round(min(timings), 3),
                "max_ms": round(max(timings), 3),
                "requests_per_sec_p50": round(repeats / (sum(timings) / 1000), 1),
            }
    return results


def run_graph(repeats: int = 200) -> dict[str, object]:
    """Measure graph network latency at the fixed 4,000-case scale."""
    assembly = generate_synthetic_graph(SyntheticDataConfig(
        seed=42,
        case_count=4000,
        person_count=8000,
        officer_count=1000,
        evidence_count=8000,
        dependency_count=2000,
    ))
    graph = GraphLoader().load_graph(
        nodes=[NodeRecord(node_id=str(n.id), entity_type=n.entity_type.value, properties=n.properties) for n in assembly.dataset.nodes],
        edges=[AdjEdge(source_id=str(e.source_id), target_id=str(e.target_id), edge_type=e.edge_type.value, properties=e.properties) for e in assembly.dataset.edges],
    )
    service = GraphService(GraphRepository(graph))
    case_id = next(node_id for node_id, node in graph.nodes.items() if node.entity_type == "Case")
    result: dict[str, object] = {
        "cases": len(assembly.case_blueprints),
        "nodes": len(graph.nodes),
        "edges": sum(len(edges) for edges in graph.edge_index.values()),
        "queries": repeats,
    }
    for depth in (1, 2):
        for _ in range(10):
            service.get_case_network(case_id, depth=depth)
        timings: list[float] = []
        for _ in range(repeats):
            start = time.perf_counter()
            service.get_case_network(case_id, depth=depth)
            timings.append((time.perf_counter() - start) * 1000)
        result[f"depth_{depth}"] = {
            "p50_ms": round(pct(timings, 50), 3),
            "p95_ms": round(pct(timings, 95), 3),
            "mean_ms": round(statistics.mean(timings), 3),
            "min_ms": round(min(timings), 3),
            "max_ms": round(max(timings), 3),
            "queries_per_sec_p50": round(1000 / pct(timings, 50), 1),
        }
    return result


def main() -> None:
    historical = [run_size(size) for size in (100, 500, 1000, 5000)]
    mixed = [run_size(size, mixed=True) for size in (100, 500, 1000, 5000)]
    payload = {
        "environment": {
            "os": platform.platform(),
            "python": sys.version.split()[0],
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        },
        "dataset": "SyntheticDataConfig(seed=42), generated in memory; no production data modified.",
        "results": historical,
        "mixed_state_results": mixed,
        "autonomous_sweep": run_sweep(),
        "local_api": run_local_api(),
        "graph_network": run_graph(),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
