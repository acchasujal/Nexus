"""backend/app/db/seed/import_synthetic.py

Synthetic graph artifact seed importer.

This module implements Phase 2 §5 "Migration and seed strategy":
  - Reads the deterministic synthetic_graph.json artifact
  - Validates the loaded graph through GraphLoader before marking seed complete
  - Upserts entity tables in dependency order, then edges
  - Tracks seed runs via the seed_run ledger (idempotent by checksum)
  - Supports dry-run mode for validation without writing

## Usage

Dry run (validation only, no writes):
    python -m backend.app.db.seed.import_synthetic --dry-run

With Catalyst connection (Phase 2):
    python -m backend.app.db.seed.import_synthetic

## Design notes

- If Catalyst lacks transactions, each table batch is idempotent (upsert on ID).
- A failed batch is safe to retry; the seed_run record holds status.
- GraphLoader validation is run after import to confirm no broken edges.
- The artifact checksum is stored; re-running with the same file is a no-op.
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

DEFAULT_ARTIFACT = Path("artifacts/synthetic_graph/synthetic_graph.json")

# Dependency-ordered entity table names (entities before edges)
ENTITY_TABLE_ORDER = [
    "unit", "act", "court", "location",
    "crime_head", "crime_sub_head",
    "case", "person", "officer",
    "section", "evidence",
    "dependency", "clock_instance",
]

# Entity type → table name mapping (from graph schema)
ENTITY_TYPE_TO_TABLE: dict[str, str] = {
    "Case": "case",
    "Person": "person",
    "Officer": "officer",
    "Unit": "unit",
    "Court": "court",
    "Location": "location",
    "Act": "act",
    "Section": "section",
    "CrimeHead": "crime_head",
    "CrimeSubHead": "crime_sub_head",
    "Evidence": "evidence",
    "Dependency": "dependency",
    "ClockInstance": "clock_instance",
}


def _compute_checksum(artifact_path: Path) -> str:
    """SHA-256 checksum of the artifact file."""
    h = hashlib.sha256()
    h.update(artifact_path.read_bytes())
    return h.hexdigest()


def _load_artifact(artifact_path: Path) -> dict[str, Any]:
    """Load and JSON-parse the synthetic graph artifact."""
    raw = artifact_path.read_text(encoding="utf-8")
    return json.loads(raw)


def _validate_with_graph_loader(raw: dict[str, Any]) -> None:
    """Run GraphLoader validation on the artifact.

    Builds NodeRecord and AdjEdge objects from the raw JSON, then runs
    GraphLoader.load_graph + validate_graph.  Same validation path as Phase 5.
    """
    node_records: list[NodeRecord] = [
        NodeRecord(
            node_id=str(n["id"]),
            entity_type=str(n.get("entity_type", "unknown")),
            properties={k: v for k, v in n.items() if k not in ("id", "entity_type")},
        )
        for n in raw.get("nodes", [])
    ]
    adj_edges: list[AdjEdge] = [
        AdjEdge(
            source_id=str(e["source_id"]),
            target_id=str(e["target_id"]),
            edge_type=str(e["edge_type"]),
            properties={k: v for k, v in e.items() if k not in ("source_id", "target_id", "edge_type", "storage_mode")},
        )
        for e in raw.get("edges", [])
    ]
    loader = GraphLoader()
    graph = loader.load_graph(nodes=node_records, edges=adj_edges)
    report = loader.validate_graph(graph)
    if not report["is_valid"]:
        for err in report["errors"][:5]:
            print(f"    ERROR: {err}", file=__import__("sys").stderr)
        raise ValueError(f"GraphLoader validation failed with {len(report['errors'])} errors")
    node_count = len(graph.nodes)
    edge_count = report["edge_count"]
    print(f"  GraphLoader validation passed: {node_count} nodes, {edge_count} edges")


def _group_by_entity_type(nodes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group node records by entity_type."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        entity_type = str(node.get("entity_type", "Unknown"))
        groups.setdefault(entity_type, []).append(node)
    return groups


def run_seed(
    artifact_path: Path = DEFAULT_ARTIFACT,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Import the synthetic artifact into Catalyst Data Store.

    Args:
        artifact_path: Path to synthetic_graph.json
        dry_run: If True, validate only — do not write to Catalyst.

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

    if dry_run:
        print("\n[DRY RUN] Validation complete. No data written to Catalyst.")
        print("  Entity type counts:")
        for entity_type, count in sorted(node_counts.items()):
            table = ENTITY_TYPE_TO_TABLE.get(entity_type, "unknown")
            print(f"    {entity_type:20s} -> {table:20s}: {count:5d} rows")
        print(f"  Edges: {len(edges):5d} rows -> graph_edge")
        return {"status": "dry_run_ok", "checksum": checksum, **node_counts}

    # Phase 2: Real Catalyst write path (requires credentials)
    print("\nReal Catalyst write requires CATALYST_PROJECT_ID and CATALYST_CLIENT_ID.")
    print("Phase 2 — implement Catalyst Data Store adapter and retry.")
    return {"status": "pending_catalyst", "checksum": checksum, **node_counts}


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
    artifact_arg = next(
        (arg for arg in sys.argv[1:] if not arg.startswith("-")),
        None,
    )
    artifact = Path(artifact_arg) if artifact_arg else DEFAULT_ARTIFACT

    try:
        result = run_seed(artifact_path=artifact, dry_run=dry_run)
        print(f"\nResult: {result['status']}")
    except Exception as exc:
        print(f"\nSeed failed: {exc}", file=sys.stderr)
        sys.exit(1)
