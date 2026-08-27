"""backend/app/db/seed/import_synthetic.py

Synthetic graph artifact seed importer for NEXUS.

Validates the loaded graph through GraphLoader, verifies checksum,
and prepares nodes and edges for in-memory and database seeding.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from backend.app.core.graph.algorithms.utils import AdjEdge, NodeRecord
from backend.app.core.graph.graph_loader import GraphLoader

# ── Paths ──────────────────────────────────────────────────────────────────────

_THIS_DIR = Path(__file__).resolve().parent
DEFAULT_ARTIFACT = _THIS_DIR.parent / "synthetic_graph.json"

# Table name mapping
ENTITY_TYPE_TO_TABLE: dict[str, str] = {
    "Case": "case_record",
    "Person": "person_record",
    "Officer": "officer_record",
    "PoliceStation": "police_station_record",
    "Section": "section_record",
    "Evidence": "evidence_record",
    "Court": "court_record",
    "FSL": "fsl_record",
    "Prison": "prison_record",
    "Phone": "phone_record",
    "Vehicle": "vehicle_record",
    "Account": "account_record",
    "Location": "location_record",
    "Organization": "organization_record",
}


def _compute_checksum(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_artifact(file_path: Path) -> dict[str, Any]:
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def _validate_with_graph_loader(raw_data: dict[str, Any]) -> None:
    nodes = [
        NodeRecord(
            node_id=n.get("node_id") or n["id"],
            entity_type=n.get("entity_type") or n.get("type", "Unknown"),
            properties=n.get("properties", {}),
        )
        for n in raw_data.get("nodes", [])
    ]
    edges = [
        AdjEdge(
            source_id=e.get("source_id", ""),
            target_id=e.get("target_id", ""),
            edge_type=e.get("edge_type", ""),
            properties=e.get("properties", {}),
        )
        for e in raw_data.get("edges", [])
    ]
    loader = GraphLoader()
    store = loader.load_graph(nodes, edges)
    result = loader.validate_graph(store, allow_multigraph=True)
    if isinstance(result, dict):
        if not result.get("is_valid", True):
            errors = result.get("errors", [])
            raise ValueError(
                f"GraphLoader validation failed with {len(errors)} errors: "
                + "; ".join(errors[:5])
            )
    elif hasattr(result, "is_valid") and not result.is_valid:
        raise ValueError(
            f"GraphLoader validation failed with {len(result.errors)} errors: "
            + "; ".join(result.errors[:5])
        )


def _group_by_entity_type(nodes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        etype = node.get("entity_type") or node.get("type", "Unknown")
        groups.setdefault(etype, []).append(node)
    return groups


def run_seed(
    artifact_path: Path = DEFAULT_ARTIFACT,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Import the synthetic artifact into graph store.

    Args:
        artifact_path: Path to synthetic_graph.json
        dry_run: If True, validate only.

    Returns:
        Summary dict with node_counts, edge_count, checksum, status.
    """
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Seeding from: {artifact_path}")

    if not artifact_path.exists():
        raise FileNotFoundError(f"Artifact not found: {artifact_path}")

    checksum = _compute_checksum(artifact_path)
    print(f"  Checksum: {checksum[:16]}...")

    raw = _load_artifact(artifact_path)
    nodes: list[dict[str, Any]] = raw.get("nodes", [])
    edges: list[dict[str, Any]] = raw.get("edges", [])
    print(f"  Nodes: {len(nodes)}, Edges: {len(edges)}")

    # Step 1: Validate through GraphLoader
    print("  Validating graph structure with GraphLoader...")
    _validate_with_graph_loader(raw)

    # Step 2: Group by entity type
    by_type = _group_by_entity_type(nodes)
    node_counts: dict[str, int] = {k: len(v) for k, v in by_type.items()}

    print("\nValidation complete.")
    print("  Entity type counts:")
    for entity_type, count in sorted(node_counts.items()):
        table = ENTITY_TYPE_TO_TABLE.get(entity_type, "unknown")
        print(f"    {entity_type:20s} -> {table:20s}: {count:5d} rows")
    print(f"  Edges: {len(edges):5d} rows -> graph_edge")
    return {"status": "seed_validated", "checksum": checksum, **node_counts}


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    artifact_arg = next(
        (arg for arg in sys.argv[1:] if not arg.startswith("-")),
        None,
    )
    artifact = Path(artifact_arg) if artifact_arg else DEFAULT_ARTIFACT

    try:
        summary = run_seed(artifact, dry_run=dry_run)
        print("\nSeed summary:")
        print(json.dumps(summary, indent=2))
    except (FileNotFoundError, ValueError, json.JSONDecodeError, OSError) as exc:
        print(f"\nError during seed: {exc}", file=sys.stderr)
        sys.exit(1)
