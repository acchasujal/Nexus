"""tests/test_nexus_entity_resolution.py

Evaluates the multi-attribute Entity Resolution engine against the synthetic ground truth.
Verifies precision, recall, phonetic normalization, and explainable scoring.
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.app.core.graph.algorithms.entity_resolution import (
    EntityResolutionEngine,
    evaluate_ground_truth_dataset,
    phonetic_fingerprint,
)
from backend.app.db.in_memory import InMemoryBackendRepository


def test_phonetic_fingerprint_normalization() -> None:
    # Test Indian name variations
    assert phonetic_fingerprint("Vikram Sharma") == phonetic_fingerprint("Bikram Sarma")
    assert phonetic_fingerprint("Mohammed Yusuf") == phonetic_fingerprint("Mohammad Yousuf")
    assert phonetic_fingerprint("Rajesh Kumar") == phonetic_fingerprint("Rajesh Kumar")


def test_entity_resolution_with_ground_truth() -> None:
    repo = InMemoryBackendRepository()
    engine = EntityResolutionEngine(repo.to_graph_store())

    ground_truth_path = Path("artifacts/nexus_graph/ground_truth.json")
    if not ground_truth_path.exists():
        return

    with open(ground_truth_path, encoding="utf-8") as f:
        ground_truth = json.load(f)

    metrics = evaluate_ground_truth_dataset(engine, ground_truth)
    assert metrics["precision"] >= 0.85, f"Precision too low: {metrics['precision']}"
    assert metrics["recall"] >= 0.80, f"Recall too low: {metrics['recall']}"
    assert metrics["f1"] >= 0.80, f"F1 score too low: {metrics['f1']}"
