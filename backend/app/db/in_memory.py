"""backend/app/db/in_memory.py

In-memory backend repository for the NEXUS Criminal Intelligence Platform.
Provides fast index lookups, graph traversals, case retrieval, audit logging,
and graph store extraction for analytical algorithms.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from shared.contracts.api import (
    AuditLogEntry,
    EvidenceItemResponse,
    EvidenceProvenanceContract,
    GraphEdgeResponse,
    GraphNodeResponse,
    InvestigationDetailResponse,
    InvestigationSummaryResponse,
    NetworkGraphResponse,
    UserRole,
)


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
        self.audit_events: list[dict[str, Any]] = []
        self.state_path = state_path

        self._load_artifact(artifact_path or self._default_artifact_path())
        self._load_state()
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

    def _load_state(self) -> None:
        if self.state_path is None or not self.state_path.exists():
            return
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            for node_id, patch in raw.get("node_patches", {}).items():
                if node_id in self.nodes:
                    self.nodes[node_id].setdefault("properties", {}).update(patch)
            self.audit_events = list(raw.get("audit_events", []))
        except Exception:
            pass

    def _save_state(self) -> None:
        if self.state_path is None:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "audit_events": self.audit_events,
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

    def get_case_network(self, case_id: str, depth: int = 2) -> NetworkGraphResponse:
        """Extract a multi-hop neighborhood graph centered around a case or entity."""
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

        # Build response nodes and edges
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
                prov = e.get("provenance", {})
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
        entry = AuditLogEntry(
            id=f"audit-{_utcnow().timestamp()}-{len(self.audit_events)+1}",
            user_id=user_id,
            user_role=user_role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
            timestamp=_utcnow(),
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
