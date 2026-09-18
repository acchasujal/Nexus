#!/usr/bin/env python3
"""scripts/migrate_to_neo4j.py

Connects to Neo4j, initializes constraints & indexes, and migrates
all NEXUS graph entities (Cases, Persons, Phones, Accounts, Evidence)
and relationships into Neo4j using the project's native projection engine.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parents[1]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from pydantic import SecretStr
from backend.app.config import Settings
from backend.app.db.neo4j import Neo4jConnection


async def run_migration(
    uri: str | None = None,
    user: str | None = None,
    password: str | None = None,
    database: str = "neo4j",
    clear_first: bool = False,
) -> int:
    print("=" * 70)
    print("  NEXUS Neo4j Graph Database Migration & Verification")
    print("=" * 70)

    neo4j_uri = uri or os.environ.get("NEO4J_URI") or ""
    neo4j_user = user or os.environ.get("NEO4J_USER") or "neo4j"
    neo4j_password = password or os.environ.get("NEO4J_PASSWORD") or ""
    neo4j_database = database or os.environ.get("NEO4J_DATABASE") or "neo4j"

    if not neo4j_uri or not neo4j_password:
        print("[-] Error: Neo4j connection parameters missing!")
        print("    Please provide NEO4J_URI and NEO4J_PASSWORD via:")
        print("    1. CLI args: --uri <uri> --user <user> --password <pass>")
        print("    2. Environment variables: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        print("    3. In .env file")
        print("")
        print("Example URI:")
        print("  - Neo4j AuraDB (Cloud): neo4j+s://xxxxxxxx.databases.neo4j.io")
        print("  - Local Neo4j:          bolt://localhost:7687")
        return 1

    settings = Settings(
        graph_backend="neo4j",
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=SecretStr(neo4j_password),
        neo4j_database=neo4j_database,
        neo4j_connection_timeout=15.0,
        neo4j_query_timeout=30.0,
        neo4j_failure_policy="required",
    )

    print(f"[1/5] Connecting to Neo4j at: {neo4j_uri} (database: {neo4j_database})...")
    conn = Neo4jConnection(settings)
    try:
        await conn.start()
        is_ok = await conn.check(verify=True)
        if not is_ok:
            print("[-] Connectivity probe failed.")
            return 1
        print("[✔] Successfully connected to Neo4j instance!")
    except Exception as exc:
        print(f"[-] Connection failed: {exc}")
        return 1

    try:
        # 1. Clear if requested
        if clear_first:
            print("[2/5] Clearing existing Neo4j graph projection...")
            await conn.clear_projection()
        else:
            print("[2/5] Preserving existing data (upsert mode via UNWIND MERGE)...")

        # 2. Schema Constraints & Indexes
        print("[3/5] Applying schema constraints (nexus_node_id UNIQUE) and indexes...")
        await conn.ensure_schema()
        print("[✔] Schema constraints and indexes verified.")

        # 3. Load Dataset
        print("[4/5] Loading artifact dataset from artifacts/nexus_graph/nexus_graph.json...")
        artifact_path = root_dir / "artifacts" / "nexus_graph" / "nexus_graph.json"
        if not artifact_path.exists():
            artifact_path = root_dir / "backend" / "app" / "db" / "synthetic_graph.json"

        with open(artifact_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw_nodes = data.get("nodes", [])
        raw_edges = data.get("edges", [])
        print(f"      Found {len(raw_nodes)} nodes and {len(raw_edges)} edges to synchronize.")

        # 4. Synchronize Projection
        print("      Migrating nodes and edges into Neo4j...")
        await conn.sync_projection(raw_nodes, raw_edges)
        print("[✔] Graph projection synchronized.")

        # 5. Verification Queries
        print("[5/5] Running Cypher verification queries on Neo4j...")
        from neo4j import Query

        # Count nodes
        records, _, _ = await conn.driver.execute_query(
            Query("MATCH (n:NexusNode) RETURN count(n) AS node_count"),
            database_=neo4j_database,
            routing_="r",
        )
        node_count = records[0]["node_count"] if records else 0

        # Count edges
        records, _, _ = await conn.driver.execute_query(
            Query("MATCH ()-[r:CONNECTED_TO]->() RETURN count(r) AS edge_count"),
            database_=neo4j_database,
            routing_="r",
        )
        edge_count = records[0]["edge_count"] if records else 0

        # Entity breakdown
        records, _, _ = await conn.driver.execute_query(
            Query(
                "MATCH (n:NexusNode) "
                "RETURN n.entity_type AS etype, count(n) AS count "
                "ORDER BY count DESC"
            ),
            database_=neo4j_database,
            routing_="r",
        )
        breakdown = [(r["etype"], r["count"]) for r in records]

        # Relationship types
        records, _, _ = await conn.driver.execute_query(
            Query(
                "MATCH ()-[r:CONNECTED_TO]->() "
                "RETURN r.edge_type AS rtype, count(r) AS count "
                "ORDER BY count DESC"
            ),
            database_=neo4j_database,
            routing_="r",
        )
        edge_breakdown = [(r["rtype"], r["count"]) for r in records]

        print("\n" + "-" * 70)
        print("  [✔] Neo4j Migration & Verification COMPLETED Successfully!")
        print(f"      Total Nodes in Neo4j: {node_count}")
        print(f"      Total Relationships in Neo4j: {edge_count}")
        print("\n      Entity Breakdown:")
        for etype, count in breakdown:
            print(f"        • {etype}: {count}")
        print("\n      Relationship Breakdown:")
        for rtype, count in edge_breakdown:
            print(f"        • {rtype}: {count}")
        print("-" * 70)
        return 0

    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate NEXUS dataset to Neo4j")
    parser.add_argument("--uri", help="Neo4j connection URI (e.g. neo4j+s://... or bolt://localhost:7687)")
    parser.add_argument("--user", default="neo4j", help="Neo4j username (default: neo4j)")
    parser.add_argument("--password", help="Neo4j password")
    parser.add_argument("--database", default="neo4j", help="Neo4j database name (default: neo4j)")
    parser.add_argument("--clear", action="store_true", help="Clear existing graph in Neo4j before migrating")

    args = parser.parse_args()
    rc = asyncio.run(
        run_migration(
            uri=args.uri,
            user=args.user,
            password=args.password,
            database=args.database,
            clear_first=args.clear,
        )
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()
