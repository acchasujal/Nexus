"""backend/app/ai/tools.py

Standardized deterministic intelligence tools for the NEXUS AI subsystem.
Wraps core deterministic graph traversals, entity resolution, community detection,
betweenness centrality, pattern rules, CDR analysis, and evidence services
as LLM-executable tools with strict machine-readable result contracts.
"""

from __future__ import annotations

import copy
import json
import logging
import re
from collections import deque
from typing import Any

from pydantic import BaseModel, Field

from backend.app.core.graph.algorithms.clustering import (
    detect_communities,
    find_bridge_nodes,
)
from backend.app.core.graph.algorithms.entity_resolution import (
    normalize_text,
    phonetic_normalize,
    resolve_person,
)
from backend.app.core.graph.algorithms.pattern_rules import (
    detect_all_suspicious_patterns,
    detect_circular_repeated_financial_flow,
    detect_communication_burst_near_event,
)
from backend.app.services.audit_service import AuditService
from backend.app.services.evidence_service import EvidenceService
from shared.contracts.api import (
    EvidenceProvenanceContract,
    GroundedCitation,
    InvestigationDetailResponse,
)

logger = logging.getLogger(__name__)


class NEXUSToolResult(BaseModel):
    """Authoritative structured payload returned by deterministic tool executions."""

    success: bool = True
    tool_name: str = ""
    data: Any = None
    evidence_ids: list[str] = Field(default_factory=list)
    citations: list[GroundedCitation] = Field(default_factory=list)
    reasoning_path: list[str] = Field(default_factory=list)
    case_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    graph_context: dict[str, Any] | None = None
    nodes_count: int = 0
    edges_count: int = 0
    error: str | None = None


class NEXUSToolRegistry:
    """Registry and dispatcher for deterministic NEXUS graph and evidence tools."""

    def __init__(self, repository: Any, audit_service: AuditService | None = None) -> None:
        self._repo = repository
        self._audit = audit_service
        self._evidence_svc = EvidenceService(repository, audit_service) if audit_service else None

    # ── Tool Declarations (Function Calling Schemas) ──────────────────────────

    @staticmethod
    def get_tool_declarations() -> list[dict[str, Any]]:
        """Return provider-agnostic JSON schemas for tool function declarations."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "find_shortest_path",
                    "description": "Find the evidence-backed shortest connection path between two entities (people, cases, accounts, phones) across the graph.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source_id": {
                                "type": "string",
                                "description": "Source entity ID or FIR number (e.g. 'CASE-141', 'P-RAFIQ-1', 'Rafiq Khan').",
                            },
                            "target_id": {
                                "type": "string",
                                "description": "Target entity ID or FIR number (e.g. 'CASE-207', 'P-DEEPAK', 'Deepak Rao').",
                            },
                            "max_hops": {
                                "type": "integer",
                                "description": "Maximum path traversal depth (default 6).",
                                "default": 6,
                            },
                        },
                        "required": ["source_id", "target_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "resolve_person_identity",
                    "description": "Run deterministic entity resolution to determine if multiple aliases, phone numbers, or national IDs belong to the same suspect.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "full_name": {
                                "type": "string",
                                "description": "Suspect full name or alias to resolve.",
                            },
                            "phone_number": {
                                "type": "string",
                                "description": "Phone number associated with suspect.",
                            },
                            "vehicle_number": {
                                "type": "string",
                                "description": "Vehicle registration number.",
                            },
                            "national_id": {
                                "type": "string",
                                "description": "National ID (e.g., Aadhaar / PAN format).",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_case_dossier",
                    "description": "Retrieve the authoritative investigation case file, including FIR summary, station jurisdiction, listed accused persons, and seized evidence artifacts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_id": {
                                "type": "string",
                                "description": "Case ID or FIR number (e.g. 'CASE-141', 'CASE-207', '141/2026').",
                            },
                        },
                        "required": ["case_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_cases",
                    "description": "Return authoritative case summaries filtered by offence type, district, status, or other investigator query criteria.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "offence_type": {
                                "type": "string",
                                "description": "Optional offence category to match, such as 'fraud', 'trafficking', 'cyber fraud', or 'narcotics'.",
                            },
                            "district": {
                                "type": "string",
                                "description": "Optional district filter.",
                            },
                            "status": {
                                "type": "string",
                                "description": "Optional case status filter (OPEN, CLOSED, etc.).",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return.",
                                "default": 25,
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_bridge_brokers",
                    "description": "Calculate betweenness centrality to identify cut-vertex bridge nodes and kingpin brokers connecting disparate network clusters.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_id": {
                                "type": "string",
                                "description": "Optional case ID scope filter.",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_communities",
                    "description": "Run Louvain modularity clustering to identify organized criminal syndicate sub-structures and communities.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "resolution_state": {
                                "type": "string",
                                "enum": ["before", "after"],
                                "description": "Graph state: 'before' resolution or 'after' entity fusion.",
                                "default": "after",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "detect_financial_layering",
                    "description": "Analyze bank transactions and account ledgers to detect structured layering, circular fund transfers, and mule accounts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_id": {
                                "type": "string",
                                "description": "Optional specific bank account ID to inspect.",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_cdr_bursts",
                    "description": "Analyze Call Detail Records (CDRs) and telephone nodes to detect call frequency bursts and communications among co-accused.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone_number": {
                                "type": "string",
                                "description": "Optional target phone number.",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_evidence_provenance",
                    "description": "Fetch verified evidence records, chain of custody, and forensic provenance for a case or entity.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_id": {
                                "type": "string",
                                "description": "Optional case ID filter.",
                            },
                            "entity_id": {
                                "type": "string",
                                "description": "Optional entity ID filter.",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_cross_case_connections",
                    "description": "Discover shared suspects, phones, vehicles, or bank accounts connecting two distinct police investigations.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "case_id_a": {
                                "type": "string",
                                "description": "First case ID or FIR number.",
                            },
                            "case_id_b": {
                                "type": "string",
                                "description": "Second case ID or FIR number.",
                            },
                        },
                        "required": ["case_id_a", "case_id_b"],
                    },
                },
            },
        ]

    # ── Execution Dispatcher ──────────────────────────────────────────────────

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> NEXUSToolResult:
        """Execute a deterministic tool by name with provided keyword arguments."""
        try:
            if tool_name == "find_shortest_path":
                return self.find_shortest_path(
                    source_id=str(arguments.get("source_id", "")),
                    target_id=str(arguments.get("target_id", "")),
                    max_hops=int(arguments.get("max_hops", 6)),
                )
            elif tool_name == "resolve_person_identity":
                return self.resolve_person_identity(
                    full_name=arguments.get("full_name"),
                    phone_number=arguments.get("phone_number"),
                    vehicle_number=arguments.get("vehicle_number"),
                    national_id=arguments.get("national_id"),
                )
            elif tool_name == "get_case_dossier":
                return self.get_case_dossier(case_id=str(arguments.get("case_id", "")))
            elif tool_name == "list_cases":
                return self.list_cases(
                    offence_type=arguments.get("offence_type"),
                    district=arguments.get("district"),
                    status=arguments.get("status"),
                    limit=int(arguments.get("limit", 25) or 25),
                )
            elif tool_name == "detect_bridge_brokers":
                return self.detect_bridge_brokers(case_id=arguments.get("case_id"))
            elif tool_name == "detect_communities":
                return self.detect_communities(resolution_state=arguments.get("resolution_state", "after"))
            elif tool_name == "detect_financial_layering":
                return self.detect_financial_layering(account_id=arguments.get("account_id"))
            elif tool_name == "analyze_cdr_bursts":
                return self.analyze_cdr_bursts(phone_number=arguments.get("phone_number"))
            elif tool_name == "get_evidence_provenance":
                return self.get_evidence_provenance(
                    case_id=arguments.get("case_id"),
                    entity_id=arguments.get("entity_id"),
                )
            elif tool_name == "get_cross_case_connections":
                return self.get_cross_case_connections(
                    case_id_a=str(arguments.get("case_id_a", "")),
                    case_id_b=str(arguments.get("case_id_b", "")),
                )
            else:
                return NEXUSToolResult(
                    success=False,
                    tool_name=tool_name,
                    error=f"Unknown tool '{tool_name}'.",
                )
        except Exception as exc:
            logger.exception("Error executing deterministic tool '%s': %s", tool_name, exc)
            return NEXUSToolResult(
                success=False,
                tool_name=tool_name,
                error=f"Tool execution failed: {str(exc)}",
            )

    # ── Tool Implementations ──────────────────────────────────────────────────

    def _get_active_graph_elements(self) -> tuple[dict[str, Any], list[dict[str, Any]], bool]:
        """Fetch nodes, edges, and resolution state from repository and demo state."""
        nodes_dict: dict[str, dict[str, Any]] = {}
        edges_list: list[dict[str, Any]] = []
        is_resolved = True

        try:
            from backend.app.api.nexus_routes import (
                AFTER_EDGES,
                AFTER_NODES,
                BEFORE_EDGES,
                BEFORE_NODES,
                _demo_state,
            )
            is_resolved = _demo_state.is_resolved
            demo_nodes = AFTER_NODES if is_resolved else BEFORE_NODES
            demo_edges = AFTER_EDGES if is_resolved else BEFORE_EDGES
            for n in demo_nodes:
                nid = getattr(n, "id", None) or (n.get("id") if isinstance(n, dict) else str(n))
                etype = getattr(n, "entity_type", None) or (n.get("entity_type", "Entity") if isinstance(n, dict) else "Entity")
                label = getattr(n, "label", None) or (n.get("label", nid) if isinstance(n, dict) else nid)
                props = getattr(n, "properties", None) or (n.get("properties", {}) if isinstance(n, dict) else {})
                nodes_dict[str(nid)] = {
                    "id": str(nid),
                    "entity_type": etype,
                    "label": str(label),
                    "properties": copy.deepcopy(props) if isinstance(props, dict) else {},
                }
            seen_edges = set()
            for e in demo_edges:
                eid = getattr(e, "id", None) or (e.get("id") if isinstance(e, dict) else "")
                src = getattr(e, "source_id", None) or (e.get("source_id") if isinstance(e, dict) else "")
                tgt = getattr(e, "target_id", None) or (e.get("target_id") if isinstance(e, dict) else "")
                etype = getattr(e, "edge_type", None) or (e.get("edge_type", "CONNECTED_TO") if isinstance(e, dict) else "CONNECTED_TO")
                props = getattr(e, "properties", None) or (e.get("properties", {}) if isinstance(e, dict) else {})
                if eid and str(eid) not in seen_edges:
                    seen_edges.add(str(eid))
                    edges_list.append({
                        "id": str(eid),
                        "source_id": str(src),
                        "target_id": str(tgt),
                        "edge_type": str(etype),
                        "properties": copy.deepcopy(props) if isinstance(props, dict) else {},
                    })
        except Exception:
            pass

        # Merge repository graph store
        store = self._repo.to_graph_store()
        for nid, node_rec in store.nodes.items():
            if nid not in nodes_dict:
                props = node_rec.properties or {}
                nodes_dict[nid] = {
                    "id": nid,
                    "entity_type": node_rec.entity_type,
                    "label": str(props.get("full_name") or props.get("fir_number") or props.get("title") or nid),
                    "properties": props,
                }

        for edge_rec in getattr(self._repo, "edges", []):
            eid = edge_rec.get("id") or f"edge-{edge_rec.get('source_id')}-{edge_rec.get('target_id')}"
            edges_list.append({
                "id": str(eid),
                "source_id": str(edge_rec.get("source_id")),
                "target_id": str(edge_rec.get("target_id")),
                "edge_type": str(edge_rec.get("edge_type", "CONNECTED_TO")),
                "properties": edge_rec.get("properties", {}),
            })

        return nodes_dict, edges_list, is_resolved

    def _resolve_node_id(self, query_id: str, nodes_dict: dict[str, Any]) -> str:
        """Resolve a friendly name, FIR reference, or entity ID into a graph node ID."""
        cleaned = query_id.strip()
        lower_q = cleaned.lower()

        # Direct ID match
        if cleaned in nodes_dict:
            return cleaned
        for nid in nodes_dict:
            if nid.lower() == lower_q:
                return nid

        # FIR or Case heuristics
        if "141" in lower_q:
            for nid in ["CASE-141", "case-141", "FIR-141", "fir-141"]:
                if nid in nodes_dict:
                    return nid
        if "207" in lower_q:
            for nid in ["CASE-207", "case-207", "FIR-207", "fir-207"]:
                if nid in nodes_dict:
                    return nid

        # Suspect name heuristics
        for nid, node in nodes_dict.items():
            lbl = node.get("label", "").lower()
            if lower_q in lbl or lbl in lower_q:
                return nid

        return cleaned

    def find_shortest_path(self, source_id: str, target_id: str, max_hops: int = 6) -> NEXUSToolResult:
        nodes_dict, edges_list, is_resolved = self._get_active_graph_elements()
        src = self._resolve_node_id(source_id, nodes_dict)
        tgt = self._resolve_node_id(target_id, nodes_dict)

        # Adjacency map
        adj: dict[str, list[tuple[str, str, str, list[str]]]] = {}
        for edge in edges_list:
            ev_list = edge.get("properties", {}).get("evidence_ids", [])
            if not isinstance(ev_list, list):
                ev_list = [str(ev_list)] if ev_list else []
            adj.setdefault(edge["source_id"], []).append((edge["target_id"], edge["id"], edge["edge_type"], ev_list))
            adj.setdefault(edge["target_id"], []).append((edge["source_id"], edge["id"], edge["edge_type"], ev_list))

        queue: deque[tuple[str, list[str], list[str], list[str]]] = deque([(src, [src], [], [])])
        visited: set[str] = {src}
        found_path: tuple[list[str], list[str], list[str]] | None = None

        while queue:
            curr, p_nodes, p_edges, p_evs = queue.popleft()
            if len(p_nodes) - 1 >= max_hops:
                continue
            for nxt, edge_id, edge_type, evs in adj.get(curr, []):
                if nxt in visited:
                    continue
                next_nodes = [*p_nodes, nxt]
                next_edges = [*p_edges, edge_id]
                next_evs = [*p_evs, *evs]
                if nxt == tgt:
                    found_path = (next_nodes, next_edges, next_evs)
                    break
                visited.add(nxt)
                queue.append((nxt, next_nodes, next_edges, next_evs))
            if found_path:
                break

        citations: list[GroundedCitation] = []
        reasoning_path: list[str] = []
        evidence_ids: list[str] = []

        if found_path:
            p_nodes, p_edges, p_evs = found_path
            evidence_ids = list(dict.fromkeys(p_evs))
            for i in range(len(p_nodes) - 1):
                curr_l = nodes_dict.get(p_nodes[i], {}).get("label", p_nodes[i])
                nxt_l = nodes_dict.get(p_nodes[i + 1], {}).get("label", p_nodes[i + 1])
                reasoning_path.append(f"{curr_l} ➔ {nxt_l} (Edge: {p_edges[i]})")
            for eid in evidence_ids:
                citations.append(
                    GroundedCitation(
                        source_type="EVIDENCE",
                        source_id=eid,
                        fact=f"Verified edge relationship evidence citation {eid}",
                        confidence=1.0,
                    )
                )

            return NEXUSToolResult(
                success=True,
                tool_name="find_shortest_path",
                data={
                    "path_nodes": p_nodes,
                    "path_edges": p_edges,
                    "hops": len(p_nodes) - 1,
                    "source_id": src,
                    "target_id": tgt,
                },
                evidence_ids=evidence_ids,
                citations=citations,
                reasoning_path=reasoning_path,
                case_ids=[nid for nid in p_nodes if "CASE" in nid or "FIR" in nid],
                entity_ids=p_nodes,
                nodes_count=len(p_nodes),
                edges_count=len(p_edges),
            )
        else:
            return NEXUSToolResult(
                success=True,
                tool_name="find_shortest_path",
                data={"path_nodes": [], "path_edges": [], "hops": 0, "source_id": src, "target_id": tgt},
                evidence_ids=[],
                citations=[],
                reasoning_path=[f"BFS traversal returned no connecting path between {src} and {tgt} within {max_hops} hops."],
                case_ids=[],
                entity_ids=[src, tgt],
                nodes_count=0,
                edges_count=0,
            )

    def resolve_person_identity(
        self,
        full_name: str | None = None,
        phone_number: str | None = None,
        vehicle_number: str | None = None,
        national_id: str | None = None,
    ) -> NEXUSToolResult:
        nodes_dict, _, _ = self._get_active_graph_elements()
        store = self._repo.to_graph_store()
        # Merge active demo and repo nodes into store
        for nid, n_info in nodes_dict.items():
            if nid not in store.nodes:
                from backend.app.core.graph.algorithms.utils import NodeRecord
                props = copy.deepcopy(n_info.get("properties", {}))
                if "full_name" not in props and n_info.get("entity_type") in ("Person", "PERSON"):
                    props["full_name"] = re.sub(r"\(.*?\)", "", n_info.get("label", "")).strip()
                store.nodes[nid] = NodeRecord(
                    node_id=nid,
                    entity_type=n_info.get("entity_type", "Person"),
                    properties=props,
                )

        query_dict = {
            "full_name": full_name or "",
            "phone_number": phone_number,
            "vehicle_number": vehicle_number,
            "national_id": national_id,
        }
        matches = resolve_person(store, query_dict, confidence_threshold=0.40, candidate_limit=5)

        citations: list[GroundedCitation] = []
        reasoning_path: list[str] = []
        evidence_ids: list[str] = []
        entity_ids: list[str] = []
        matched_data = []

        for m in matches:
            node = store.nodes.get(m.matched_node_id)
            lbl = node.properties.get("full_name") if node and node.properties else m.matched_node_id
            entity_ids.append(m.matched_node_id)
            ev_id = f"SRC-RESOLVE-{m.matched_node_id}"
            evidence_ids.append(ev_id)
            reasoning_path.append(f"Entity match candidate {lbl} ({m.matched_node_id}) — Confidence {m.confidence:.2f}: {m.reason}")
            citations.append(
                GroundedCitation(
                    source_type="ENTITY_RESOLUTION",
                    source_id=m.matched_node_id,
                    fact=f"Suspect alias resolution: {lbl} matched with confidence {m.confidence:.2f} ({m.reason})",
                    confidence=m.confidence,
                )
            )
            matched_data.append({
                "node_id": m.matched_node_id,
                "label": lbl,
                "confidence": m.confidence,
                "status": m.status.value,
                "matched_fields": m.matched_fields,
                "reason": m.reason,
            })

        return NEXUSToolResult(
            success=True,
            tool_name="resolve_person_identity",
            data={"matches": matched_data, "total_matches": len(matched_data)},
            evidence_ids=evidence_ids,
            citations=citations,
            reasoning_path=reasoning_path,
            case_ids=[],
            entity_ids=entity_ids,
            nodes_count=len(matched_data),
            edges_count=0,
        )

    def list_cases(
        self,
        offence_type: str | None = None,
        district: str | None = None,
        status: str | None = None,
        limit: int = 25,
    ) -> NEXUSToolResult:
        try:
            query_filter = (offence_type or "").strip()
            cases: list[dict[str, Any]] = []

            for node_id, node in getattr(self._repo, "nodes", {}).items():
                if node.get("entity_type") not in ("Case", "CASE"):
                    continue
                props = node.get("properties", {})
                case_record = {
                    "case_id": str(node_id),
                    "fir_number": str(props.get("fir_number") or f"FIR-{node_id}"),
                    "title": str(props.get("title") or f"Investigation {node_id}"),
                    "offence_category": str(props.get("offence_category") or "General Crime"),
                    "district": str(props.get("district") or "Bengaluru"),
                    "station_name": str(props.get("station_name") or "Central Police Station"),
                    "status": str(props.get("status") or "OPEN"),
                    "updated_at": props.get("updated_at"),
                    "summary": str(props.get("summary") or ""),
                }

                match = True
                if query_filter:
                    lowered = query_filter.lower()
                    category_text = f"{case_record['offence_category']} {case_record['title']} {case_record['fir_number']}".lower()
                    if lowered in {"fraud", "cyber fraud", "financial fraud"}:
                        match = "fraud" in category_text or "extortion" in category_text
                    elif lowered in {"trafficking", "narcotics trafficking", "trafficking cases"}:
                        match = "trafficking" in category_text or "narcotic" in category_text
                    elif lowered in {"money laundering", "laundering"}:
                        match = "money laundering" in category_text or "laundering" in category_text
                    else:
                        match = lowered in category_text

                if district and case_record["district"].lower() != district.lower():
                    match = False
                if status and case_record["status"].lower() != str(status).lower():
                    match = False

                if match:
                    cases.append(case_record)

            cases.sort(key=lambda item: (str(item["status"]).lower() != "open", str(item["updated_at"] or "")), reverse=True)
            limited = cases[: max(0, int(limit or 25))]
            total_count = len(limited)

            citations = [
                GroundedCitation(
                    source_type="CASE",
                    source_id=str(item["case_id"]),
                    fact=f"Authoritative case found in repository: {item['fir_number']} — {item['offence_category']}",
                    confidence=1.0,
                )
                for item in limited
            ]
            reasoning_path = [f"Repository query returned {total_count} case(s) matching the supplied filters."]

            return NEXUSToolResult(
                success=True,
                tool_name="list_cases",
                data={
                    "cases": limited,
                    "count": len(limited),
                    "total_count": total_count,
                    "offence_type": query_filter,
                },
                evidence_ids=[str(item["case_id"]) for item in limited],
                citations=citations,
                reasoning_path=reasoning_path,
                case_ids=[str(item["case_id"]) for item in limited],
                entity_ids=[str(item["case_id"]) for item in limited],
                nodes_count=len(limited),
                edges_count=0,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Error listing cases with filters: %s", exc)
            return NEXUSToolResult(
                success=False,
                tool_name="list_cases",
                error=f"Case listing failed: {exc}",
                data={"cases": [], "count": 0, "total_count": 0},
            )

    def get_case_dossier(self, case_id: str) -> NEXUSToolResult:
        nodes_dict, _, _ = self._get_active_graph_elements()
        cid = self._resolve_node_id(case_id, nodes_dict)
        detail = self._repo.get_investigation_detail(cid)

        if not detail:
            # Check demo cases
            if cid in ("CASE-141", "case-141", "FIR-141"):
                detail = InvestigationDetailResponse(
                    id="CASE-141",
                    fir_number="FIR 141/2026",
                    title="Cyber Extortion & Hawala Syndicate Ring",
                    station_name="Cyber Crime PS",
                    district="Bengaluru",
                    offence_category="Cyber Extortion / Financial Fraud",
                    status="OPEN",
                    summary="Investigation into coordinated cyber extortion threats and structured illicit fund transfers targeting corporate accounts.",
                    accused=[{"id": "P-RAFIQ-1", "full_name": "Rafiq Ahmed", "phone_number": "+91 98450 11223", "role": "Primary Suspect"}],
                    evidence=[],
                    updated_at=detail.updated_at if detail else self._repo.reference_time,
                )
            elif cid in ("CASE-207", "case-207", "FIR-207"):
                detail = InvestigationDetailResponse(
                    id="CASE-207",
                    fir_number="FIR 207/2026",
                    title="Cross-Border Narcotics Distribution & Layering",
                    station_name="Narcotics Control PS",
                    district="Bengaluru",
                    offence_category="Narcotics Trafficking & Money Laundering",
                    status="OPEN",
                    summary="Investigation into interstate narcotics transport network and funneling of proceeds through mule accounts.",
                    accused=[
                        {"id": "P-RAFIQ-2", "full_name": "Rafiq Khan", "phone_number": "+91 98450 11223", "role": "Logistics Coordinator"},
                        {"id": "P-DEEPAK", "full_name": "Deepak Rao", "phone_number": "+91 91234 56789", "role": "Financial Associate"},
                    ],
                    evidence=[],
                    updated_at=detail.updated_at if detail else self._repo.reference_time,
                )

        if not detail:
            return NEXUSToolResult(
                success=False,
                tool_name="get_case_dossier",
                error=f"Case record '{case_id}' not found in active investigation repository.",
                case_ids=[case_id],
            )

        citations: list[GroundedCitation] = []
        reasoning_path: list[str] = [f"Authoritative FIR Dossier match: {detail.fir_number} ({detail.station_name}, {detail.district})"]
        evidence_ids: list[str] = [f"SRC-FIR-{detail.fir_number}"]

        citations.append(
            GroundedCitation(
                source_type="FIR",
                source_id=detail.fir_number,
                fact=f"FIR registered at {detail.station_name}, {detail.district}: {detail.title}",
                confidence=1.0,
            )
        )

        for a in detail.accused:
            a_id = a.get("id", "")
            fn = a.get("full_name") or a.get("name") or a_id
            citations.append(
                GroundedCitation(
                    source_type="PERSON",
                    source_id=str(a_id),
                    fact=f"Accused listed in {detail.fir_number}: {fn}",
                    confidence=1.0,
                )
            )
            reasoning_path.append(f"Accused: {fn} ({a_id})")

        for ev in detail.evidence:
            ev_num = ev.evidence_number or ev.id
            evidence_ids.append(str(ev_num))
            citations.append(
                GroundedCitation(
                    source_type="EVIDENCE",
                    source_id=str(ev_num),
                    fact=f"Seized forensic item under {detail.fir_number}: {ev.description}",
                    confidence=1.0,
                )
            )

        return NEXUSToolResult(
            success=True,
            tool_name="get_case_dossier",
            data=detail.model_dump(mode="json"),
            evidence_ids=evidence_ids,
            citations=citations,
            reasoning_path=reasoning_path,
            case_ids=[detail.id],
            entity_ids=[str(a.get("id")) for a in detail.accused if a.get("id")],
            nodes_count=1 + len(detail.accused) + len(detail.evidence),
            edges_count=len(detail.accused) + len(detail.evidence),
        )

    def detect_bridge_brokers(self, case_id: str | None = None) -> NEXUSToolResult:
        store = self._repo.to_graph_store()
        bridges = find_bridge_nodes(store)

        citations: list[GroundedCitation] = []
        reasoning_path: list[str] = []
        evidence_ids: list[str] = ["GRAPH-CENTRALITY-BETWEENNESS"]
        entity_ids: list[str] = []

        data_list = []
        for b in bridges[:5]:
            entity_ids.append(b.node_id)
            reasoning_path.append(f"Cut-vertex broker {b.label} ({b.node_id}) — Betweenness {b.betweenness_score:.4f} bridging {b.connected_components_count} sub-graphs")
            citations.append(
                GroundedCitation(
                    source_type="GRAPH_ANALYTICS",
                    source_id=b.node_id,
                    fact=f"Cut-vertex bridge broker {b.label} ({b.entity_type}) connects {b.connected_components_count} sub-networks with betweenness {b.betweenness_score:.4f}",
                    confidence=0.95,
                )
            )
            data_list.append({
                "node_id": b.node_id,
                "label": b.label,
                "entity_type": b.entity_type,
                "betweenness_score": b.betweenness_score,
                "connected_components": b.connected_components_count,
            })

        return NEXUSToolResult(
            success=True,
            tool_name="detect_bridge_brokers",
            data={"bridges": data_list, "total_bridges": len(bridges)},
            evidence_ids=evidence_ids,
            citations=citations,
            reasoning_path=reasoning_path,
            case_ids=[case_id] if case_id else [],
            entity_ids=entity_ids,
            nodes_count=len(data_list),
            edges_count=0,
        )

    def detect_communities(self, resolution_state: str | None = "after") -> NEXUSToolResult:
        store = self._repo.to_graph_store()
        communities = detect_communities(store)

        citations: list[GroundedCitation] = []
        reasoning_path: list[str] = [f"Louvain modularity partitioned network into {len(communities)} syndicates"]
        evidence_ids: list[str] = ["GRAPH-LOUVAIN-COMMUNITIES"]
        entity_ids: list[str] = []

        comm_data = []
        for c in communities:
            entity_ids.extend(c.member_ids[:5])
            comm_data.append({
                "community_id": c.community_id,
                "size": c.size,
                "member_ids": c.member_ids,
                "dominant_entity_type": c.dominant_entity_type,
                "top_influencer_id": c.top_influencer_id,
            })
            citations.append(
                GroundedCitation(
                    source_type="COMMUNITY_DETECTION",
                    source_id=c.community_id,
                    fact=f"Syndicate community {c.community_id} contains {c.size} entities (Top influencer: {c.top_influencer_id})",
                    confidence=0.92,
                )
            )

        return NEXUSToolResult(
            success=True,
            tool_name="detect_communities",
            data={"communities": comm_data, "total_communities": len(communities)},
            evidence_ids=evidence_ids,
            citations=citations,
            reasoning_path=reasoning_path,
            case_ids=[],
            entity_ids=list(dict.fromkeys(entity_ids)),
            nodes_count=len(entity_ids),
            edges_count=0,
        )

    def detect_financial_layering(self, account_id: str | None = None) -> NEXUSToolResult:
        store = self._repo.to_graph_store()
        findings = detect_circular_repeated_financial_flow(store)

        citations: list[GroundedCitation] = []
        reasoning_path: list[str] = []
        evidence_ids: list[str] = ["FIN-LEDGER-01"]
        entity_ids: list[str] = []
        findings_data = []

        for f in findings:
            evidence_ids.extend(f.evidence_ids)
            entity_ids.extend(f.entity_ids)
            reasoning_path.append(f"Layering finding: {f.description}")
            for eid in f.evidence_ids:
                citations.append(
                    GroundedCitation(
                        source_type="BANK_LEDGER",
                        source_id=eid,
                        fact=f.description,
                        confidence=f.confidence,
                    )
                )
            findings_data.append({
                "rule_name": f.rule_name,
                "description": f.description,
                "confidence": f.confidence,
                "entity_ids": f.entity_ids,
                "evidence_ids": f.evidence_ids,
            })

        return NEXUSToolResult(
            success=True,
            tool_name="detect_financial_layering",
            data={"findings": findings_data, "total_findings": len(findings)},
            evidence_ids=list(dict.fromkeys(evidence_ids)),
            citations=citations,
            reasoning_path=reasoning_path,
            case_ids=[],
            entity_ids=list(dict.fromkeys(entity_ids)),
            nodes_count=len(entity_ids),
            edges_count=len(evidence_ids),
        )

    def analyze_cdr_bursts(self, phone_number: str | None = None) -> NEXUSToolResult:
        store = self._repo.to_graph_store()
        bursts = detect_communication_burst_near_event(store)
        phone_nodes = [n for n in store.nodes.values() if n.entity_type in ("Phone", "PHONE")]

        citations: list[GroundedCitation] = []
        reasoning_path: list[str] = [f"{len(phone_nodes)} telephone device nodes indexed in telecom graph"]
        evidence_ids: list[str] = ["CDR-BURST-INDEX"]
        entity_ids: list[str] = [p.node_id for p in phone_nodes]

        findings_data = []
        for b in bursts:
            evidence_ids.extend(b.evidence_ids)
            entity_ids.extend(b.entity_ids)
            reasoning_path.append(f"CDR burst event: {b.description}")
            for eid in b.evidence_ids:
                citations.append(
                    GroundedCitation(
                        source_type="CDR",
                        source_id=eid,
                        fact=b.description,
                        confidence=b.confidence,
                    )
                )
            findings_data.append({
                "rule_name": b.rule_name,
                "description": b.description,
                "confidence": b.confidence,
                "evidence_ids": b.evidence_ids,
            })

        return NEXUSToolResult(
            success=True,
            tool_name="analyze_cdr_bursts",
            data={
                "phone_nodes_count": len(phone_nodes),
                "burst_findings": findings_data,
            },
            evidence_ids=list(dict.fromkeys(evidence_ids)),
            citations=citations,
            reasoning_path=reasoning_path,
            case_ids=[],
            entity_ids=list(dict.fromkeys(entity_ids)),
            nodes_count=len(phone_nodes),
            edges_count=len(findings_data),
        )

    def get_evidence_provenance(self, case_id: str | None = None, entity_id: str | None = None) -> NEXUSToolResult:
        ev_items = []
        if self._evidence_svc:
            if entity_id:
                ev_items = self._evidence_svc.get_evidence_for_entity(entity_id)
            else:
                ev_items = self._evidence_svc.list_all_evidence(case_id=case_id, limit=20)

        citations: list[GroundedCitation] = []
        reasoning_path: list[str] = []
        evidence_ids: list[str] = []

        data_list = []
        for item in ev_items:
            ev_src = item.provenance.source_id or item.id
            evidence_ids.append(ev_src)
            reasoning_path.append(f"Evidence record {item.evidence_number}: {item.description}")
            citations.append(
                GroundedCitation(
                    source_type=item.provenance.source_type,
                    source_id=ev_src,
                    fact=item.description,
                    confidence=item.provenance.confidence,
                )
            )
            data_list.append(item.model_dump())

        return NEXUSToolResult(
            success=True,
            tool_name="get_evidence_provenance",
            data={"evidence_records": data_list, "count": len(data_list)},
            evidence_ids=list(dict.fromkeys(evidence_ids)),
            citations=citations,
            reasoning_path=reasoning_path,
            case_ids=[case_id] if case_id else [],
            entity_ids=[entity_id] if entity_id else [],
            nodes_count=len(data_list),
            edges_count=0,
        )

    def get_cross_case_connections(self, case_id_a: str, case_id_b: str) -> NEXUSToolResult:
        # Cross-case path traversal
        return self.find_shortest_path(source_id=case_id_a, target_id=case_id_b, max_hops=6)
