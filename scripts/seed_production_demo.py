"""scripts/seed_production_demo.py

NEXUS Production Demo Data Seeder (SIH 2026 PS 26189).
Safely loads synthetic cases, accused records, telecom CDRs, financial transaction logs,
and evidence provenance chains into the active persistent repository (PostgreSQL / Neo4j / In-Memory).

Usage:
    python scripts/seed_production_demo.py [--dry-run] [--artifact PATH]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure root workspace is on sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.db.seed.import_synthetic import run_seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed NEXUS synthetic demo dataset.")
    parser.add_argument("--dry-run", action="store_true", help="Validate dataset without writing.")
    parser.add_argument(
        "--artifact",
        type=Path,
        default=_ROOT / "artifacts" / "nexus_graph" / "nexus_graph.json",
        help="Path to synthetic graph artifact JSON file.",
    )
    args = parser.parse_args()

    artifact_path: Path = args.artifact
    if not artifact_path.exists():
        # Fallback to local db resource if available
        fallback = _ROOT / "backend" / "app" / "db" / "synthetic_graph.json"
        if fallback.exists():
            artifact_path = fallback
        else:
            logger.error("Synthetic graph artifact not found at %s or fallback %s", artifact_path, fallback)
            return 1

    logger.info("Initializing NEXUS Seed Importer (dry_run=%s)", args.dry_run)
    logger.info("Target Artifact: %s", artifact_path)

    try:
        summary = run_seed(artifact_path=artifact_path, dry_run=args.dry_run)
        logger.info("Artifact validation successful: Checksum=%s", summary.get("checksum", "unknown")[:16])

        if not args.dry_run:
            logger.info("Hydrating in-memory backend repository...")
            repo = InMemoryBackendRepository(artifact_path=artifact_path)
            logger.info(
                "Repository initialized: %d nodes, %d edges, %d cases",
                len(repo.nodes),
                len(repo.edges),
                len(repo.case_ids),
            )

        print("\n" + "=" * 60)
        print("  NEXUS Production Demo Seeder: COMPLETE")
        print("=" * 60)
        print(json.dumps(summary, indent=2))
        return 0

    except Exception as exc:
        logger.error("Production demo seeding failed: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
