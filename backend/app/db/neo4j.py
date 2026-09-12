"""Durable Neo4j graph projection and read-write integration layer for NEXUS.

Manages AsyncDriver lifecycle, schema constraints, parameterized Cypher batch writes,
graph reading, and operational gating. No fallback to in-memory graphs when Neo4j is active.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any

from backend.app.config import Settings
from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord

if TYPE_CHECKING:
    from neo4j import AsyncDriver

logger = logging.getLogger(__name__)


class Neo4jUnavailableError(RuntimeError):
    """Sanitized connection failure safe to surface during application startup."""


class Neo4jConnection:
    """One driver/pool per application lifespan (one app per worker process).

    Sessions/queries are asynchronous. Never create drivers per request or share
    them across event loops. A degraded connection reuses its pool on later probes.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._driver: AsyncDriver | None = None
        self.status = "disabled" if settings.graph_backend == "memory" else "not_started"
        self.is_operational = settings.graph_backend == "memory"

    @property
    def driver(self) -> AsyncDriver:
        if self._driver is None:
            raise Neo4jUnavailableError("Neo4j driver is not available")
        return self._driver

    async def start(self) -> None:
        if self._settings.graph_backend == "memory":
            self.is_operational = True
            return
        if self._driver is not None:
            raise RuntimeError("Neo4j connection already started")
        try:
            from neo4j import AsyncGraphDatabase

            self._driver = AsyncGraphDatabase.driver(
                self._settings.neo4j_uri,
                auth=(self._settings.neo4j_user, self._settings.neo4j_password.get_secret_value()),
                connection_timeout=self._settings.neo4j_connection_timeout,
                connection_acquisition_timeout=self._settings.neo4j_connection_timeout,
                max_transaction_retry_time=0,
                telemetry_disabled=True,
            )
            available = await self.check(verify=True)
        except asyncio.CancelledError:
            await self.close()
            raise
        except Exception:
            # Never log driver exceptions, URIs, settings or authentication payloads.
            self.status = "unavailable"
            self.is_operational = False
            available = False
        if not available and self._settings.neo4j_failure_policy == "required":
            await self.close()
            raise Neo4jUnavailableError("Required Neo4j connection is unavailable") from None

    async def check(self, *, verify: bool = False) -> bool:
        if self._settings.graph_backend == "memory":
            return True
        if self._driver is None:
            return False
        try:
            from neo4j import Query

            # Server query timeout plus a client deadline bounds connection/routing
            # and query execution, including a hung or unavailable dependency.
            deadline = 2 * self._settings.neo4j_connection_timeout + self._settings.neo4j_query_timeout
            async with asyncio.timeout(deadline):
                if verify:
                    await self._driver.verify_connectivity()
                records, _, _ = await self._driver.execute_query(
                    Query("RETURN 1 AS ok", timeout=self._settings.neo4j_query_timeout),
                    database_=self._settings.neo4j_database,
                    routing_="r",
                )
                if len(records) != 1 or records[0]["ok"] != 1:
                    raise Neo4jUnavailableError("Unexpected connectivity probe result")
            self.status = "connected"
            return True
        except asyncio.CancelledError:
            self.status = "unavailable"
            self.is_operational = False
            raise
        except Exception:
            self.status = "unavailable"
            self.is_operational = False
            logger.warning("Neo4j connectivity probe failed; connection unavailable")
            return False

    async def close(self) -> None:
        self.is_operational = False
        driver, self._driver = self._driver, None
        if driver is not None:
            try:
                await driver.close()
            except Exception:
                self.status = "cleanup_failed"
                logger.warning("Neo4j driver cleanup failed")
                return
        if self._settings.graph_backend == "neo4j" and self.status != "cleanup_failed":
            self.status = "closed"

    # ── Schema Initialization ────────────────────────────────────────────────

    async def ensure_schema(self) -> None:
        """Create uniqueness constraints and indexes idempotently."""
        if self._settings.graph_backend == "memory" or self._driver is None:
            return
        from neo4j import Query

        constraint_query = (
            "CREATE CONSTRAINT nexus_node_id IF NOT EXISTS "
            "FOR (n:NexusNode) REQUIRE n.id IS UNIQUE"
        )
        index_query = (
            "CREATE INDEX nexus_node_entity_type IF NOT EXISTS "
            "FOR (n:NexusNode) ON (n.entity_type)"
        )
        try:
            await self._driver.execute_query(
                Query(constraint_query, timeout=self._settings.neo4j_query_timeout),
                database_=self._settings.neo4j_database,
                routing_="w",
            )
            await self._driver.execute_query(
                Query(index_query, timeout=self._settings.neo4j_query_timeout),
                database_=self._settings.neo4j_database,
                routing_="w",
            )
            logger.info("Neo4j schema constraints and indexes verified.")
        except Exception as err:
            logger.warning("Failed to initialize Neo4j constraints: %s", err)
            raise

    # ── Batch Write / Projection Methods ─────────────────────────────────────

    async def sync_nodes(self, nodes: list[dict[str, Any]]) -> int:
        """Batch upsert nodes into Neo4j using UNWIND MERGE."""
        if not nodes or self._settings.graph_backend == "memory" or self._driver is None:
            return 0
        from neo4j import Query

        batch = []
        for n in nodes:
            nid = str(n.get("id", ""))
            if not nid:
                continue
            etype = str(n.get("entity_type", "Unknown"))
            props = n.get("properties", {})
            label = str(props.get("full_name") or props.get("name") or nid)
            case_ids = [str(c) for c in n.get("case_ids", [])]
            if not case_ids and props.get("case_id"):
                case_ids = [str(props["case_id"])]
            badges = [str(b) for b in n.get("badges", [])]
            props_json = json.dumps(props, default=str)

            batch.append({
                "id": nid,
                "entity_type": etype,
                "label": label,
                "case_ids": case_ids,
                "badges": badges,
                "properties_json": props_json,
            })

        cypher = (
            "UNWIND $batch AS row "
            "MERGE (n:NexusNode {id: row.id}) "
            "SET n.entity_type = row.entity_type, "
            "    n.label = row.label, "
            "    n.case_ids = row.case_ids, "
            "    n.badges = row.badges, "
            "    n.properties_json = row.properties_json"
        )
        await self._driver.execute_query(
            Query(cypher, timeout=self._settings.neo4j_query_timeout),
            parameters_={"batch": batch},
            database_=self._settings.neo4j_database,
            routing_="w",
        )
        return len(batch)

    async def sync_edges(self, edges: list[dict[str, Any]]) -> int:
        """Batch upsert edges into Neo4j using UNWIND MERGE."""
        if not edges or self._settings.graph_backend == "memory" or self._driver is None:
            return 0
        from neo4j import Query

        batch = []
        for e in edges:
            eid = str(e.get("id") or f"edge-{e.get('source_id')}-{e.get('target_id')}")
            src = str(e.get("source_id", ""))
            tgt = str(e.get("target_id", ""))
            if not src or not tgt:
                continue
            etype = str(e.get("edge_type", "CONNECTED_TO"))
            weight = float(e.get("weight", 1.0))
            confidence = float(e.get("confidence", 1.0))
            derivation = str(e.get("derivation_class", "FACT"))
            start_time = str(e.get("start_time") or "")
            end_time = str(e.get("end_time") or "")
            source_rec_id = str(e.get("source_record_id") or "")
            props = e.get("properties", {})
            props_json = json.dumps(props, default=str)

            batch.append({
                "id": eid,
                "source_id": src,
                "target_id": tgt,
                "edge_type": etype,
                "weight": weight,
                "confidence": confidence,
                "derivation_class": derivation,
                "start_time": start_time,
                "end_time": end_time,
                "source_record_id": source_rec_id,
                "properties_json": props_json,
            })

        cypher = (
            "UNWIND $batch AS row "
            "MATCH (src:NexusNode {id: row.source_id}) "
            "MATCH (tgt:NexusNode {id: row.target_id}) "
            "MERGE (src)-[r:CONNECTED_TO {id: row.id}]->(tgt) "
            "SET r.edge_type = row.edge_type, "
            "    r.weight = row.weight, "
            "    r.confidence = row.confidence, "
            "    r.derivation_class = row.derivation_class, "
            "    r.start_time = row.start_time, "
            "    r.end_time = row.end_time, "
            "    r.source_record_id = row.source_record_id, "
            "    r.properties_json = row.properties_json"
        )
        await self._driver.execute_query(
            Query(cypher, timeout=self._settings.neo4j_query_timeout),
            parameters_={"batch": batch},
            database_=self._settings.neo4j_database,
            routing_="w",
        )
        return len(batch)

    async def sync_projection(
        self,
        nodes: list[dict[str, Any]] | Any,
        edges: list[dict[str, Any]],
    ) -> None:
        """Synchronize complete graph projection to Neo4j and mark operational."""
        if self._settings.graph_backend == "memory":
            self.is_operational = True
            return
        node_list = list(nodes) if not isinstance(nodes, list) else nodes
        await self.sync_nodes(node_list)
        await self.sync_edges(edges)
        self.is_operational = True
        logger.info(
            "Neo4j projection synchronized: %d nodes, %d edges.",
            len(node_list),
            len(edges),
        )

    async def clear_projection(self) -> None:
        """Clear all nodes and relationships from the Neo4j database."""
        if self._settings.graph_backend == "memory" or self._driver is None:
            return
        from neo4j import Query

        cypher = "MATCH (n:NexusNode) DETACH DELETE n"
        await self._driver.execute_query(
            Query(cypher, timeout=self._settings.neo4j_query_timeout),
            database_=self._settings.neo4j_database,
            routing_="w",
        )
        logger.info("Neo4j projection cleared.")

    # ── Read Projection Methods ──────────────────────────────────────────────

    async def read_projection(self) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        """Read all NexusNodes and CONNECTED_TO relationships from Neo4j."""
        if self._settings.graph_backend == "memory" or self._driver is None:
            return {}, []
        from neo4j import Query

        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []

        node_cypher = (
            "MATCH (n:NexusNode) "
            "RETURN n.id AS id, n.entity_type AS entity_type, "
            "       n.label AS label, n.case_ids AS case_ids, "
            "       n.badges AS badges, n.properties_json AS properties_json"
        )
        records, _, _ = await self._driver.execute_query(
            Query(node_cypher, timeout=self._settings.neo4j_query_timeout),
            database_=self._settings.neo4j_database,
            routing_="r",
        )
        for r in records:
            nid = r["id"]
            props = {}
            if r["properties_json"]:
                try:
                    props = json.loads(r["properties_json"])
                except Exception:
                    props = {}
            nodes[nid] = {
                "id": nid,
                "entity_type": r["entity_type"] or "Unknown",
                "label": r["label"] or nid,
                "case_ids": list(r["case_ids"] or []),
                "badges": list(r["badges"] or []),
                "properties": props,
            }

        edge_cypher = (
            "MATCH (src:NexusNode)-[r:CONNECTED_TO]->(tgt:NexusNode) "
            "RETURN r.id AS id, src.id AS source_id, tgt.id AS target_id, "
            "       r.edge_type AS edge_type, r.weight AS weight, "
            "       r.confidence AS confidence, r.derivation_class AS derivation_class, "
            "       r.start_time AS start_time, r.end_time AS end_time, "
            "       r.source_record_id AS source_record_id, "
            "       r.properties_json AS properties_json"
        )
        edge_records, _, _ = await self._driver.execute_query(
            Query(edge_cypher, timeout=self._settings.neo4j_query_timeout),
            database_=self._settings.neo4j_database,
            routing_="r",
        )
        for er in edge_records:
            props = {}
            if er["properties_json"]:
                try:
                    props = json.loads(er["properties_json"])
                except Exception:
                    props = {}
            edges.append({
                "id": er["id"],
                "source_id": er["source_id"],
                "target_id": er["target_id"],
                "edge_type": er["edge_type"] or "CONNECTED_TO",
                "weight": float(er["weight"] or 1.0),
                "confidence": float(er["confidence"] or 1.0),
                "derivation_class": er["derivation_class"] or "FACT",
                "start_time": er["start_time"] or None,
                "end_time": er["end_time"] or None,
                "source_record_id": er["source_record_id"] or None,
                "properties": props,
            })

        return nodes, edges

    async def to_graph_store(self) -> GraphStore:
        """Construct an in-memory GraphStore directly from Neo4j projection."""
        nodes, edges = await self.read_projection()
        store = GraphStore()
        for nid, n in nodes.items():
            store.nodes[nid] = NodeRecord(
                node_id=nid,
                entity_type=n.get("entity_type", "Unknown"),
                properties=dict(n.get("properties", {})),
            )
        for e in edges:
            src = str(e["source_id"])
            tgt = str(e["target_id"])
            etype = str(e.get("edge_type", "CONNECTED_TO"))
            weight = float(e.get("weight", 1.0))
            adj = AdjEdge(
                source_id=src,
                target_id=tgt,
                edge_type=etype,
                properties={"weight": weight, **e.get("properties", {})},
            )
            store.adj.setdefault(src, []).append(adj)
            store.radj.setdefault(tgt, []).append(adj)
            store.edge_index.setdefault(etype, []).append(adj)
        return store
