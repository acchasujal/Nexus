"""backend/app/db/in_memory.py

In-memory backend repository for the NEXUS Criminal Intelligence Platform.
Provides fast index lookups, graph traversals, case retrieval, audit logging,
and graph store extraction for analytical algorithms.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    NodeContextResponse,
    NodePresenceType,
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


class InMemoryBackendRepository:
    """Read/write in-memory repository for the NEXUS intelligence backend."""

    def __init__(
        self,
        artifact_path: Path | None = None,
        state_path: Path | None = None,
        reference_time: datetime | None = None,
    ) -> None:
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
        self.intelligence_pulses: dict[str, dict[str, Any]] = {}
        self.identity_drifts: dict[str, dict[str, Any]] = {}
        self.network_adaptations: dict[str, dict[str, Any]] = {}
        self.digital_shadows: dict[str, dict[str, Any]] = {}
        self.documents: dict[str, dict[str, Any]] = {}
        self.candidate_extractions: dict[str, dict[str, Any]] = {}
        self.candidate_decisions: dict[str, list[dict[str, Any]]] = {}
        self.state_path = state_path

        self._load_artifact(artifact_path or self._default_artifact_path())
        self._load_state()
        self._rebuild_indexes()

    def clear(self) -> None:
        """Clear all in-memory state and reload the base artifact."""
        self.nodes.clear()
        self.edges.clear()
        self.incident_edges.clear()
        self.source_records.clear()
        self.audit_events.clear()
        self.review_candidates.clear()
        self.batches.clear()
        self.intelligence_pulses.clear()
        self.identity_drifts.clear()
        self.network_adaptations.clear()
        self.digital_shadows.clear()
        self.documents.clear()
        self.candidate_extractions.clear()
        self.candidate_decisions.clear()
        self._load_artifact(self._default_artifact_path())
        if self.state_path and self.state_path.exists():
            try:
                self.state_path.unlink()
            except OSError:
                pass
        self._rebuild_indexes()

    def _default_artifact_path(self) -> Path:
        local_resource = Path(__file__).resolve().parent / "synthetic_graph.json"
        if local_resource.exists():
            return local_resource
        nexus_art = Path(__file__).resolve().parents[3] / "artifacts" / "nexus_graph" / "nexus_graph.json"
        if nexus_art.exists():
            return nexus_art
        return local_resource

    def _load_artifact(self, artifact_path: Path) -> None:
        if not artifact_path.exists():
            # Fallback to creating a sample dataset if file doesn't exist
            from synthetic_data.nexus_generator import generate_nexus_synthetic_dataset
            data = generate_nexus_synthetic_dataset()["dataset"]
            self.nodes = {str(node["id"]): dict(node) for node in data.get("nodes", [])}
            self.edges = [dict(edge) for edge in data.get("edges", [])]
            return

        raw = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.nodes = {str(node["id"]): dict(node) for node in raw.get("nodes", [])}
        self.edges = [dict(edge) for edge in raw.get("edges", [])]
        self._seed_default_source_records()

    def _seed_default_source_records(self) -> None:
        """Seed canonical forensic source records so citations resolve deterministically."""
        default_sources = {
            "SRC-FIR-141": {
                "id": "SRC-FIR-141",
                "batch_id": "BATCH-2026-08-24",
                "source_type": "FIR",
                "locator": "fir_141_2026.pdf — page 2, row 4 (accused list)",
                "raw_excerpt": "Accused: Rafiq Khan, s/o Iqbal Khan, age 35, res. Hootagalli, Mysuru. Mobile disclosed: +91 98450 11223.",
                "occurred_at": "2026-02-11T09:30:00Z",
                "case_ids": ["CASE-141"],
                "content_hash": "2f6a96ef1d0b38bc9381c855a02cfc2de25df963ebefc0bb4f04c0ec23a85b9b",
                "hash_algorithm": "SHA-256",
            },
            "SRC-FIR-207": {
                "id": "SRC-FIR-207",
                "batch_id": "BATCH-2026-08-24",
                "source_type": "FIR",
                "locator": "fir_207_2026.pdf — page 1, row 7 (accused list)",
                "raw_excerpt": "Accused: Rafiq Ahmed, s/o Iqbal Khan, age 35, res. Hootagalli Colony, Mysuru. Mobile: +91 98450 11223.",
                "occurred_at": "2026-03-02T14:15:00Z",
                "case_ids": ["CASE-207"],
                "content_hash": "7d9959e19d7b42aa1527c70c04f9810f60c70428efb0451a44e59174df44b4c7",
                "hash_algorithm": "SHA-256",
            },
            "SRC-CDR-A12": {
                "id": "SRC-CDR-A12",
                "batch_id": "BATCH-2026-08-24",
                "source_type": "CDR",
                "locator": "cdr_mysuru_feb.csv — row 1287 (A-party +91 98450 11223)",
                "raw_excerpt": "2026-02-14T22:41:05Z, +91 98450 11223 → +91 99801 55210, duration 412s, cell 4701-Hootagalli.",
                "occurred_at": "2026-02-14T22:41:05Z",
                "case_ids": ["CASE-141"],
                "content_hash": "a189f7d466f289cf30c49eb9e782d09bb2f35d283ad6f73db5817cbe30c50009",
                "hash_algorithm": "SHA-256",
            },
            "SRC-CDR-B31": {
                "id": "SRC-CDR-B31",
                "batch_id": "BATCH-2026-08-24",
                "source_type": "CDR",
                "locator": "cdr_bengaluru_mar.csv — row 4402 (A-party +91 98450 11223)",
                "raw_excerpt": "2026-03-05T02:12:44Z, +91 98450 11223 → +91 98450 77310, duration 96s, cell 6112-Whitefield.",
                "occurred_at": "2026-03-05T02:12:44Z",
                "case_ids": ["CASE-207"],
                "content_hash": "20b2241cfb25a3d7637841c7b3991c0e3a6c116d790d9326e6ef1c3cb16ff369",
                "hash_algorithm": "SHA-256",
            },
            "SRC-TXN-55": {
                "id": "SRC-TXN-55",
                "batch_id": "BATCH-2026-08-24",
                "source_type": "BANK_TXN",
                "locator": "txns_axis_9914.csv — row 55",
                "raw_excerpt": "2026-03-09T11:03:00Z, ACC-9914 → ACC-7731, ₹4,80,000, ref NIFT/20260309/5521.",
                "occurred_at": "2026-03-09T11:03:00Z",
                "case_ids": ["CASE-141", "CASE-207"],
                "content_hash": "f68d90fae134df39c5957d191295bcfcfbc8732890ae15bb7c44040a455dc87c",
                "hash_algorithm": "SHA-256",
            },
            "SRC-TXN-71": {
                "id": "SRC-TXN-71",
                "batch_id": "BATCH-2026-08-24",
                "source_type": "BANK_TXN",
                "locator": "txns_axis_9914.csv — row 71",
                "raw_excerpt": "2026-03-11T16:47:00Z, ACC-9914 → ACC-7731, ₹2,15,000, ref NIFT/20260311/8830.",
                "occurred_at": "2026-03-11T16:47:00Z",
                "case_ids": ["CASE-141", "CASE-207"],
                "content_hash": "848da09c3f41a0d242637217db587d55c70ef37d1217e94e5a953e5eef725eb7",
                "hash_algorithm": "SHA-256",
            },
            "SRC-FIR-305": {
                "id": "SRC-FIR-305",
                "batch_id": "BATCH-2026-08-24",
                "source_type": "FIR",
                "locator": "fir_305_2026.pdf — page 2, row 3",
                "raw_excerpt": "Accused: Vikram Sharma, age 32, res. Indiranagar Bengaluru. Mobile: +91 98450 77310. Aadhaar: XXXX-XXXX-4491.",
                "occurred_at": "2026-03-15T11:00:00Z",
                "case_ids": ["CASE-305"],
                "content_hash": "37f40778cba2207b1a646c2415d8f6f578dfca4b9671d18f553f1915eafe7539",
                "hash_algorithm": "SHA-256",
            },
            "SRC-FIR-412": {
                "id": "SRC-FIR-412",
                "batch_id": "BATCH-2026-08-24",
                "source_type": "FIR",
                "locator": "fir_412_2026.pdf — page 1, row 5",
                "raw_excerpt": "Accused: Bikram Sarma, age 32, res. Domlur Layout Bengaluru. Mobile: +91 98450 77310. Aadhaar: XXXX-XXXX-4491.",
                "occurred_at": "2026-03-22T16:30:00Z",
                "case_ids": ["CASE-412"],
                "content_hash": "0f622d0577d612ec9bb399991207e78696b99480ffda32cf16995642a8b9e69c",
                "hash_algorithm": "SHA-256",
            },
            "SRC-FIR-501": {
                "id": "SRC-FIR-501",
                "batch_id": "BATCH-2026-08-24",
                "source_type": "FIR",
                "locator": "fir_501_2026.pdf — page 3, row 2",
                "raw_excerpt": "Accused: Suniel Shetty, s/o R. Shetty, age 41, res. Jayanagar Bengaluru. Vehicle: KA-01-AB-1001.",
                "occurred_at": "2026-04-02T10:15:00Z",
                "case_ids": ["CASE-501"],
                "content_hash": "848e02611a91e55ec746bf9971ceea3a58e3eb99b514ca597db2bfbe5f27c3d7",
                "hash_algorithm": "SHA-256",
            },
            "SRC-FIR-502": {
                "id": "SRC-FIR-502",
                "batch_id": "BATCH-2026-08-24",
                "source_type": "FIR",
                "locator": "fir_502_2026.pdf — page 2, row 8",
                "raw_excerpt": "Accused: Sunil Shetty, s/o R. Shetty, age 41, res. 4th Block Jayanagar. Vehicle: KA-01-AB-1001.",
                "occurred_at": "2026-04-18T14:40:00Z",
                "case_ids": ["CASE-502"],
                "content_hash": "b2fbb1b93f1ea1a9420b784a92c3a525f0a78cae08bb39c90380f2b3886196dc",
                "hash_algorithm": "SHA-256",
            },
        }
        for k, v in default_sources.items():
            if k not in self.source_records:
                self.source_records[k] = v

    def _load_state(self) -> None:
        if self.state_path is None or not self.state_path.exists():
            return
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            for node_id, patch in raw.get("node_patches", {}).items():
                if node_id in self.nodes:
                    self.nodes[node_id].setdefault("properties", {}).update(patch)
            self.audit_events = list(raw.get("audit_events", []))
            self.review_candidates = dict(raw.get("review_candidates", {}))
        except (json.JSONDecodeError, OSError, ValueError, TypeError) as exc:
            logger.debug("Optional state file loading skipped: %s", exc)

    def _save_state(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "audit_events": self.audit_events,
            "review_candidates": self.review_candidates,
            "saved_at": _utcnow().isoformat(),
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _rebuild_indexes(self) -> None:
        self.incident_edges = {}
        for edge in self.edges:
            src = str(edge.get("source_id", ""))
            tgt = str(edge.get("target_id", ""))
            self.incident_edges.setdefault(src, []).append(edge)
            self.incident_edges.setdefault(tgt, []).append(edge)

    def apply_bundle(self, bundle: IngestionBundle) -> tuple[int, int, int, int]:
        """
        Atomically apply a fully resolved IngestionBundle to the repository.
        Returns: (nodes_created, nodes_reused, edges_created, edges_reused)
        """
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
                    "entity_type": node.entity_type.value,
                    "properties": dict(node.properties),
                }
                self.nodes[nid] = new_node
                self.batches[batch_id]["nodes"].append(new_node)

        existing_edge_ids = {str(e.get("id")) for e in self.edges if "id" in e}
        for edge in bundle.relationships:
            eid = str(edge.id)
            edge_data = {
                "id": eid,
                "source_id": str(edge.source_id),
                "target_id": str(edge.target_id),
                "edge_type": edge.edge_type.value,
                "start_time": edge.start_time.isoformat() if edge.start_time else None,
                "end_time": edge.end_time.isoformat() if edge.end_time else None,
                "source_record_id": edge.source_record_id,
                "derivation_class": edge.derivation_class.value,
                "confidence": edge.confidence,
                "provenance": edge.provenance.model_dump(mode="json"),
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

        for sr in bundle.source_records:
            srid = str(sr.id)
            self.source_records[srid] = sr.model_dump(mode="json")

        self._rebuild_indexes()
        self._save_state()
        return nodes_created, nodes_reused, edges_created, edges_reused

    def get_batch_network(self, batch_id: str) -> dict[str, Any] | None:
        """Return the isolated nodes and edges for a specific batch."""
        return self.batches.get(batch_id)

    def store_review_candidates(self, candidates: list[EntityReviewCandidate]) -> None:
        """Store entity review candidates from an ingestion batch."""
        for c in candidates:
            # Generate a stable candidate ID
            candidate_id = f"RC-{c.incoming_record_id}-{c.candidate_node_id}"
            self.review_candidates[candidate_id] = c.model_dump(mode="json")
        self._save_state()

    def get_review_candidates(self) -> list[EntityReviewCandidate]:
        """Return all pending review candidates."""
        return [
            EntityReviewCandidate(**data)
            for data in self.review_candidates.values()
        ]

    def update_candidate_status(self, candidate_id: str, status: str) -> None:
        """Update the status of a review candidate."""
        if candidate_id in self.review_candidates:
            self.review_candidates[candidate_id]["status"] = status
            self._save_state()

    def merge_nodes(self, incoming_node_id: str, canonical_node_id: str) -> None:
        """Merge an incoming (provisional) node into a canonical node."""
        if incoming_node_id not in self.nodes or canonical_node_id not in self.nodes:
            return

        incoming = self.nodes[incoming_node_id]
        canonical = self.nodes[canonical_node_id]

        # Merge properties (canonical overwrites provisional if conflicts exist)
        merged_props = dict(incoming.get("properties", {}))
        merged_props.update(canonical.get("properties", {}))
        
        # Add badge to indicate it's a merged node
        if "badges" not in canonical:
            canonical["badges"] = []
        if "MERGED_ENTITY" not in canonical["badges"]:
            canonical["badges"].append("MERGED_ENTITY")
            
        canonical["properties"] = merged_props

        # Migrate all edges pointing to/from incoming_node_id
        for edge in self.edges:
            if edge.get("source_id") == incoming_node_id:
                edge["source_id"] = canonical_node_id
            if edge.get("target_id") == incoming_node_id:
                edge["target_id"] = canonical_node_id

        # Remove the incoming node
        del self.nodes[incoming_node_id]

        self._rebuild_indexes()
        self._save_state()

    def global_search(self, query: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Search cases and entities by matching text fields."""
        query_lower = query.lower()
        cases = []
        entities = []
        
        for nid, n_data in self.nodes.items():
            props = n_data.get("properties", {})
            entity_type = n_data.get("entity_type", "")
            
            # Extract searchable text
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
        """Export raw repository nodes and edges into an in-memory GraphStore."""
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
            if not provenance.get("source_id") and edge.get("source_record_id"):
                provenance["source_id"] = str(edge["source_record_id"])

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

    # ── Cases & Investigations ───────────────────────────────────────────────

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

    # Legacy alias for backward compatibility with existing tests
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

    # Legacy alias
    def get_case_detail(self, case_id: str) -> dict[str, Any] | None:
        res = self.get_investigation_detail(case_id)
        return res.model_dump() if res else None

    # ── Subgraph & Network Visualizer ─────────────────────────────────────────

    # ── Subgraph & Network Visualizer ─────────────────────────────────────────

    def get_case_network(
        self,
        case_id: str,
        depth: int = 1,
        principal: Any | None = None,
    ) -> NetworkGraphResponse:
        """Extract an investigator-controlled neighborhood graph centered around a case.
        
        Semantics:
          depth=0: Case Only (strict case scope, 0-hop)
          depth=1: Direct relationships (direct accused, direct evidence, direct case links)
          depth=2: Expanded intelligence (2-hop syndicate, CDR contacts, bridge brokers)
          depth=3: Extended intelligence (3-hop network)
        """
        # 1. Resolve case_id to canonical node ID
        root_id: str | None = None
        if case_id in self.nodes:
            root_id = case_id
        else:
            for nid, n in self.nodes.items():
                if n.get("properties", {}).get("fir_number") == case_id:
                    root_id = str(nid)
                    break

        if not root_id or root_id not in self.nodes:
            return NetworkGraphResponse(
                nodes=[],
                edges=[],
                total_nodes=0,
                total_edges=0,
                case_id=case_id,
                depth=depth,
            )

        root_node = self.nodes[root_id]
        root_props = root_node.get("properties", {})
        root_fir = str(root_props.get("fir_number") or root_id)

        # 2. BFS traversal tracking distance and parent/edge for shortest path reconstruction
        visited_nodes: set[str] = {root_id}
        distance: dict[str, int] = {root_id: 0}
        # predecessor[nid] = (parent_id, edge_dict)
        predecessor: dict[str, tuple[str, dict[str, Any]]] = {}

        if depth > 0:
            current_level = [root_id]
            for current_depth in range(1, depth + 1):
                next_level: list[str] = []
                for nid in current_level:
                    for edge in self.incident_edges.get(nid, []):
                        src = str(edge.get("source_id", ""))
                        tgt = str(edge.get("target_id", ""))
                        nbr = tgt if src == nid else src
                        if not nbr or nbr not in self.nodes:
                            continue
                        if nbr not in visited_nodes:
                            visited_nodes.add(nbr)
                            distance[nbr] = current_depth
                            predecessor[nbr] = (nid, edge)
                            next_level.append(nbr)
                current_level = next_level
                if not current_level:
                    break

        # 3. Build response nodes with deterministic NodeContextResponse
        store = self.to_graph_store()
        resp_nodes: list[GraphNodeResponse] = []

        for nid in visited_nodes:
            n_data = self.nodes.get(nid)
            if not n_data:
                continue
            props = n_data.get("properties", {})
            entity_type = str(n_data.get("entity_type", "Unknown"))
            label = (
                props.get("full_name")
                or props.get("fir_number")
                or props.get("phone_number")
                or props.get("account_number")
                or props.get("evidence_number")
                or props.get("name")
                or nid
            )
            in_deg = len(store.radj.get(nid, []))
            out_deg = len(store.adj.get(nid, []))

            # Deterministic context calculation
            if nid == root_id:
                context = NodeContextResponse(
                    presence_type=NodePresenceType.DIRECT_CASE,
                    reason=f"Target investigation case {root_fir}.",
                    source_ids=[root_fir],
                    relationship_types=[],
                    distance_from_case=0,
                    path=[root_id],
                    readable_path=root_fir,
                )
            else:
                # Reconstruct path from root_id to nid
                path_node_ids: list[str] = []
                path_edges: list[dict[str, Any]] = []
                curr = nid
                while curr != root_id and curr in predecessor:
                    path_node_ids.append(curr)
                    parent, edge_used = predecessor[curr]
                    path_edges.append(edge_used)
                    curr = parent
                path_node_ids.append(root_id)
                path_node_ids.reverse()
                path_edges.reverse()

                dist = distance.get(nid, len(path_node_ids) - 1)
                incoming_edge = path_edges[-1] if path_edges else {}
                edge_type = str(incoming_edge.get("edge_type", "CONNECTED_TO"))
                prov = incoming_edge.get("provenance", {}) or {}
                source_type = str(prov.get("source_type", ""))
                source_id = str(prov.get("source_id", ""))
                extracted_fact = str(prov.get("extracted_fact", ""))
                edge_props = incoming_edge.get("properties", {}) or {}

                rel_types = [edge_type]
                src_ids: list[str] = [source_id] if source_id else []

                if dist == 1:
                    if entity_type in ("Evidence", "EVIDENCE") or edge_type == "HAS_EVIDENCE":
                        presence_type = NodePresenceType.EVIDENCE
                        ev_num = str(props.get("evidence_number") or label)
                        reason = f"Direct evidence item ({ev_num}) seized and indexed under {root_fir}."
                        if ev_num and ev_num not in src_ids:
                            src_ids.insert(0, ev_num)
                        if root_fir not in src_ids:
                            src_ids.append(root_fir)
                    elif edge_type in ("ACCUSED_IN", "INVOLVED_IN"):
                        presence_type = NodePresenceType.DIRECT_CASE
                        reason = f"Named as accused directly in {root_fir}."
                        if root_fir not in src_ids:
                            src_ids.append(root_fir)
                    elif edge_type == "VICTIM_IN":
                        presence_type = NodePresenceType.DIRECT_CASE
                        reason = f"Complainant / victim registered in {root_fir}."
                        if root_fir not in src_ids:
                            src_ids.append(root_fir)
                    else:
                        presence_type = NodePresenceType.DIRECT_CASE
                        reason = f"Direct relationship ({edge_type}) attached to {root_fir}."
                        if root_fir not in src_ids:
                            src_ids.append(root_fir)
                else:
                    # Multi-hop expansion (dist >= 2)
                    if source_type == "INTEL_REPORT" or source_id.startswith("INTEL") or edge_type in ("CO_ACCUSED", "MEMBER_OF", "AFFILIATED_WITH"):
                        presence_type = NodePresenceType.INTELLIGENCE_EXPANSION
                        if extracted_fact:
                            reason = f"Intelligence expansion via {source_id or 'intel report'}: {extracted_fact}."
                        else:
                            reason = f"Reached through intelligence network association ({source_id or 'INTEL'})."
                    elif source_type == "CDR" or source_id.startswith("CDR") or edge_props.get("channel") in ("VOICE_CALL", "SMS") or edge_type in ("CALLED", "COMMUNICATED_WITH"):
                        presence_type = NodePresenceType.CDR_CONNECTION
                        if extracted_fact:
                            reason = f"Telecommunications link via {source_id or 'CDR'}: {extracted_fact}."
                        else:
                            call_count = edge_props.get("call_count", "")
                            count_text = f" ({call_count} calls)" if call_count else ""
                            reason = f"Telecommunications contact{count_text} logged in {source_id or 'CDR sweep'}."
                    elif entity_type in ("Case", "CASE") or edge_type in ("ACCUSED_IN", "INVOLVED_IN", "VICTIM_IN", "HAS_EVIDENCE"):
                        presence_type = NodePresenceType.CROSS_CASE
                        other_fir = str(props.get("fir_number") or source_id or nid)
                        reason = f"Cross-case bridge connection linked to case {other_fir}."
                        if other_fir not in src_ids:
                            src_ids.append(other_fir)
                    elif source_type in ("BANK_TXN", "BANK") or edge_props.get("amount") or edge_type in ("TRANSFERRED_TO", "TRANSACTION"):
                        presence_type = NodePresenceType.INTELLIGENCE_EXPANSION
                        amt = edge_props.get("amount")
                        amt_text = f" (INR {amt})" if amt else ""
                        reason = f"Financial transaction trail{amt_text} logged under {source_id or 'banking records'}."
                    else:
                        presence_type = NodePresenceType.OTHER
                        reason = extracted_fact or f"Connected entity in expanded graph ({dist} hops from case)."

                # Build readable path
                path_labels: list[str] = []
                for p_idx, step_nid in enumerate(path_node_ids):
                    step_n = self.nodes.get(step_nid, {})
                    step_props = step_n.get("properties", {})
                    step_lbl = str(
                        step_props.get("full_name")
                        or step_props.get("fir_number")
                        or step_props.get("phone_number")
                        or step_props.get("account_number")
                        or step_props.get("evidence_number")
                        or step_props.get("name")
                        or step_nid
                    )
                    if p_idx > 0:
                        step_edge = path_edges[p_idx - 1]
                        step_doc = str(step_edge.get("provenance", {}).get("source_id") or step_edge.get("edge_type") or "rel")
                        path_labels.append(f"[{step_doc}]")
                    path_labels.append(step_lbl)
                readable_path = " → ".join(path_labels)

                context = NodeContextResponse(
                    presence_type=presence_type,
                    reason=reason,
                    source_ids=src_ids,
                    relationship_types=rel_types,
                    distance_from_case=dist,
                    path=path_node_ids,
                    readable_path=readable_path,
                )

            resp_nodes.append(
                GraphNodeResponse(
                    id=nid,
                    entity_type=entity_type,
                    label=label,
                    properties=props,
                    degree=in_deg + out_deg,
                    confidence=float(props.get("confidence", 1.0)),
                    context=context,
                )
            )

        # 4. Build response edges (only between visited nodes)
        resp_edges: list[GraphEdgeResponse] = []
        for e in self.edges:
            src = str(e.get("source_id"))
            tgt = str(e.get("target_id"))
            if src in visited_nodes and tgt in visited_nodes:
                prov = dict(e.get("provenance") or {})
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
            case_id=root_fir,
            depth=depth,
        )

    # ── Audit Logging ─────────────────────────────────────────────────────────

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
        self._save_state()
        return entry

    def list_audit_events(self, limit: int = 100) -> list[AuditLogEntry]:
        sorted_events = sorted(
            self.audit_events,
            key=lambda e: _parse_datetime(e.get("timestamp")),
            reverse=True,
        )
        return [AuditLogEntry(**e) for e in sorted_events[:limit]]

    # ── Document Repository Methods (P1-A) ──────────────────────────────────

    def store_document(self, doc_record: dict[str, Any]) -> dict[str, Any]:
        """Store or update a document record in repository."""
        doc_id = doc_record["document_id"]
        self.documents[doc_id] = doc_record
        return doc_record

    def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """Retrieve a document record by its ID."""
        return self.documents.get(doc_id)

    def get_document_by_hash(self, content_hash: str) -> dict[str, Any] | None:
        """Find an existing document with the identical content hash."""
        for doc in self.documents.values():
            if doc.get("content_hash") == content_hash:
                return doc
        return None

    def list_documents(self, case_id: str | None = None) -> list[dict[str, Any]]:
        """List documents, optionally filtered by case_id."""
        docs = list(self.documents.values())
        if case_id is not None:
            docs = [d for d in docs if d.get("case_id") == case_id]
        return sorted(docs, key=lambda d: str(d.get("uploaded_at", "")), reverse=True)

    # ── Candidate Intelligence & Entity Extraction Methods (P1-B) ───────────

    def store_candidate_extraction(self, extraction_record: dict[str, Any]) -> dict[str, Any]:
        """Store or update candidate extraction results for a document."""
        doc_id = extraction_record["document_id"]
        self.candidate_extractions[doc_id] = extraction_record
        return extraction_record

    def get_candidate_extraction(self, doc_id: str) -> dict[str, Any] | None:
        """Retrieve candidate extraction results for a document."""
        return self.candidate_extractions.get(doc_id)

    def get_candidate_entity(self, candidate_id: str) -> dict[str, Any] | None:
        """Retrieve a specific candidate entity by candidate_id across all extractions."""
        for extraction in self.candidate_extractions.values():
            for entity in extraction.get("candidate_entities", []):
                if entity.get("candidate_id") == candidate_id:
                    return entity
        return None

    def get_candidate_relationship(self, relationship_id: str) -> dict[str, Any] | None:
        """Retrieve a specific candidate relationship by relationship_id across all extractions."""
        for extraction in self.candidate_extractions.values():
            for rel in extraction.get("candidate_relationships", []):
                if rel.get("candidate_relationship_id") == relationship_id:
                    return rel
        return None

    # ── Candidate Review & Investigator Decisions (P1-C) ─────────────────────

    def store_candidate_decision(self, decision: dict[str, Any]) -> dict[str, Any]:
        """Store an investigator decision on a candidate entity or relationship."""
        cand_id = str(decision["candidate_id"])
        self.candidate_decisions.setdefault(cand_id, []).append(decision)
        self._save_state()
        return decision

    def get_candidate_decisions(self, candidate_id: str) -> list[dict[str, Any]]:
        """Retrieve the decision history for a given candidate entity or relationship."""
        return list(self.candidate_decisions.get(candidate_id, []))

    def update_candidate_entity_status(
        self,
        candidate_id: str,
        status: str,
        resulting_graph_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Update the review status and resulting authoritative graph ID of a candidate entity."""
        for extraction in self.candidate_extractions.values():
            for entity in extraction.get("candidate_entities", []):
                if entity.get("candidate_id") == candidate_id:
                    entity["status"] = status
                    if resulting_graph_id is not None:
                        entity["resulting_graph_id"] = resulting_graph_id
                    self._save_state()
                    return entity
        return None

    def update_candidate_relationship_status(
        self,
        relationship_id: str,
        status: str,
        resulting_edge_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Update the review status and resulting authoritative edge ID of a candidate relationship."""
        for extraction in self.candidate_extractions.values():
            for rel in extraction.get("candidate_relationships", []):
                if rel.get("candidate_relationship_id") == relationship_id:
                    rel["status"] = status
                    if resulting_edge_id is not None:
                        rel["resulting_edge_id"] = resulting_edge_id
                    self._save_state()
                    return rel
        return None
