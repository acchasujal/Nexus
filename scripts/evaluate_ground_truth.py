"""scripts/evaluate_ground_truth.py

Precision and Recall evaluator for NEXUS Entity Resolution & Graph Intelligence.
Loads the synthetic dataset and evaluates against ground truth planted associations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.core.graph.algorithms.entity_resolution import (
    EntityResolutionEngine,
    evaluate_ground_truth_dataset,
)
from backend.app.db.in_memory import InMemoryBackendRepository


def main() -> int:
    print("=" * 70)
    print("  NEXUS Ground Truth Evaluation (SIH 2026 PS 26189)")
    print("=" * 70)

    repo = InMemoryBackendRepository()
    engine = EntityResolutionEngine(repo.to_graph_store())

    ground_truth_path = Path("artifacts/nexus_graph/ground_truth.json")
    if not ground_truth_path.exists():
        print(f"Error: Ground truth file not found at {ground_truth_path}")
        return 1

    with open(ground_truth_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    metrics = evaluate_ground_truth_dataset(engine, ground_truth)

    print("\n[Entity Resolution Evaluation Results]")
    print(f"  Total True Positives:  {metrics['true_positives']}")
    print(f"  Total False Positives: {metrics['false_positives']}")
    print(f"  Total False Negatives: {metrics['false_negatives']}")
    print(f"  Precision:             {metrics['precision'] * 100:.2f}%")
    print(f"  Recall:                {metrics['recall'] * 100:.2f}%")
    print(f"  F1 Score:              {metrics['f1_score'] * 100:.2f}%")

    if metrics["precision"] >= 0.85 and metrics["recall"] >= 0.80:
        print("\n>> Ground Truth Benchmark PASSED: Engine meets high-accuracy criteria.")
        return 0
    else:
        print("\n>> Ground Truth Benchmark FAILED: Below target accuracy threshold.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
