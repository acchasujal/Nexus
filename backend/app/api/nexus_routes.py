"""backend/app/api/nexus_routes.py

FastAPI routes for the frozen NEXUS prototype contract (/api/v1/nexus/*).
Implements:
  - Ingest & Demo Reset (/nexus/ingest, /nexus/demo/reset)
  - Entity Fusion Candidates & Decisions (/nexus/resolution/*)
  - Global Network Explorer & Diff (/nexus/network, /nexus/network/diff)
  - Edge Evidence Inspection (/nexus/relationships/{id}/evidence)
  - Cross-Case Pathfinder (/nexus/path)
  - Lead Inbox & Decisions (/nexus/leads/*)
  - Grounded Copilot with Refusal Gate (/nexus/copilot/query)
  - Global Search (/nexus/search)
  - Source Record Registry (/nexus/sources/{id})
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
import os
import shutil
import tempfile
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from backend.app.api.dependencies import (
    get_audit_service,
    get_copilot_service,
    get_ingestion_service,
    get_principal,
    get_repository,
    get_request_id,
    get_graph_repository,
)
from backend.app.auth.principal import Principal
from backend.app.core.graph.enums import ResolutionStatus
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.db.ingestion.pipeline import CsvIngestionPipeline
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.copilot_service import CopilotService
from backend.app.services.ingestion_service import IngestionService
from backend.app.db.ingestion.contracts import UploadedSource, SourceType
from shared.contracts.api import CopilotQueryRequest, GroundedCitation, NetworkGraphResponse

# ── Pydantic Models ────────────────────────────────────────────────────────────

class NexusSourceRecord(BaseModel):
    id: str
    batch_id: str
    source_type: str
    locator: str
    raw_excerpt: str
    occurred_at: str


class NexusGraphNode(BaseModel):
    id: str
    entity_type: str
    label: str
    case_ids: list[str]
    badges: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class NexusGraphEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    edge_type: str
    weight: float = 1.0
    confidence: float = 1.0
    derivation_class: Literal["FACT", "DERIVED", "HYPOTHESIS"] = "FACT"
    recorded_at: str
    case_ids: list[str]
    properties: dict[str, Any] = Field(default_factory=dict)


class NexusNetworkResponse(BaseModel):
    snapshot_id: str
    state: Literal["before", "after"]
    nodes: list[NexusGraphNode]
    edges: list[NexusGraphEdge]
    total_nodes: int
    total_edges: int


class SnapshotDiffResponse(BaseModel):
    before_snapshot_id: str
    after_snapshot_id: str
    added_node_ids: list[str]
    removed_node_ids: list[str]
    changed_node_ids: list[str]
    added_edge_ids: list[str]
    removed_edge_ids: list[str]
    changed_edge_ids: list[str]


class ResolutionCandidateRecord(BaseModel):
    node_id: str
    entity_type: str
    label: str
    case_ids: list[str]
    properties: dict[str, Any]
    source_records: list[NexusSourceRecord]


class CandidateReason(BaseModel):
    field: str
    detail: str
    weight: float


class CandidateConflict(BaseModel):
    field: str
    left_value: str
    right_value: str


class ResolutionCandidate(BaseModel):
    id: str
    score: float
    status: Literal["PENDING", "CONFIRMED", "REJECTED", "DEFERRED"]
    left: ResolutionCandidateRecord
    right: ResolutionCandidateRecord
    reasons: list[CandidateReason]
    conflicts: list[CandidateConflict]
    decided_at: str | None = None
    decided_by: str | None = None


class ResolutionDecisionRequest(BaseModel):
    decision: Literal["CONFIRM", "REJECT", "DEFER"]
    decided_by: str = "Investigating Officer"
    note: str | None = None


class ResolutionDecisionResponse(BaseModel):
    candidate_id: str
    status: str
    affected_node_ids: list[str]
    new_snapshot_id: str | None = None


class DerivationStep(BaseModel):
    step: int
    rule: str
    inputs: list[str]


class NexusEdgeEvidenceResponse(BaseModel):
    relationship_id: str
    edge_type: str
    source_label: str
    target_label: str
    derivation_class: Literal["FACT", "DERIVED", "HYPOTHESIS"]
    confidence: float
    recorded_at: str
    source_records: list[NexusSourceRecord]
    derivation_chain: list[DerivationStep]


class NexusPathResponse(BaseModel):
    found: bool
    source_id: str
    target_id: str
    node_ids: list[str]
    edge_ids: list[str]
    hops: int
    explanation: str
    evidence_ids: list[str]


class NexusLeadPath(BaseModel):
    node_ids: list[str]
    edge_ids: list[str]


class NexusLead(BaseModel):
    id: str
    title: str
    rule_id: str
    explanation: str
    severity: str
    derivation_class: Literal["FACT", "DERIVED", "HYPOTHESIS"]
    case_ids: list[str]
    status: Literal["NEW", "ACCEPTED", "REJECTED"]
    path: NexusLeadPath
    evidence_ids: list[str]
    created_at: str
    decided_at: str | None = None
    decided_by: str | None = None
    decision_note: str | None = None


class NexusLeadDecisionRequest(BaseModel):
    decision: Literal["ACCEPT", "REJECT"]
    decided_by: str = "Investigating Officer"
    note: str | None = None


class NexusCopilotResponse(BaseModel):
    query: str
    answer: str
    is_refusal: bool
    refusal_reason: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    reasoning_path: list[str] = Field(default_factory=list)
    intent: str | None = None
    grounded_citations: list[GroundedCitation] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    graph_context: NetworkGraphResponse | None = None
    case_id: str | None = None


class SearchCaseItem(BaseModel):
    id: str
    fir_number: str
    title: str
    score: float = 1.0


class SearchEntityItem(BaseModel):
    id: str
    label: str
    entity_type: str
    case_ids: list[str]
    score: float = 1.0
    subtext: str | None = None


class NexusSearchResponse(BaseModel):
    query: str
    cases: list[SearchCaseItem]
    entities: list[SearchEntityItem]


class ExtractionSummary(BaseModel):
    persons: int
    phones: int
    accounts: int
    events: int
    relationships: int


class IngestFileItem(BaseModel):
    source_type: str
    file_name: str


class NexusIngestRequest(BaseModel):
    files: list[IngestFileItem]


class NexusIngestResponse(BaseModel):
    batch_id: str
    source_type: str
    ingested_count: int = 3
    extraction_summary: ExtractionSummary
    snapshot_id: str


# ── Router Definition ──────────────────────────────────────────────────────────

def create_nexus_router() -> APIRouter:
    router = APIRouter(tags=["nexus"])

    @router.post("/nexus/ingest", response_model=NexusIngestResponse)
    async def ingest_csv_files(
        files: list[UploadFile] = File(...),
        principal: Principal = Depends(get_principal),
        ingestion_service: IngestionService = Depends(get_ingestion_service),
    ) -> NexusIngestResponse:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided.")

        sources: list[UploadedSource] = []
        for uf in files:
            if not uf.filename or not uf.filename.lower().endswith(".csv"):
                raise HTTPException(status_code=415, detail=f"File {uf.filename} must be a .csv file.")
            
            # Infer source type for legacy endpoint by looking at filename
            fname = uf.filename.lower()
            if "fir" in fname:
                stype = SourceType.FIR
            elif "cdr" in fname:
                stype = SourceType.CDR
            elif "bank" in fname:
                stype = SourceType.BANK_TXN
            else:
                stype = SourceType.INTEL_REPORT
                
            content = await uf.read()
            if len(content) > 5 * 1024 * 1024:
                raise HTTPException(status_code=413, detail=f"File {uf.filename} exceeds 5MB limit.")
            if not content:
                raise HTTPException(status_code=400, detail=f"File {uf.filename} is empty.")
                
            sources.append(UploadedSource(
                source_type=stype,
                file_name=uf.filename,
                data=content
            ))

        try:
            resp = await ingestion_service.ingest_files(
                user_id=principal.user_id,
                user_role=principal.role.value if hasattr(principal.role, 'value') else str(principal.role),
                sources=sources
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
            
        if resp.status.value == "FAILED":
            raise HTTPException(status_code=422, detail="Fatal validation error during ingestion.")

        return NexusIngestResponse(
            batch_id=resp.batch_id,
            source_type=sources[0].source_type.value,
            ingested_count=resp.summary.received,
            extraction_summary=ExtractionSummary(
                persons=resp.summary.nodes_created,
                phones=0,
                accounts=0,
                events=0,
                relationships=resp.summary.relationships_created
            ),
            snapshot_id="SNAP-BASE-001",
        )

    @router.post("/nexus/demo/reset")
    def reset_demo_state(
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
        repo: InMemoryBackendRepository = Depends(get_repository),
        graph_repo: GraphRepository = Depends(get_graph_repository),
    ) -> dict[str, str]:
        repo.clear()
        graph_repo.replace_store(repo.to_graph_store())
        audit.record(
            event_type=AuditEventType.SEED_COMPLETED,
            actor_id=principal.user_id,
            details={"status": "reset"},
        )
        return {"status": "reset"}

    @router.get("/nexus/resolution/candidates", response_model=list[ResolutionCandidate])
    def get_resolution_candidates(
        principal: Principal = Depends(get_principal),
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> list[ResolutionCandidate]:
        results = []
        for c_id, c_data in repo.review_candidates.items():
            left_node_id = c_data["incoming_record_id"]
            right_node_id = c_data["candidate_node_id"]
            source_ids = c_data.get("source_record_ids", [])
            
            def make_rec(nid: str, sids: list[str]) -> ResolutionCandidateRecord:
                node = repo.nodes.get(nid, {})
                props = node.get("properties", {})
                return ResolutionCandidateRecord(
                    node_id=nid,
                    entity_type=node.get("entity_type", "Person"),
                    label=str(props.get("full_name") or props.get("name") or nid),
                    case_ids=[str(props.get("case_id"))] if props.get("case_id") else [],
                    properties=props,
                    source_records=[NexusSourceRecord(**repo.source_records[rid]) for rid in sids if rid in repo.source_records]
                )
                
            reasons = [CandidateReason(field=f, detail=f"Matched on {f}", weight=1.0) for f in c_data.get("matched_fields", [])]
            if c_data.get("reason"):
                reasons.append(CandidateReason(field="general", detail=c_data["reason"], weight=1.0))
                
            conflicts = [CandidateConflict(field=f, left_value="Incoming", right_value="Existing") for f in c_data.get("conflicting_fields", [])]

            results.append(ResolutionCandidate(
                id=c_id,
                score=c_data.get("confidence", 0.0),
                status=c_data.get("status", "PENDING"),
                left=make_rec(left_node_id, source_ids),
                right=make_rec(right_node_id, []),
                reasons=reasons,
                conflicts=conflicts,
            ))
        return results

    @router.post("/nexus/resolution/{candidate_id}/decision", response_model=ResolutionDecisionResponse)
    def decide_resolution_candidate(
        candidate_id: str,
        body: ResolutionDecisionRequest,
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
        repo: InMemoryBackendRepository = Depends(get_repository),
        graph_repo: GraphRepository = Depends(get_graph_repository),
    ) -> ResolutionDecisionResponse:
        c_data = repo.review_candidates.get(candidate_id)
        if not c_data:
            raise HTTPException(status_code=404, detail="Candidate not found")

        status_map = {"CONFIRM": "CONFIRMED", "REJECT": "REJECTED", "DEFER": "DEFERRED"}
        new_status = status_map[body.decision]
        repo.update_candidate_status(candidate_id, new_status)
        
        affected = []
        if body.decision == "CONFIRM":
            repo.merge_nodes(c_data["incoming_record_id"], c_data["candidate_node_id"])
            graph_repo.replace_store(repo.to_graph_store())
            affected = [c_data["candidate_node_id"]]

        audit.record(
            event_type=AuditEventType.ENTITY_RESOLUTION_EXECUTED,
            actor_id=principal.user_id,
            entity_type="ResolutionCandidate",
            entity_id=candidate_id,
            details={"decision": body.decision, "note": body.note},
        )

        return ResolutionDecisionResponse(
            candidate_id=candidate_id,
            status=new_status,
            affected_node_ids=affected,
            new_snapshot_id="SNAP-REAL",
        )

    @router.get("/nexus/network", response_model=NexusNetworkResponse)
    def get_nexus_network(
        snapshot: Literal["before", "after"] = Query("before"),
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> NexusNetworkResponse:
        nodes = []
        for nid, n in repo.nodes.items():
            props = n.get("properties", {})
            case_ids = [str(props.get("case_id"))] if props.get("case_id") else []
            nodes.append(NexusGraphNode(
                id=nid,
                entity_type=n.get("entity_type", "Person"),
                label=str(props.get("full_name") or props.get("name") or nid),
                case_ids=case_ids,
                properties=props,
                badges=n.get("badges", []),
            ))

        edges = []
        for e in repo.edges:
            eid = e.get("id") or f"edge-{e['source_id']}-{e['target_id']}"
            edges.append(NexusGraphEdge(
                id=eid,
                source_id=e["source_id"],
                target_id=e["target_id"],
                edge_type=e.get("edge_type", "CONNECTED_TO"),
                weight=float(e.get("weight", 1.0)),
                confidence=float(e.get("confidence", 1.0)),
                derivation_class="FACT",
                recorded_at=datetime.now(timezone.utc).isoformat(),
                case_ids=[],
                properties=e.get("properties", {}),
            ))

        audit.record(
            event_type=AuditEventType.NETWORK_EXPLORED,
            actor_id=principal.user_id,
            details={"snapshot": snapshot, "total_nodes": len(nodes), "total_edges": len(edges)},
        )

        return NexusNetworkResponse(
            snapshot_id="SNAP-REAL",
            state=snapshot,
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
        )

    @router.get("/nexus/network/diff", response_model=SnapshotDiffResponse)
    def get_snapshot_diff(
        principal: Principal = Depends(get_principal),
    ) -> SnapshotDiffResponse:
        # Dynamic diff is outside current scope, return empty for now
        return SnapshotDiffResponse(
            before_snapshot_id="SNAP-BEFORE-001",
            after_snapshot_id="SNAP-AFTER-001",
            added_node_ids=[],
            removed_node_ids=[],
            changed_node_ids=[],
            added_edge_ids=[],
            removed_edge_ids=[],
            changed_edge_ids=[],
        )

    @router.get("/nexus/relationships/{rel_id}/evidence", response_model=NexusEdgeEvidenceResponse)
    def get_relationship_evidence(
        rel_id: str,
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> NexusEdgeEvidenceResponse:
        edge = None
        for e in repo.edges:
            eid = e.get("id") or f"edge-{e['source_id']}-{e['target_id']}"
            if eid == rel_id:
                edge = e
                break

        if not edge:
            raise HTTPException(
                status_code=404,
                detail=f"Evidence chain for relationship {rel_id} is unavailable in this snapshot.",
            )

        props = edge.get("properties", {})
        rec_ids = props.get("evidence_ids", [])
        records = [NexusSourceRecord(**repo.source_records[rid]) for rid in rec_ids if rid in repo.source_records]

        def get_label(nid: str) -> str:
            n = repo.nodes.get(nid, {})
            p = n.get("properties", {})
            return str(p.get("full_name") or p.get("name") or nid)

        source_label = get_label(edge["source_id"])
        target_label = get_label(edge["target_id"])
        
        deriv_class = edge.get("derivation_class", "FACT")

        derivation_chain: list[DerivationStep] = (
            [DerivationStep(step=1, rule="direct_import", inputs=rec_ids)]
            if deriv_class == "FACT"
            else [
                DerivationStep(step=1, rule="derived_rule", inputs=rec_ids),
            ]
        )

        audit.record(
            event_type=AuditEventType.EVIDENCE_VIEWED,
            actor_id=principal.user_id,
            entity_type="Relationship",
            entity_id=rel_id,
            details={"derivation_class": deriv_class, "records_count": len(records)},
        )

        return NexusEdgeEvidenceResponse(
            relationship_id=rel_id,
            edge_type=edge.get("edge_type", "CONNECTED_TO"),
            source_label=source_label,
            target_label=target_label,
            derivation_class=deriv_class,
            confidence=float(edge.get("confidence", 1.0)),
            recorded_at=datetime.now(timezone.utc).isoformat(),
            source_records=records,
            derivation_chain=derivation_chain,
        )

    @router.get("/nexus/path", response_model=NexusPathResponse)
    def find_nexus_path(
        source: str = Query("", description="Source node or case identifier"),
        target: str = Query("", description="Target node or case identifier"),
        max_depth: int = Query(6, ge=1, le=10, description="Maximum BFS traversal depth"),
        principal: Principal = Depends(get_principal),
        repo: InMemoryBackendRepository = Depends(get_repository),
        audit: AuditService = Depends(get_audit_service),
    ) -> NexusPathResponse:
        src = (source or "").strip()
        tgt = (target or "").strip()

        if not src or not tgt:
            return NexusPathResponse(
                found=False,
                source_id=src,
                target_id=tgt,
                node_ids=[],
                edge_ids=[],
                hops=0,
                explanation="Source and target entity identifiers are required.",
                evidence_ids=[],
            )

        if src == tgt:
            return NexusPathResponse(
                found=False,
                source_id=src,
                target_id=tgt,
                node_ids=[src],
                edge_ids=[],
                hops=0,
                explanation=f"Source and target entities are identical ('{src}'). No traversal required.",
                evidence_ids=[],
            )

        # Load nodes from authoritative repository
        current_nodes: list[NexusGraphNode] = []
        seen_node_ids: set[str] = set()

        graph_store = repo.to_graph_store()
        for nid, node_rec in graph_store.nodes.items():
            if nid in seen_node_ids:
                continue
            seen_node_ids.add(nid)
            props = node_rec.properties or {}
            etype = node_rec.entity_type
            if etype == "Case":
                label = str(props.get("fir_number") or props.get("title") or nid)
            elif etype == "Person":
                label = str(props.get("full_name") or nid)
            elif etype == "Phone":
                label = str(props.get("phone_number") or props.get("number") or nid)
            elif etype == "Account":
                label = str(props.get("account_number") or props.get("bank") or nid)
            elif etype == "Vehicle":
                label = str(props.get("vehicle_number") or props.get("registration") or nid)
            elif etype == "Location":
                label = str(props.get("address_text") or props.get("district") or nid)
            elif etype == "Evidence":
                label = str(props.get("evidence_number") or props.get("description") or nid)
            elif etype == "IntelligenceReport":
                label = str(props.get("report_id") or props.get("title") or nid)
            else:
                label = str(props.get("full_name") or props.get("title") or props.get("name") or props.get("label") or nid)

            case_ids_list = [str(props["case_id"])] if "case_id" in props and props["case_id"] else []
            current_nodes.append(
                NexusGraphNode(
                    id=nid,
                    entity_type=etype,
                    label=label,
                    case_ids=case_ids_list,
                    properties=props,
                )
            )

        # Load edges from authoritative repository
        current_edges: list[NexusGraphEdge] = []
        seen_edge_ids: set[str] = set()

        for edge_rec in repo.edges:
            eid = edge_rec.get("id") or f"edge-{edge_rec['source_id']}-{edge_rec['target_id']}"
            if eid in seen_edge_ids:
                continue
            seen_edge_ids.add(eid)
            src_id = edge_rec["source_id"]
            tgt_id = edge_rec["target_id"]
            e_type = edge_rec.get("edge_type", "CONNECTED_TO")
            e_props = edge_rec.get("properties", {})
            current_edges.append(
                NexusGraphEdge(
                    id=eid,
                    source_id=src_id,
                    target_id=tgt_id,
                    edge_type=e_type,
                    weight=float(edge_rec.get("weight", 1.0)),
                    confidence=float(edge_rec.get("confidence", 1.0)),
                    derivation_class="FACT",
                    recorded_at=datetime.now(timezone.utc).isoformat(),
                    case_ids=[],
                    properties=e_props,
                )
            )

        nodes_by_id = {n.id: n for n in current_nodes}

        # Case-insensitive / label fallback lookup
        def find_node(val: str) -> NexusGraphNode | None:
            if val in nodes_by_id:
                return nodes_by_id[val]
            val_lower = val.lower()
            for n in current_nodes:
                if n.id.lower() == val_lower or n.label.lower() == val_lower:
                    return n
                if n.properties.get("fir_number", "").lower() == val_lower:
                    return n
            return None

        src_node = find_node(src)
        tgt_node = find_node(tgt)

        if not src_node:
            return NexusPathResponse(
                found=False,
                source_id=src,
                target_id=tgt,
                node_ids=[],
                edge_ids=[],
                hops=0,
                explanation=f"Source entity '{src}' was not found in the active investigation graph snapshot.",
                evidence_ids=[],
            )

        if not tgt_node:
            return NexusPathResponse(
                found=False,
                source_id=src,
                target_id=tgt,
                node_ids=[],
                edge_ids=[],
                hops=0,
                explanation=f"Target entity '{tgt}' was not found in the active investigation graph snapshot.",
                evidence_ids=[],
            )

        resolved_src_id = src_node.id
        resolved_tgt_id = tgt_node.id

        if resolved_src_id == resolved_tgt_id:
            return NexusPathResponse(
                found=False,
                source_id=resolved_src_id,
                target_id=resolved_tgt_id,
                node_ids=[resolved_src_id],
                edge_ids=[],
                hops=0,
                explanation="Source and target resolve to the same node in the graph.",
                evidence_ids=[],
            )

        # Build bidirectional adjacency map from active snapshot edges
        # adj[node_id] = list of (neighbor_id, edge_id, edge_type, evidence_ids)
        adj: dict[str, list[tuple[str, str, str, list[str]]]] = {}
        for edge in current_edges:
            ev_list = edge.properties.get("evidence_ids", []) if edge.properties else []
            if not isinstance(ev_list, list):
                ev_list = [str(ev_list)]
            adj.setdefault(edge.source_id, []).append((edge.target_id, edge.id, edge.edge_type, ev_list))
            adj.setdefault(edge.target_id, []).append((edge.source_id, edge.id, edge.edge_type, ev_list))

        # BFS shortest path search
        from collections import deque
        queue: deque[tuple[str, list[str], list[str], list[str]]] = deque([
            (resolved_src_id, [resolved_src_id], [], [])
        ])
        visited: set[str] = {resolved_src_id}
        found_path: tuple[list[str], list[str], list[str]] | None = None

        while queue:
            curr, path_nodes, path_edges, path_evs = queue.popleft()
            if len(path_nodes) - 1 >= max_depth:
                continue

            for nxt, edge_id, edge_type, evs in adj.get(curr, []):
                if nxt in visited:
                    continue
                next_nodes = [*path_nodes, nxt]
                next_edges = [*path_edges, edge_id]
                next_evs = [*path_evs, *evs]

                if nxt == resolved_tgt_id:
                    found_path = (next_nodes, next_edges, next_evs)
                    break

                visited.add(nxt)
                queue.append((nxt, next_nodes, next_edges, next_evs))

            if found_path:
                break

        if found_path:
            p_nodes, p_edges, p_evs = found_path
            hops = len(p_nodes) - 1
            unique_evidence = list(dict.fromkeys(p_evs))

            labels = [nodes_by_id[nid].label if nid in nodes_by_id else nid for nid in p_nodes]
            explanation = f"Discovered {hops}-hop evidence connection: {' ➔ '.join(labels)}."

            audit.record(
                event_type=AuditEventType.GRAPH_QUERY_EXECUTED,
                actor_id=principal.user_id,
                details={
                    "path_found": True,
                    "source": resolved_src_id,
                    "target": resolved_tgt_id,
                    "hops": hops,
                    "nodes": p_nodes,
                },
            )

            return NexusPathResponse(
                found=True,
                source_id=resolved_src_id,
                target_id=resolved_tgt_id,
                node_ids=p_nodes,
                edge_ids=p_edges,
                hops=hops,
                explanation=explanation,
                evidence_ids=unique_evidence,
            )

        # Path not found within depth limit
        explanation = (
            f"No connection found between '{src_node.label}' and '{tgt_node.label}' within {max_depth} hops "
            "in the current investigation snapshot."
        )

        return NexusPathResponse(
            found=False,
            source_id=resolved_src_id,
            target_id=resolved_tgt_id,
            node_ids=[],
            edge_ids=[],
            hops=0,
            explanation=explanation,
            evidence_ids=[],
        )

    @router.get("/nexus/leads", response_model=list[NexusLead])
    def get_leads(
        principal: Principal = Depends(get_principal),
    ) -> list[NexusLead]:
        return []

    @router.post("/nexus/leads/{lead_id}/decision", response_model=NexusLead)
    def decide_lead(
        lead_id: str,
        body: NexusLeadDecisionRequest,
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
    ) -> NexusLead:
        raise HTTPException(status_code=404, detail="Lead not found")

    @router.post("/nexus/copilot/query", response_model=NexusCopilotResponse)
    def query_copilot(
        body: dict[str, Any],
        principal: Principal = Depends(get_principal),
        copilot_svc: CopilotService = Depends(get_copilot_service),
        request_id: str = Depends(get_request_id),
    ) -> NexusCopilotResponse:
        query_str = str(body.get("query") or "")
        case_id = body.get("case_id") or body.get("investigation_id")
        entity_id = body.get("entity_id")
        max_hops = int(body.get("max_hops", 2))

        req = CopilotQueryRequest(
            query=query_str,
            case_id=case_id,
            investigation_id=case_id,
            entity_id=entity_id,
            max_hops=max_hops,
            is_resolved=True,
        )
        res = copilot_svc.handle_query(req, principal=principal, request_id=request_id)
        return NexusCopilotResponse(
            query=res.query,
            answer=res.answer,
            is_refusal=res.is_refusal,
            refusal_reason=res.refusal_reason,
            evidence_ids=res.evidence_ids,
            reasoning_path=res.reasoning_path,
            intent=res.intent,
            grounded_citations=res.grounded_citations,
            suggested_actions=res.suggested_actions,
            graph_context=res.graph_context,
            case_id=res.case_id,
        )

    @router.get("/nexus/search", response_model=NexusSearchResponse)
    def nexus_search(
        q: str = Query(""),
        principal: Principal = Depends(get_principal),
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> NexusSearchResponse:
        query_raw = q.strip()
        query_str = query_raw.lower()
        if not query_str:
            return NexusSearchResponse(query="", cases=[], entities=[])

        norm_query = re.sub(r"[^\w]", "", query_str)

        # Build candidate nodes list from repo GraphStore nodes
        candidate_nodes: list[NexusGraphNode] = []
        seen_ids: set[str] = set()

        graph_store = repo.to_graph_store()
        for nid, node_rec in graph_store.nodes.items():
            if nid in seen_ids:
                continue
            seen_ids.add(nid)

            props = node_rec.properties or {}
            etype = node_rec.entity_type

            # Derive primary label for GraphStore node records
            if etype == "Case":
                label = str(props.get("fir_number") or props.get("title") or nid)
            elif etype == "Person":
                label = str(props.get("full_name") or nid)
            elif etype == "Phone":
                label = str(props.get("phone_number") or props.get("number") or nid)
            elif etype == "Account":
                label = str(props.get("account_number") or props.get("bank") or nid)
            elif etype == "Vehicle":
                label = str(props.get("vehicle_number") or props.get("registration") or nid)
            elif etype == "Location":
                label = str(props.get("address_text") or props.get("district") or nid)
            elif etype == "Evidence":
                label = str(props.get("evidence_number") or props.get("description") or nid)
            else:
                label = str(props.get("full_name") or props.get("title") or props.get("name") or props.get("label") or nid)

            case_ids_list = [str(props["case_id"])] if "case_id" in props and props["case_id"] else []

            candidate_nodes.append(
                NexusGraphNode(
                    id=nid,
                    entity_type=etype,
                    label=label,
                    case_ids=case_ids_list,
                    properties=props,
                )
            )

        def matches_node(n: NexusGraphNode) -> bool:
            # 1. Substring match on node ID, label, and property values
            if query_str in n.id.lower() or query_str in n.label.lower():
                return True
            for v in n.properties.values():
                val_str = str(v).lower()
                if query_str in val_str:
                    return True

            # 2. Normalized alphanumeric match for identifiers (phones, accounts, vehicles, FIRs, IDs)
            if norm_query and len(norm_query) >= 2:
                norm_id = re.sub(r"[^\w]", "", n.id.lower())
                if norm_query in norm_id:
                    return True
                norm_label = re.sub(r"[^\w]", "", n.label.lower())
                if norm_query in norm_label:
                    return True
                for v in n.properties.values():
                    norm_val = re.sub(r"[^\w]", "", str(v).lower())
                    if norm_query in norm_val:
                        return True
            return False

        def build_subtext(n: NexusGraphNode) -> str | None:
            props = n.properties or {}
            etype = n.entity_type
            case_info = f" • FIR: {', '.join(n.case_ids)}" if n.case_ids else ""

            if etype == "Phone":
                num = props.get("phone_number") or props.get("number") or props.get("phone") or n.label
                seen = props.get("seen_in")
                return f"Phone: {num}{f' ({seen})' if seen else ''}{case_info}"
            elif etype == "Account":
                holder = props.get("holder")
                bank = props.get("bank")
                parts = []
                if holder:
                    parts.append(f"Holder: {holder}")
                if bank:
                    parts.append(bank)
                txt = " • ".join(parts) if parts else "Bank Account"
                return f"{txt}{case_info}"
            elif etype == "Person":
                role = props.get("role")
                phone = props.get("phone_number") or props.get("phone")
                vehicle = props.get("vehicle_number") or props.get("vehicle")
                aliases = props.get("aliases")
                parts = []
                if role:
                    parts.append(str(role))
                if phone:
                    parts.append(f"Phone: {phone}")
                if vehicle:
                    parts.append(f"Vehicle: {vehicle}")
                if aliases and isinstance(aliases, list) and aliases:
                    parts.append(f"Aliases: {', '.join(aliases)}")
                txt = " • ".join(parts) if parts else "Person"
                return f"{txt}{case_info}"
            elif etype == "Vehicle":
                reg = props.get("vehicle_number") or props.get("registration")
                owner = props.get("owner")
                parts = []
                if reg:
                    parts.append(f"Reg: {reg}")
                if owner:
                    parts.append(f"Owner: {owner}")
                txt = " • ".join(parts) if parts else "Vehicle"
                return f"{txt}{case_info}"
            elif etype == "Location":
                district = props.get("district")
                addr = props.get("address_text") or props.get("address")
                parts = [p for p in (district, addr) if p]
                txt = " • ".join(parts) if parts else "Location"
                return f"{txt}{case_info}"

            desc = props.get("description") or props.get("role")
            if desc:
                return f"{desc}{case_info}"
            return f"{etype}{case_info}" if n.case_ids else None

        cases = [
            SearchCaseItem(
                id=n.id,
                fir_number=str(n.properties.get("fir_number") or n.label),
                title=str(n.properties.get("title") or n.properties.get("fir_number") or n.label),
                score=1.0,
            )
            for n in candidate_nodes
            if n.entity_type == "Case" and matches_node(n)
        ]

        entities = [
            SearchEntityItem(
                id=n.id,
                label=n.label,
                entity_type=n.entity_type,
                case_ids=n.case_ids,
                score=1.0,
                subtext=build_subtext(n),
            )
            for n in candidate_nodes
            if n.entity_type != "Case" and matches_node(n)
        ]

        return NexusSearchResponse(query=q, cases=cases, entities=entities)

    @router.get("/nexus/sources/{source_id}", response_model=NexusSourceRecord)
    def get_source_record(
        source_id: str,
        principal: Principal = Depends(get_principal),
    ) -> NexusSourceRecord:
        record = RAW_SOURCES.get(source_id)
        if not record:
            raise HTTPException(status_code=404, detail="Source record not found")
        return record

    return router
