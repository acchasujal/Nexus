#!/usr/bin/env python3
"""scripts/migrate_to_postgres.py

Transfers all NEXUS data (Nodes, Edges, Source Records, Cases, Evidence)
from synthetic graph artifacts to the Render PostgreSQL database.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import psycopg
from psycopg.types.json import Jsonb

DEFAULT_PG_URL = (
    "postgresql://nexus_7pdz_user:7iOMrcTqT4HNbyc8fclDuOkUeuVgtZeL"
    "@dpg-da99ipss728c73d4cjrg-a.singapore-postgres.render.com/nexus_7pdz"
)


def run_migration(db_url: str | None = None) -> int:
    url = db_url or os.environ.get("DATABASE_URL") or DEFAULT_PG_URL
    print("=" * 70)
    print("  NEXUS PostgreSQL Database Migration (Render)")
    print("=" * 70)
    print(f"[1/4] Connecting to PostgreSQL at: {url.split('@')[-1] if '@' in url else '***'}...")

    try:
        conn = psycopg.connect(url, connect_timeout=15)
    except Exception as exc:
        print(f"[-] Database connection failed: {exc}")
        return 1

    with conn:
        with conn.cursor() as cur:
            # 1. Apply Schema DDL
            print("[2/4] Applying database schema (tables, indexes, constraints)...")
            schema_path = root_dir / "backend" / "app" / "db" / "schema.sql"
            if not schema_path.exists():
                print(f"[-] Schema file missing: {schema_path}")
                return 1
            cur.execute(schema_path.read_text(encoding="utf-8"))

            # 2. Load Artifact Data
            print("[3/4] Loading artifact dataset from artifacts/nexus_graph/nexus_graph.json...")
            artifact_path = root_dir / "artifacts" / "nexus_graph" / "nexus_graph.json"
            if not artifact_path.exists():
                artifact_path = root_dir / "backend" / "app" / "db" / "synthetic_graph.json"

            with open(artifact_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)

            raw_nodes = raw_data.get("nodes", [])
            raw_edges = raw_data.get("edges", [])

            print(f"      Found {len(raw_nodes)} nodes and {len(raw_edges)} edges to transfer.")

            # Insert Nodes (UPSERT)
            print("      Transferring nodes to 'nodes' table...")
            node_tuples = [
                (
                    str(node["id"]),
                    str(node.get("entity_type", "Unknown")),
                    Jsonb(node.get("properties", {})),
                )
                for node in raw_nodes
            ]
            cur.executemany(
                """
                INSERT INTO nodes (id, entity_type, properties, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    entity_type = EXCLUDED.entity_type,
                    properties = EXCLUDED.properties,
                    updated_at = NOW();
                """,
                node_tuples,
            )

            # Insert Edges (UPSERT)
            print("      Transferring edges to 'edges' table...")
            edge_tuples = [
                (
                    str(edge.get("id", f"{edge['source_id']}-{edge['target_id']}")),
                    str(edge["source_id"]),
                    str(edge["target_id"]),
                    str(edge.get("edge_type", "LINKED_TO")),
                    float(edge.get("weight", 1.0)),
                    edge.get("start_time"),
                    edge.get("end_time"),
                    edge.get("source_record_id"),
                    edge.get("derivation_class"),
                    float(edge.get("confidence", 1.0)),
                    Jsonb(edge.get("provenance", {})),
                    Jsonb(edge.get("properties", {})),
                )
                for edge in raw_edges
            ]
            cur.executemany(
                """
                INSERT INTO edges (
                    id, source_id, target_id, edge_type, weight,
                    start_time, end_time, source_record_id, derivation_class,
                    confidence, provenance, properties
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    source_id = EXCLUDED.source_id,
                    target_id = EXCLUDED.target_id,
                    edge_type = EXCLUDED.edge_type,
                    weight = EXCLUDED.weight,
                    start_time = EXCLUDED.start_time,
                    end_time = EXCLUDED.end_time,
                    source_record_id = EXCLUDED.source_record_id,
                    derivation_class = EXCLUDED.derivation_class,
                    confidence = EXCLUDED.confidence,
                    provenance = EXCLUDED.provenance,
                    properties = EXCLUDED.properties;
                """,
                edge_tuples,
            )

            # Seed system metadata
            metadata_val = Jsonb({"version": "1.0.0", "seeded_nodes": len(raw_nodes), "seeded_edges": len(raw_edges)})
            cur.execute(
                """
                INSERT INTO system_metadata (key, value, updated_at)
                VALUES ('migration_version', %s, NOW())
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW();
                """,
                (metadata_val,),
            )

            # 3. Verify Counts
            print("[4/4] Verifying database row counts...")
            cur.execute("SELECT COUNT(*) FROM nodes;")
            node_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM edges;")
            edge_count = cur.fetchone()[0]
            cur.execute("SELECT entity_type, COUNT(*) FROM nodes GROUP BY entity_type ORDER BY COUNT(*) DESC;")
            entity_breakdown = cur.fetchall()

    conn.close()

    print("\n" + "-" * 70)
    print("  [✔] PostgreSQL Migration COMPLETED Successfully!")
    print(f"      Total Nodes in PostgreSQL: {node_count}")
    print(f"      Total Edges in PostgreSQL: {edge_count}")
    print("      Entity Breakdown:")
    for etype, count in entity_breakdown:
        print(f"        • {etype}: {count}")
    print("-" * 70)
    return 0


if __name__ == "__main__":
    db_arg = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_migration(db_arg))
