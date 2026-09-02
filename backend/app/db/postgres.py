"""backend/app/db/postgres.py

PostgreSQL-backed repository for the NEXUS Criminal Intelligence Platform.
Persists nodes, edges, source records, review candidates, and audit events in PostgreSQL
while maintaining fast in-memory graph cache and indices for graph intelligence.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:
    psycopg = None  # type: ignore[assignment]
    Jsonb = None  # type: ignore[assignment]

from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord
from backend.app.core.graph.enums import ResolutionStatus
from backend.app.db.ingestion.contracts import IngestionBundle, EntityReviewCandidate
from backend.app.db.ingestion.graph_adapter import validate_graph_references
from shared.contracts.api import (
    AuditLogEntry,
    EvidenceItemResponse,
    EvidenceProvenanceContract,
    GraphEdgeResponse,
    GraphNodeResponse,
    InvestigationDetailResponse,
    InvestigationSummaryResponse,
    NetworkGraphResponse,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    if isinstance(val, str) and val:
        try:
            cleaned = val.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return _utcnow()


def _to_jsonb(obj: Any) -> Jsonb:
    """Safely convert any dictionary/list (including datetimes/enums) to Jsonb."""
    if obj is None:
        return Jsonb({})
    if isinstance(obj, Jsonb):
        return obj
    try:
        serialized = json.loads(json.dumps(obj, default=str))
        return Jsonb(serialized)
    except Exception:
        return Jsonb({})


class PostgresBackendRepository:
    """PostgreSQL-backed repository with write-through persistence and fast graph indexing."""

    def __init__(
        self,
        database_url: str,
        artifact_path: Path | None = None,
        state_path: Path | None = None,
        reference_time: datetime | None = None,
    ) -> None:
        self.database_url = database_url
        self.artifact_path = artifact_path
        self.state_path = state_path
        self.reference_time = reference_time or _utcnow()
        if self.reference_time.tzinfo is None:
            self.reference_time = self.reference_time.replace(tzinfo=timezone.utc)

        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self.incident_edges: dict[str, list[dict[str, Any]]] = {}
        self.source_records: dict[str, dict[str, Any]] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.review_candidates: dict[str, dict[str, Any]] = {}
        self.batches: dict[str, dict[str, Any]] = {}

        # 1. Initialize schema
        self._init_schema()

        # 2. Sync / Load data from PostgreSQL
        self._load_from_postgres()

        # 3. If PostgreSQL was empty, seed from artifact
        if not self.nodes:
            logger.info("PostgreSQL database is empty. Seeding from artifact dataset...")
            self._seed_from_artifact()
            self._load_from_postgres()

        # 4. Rebuild graph indices
        self._rebuild_indexes()

    def _get_connection(self) -> psycopg.Connection:
        """Create a new PostgreSQL connection with sensible timeouts."""
        return psycopg.connect(self.database_url, connect_timeout=15)

    def _init_schema(self) -> None:
        """Create tables and indexes if they do not exist."""
        schema_path = Path(__file__).resolve().parent / "schema.sql"
        if not schema_path.exists():
            return

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(schema_path.read_text(encoding="utf-8"))
                conn.commit()
            logger.info("PostgreSQL schema validated successfully.")
        except Exception as exc:
            logger.error("Failed to initialize PostgreSQL schema: %s", exc)
            raise

    def _load_from_postgres(self) -> None:
        """Fetch all nodes, edges, source records, and audit events from PostgreSQL."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Load nodes
                    cur.execute("SELECT id, entity_type, properties, created_at, updated_at FROM nodes;")
                    self.nodes = {}
                    for row in cur.fetchall():
                        nid, etype, props, c_at, u_at = row
                        self.nodes[nid] = {
                            "id": nid,
                            "entity_type": etype,
                            "properties": props or {},
                            "created_at": c_at.isoformat() if c_at else None,
                            "updated_at": u_at.isoformat() if u_at else None,
                        }

                    # Load edges
                    cur.execute("""
                        SELECT id, source_id, target_id, edge_type, weight,
                               start_time, end_time, source_record_id, derivation_class,
                               confidence, provenance, properties
                        FROM edges;
                    """)
                    self.edges = []
                    for row in cur.fetchall():
                        (
                            eid, src, tgt, etype, weight,
                            s_time, e_time, s_rec_id, deriv,
                            conf, prov, props
                        ) = row
                        self.edges.append({
                            "id": eid,
                            "source_id": src,
                            "target_id": tgt,
                            "edge_type": etype,
                            "weight": float(weight) if weight is not None else 1.0,
                            "start_time": s_time.isoformat() if s_time else None,
                            "end_time": e_time.isoformat() if e_time else None,
                            "source_record_id": s_rec_id,
                            "derivation_class": deriv,
                            "confidence": float(conf) if conf is not None else 1.0,
                            "provenance": prov or {},
                            "properties": props or {},
                        })

                    # Load source records
                    cur.execute("SELECT id, batch_id, source_type, locator, raw_excerpt, hash, occurred_at FROM source_records;")
                    self.source_records = {}
                    for row in cur.fetchall():
                        srid, bid, stype, loc, raw, h, occ = row
                        self.source_records[srid] = {
                            "id": srid,
                            "batch_id": bid,
                            "source_type": stype,
                            "locator": loc,
                            "raw_excerpt": raw,
                            "hash": h,
                            "occurred_at": occ.isoformat() if occ else None,
                        }

                    # Load audit events
                    cur.execute("SELECT id, user_id, user_role, action, entity_type, entity_id, details, timestamp FROM audit_events ORDER BY timestamp ASC;")
                    self.audit_events = []
                    for row in cur.fetchall():
                        aid, uid, urole, act, etype, eid, det, ts = row
                        self.audit_events.append({
                            "id": aid,
                            "user_id": uid,
                            "user_role": urole,
                            "action": act,
                            "entity_type": etype,
                            "entity_id": eid,
                            "details": det or {},
                            "timestamp": ts.isoformat() if ts else _utcnow().isoformat(),
                        })

                    # Load review candidates
                    cur.execute("SELECT id, incoming_record_id, candidate_node_id, confidence, status, matched_fields, evidence_breakdown, incoming_payload FROM review_candidates;")
                    self.review_candidates = {}
                    for row in cur.fetchall():
                        cid, inc_id, cand_id, conf, st, m_fields, ev_bd, inc_pay = row
                        self.review_candidates[cid] = {
                            "incoming_record_id": inc_id,
                            "candidate_node_id": cand_id,
                            "confidence": conf,
                            "status": st,
                            "matched_fields": m_fields or [],
                            "evidence_breakdown": ev_bd or {},
                            "incoming_payload": inc_pay or {},
                        }

            logger.info(
                "Loaded %d nodes, %d edges, %d audit events from PostgreSQL.",
                len(self.nodes),
                len(self.edges),
                len(self.audit_events),
            )
        except Exception as exc:
            logger.error("Error loading state from PostgreSQL: %s", exc)
            raise

    def _seed_from_artifact(self) -> None:
        """Seed PostgreSQL from artifact file or generator."""
        art_path = self.artifact_path
        if not art_path or not art_path.exists():
            art_path = Path(__file__).resolve().parents[3] / "artifacts" / "nexus_graph" / "nexus_graph.json"
        if not art_path.exists():
            art_path = Path(__file__).resolve().parent / "synthetic_graph.json"

        if art_path.exists():
            raw = json.loads(art_path.read_text(encoding="utf-8"))
            nodes_data = raw.get("nodes", [])
            edges_data = raw.get("edges", [])
        else:
            from synthetic_data.nexus_generator import generate_nexus_synthetic_dataset
            dataset = generate_nexus_synthetic_dataset()["dataset"]
            nodes_data = dataset.get("nodes", [])
            edges_data = dataset.get("edges", [])

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Insert nodes
                    node_tuples = [
                        (str(n["id"]), str(n.get("entity_type", "Unknown")), _to_jsonb(n.get("properties", {})))
                        for n in nodes_data
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

                    # Insert edges
                    edge_tuples = [
                        (
                            str(e.get("id", f"{e['source_id']}-{e['target_id']}")),
                            str(e["source_id"]),
                            str(e["target_id"]),
                            str(e.get("edge_type", "LINKED_TO")),
                            float(e.get("weight", 1.0)),
                            e.get("start_time"),
                            e.get("end_time"),
                            e.get("source_record_id"),
                            e.get("derivation_class"),
                            float(e.get("confidence", 1.0)),
                            _to_jsonb(e.get("provenance", {})),
                            _to_jsonb(e.get("properties", {})),
                        )
                        for e in edges_data
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
                conn.commit()
            logger.info("Successfully seeded %d nodes and %d edges into PostgreSQL.", len(nodes_data), len(edges_data))
        except Exception as exc:
            logger.error("Failed to seed artifact into PostgreSQL: %s", exc)

    def _rebuild_indexes(self) -> None:
        self.incident_edges = {}
        for edge in self.edges:
            src = str(edge.get("source_id", ""))
            tgt = str(edge.get("target_id", ""))
            self.incident_edges.setdefault(src, []).append(edge)
            self.incident_edges.setdefault(tgt, []).append(edge)

    def clear(self) -> None:
        """Clear database tables and re-seed base artifact."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("TRUNCATE TABLE edges, nodes, source_records, audit_events, review_candidates, ingestion_batches CASCADE;")
                conn.commit()
        except Exception as exc:
            logger.error("Error clearing PostgreSQL tables: %s", exc)

        self.nodes.clear()
        self.edges.clear()
        self.incident_edges.clear()
        self.source_records.clear()
        self.audit_events.clear()
        self.review_candidates.clear()
        self.batches.clear()

        self._seed_from_artifact()
        self._load_from_postgres()
        self._rebuild_indexes()

    def apply_bundle(self, bundle: IngestionBundle) -> tuple[int, int, int, int]:
        """Atomically apply and persist a resolved IngestionBundle to PostgreSQL."""
        errors = validate_graph_references(bundle.nodes, bundle.relationships, bundle.source_records)
        if errors:
            raise ValueError(f"Bundle validation failed: {'; '.join(errors)}")

        nodes_created = 0
        nodes_reused = 0
        edges_created = 0
        edges_reused = 0

        batch_id = bundle.batch_id
        if batch_id not in self.batches:
            self.batches[batch_id] = {"nodes": [], "edges": []}

        # 1. Update in-memory structures
        nodes_to_insert = []
        for node in bundle.nodes:
            nid = str(node.id)
            if nid in self.nodes:
                nodes_reused += 1
                self.nodes[nid].setdefault("properties", {}).update(node.properties)
                self.batches[batch_id]["nodes"].append(self.nodes[nid])
            else:
                nodes_created += 1
                new_node = {
                    "id": nid,
                    "entity_type": node.entity_type.value if hasattr(node.entity_type, "value") else str(node.entity_type),
                    "properties": dict(node.properties),
                }
                self.nodes[nid] = new_node
                self.batches[batch_id]["nodes"].append(new_node)
            nodes_to_insert.append((
                nid,
                node.entity_type.value if hasattr(node.entity_type, "value") else str(node.entity_type),
                _to_jsonb(self.nodes[nid]["properties"]),
            ))

        existing_edge_ids = {str(e.get("id")) for e in self.edges if "id" in e}
        edges_to_insert = []
        for edge in bundle.relationships:
            eid = str(edge.id)
            edge_data = {
                "id": eid,
                "source_id": str(edge.source_id),
                "target_id": str(edge.target_id),
                "edge_type": edge.edge_type.value if hasattr(edge.edge_type, "value") else str(edge.edge_type),
                "start_time": edge.start_time.isoformat() if edge.start_time else None,
                "end_time": edge.end_time.isoformat() if edge.end_time else None,
                "source_record_id": edge.source_record_id,
                "derivation_class": edge.derivation_class.value if hasattr(edge.derivation_class, "value") else str(edge.derivation_class),
                "confidence": edge.confidence,
                "provenance": edge.provenance.model_dump(mode="json") if hasattr(edge.provenance, "model_dump") else dict(edge.provenance),
                "properties": dict(edge.properties),
            }

            if eid in existing_edge_ids:
                edges_reused += 1
                for existing in self.edges:
                    if str(existing.get("id")) == eid:
                        existing.update(edge_data)
                        self.batches[batch_id]["edges"].append(existing)
                        break
            else:
                edges_created += 1
                self.edges.append(edge_data)
                existing_edge_ids.add(eid)
                self.batches[batch_id]["edges"].append(edge_data)

            edges_to_insert.append((
                eid,
                str(edge.source_id),
                str(edge.target_id),
                edge.edge_type.value if hasattr(edge.edge_type, "value") else str(edge.edge_type),
                float(edge.properties.get("weight", 1.0)) if hasattr(edge, "properties") else 1.0,
                edge.start_time,
                edge.end_time,
                edge.source_record_id,
                edge.derivation_class.value if hasattr(edge.derivation_class, "value") else str(edge.derivation_class),
                float(edge.confidence),
                _to_jsonb(edge_data["provenance"]),
                _to_jsonb(edge_data["properties"]),
            ))

        sr_to_insert = []
        for sr in bundle.source_records:
            srid = str(sr.id)
            self.source_records[srid] = sr.model_dump(mode="json") if hasattr(sr, "model_dump") else dict(sr)
            sr_hash = getattr(sr, "content_hash", None) or getattr(sr, "hash", None) or ""
            sr_to_insert.append((
                srid,
                getattr(sr, "batch_id", "") or "",
                str(getattr(sr, "source_type", "DIRECT_RECORD") or "DIRECT_RECORD"),
                getattr(sr, "locator", "") or "",
                getattr(sr, "raw_excerpt", "") or "",
                sr_hash,
                getattr(sr, "occurred_at", None),
            ))

        self._rebuild_indexes()

        # 2. Persist directly to PostgreSQL
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    if nodes_to_insert:
                        cur.executemany(
                            """
                            INSERT INTO nodes (id, entity_type, properties, updated_at)
                            VALUES (%s, %s, %s, NOW())
                            ON CONFLICT (id) DO UPDATE SET
                                entity_type = EXCLUDED.entity_type,
                                properties = EXCLUDED.properties,
                                updated_at = NOW();
                            """,
                            nodes_to_insert,
                        )
                    if edges_to_insert:
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
                            edges_to_insert,
                        )
                    if sr_to_insert:
                        cur.executemany(
                            """
                            INSERT INTO source_records (id, batch_id, source_type, locator, raw_excerpt, hash, occurred_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (id) DO UPDATE SET
                                locator = EXCLUDED.locator,
                                raw_excerpt = EXCLUDED.raw_excerpt,
                                hash = EXCLUDED.hash,
                                updated_at = NOW();
                            """,
                            sr_to_insert,
                        )
                    # Record batch
                    cur.execute(
                        """
                        INSERT INTO ingestion_batches (batch_id, status, summary, created_at)
                        VALUES (%s, 'COMPLETED', %s, NOW())
                        ON CONFLICT (batch_id) DO UPDATE SET
                            summary = EXCLUDED.summary;
                        """,
                        (batch_id, _to_jsonb({"nodes_created": nodes_created, "edges_created": edges_created})),
                    )
                conn.commit()
        except Exception as exc:
            logger.error("Failed to persist bundle to PostgreSQL: %s", exc)

        return nodes_created, nodes_reused, edges_created, edges_reused

    def get_batch_network(self, batch_id: str) -> dict[str, Any] | None:
        return self.batches.get(batch_id)

    def store_review_candidates(self, candidates: list[EntityReviewCandidate]) -> None:
        tuples = []
        for c in candidates:
            c_dict = c.model_dump(mode="json") if hasattr(c, "model_dump") else dict(c)
            candidate_id = f"RC-{c_dict.get('incoming_record_id', '')}-{c_dict.get('candidate_node_id', '')}"
            self.review_candidates[candidate_id] = c_dict
            tuples.append((
                candidate_id,
                c_dict.get("incoming_record_id", ""),
                c_dict.get("candidate_node_id", ""),
                float(c_dict.get("confidence", 0.0)),
                str(c_dict.get("status", "PENDING")),
                _to_jsonb(c_dict.get("matched_fields", [])),
                _to_jsonb(c_dict.get("evidence_breakdown", {})),
                _to_jsonb(c_dict.get("incoming_payload", {})),
            ))

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.executemany(
                        """
                        INSERT INTO review_candidates (
                            id, incoming_record_id, candidate_node_id, confidence,
                            status, matched_fields, evidence_breakdown, incoming_payload, created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (id) DO UPDATE SET
                            status = EXCLUDED.status,
                            confidence = EXCLUDED.confidence;
                        """,
                        tuples,
                    )
                conn.commit()
        except Exception as exc:
            logger.error("Failed to store review candidates in PostgreSQL: %s", exc)

    def get_review_candidates(self) -> list[EntityReviewCandidate]:
        return [
            EntityReviewCandidate(**data)
            for data in self.review_candidates.values()
        ]

    def update_candidate_status(self, candidate_id: str, status: str) -> None:
        if candidate_id in self.review_candidates:
            self.review_candidates[candidate_id]["status"] = status

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE review_candidates SET status = %s WHERE id = %s;", (status, candidate_id))
                conn.commit()
        except Exception as exc:
            logger.error("Failed to update candidate status in PostgreSQL: %s", exc)

    def merge_nodes(self, incoming_node_id: str, canonical_node_id: str) -> None:
        if incoming_node_id not in self.nodes or canonical_node_id not in self.nodes:
            return

        incoming = self.nodes[incoming_node_id]
        canonical = self.nodes[canonical_node_id]

        merged_props = dict(incoming.get("properties", {}))
        merged_props.update(canonical.get("properties", {}))
        
        if "badges" not in canonical:
            canonical["badges"] = []
        if "MERGED_ENTITY" not in canonical["badges"]:
            canonical["badges"].append("MERGED_ENTITY")
            
        canonical["properties"] = merged_props

        for edge in self.edges:
            if edge.get("source_id") == incoming_node_id:
                edge["source_id"] = canonical_node_id
            if edge.get("target_id") == incoming_node_id:
                edge["target_id"] = canonical_node_id

        del self.nodes[incoming_node_id]
        self._rebuild_indexes()

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Update canonical node
                    cur.execute(
                        "UPDATE nodes SET properties = %s, updated_at = NOW() WHERE id = %s;",
                        (Jsonb(merged_props), canonical_node_id),
                    )
                    # Rewire edges
                    cur.execute("UPDATE edges SET source_id = %s WHERE source_id = %s;", (canonical_node_id, incoming_node_id))
                    cur.execute("UPDATE edges SET target_id = %s WHERE target_id = %s;", (canonical_node_id, incoming_node_id))
                    # Delete incoming node
                    cur.execute("DELETE FROM nodes WHERE id = %s;", (incoming_node_id,))
                conn.commit()
        except Exception as exc:
            logger.error("Failed to persist node merge in PostgreSQL: %s", exc)

    def global_search(self, query: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        query_lower = query.lower()
        cases = []
        entities = []
        
        for nid, n_data in self.nodes.items():
            props = n_data.get("properties", {})
            entity_type = n_data.get("entity_type", "")
            
            searchable_texts = [nid.lower()]
            for val in props.values():
                if isinstance(val, str):
                    searchable_texts.append(val.lower())
                elif isinstance(val, (int, float)):
                    searchable_texts.append(str(val))
                    
            if any(query_lower in text for text in searchable_texts):
                if entity_type in ("Case", "CASE"):
                    cases.append(n_data)
                else:
                    entities.append(n_data)
                    
        return cases, entities

    def to_graph_store(self) -> GraphStore:
        store = GraphStore()
        for nid, node_data in self.nodes.items():
            store.nodes[nid] = NodeRecord(
                node_id=nid,
                entity_type=node_data.get("entity_type", "Unknown"),
                properties=dict(node_data.get("properties", {})),
            )

        for edge in self.edges:
            src = str(edge.get("source_id", ""))
            tgt = str(edge.get("target_id", ""))
            etype = str(edge.get("edge_type", "LINKED_TO"))
            weight = float(edge.get("weight", 1.0))
            provenance = dict(edge.get("provenance", {}))

            adj_edge = AdjEdge(
                source_id=src,
                target_id=tgt,
                edge_type=etype,
                properties={"weight": weight, "provenance": provenance},
            )
            store.adj.setdefault(src, []).append(adj_edge)
            store.radj.setdefault(tgt, []).append(adj_edge)
            store.edge_index.setdefault(etype, []).append(adj_edge)

        return store

    @property
    def case_ids(self) -> list[str]:
        return [str(nid) for nid, n in self.nodes.items() if n.get("entity_type") in ("Case", "CASE")]

    def list_investigations(
        self,
        district: str | None = None,
        category: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[InvestigationSummaryResponse]:
        cases = [n for n in self.nodes.values() if n.get("entity_type") in ("Case", "CASE")]
        summaries: list[InvestigationSummaryResponse] = []

        for c in cases:
            props = c.get("properties", {})
            cid = str(c["id"])

            if district and props.get("district", "").lower() != district.lower():
                continue
            if category and props.get("offence_category", "").lower() != category.lower():
                continue
            if status and props.get("status", "").lower() != status.lower():
                continue

            incident_edges = self.incident_edges.get(cid, [])
            accused_count = sum(1 for e in incident_edges if e.get("edge_type") in ("ACCUSED_IN", "INVOLVED_IN"))
            evidence_count = sum(1 for e in incident_edges if e.get("edge_type") == "HAS_EVIDENCE")

            updated_at = _parse_datetime(props.get("updated_at") or c.get("updated_at") or props.get("incident_date"))

            summaries.append(
                InvestigationSummaryResponse(
                    id=cid,
                    fir_number=props.get("fir_number") or f"FIR-{cid}",
                    title=props.get("title") or f"Investigation {cid}",
                    station_name=props.get("station_name", "Central Station"),
                    district=props.get("district", "Bengaluru"),
                    offence_category=props.get("offence_category", "General Crime"),
                    status=props.get("status", "OPEN"),
                    updated_at=updated_at,
                    accused_count=accused_count,
                    evidence_count=evidence_count,
                    priority_rank=accused_count * 2 + evidence_count,
                )
            )

        summaries.sort(key=lambda s: s.priority_rank, reverse=True)
        return summaries[:limit]

    def list_worklist(self, role: str = "INVESTIGATOR") -> list[dict[str, Any]]:
        invs = self.list_investigations()
        return [inv.model_dump() for inv in invs]

    def get_investigation_detail(self, case_id: str) -> InvestigationDetailResponse | None:
        node = self.nodes.get(case_id)
        if not node or node.get("entity_type") not in ("Case", "CASE"):
            return None

        props = node.get("properties", {})
        incident_edges = self.incident_edges.get(case_id, [])

        accused: list[dict[str, Any]] = []
        victims: list[dict[str, Any]] = []
        evidence: list[EvidenceItemResponse] = []

        for e in incident_edges:
            etype = e.get("edge_type")
            src_id = str(e.get("source_id"))
            tgt_id = str(e.get("target_id"))
            other_id = src_id if tgt_id == case_id else tgt_id
            other_node = self.nodes.get(other_id, {})
            other_props = other_node.get("properties", {})

            if etype in ("ACCUSED_IN", "INVOLVED_IN"):
                accused.append({"id": other_id, **other_props})
            elif etype == "VICTIM_IN":
                victims.append({"id": other_id, **other_props})
            elif etype == "HAS_EVIDENCE":
                prov_dict = e.get("provenance", {})
                evidence.append(
                    EvidenceItemResponse(
                        id=other_id,
                        evidence_number=other_props.get("evidence_number", f"EV-{other_id}"),
                        case_id=case_id,
                        evidence_type=other_props.get("evidence_type", "PHYSICAL"),
                        description=other_props.get("description", "Collected evidence item"),
                        collected_at=_parse_datetime(other_props.get("collected_at")),
                        storage_location=other_props.get("storage_location"),
                        provenance=EvidenceProvenanceContract(**prov_dict) if prov_dict else EvidenceProvenanceContract(),
                    )
                )

        updated_at = _parse_datetime(props.get("updated_at") or node.get("updated_at"))
        incident_date = _parse_datetime(props.get("incident_date")) if props.get("incident_date") else None

        return InvestigationDetailResponse(
            id=case_id,
            fir_number=props.get("fir_number") or f"FIR-{case_id}",
            title=props.get("title") or f"Investigation {case_id}",
            station_name=props.get("station_name", "Central Police Station"),
            district=props.get("district", "Bengaluru"),
            offence_category=props.get("offence_category", "General Crime"),
            incident_date=incident_date,
            status=props.get("status", "OPEN"),
            summary=props.get("summary", ""),
            sections=props.get("sections", []),
            accused=accused,
            victims=victims,
            evidence=evidence,
            updated_at=updated_at,
        )

    def get_case_detail(self, case_id: str) -> dict[str, Any] | None:
        res = self.get_investigation_detail(case_id)
        return res.model_dump() if res else None

    def get_case_network(self, case_id: str, depth: int = 2) -> NetworkGraphResponse:
        store = self.to_graph_store()
        visited_nodes: set[str] = {case_id}
        frontier: set[str] = {case_id}

        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in frontier:
                for edge in store.adj.get(nid, []):
                    if edge.target_id not in visited_nodes:
                        visited_nodes.add(edge.target_id)
                        next_frontier.add(edge.target_id)
                for edge in store.radj.get(nid, []):
                    if edge.source_id not in visited_nodes:
                        visited_nodes.add(edge.source_id)
                        next_frontier.add(edge.source_id)
            frontier = next_frontier

        resp_nodes: list[GraphNodeResponse] = []
        for nid in visited_nodes:
            n_data = self.nodes.get(nid)
            if not n_data:
                continue
            props = n_data.get("properties", {})
            label = (
                props.get("full_name")
                or props.get("fir_number")
                or props.get("phone_number")
                or props.get("account_number")
                or props.get("name")
                or nid
            )
            in_deg = len(store.radj.get(nid, []))
            out_deg = len(store.adj.get(nid, []))

            resp_nodes.append(
                GraphNodeResponse(
                    id=nid,
                    entity_type=n_data.get("entity_type", "Unknown"),
                    label=label,
                    properties=props,
                    degree=in_deg + out_deg,
                    confidence=float(props.get("confidence", 1.0)),
                )
            )

        resp_edges: list[GraphEdgeResponse] = []
        for e in self.edges:
            src = str(e.get("source_id"))
            tgt = str(e.get("target_id"))
            if src in visited_nodes and tgt in visited_nodes:
                prov = e.get("provenance") or {}
                if not prov.get("source_id") and e.get("source_record_id"):
                    prov["source_id"] = e["source_record_id"]
                
                resp_edges.append(
                    GraphEdgeResponse(
                        id=str(e.get("id", f"{src}-{tgt}")),
                        source_id=src,
                        target_id=tgt,
                        edge_type=str(e.get("edge_type", "CONNECTED_TO")),
                        weight=float(e.get("weight", 1.0)),
                        provenance=EvidenceProvenanceContract(**prov) if prov else EvidenceProvenanceContract(),
                        properties=e.get("properties", {}),
                    )
                )

        return NetworkGraphResponse(
            nodes=resp_nodes,
            edges=resp_edges,
            total_nodes=len(resp_nodes),
            total_edges=len(resp_edges),
        )

    def record_audit(
        self,
        user_id: str,
        user_role: str,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        from backend.app.core.crypto.audit_integrity import compute_audit_event_hash
        previous_hash = self.audit_events[-1].get("integrity_hash") if self.audit_events else None
        now_dt = _utcnow()
        raw_payload = {
            "id": f"audit-{now_dt.timestamp()}-{len(self.audit_events)+1}",
            "actor_id": user_id,
            "event_type": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
            "timestamp": now_dt.isoformat(),
            "previous_hash": previous_hash,
        }
        computed_hash = compute_audit_event_hash(raw_payload)

        entry = AuditLogEntry(
            id=raw_payload["id"],
            user_id=user_id,
            user_role=user_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            timestamp=now_dt,
            integrity_hash=computed_hash,
            previous_hash=previous_hash,
        )
        self.audit_events.append(entry.model_dump())

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO audit_events (id, user_id, user_role, action, entity_type, entity_id, details, timestamp)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                        """,
                        (entry.id, entry.user_id, entry.user_role, entry.action, entry.entity_type, entry.entity_id, Jsonb(entry.details), entry.timestamp),
                    )
                conn.commit()
        except Exception as exc:
            logger.error("Failed to record audit event in PostgreSQL: %s", exc)

        return entry

    def list_audit_events(self, limit: int = 100) -> list[AuditLogEntry]:
        sorted_events = sorted(
            self.audit_events,
            key=lambda e: _parse_datetime(e.get("timestamp")),
            reverse=True,
        )
        return [AuditLogEntry(**e) for e in sorted_events[:limit]]
