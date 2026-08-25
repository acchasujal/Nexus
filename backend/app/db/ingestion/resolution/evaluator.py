"""Ground-truth evaluation for identity links."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def evaluate_ground_truth(
    ground_truth_path: str | Path,
    record_to_person_map: dict[str, str],
    reviews: Iterable[Any] = (),
) -> dict[str, Any]:
    """Calculate precision, recall, F1, and error counts from ground truth CSV.
    
    Pairs are treated as unordered. MATCHED means predicted positive.
    NOT_MATCHED means predicted negative. REVIEW_REQUIRED is not an automatic positive.
    """
    path = Path(ground_truth_path)
    if not path.exists():
        return {"evaluated": False, "reason": "ground-truth fixture unavailable"}

    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    true_positives = 0
    true_negatives = 0
    false_positives = []
    false_negatives = []

    for row in rows:
        a_id = row["record_a_id"].strip()
        b_id = row["record_b_id"].strip()
        expected = str(row["expected_same_entity"]).strip().lower() in {"true", "1", "yes"}
        
        # Check if they map to the exact same canonical person ID
        p_a = record_to_person_map.get(a_id)
        p_b = record_to_person_map.get(b_id)
        
        predicted = (p_a == p_b) and (p_a is not None)

        pair_tuple = tuple(sorted((a_id, b_id)))
        
        if expected and predicted:
            true_positives += 1
        elif not expected and not predicted:
            true_negatives += 1
        elif not expected and predicted:
            false_positives.append(pair_tuple)
        elif expected and not predicted:
            false_negatives.append(pair_tuple)

    tp = true_positives
    fp = len(false_positives)
    fn = len(false_negatives)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    review_list = list(reviews)
    auto_count = sum(getattr(r, "auto_link_allowed", False) for r in review_list)
    review_count = sum(getattr(r, "requires_human_review", False) for r in review_list)

    return {
        "evaluated": True,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "true_positives": tp,
        "true_negatives": true_negatives,
        "false_positives": fp,
        "false_negatives": fn,
        "false_positive_pairs": false_positives,
        "false_negative_pairs": false_negatives,
        "automatic_link_count": auto_count,
        "review_required_count": review_count,
    }


__all__ = ["evaluate_ground_truth"]
