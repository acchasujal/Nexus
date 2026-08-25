"""Command-line runner for the additive synthetic CSV ingestion trial."""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from backend.app.core.graph.algorithms.pattern_rules import (
    detect_all_suspicious_patterns,
)
from backend.app.core.graph.edges import GraphEdge

from .graph_adapter import validate_graph_references
from .pipeline import CsvIngestionPipeline

OUTPUT_FILES = (
    "ingestion_summary.json",
    "normalized_nodes.json",
    "normalized_relationships.json",
    "entity_review_candidates.json",
    "rejected_rows.json",
    "evaluation_metrics.json",
)


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _validate_models(bundle: Any) -> list[str]:
    errors: list[str] = []
    for node in bundle.nodes:
        try:
            type(node).model_validate(node.model_dump())
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"node {node.id}: {exc}")
    for edge in bundle.relationships:
        try:
            GraphEdge.model_validate(edge.model_dump())
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"relationship {edge.id}: {exc}")
    return errors


def _provenance_percentage(bundle: Any) -> float:
    factual = [edge for edge in bundle.relationships if edge.derivation_class.value == "FACT"]
    if not factual:
        return 100.0
    source_ids = {record.id for record in bundle.source_records}
    complete = sum(1 for edge in factual if edge.source_record_id in source_ids)
    return round(complete * 100.0 / len(factual), 2)


def _evaluation_metrics(input_dir: Path) -> dict[str, Any]:
    """Return metrics only when a compatible ground-truth CSV is available."""
    ground_truth = input_dir / "entity_resolution_ground_truth.csv"
    if not ground_truth.exists():
        return {"evaluated": False, "reason": "ground-truth fixture unavailable", "precision": 0.0, "recall": 0.0, "f1": 0.0, "false_positives": 0, "false_negatives": 0}
    rows = list(csv.DictReader(ground_truth.read_text(encoding="utf-8-sig").splitlines()))
    positives = sum(str(row.get("expected_same_entity", "")).strip().lower() in {"true", "1", "yes"} for row in rows)
    negatives = len(rows) - positives
    return {"evaluated": False, "reason": "ground-truth pairs require approved canonical-link predictions", "positive_pairs": positives, "negative_pairs": negatives, "precision": 0.0, "recall": 0.0, "f1": 0.0, "false_positives": 0, "false_negatives": positives}


def run_trial(input_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Run the trial and write artifacts only below ``output_dir``."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    pipeline = CsvIngestionPipeline()
    bundle = pipeline.ingest_directory(input_path)
    model_errors = _validate_models(bundle)
    reference_errors = validate_graph_references(bundle.nodes, bundle.relationships, bundle.source_records)
    all_errors = sorted(model_errors + reference_errors)
    if all_errors:
        raise ValueError("Schema/provenance validation failed: " + "; ".join(all_errors))
    findings = detect_all_suspicious_patterns(pipeline.graph_store)
    metrics = _evaluation_metrics(input_path)
    summary = {
        **bundle.summary.model_dump(mode="json"),
        "provenance_completeness_percent": _provenance_percentage(bundle),
        "auto_linked_identities": sum(1 for candidate in bundle.review_candidates if candidate.auto_link_allowed),
        "review_required_identities": sum(1 for candidate in bundle.review_candidates if candidate.requires_human_review),
        "pattern_finding_count": len(findings),
        "schema_validation_errors": [],
        "graph_store_node_count": len(pipeline.graph_store.nodes),
        "graph_store_relationship_count": sum(len(edges) for edges in pipeline.graph_store.edge_index.values()),
    }
    artifacts = {
        "ingestion_summary.json": summary,
        "normalized_nodes.json": [_json_value(node) for node in bundle.nodes],
        "normalized_relationships.json": [_json_value(edge) for edge in bundle.relationships],
        "entity_review_candidates.json": [_json_value(candidate) for candidate in bundle.review_candidates],
        "rejected_rows.json": [_json_value(issue) for issue in bundle.issues if issue.severity.value == "ERROR"],
        "evaluation_metrics.json": metrics,
    }
    for filename, payload in artifacts.items():
        (output_path / filename).write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"rows received: {summary['received_count']}")
    print(f"accepted: {summary['accepted_count']}")
    print(f"duplicates: {summary['duplicate_count']}")
    print(f"rejected: {summary['rejected_count']}")
    print(f"nodes created/reused: {summary['node_created_count']}/{summary['node_reused_count']}")
    print(f"relationships: {summary['relationship_created_count']}")
    print(f"SourceRecords: {summary['source_record_count']}")
    print(f"provenance completeness: {summary['provenance_completeness_percent']}%")
    print(f"auto-linked identities: {summary['auto_linked_identities']}")
    print(f"review-required identities: {summary['review_required_identities']}")
    print(f"precision/recall/F1: {metrics['precision']}/{metrics['recall']}/{metrics['f1']}")
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line trial."""
    parser = argparse.ArgumentParser(description="Run the NEXUS synthetic CSV ingestion trial")
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    run_trial(args.input_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
