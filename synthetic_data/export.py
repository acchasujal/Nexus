"""Export helpers for synthetic graph data."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from synthetic_data.configs import SyntheticGraphDataset, _serialize_value


def export_json(dataset: SyntheticGraphDataset, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": dataset.seed,
        "generated_at": dataset.generated_at.isoformat(),
        "metadata": _serialize_value(dataset.metadata),
        "nodes": [node.to_flat_row() for node in dataset.nodes],
        "edges": [edge.to_flat_row() for edge in dataset.edges],
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


def export_csv(dataset: SyntheticGraphDataset, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    nodes_path = output_dir / "nodes.csv"
    edges_path = output_dir / "edges.csv"
    _write_csv(nodes_path, [node.to_flat_row() for node in dataset.nodes])
    _write_csv(edges_path, [edge.to_flat_row() for edge in dataset.edges])
    return nodes_path, edges_path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key in seen:
                continue
            seen.add(key)
            fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _serialize_value(row.get(key, "")) for key in fieldnames})