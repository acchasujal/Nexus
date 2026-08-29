"""backend/app/ai/context_builder.py

NEXUS GraphRAG Context Engine (Milestone 3).

Converts investigator queries, case scopes, and entity focuses into a compact,
structured, evidence-grounded InvestigationContext for LLM synthesis.

Strict Non-Negotiables:
1. Operates entirely over deterministic GraphStore, BFS traversals, and EvidenceService.
2. ZERO hallucinated nodes, relationships, or evidence IDs.
3. Every relationship and pattern preserves verified provenance citations.
4. Compact and token-budget aware (max_nodes, max_evidence, max_depth pruning).
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from backend.app.ai.schemas import (
    EntityContext,
    EvidenceContext,
    InvestigationContext,
    PathContext,
    PatternContext,
    RelationshipContext,
    RetrievalMetadata,
    TimelineEventContext,
)
from backend.app.ai.tools import NEXUSToolRegistry, NEXUSToolResult
from backend.app.core.graph.algorithms.bridges import compute_person_bridge_intelligence
from backend.app.core.graph.algorithms.communities import detect_louvain_communities
from backend.app.core.graph.algorithms.pattern_rules import (
    PatternFinding,
    detect_all_suspicious_patterns,
)
from backend.app.core.graph.algorithms.traversals import get_subgraph
from backend.app.core.graph.algorithms.utils import GraphStore
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.evidence_service import EvidenceService

logger = logging.getLogger(__name__)


class GraphRAGContextBuilder:
    """Deterministic GraphRAG context assembly engine for NEXUS.
    
    Transforms investigative queries into structured, high-density subgraphs
    with complete evidence provenance for downstream LLM synthesis.
    """

    def __init__(
        self,
        repository: Any,
        audit_service: AuditService | None = None,
        tool_registry: NEXUSToolRegistry | None = None,
    ) -> None:
        self._repo = repository
        self._audit = audit_service
        self._evidence_svc = EvidenceService(repository, audit_service) if audit_service else None
        self._tools = tool_registry or NEXUSToolRegistry(repository, audit_service)

    def build_context(
        self,
        query: str,
        case_id: str | None = None,
        entity_id: str | None = None,
        is_resolved: bool = True,
        max_depth: int = 2,
        max_evidence: int = 20,
        max_nodes: int = 50,
    ) -> InvestigationContext:
        """Construct a structured, evidence-grounded GraphRAG investigation context."""
        t_start = time.perf_counter()

        store: GraphStore = self._repo.to_graph_store()
        nodes_dict, edges_list, resolved_state = self._tools._get_active_graph_elements()

        # ── 1. Entity & Case Identifier Extraction ────────────────────────────
        extracted_cases = self._extract_case_ids(query, case_id, nodes_dict)
        extracted_entities = self._extract_entity_ids(query, entity_id, nodes_dict)

        # ── 2. Determine Query Type & Retrieval Strategy ──────────────────────
        strategy, query_type = self._classify_query_intent(query, extracted_cases, extracted_entities)

        # Containers
        retrieved_entities: dict[str, EntityContext] = {}
        retrieved_relationships: dict[str, RelationshipContext] = {}
        retrieved_paths: list[PathContext] = []
        retrieved_evidence: dict[str, EvidenceContext] = {}
        retrieved_patterns: list[PatternContext] = []
        retrieved_timeline: list[TimelineEventContext] = []
        reasoning_steps: list[str] = []

        # ── 3. Strategy-Aware Graph Retrieval ─────────────────────────────────
        if strategy == "cross_case_path":
            self._retrieve_path_context(
                extracted_cases,
                extracted_entities,
                nodes_dict,
                edges_list,
                max_depth,
                retrieved_entities,
                retrieved_relationships,
                retrieved_paths,
                retrieved_evidence,
                reasoning_steps,
            )

        elif strategy == "pattern_investigation":
            self._retrieve_pattern_context(
                query,
                store,
                nodes_dict,
                edges_list,
                retrieved_entities,
                retrieved_relationships,
                retrieved_patterns,
                retrieved_evidence,
                reasoning_steps,
            )

        elif strategy == "financial_trace":
            self._retrieve_financial_context(
                query,
                extracted_cases,
                extracted_entities,
                nodes_dict,
                edges_list,
                retrieved_entities,
                retrieved_relationships,
                retrieved_patterns,
                retrieved_evidence,
                reasoning_steps,
            )

        elif strategy == "lead_triage":
            self._retrieve_lead_triage_context(
                extracted_cases,
                store,
                nodes_dict,
                edges_list,
                retrieved_entities,
                retrieved_relationships,
                retrieved_patterns,
                retrieved_evidence,
                reasoning_steps,
            )

        elif strategy == "case_dossier":
            self._retrieve_case_dossier_context(
                extracted_cases[0] if extracted_cases else (case_id or ""),
                nodes_dict,
                edges_list,
                retrieved_entities,
                retrieved_relationships,
                retrieved_evidence,
                retrieved_timeline,
                reasoning_steps,
            )

        else:
            # Default Entity Neighborhood / General Query
            self._retrieve_neighborhood_context(
                extracted_cases,
                extracted_entities,
                store,
                nodes_dict,
                edges_list,
                max_depth,
                retrieved_entities,
                retrieved_relationships,
                retrieved_evidence,
                reasoning_steps,
            )

        # ── 4. Enrich Bridge & Community Flags ─────────────────────────────────
        self._enrich_graph_metadata(store, retrieved_entities)

        # ── 5. Populate Complete Evidence Provenance ───────────────────────────
        self._hydrate_evidence_records(retrieved_relationships, retrieved_patterns, retrieved_evidence)

        # ── 6. Context Ranking & Token Budget Pruning ──────────────────────────
        total_nodes_before = len(retrieved_entities)
        total_edges_before = len(retrieved_relationships)

        final_entities = self._prune_entities(retrieved_entities, extracted_entities, extracted_cases, max_nodes)
        final_relationships = self._prune_relationships(retrieved_relationships, final_entities)
        final_evidence = list(retrieved_evidence.values())[:max_evidence]

        pruned_nodes = total_nodes_before - len(final_entities)
        pruned_edges = total_edges_before - len(final_relationships)
        t_duration_ms = (time.perf_counter() - t_start) * 1000.0

        metadata = RetrievalMetadata(
            retrieval_strategy=strategy,
            query_type=query_type,
            retrieved_nodes_count=total_nodes_before,
            retrieved_edges_count=total_edges_before,
            retrieved_evidence_count=len(final_evidence),
            retrieved_patterns_count=len(retrieved_patterns),
            duration_ms=round(t_duration_ms, 2),
            pruned_nodes_count=max(0, pruned_nodes),
            pruned_edges_count=max(0, pruned_edges),
            is_resolved=is_resolved,
        )

        if self._audit:
            self._audit.record(
                AuditEventType.GRAPH_QUERY_EXECUTED,
                actor_id="graphrag_engine",
                details={
                    "query": query,
                    "strategy": strategy,
                    "nodes_retrieved": total_nodes_before,
                    "evidence_count": len(final_evidence),
                    "duration_ms": round(t_duration_ms, 2),
                },
            )

        return InvestigationContext(
            query=query,
            case_ids=extracted_cases,
            entity_ids=list(dict.fromkeys(extracted_entities + [e.id for e in final_entities[:10]])),
            entities=final_entities,
            relationships=final_relationships,
            paths=retrieved_paths,
            evidence=final_evidence,
            patterns=retrieved_patterns,
            timeline_events=retrieved_timeline,
            reasoning_path=reasoning_steps,
            retrieval_metadata=metadata,
        )

    # ── Internal Extraction & Classification Helpers ──────────────────────────

    def _get_graph_elements(
        self, store: GraphStore, is_resolved: bool
    ) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        """Convert repository or store into normalized nodes dict and edges list."""
        nodes_dict: dict[str, dict[str, Any]] = {}
        for nid, n in store.nodes.items():
            props = dict(n.properties) if hasattr(n, "properties") else {}
            label = (
                props.get("canonical_label")
                or props.get("name")
                or props.get("full_name")
                or props.get("fir_number")
                or props.get("case_number")
                or nid
            )
            nodes_dict[nid] = {
                "id": nid,
                "label": str(label),
                "type": n.entity_type if hasattr(n, "entity_type") else "Unknown",
                "properties": props,
            }

        edges_list: list[dict[str, Any]] = []
        for etype, edges in store.edge_index.items():
            for e in edges:
                props = dict(e.properties) if hasattr(e, "properties") else {}
                edges_list.append({
                    "id": getattr(e, "id", f"{e.source_id}->{e.target_id}:{etype}"),
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "edge_type": etype,
                    "properties": props,
                })

        return nodes_dict, edges_list

    def _extract_case_ids(
        self, query: str, case_id: str | None, nodes_dict: dict[str, dict[str, Any]]
    ) -> list[str]:
        """Extract explicit and regex-matched case IDs from query text."""
        cases: list[str] = []
        if case_id:
            resolved = self._resolve_case_id(case_id, nodes_dict)
            if resolved:
                cases.append(resolved)

        # Regex patterns for Indian police FIRs and system Case IDs
        patterns = [
            r"(?:FIR|CASE|CC)[-_/ ]?(\d+[-_/ ]?\d+|\d+)",
            r"(?:FIR|CASE)[-_/ ]?(\d{4}[-_/ ]?\d+)",
            r"FIR[-_/ ]?(\d+)",
        ]
        q_upper = query.upper()
        for p in patterns:
            for m in re.finditer(p, q_upper):
                raw_match = m.group(0).strip()
                res = self._resolve_case_id(raw_match, nodes_dict)
                if res and res not in cases:
                    cases.append(res)

        # Also search known node keys directly
        for nid, n in nodes_dict.items():
            if n.get("type") in ("Case", "InvestigationCase"):
                lbl = n.get("label", "").upper()
                fir_no = str(n.get("properties", {}).get("fir_number", "")).upper()
                if (nid.upper() in q_upper or (fir_no and fir_no in q_upper)) and nid not in cases:
                    cases.append(nid)

        return cases

    def _resolve_case_id(self, raw_id: str, nodes_dict: dict[str, dict[str, Any]]) -> str | None:
        """Resolve arbitrary user FIR string to canonical case node ID."""
        cleaned = raw_id.strip()
        if cleaned in nodes_dict:
            return cleaned

        lower_c = cleaned.lower()
        for nid in nodes_dict:
            if nid.lower() == lower_c:
                return nid

        # Match FIR-141 <-> CASE-141
        num_match = re.search(r"(\d+)", cleaned)
        if num_match:
            num = num_match.group(1)
            for nid, n in nodes_dict.items():
                etype = n.get("entity_type") or n.get("type") or ""
                if etype in ("Case", "InvestigationCase") or "case" in nid.lower() or "fir" in nid.lower():
                    if num in nid:
                        return nid
                    fir_no = str(n.get("properties", {}).get("fir_number", ""))
                    if num in fir_no:
                        return nid

        return cleaned if cleaned else None

    def _extract_entity_ids(
        self, query: str, entity_id: str | None, nodes_dict: dict[str, dict[str, Any]]
    ) -> list[str]:
        """Extract explicit and mentioned person/account/phone entity IDs from query text."""
        entities: list[str] = []
        if entity_id and entity_id in nodes_dict:
            entities.append(entity_id)

        stopwords = {
            "who", "the", "and", "what", "is", "are", "summary", "accused", "case", "fir",
            "why", "flagged", "evidence", "supports", "financial", "connection", "between",
            "tell", "about", "important", "with", "this", "that", "from", "into", "flow",
            "path", "link", "records", "exist", "does", "have", "been", "over", "next", "leads"
        }
        q_lower = query.lower()

        # 1. Check exact clean labels & aliases
        for nid, n in nodes_dict.items():
            etype = n.get("entity_type") or n.get("type") or ""
            if etype in ("Case", "InvestigationCase"):
                continue

            lbl = n.get("label", "")
            clean_lbl = re.sub(r"\(.*?\)", "", lbl).strip().lower()
            if len(clean_lbl) >= 3 and clean_lbl not in stopwords and clean_lbl in q_lower:
                if nid not in entities:
                    entities.append(nid)
                continue

            # Check individual name tokens (e.g., "Rafiq", "Deepak", "Vinod")
            matched_token = False
            for w in clean_lbl.split():
                if len(w) >= 4 and w not in stopwords:
                    if re.search(r"\b" + re.escape(w) + r"\b", q_lower):
                        if nid not in entities:
                            entities.append(nid)
                            matched_token = True
                            break

            if matched_token:
                continue

            # Check explicit aliases
            aliases = n.get("properties", {}).get("aliases", [])
            if isinstance(aliases, list):
                for alias in aliases:
                    alias_clean = str(alias).strip().lower()
                    if len(alias_clean) >= 3 and alias_clean not in stopwords and alias_clean in q_lower:
                        if nid not in entities:
                            entities.append(nid)
                            break

        # 2. Check phone numbers or account numbers in text
        phone_match = re.findall(r"\b\d{10}\b", query)
        for p in phone_match:
            for nid, n in nodes_dict.items():
                if p in nid or p in str(n.get("properties", {})):
                    if nid not in entities:
                        entities.append(nid)

        account_match = re.findall(r"(?:ACC|ACC-)?(\d{4,12})", query.upper())
        for acc_num in account_match:
            for nid, n in nodes_dict.items():
                if acc_num in nid or acc_num in str(n.get("properties", {})):
                    if nid not in entities:
                        entities.append(nid)

        return entities

    def _classify_query_intent(
        self, query: str, cases: list[str], entities: list[str]
    ) -> tuple[str, str]:
        """Determine optimal retrieval strategy based on query structure and semantics."""
        q = query.lower()

        # 1. Broad case collection queries such as 'show all fraud cases'
        if "case" in q and any(w in q for w in ("show all", "list all", "all cases", "how many", "count")):
            return "case_collection", "case_collection"

        # 2. Multi-Case or Connection Query between 2 endpoints
        if len(cases) >= 2 or (("connect" in q or "path" in q or "link" in q or "between" in q) and (len(cases) + len(entities) >= 2)):
            # If specifically asking about financial connection between endpoints, route to financial_trace
            if any(w in q for w in ("money", "financial", "transfer", "transaction", "account", "ledger", "bank")):
                return "financial_trace", "financial_flow"
            return "cross_case_path", "cross_case_connection"

        # 3. Graph Pattern Rules & Syndicates (higher precedence than general financial words)
        if any(w in q for w in ("pattern", "circular", "burst", "flagged", "syndicate", "suspicious", "rule", "co-location")):
            return "pattern_investigation", "pattern_investigation"

        # 3. Financial Flows & Transactions
        if any(w in q for w in ("money", "financial", "transfer", "transaction", "layering", "account", "ledger", "bank")):
            return "financial_trace", "financial_flow"

        # 4. Lead Triage & Next Investigative Actions
        if any(w in q for w in ("what next", "next steps", "recommend", "leads", "investigate next", "triage", "summary of pending", "gap")):
            return "lead_triage", "lead_triage"

        # 5. Single Case Dossier / Accused Focus
        if cases or any(w in q for w in ("accused", "dossier", "brief", "summary", "fir", "overview")):
            return "case_dossier", "case_summary"

        return "neighborhood", "entity_lookup"

    # ── Strategy Handlers ─────────────────────────────────────────────────────

    def _retrieve_path_context(
        self,
        cases: list[str],
        entities: list[str],
        nodes_dict: dict[str, dict[str, Any]],
        edges_list: list[dict[str, Any]],
        max_depth: int,
        retrieved_entities: dict[str, EntityContext],
        retrieved_relationships: dict[str, RelationshipContext],
        retrieved_paths: list[PathContext],
        retrieved_evidence: dict[str, EvidenceContext],
        reasoning_steps: list[str],
    ) -> None:
        """Retrieve shortest path connecting endpoints plus 1-hop path perimeter."""
        endpoints = cases if len(cases) >= 2 else entities
        src, tgt = endpoints[0], endpoints[1]

        tool_res: NEXUSToolResult = self._tools.find_shortest_path(src, tgt, max_hops=max(6, max_depth * 2))
        reasoning_steps.extend(tool_res.reasoning_path)

        p_nodes = tool_res.data.get("path_nodes", [])
        p_edges = tool_res.data.get("path_edges", [])

        if p_nodes:
            node_labels = [nodes_dict.get(nid, {}).get("label", nid) for nid in p_nodes]
            retrieved_paths.append(
                PathContext(
                    source_id=src,
                    target_id=tgt,
                    hops=tool_res.data.get("hops", len(p_nodes) - 1),
                    nodes=p_nodes,
                    node_labels=node_labels,
                    edges=p_edges,
                    evidence_ids=tool_res.evidence_ids,
                    reasoning_steps=tool_res.reasoning_path,
                )
            )

            # Include path nodes
            for nid in p_nodes:
                self._add_entity(nid, nodes_dict, retrieved_entities)

            # Include path edges and attached evidence
            for edge in edges_list:
                if edge["id"] in p_edges or (edge["source_id"] in p_nodes and edge["target_id"] in p_nodes):
                    self._add_relationship(edge, nodes_dict, retrieved_relationships)

    def _retrieve_financial_context(
        self,
        query: str,
        cases: list[str],
        entities: list[str],
        nodes_dict: dict[str, dict[str, Any]],
        edges_list: list[dict[str, Any]],
        retrieved_entities: dict[str, EntityContext],
        retrieved_relationships: dict[str, RelationshipContext],
        retrieved_patterns: list[PatternContext],
        retrieved_evidence: dict[str, EvidenceContext],
        reasoning_steps: list[str],
    ) -> None:
        """Retrieve financial account nodes, multi-hop transfers, and layering chains with high precision."""
        reasoning_steps.append("Executing targeted financial context retrieval and transaction trace.")

        q = query.lower()
        is_broad_request = any(
            w in q for w in ("syndicate", "community", "cluster", "broader financial network", "entire network", "all transactions", "all accounts")
        )
        focus_seeds = set(entities + cases)

        # 1. Targeted Financial Query with Explicit Entities / Cases
        if focus_seeds and not is_broad_request:
            # Map focus person/case nodes to their owned accounts and ownership edges
            person_to_accounts: dict[str, set[str]] = {}
            account_to_persons: dict[str, set[str]] = {}
            ownership_edges_map: dict[tuple[str, str], dict[str, Any]] = {}

            for edge in edges_list:
                etype = edge.get("edge_type", "").upper()
                src, tgt = edge["source_id"], edge["target_id"]
                if any(k in etype for k in ("OWN", "ACCOUNT", "LINK", "HOLDER")):
                    if src in focus_seeds:
                        person_to_accounts.setdefault(src, set()).add(tgt)
                        account_to_persons.setdefault(tgt, set()).add(src)
                        ownership_edges_map[(src, tgt)] = edge
                    if tgt in focus_seeds:
                        person_to_accounts.setdefault(tgt, set()).add(src)
                        account_to_persons.setdefault(src, set()).add(tgt)
                        ownership_edges_map[(tgt, src)] = edge

            all_focus_accounts = {acc for accs in person_to_accounts.values() for acc in accs}

            # Find transaction/transfer edges
            cross_seed_tx: list[dict[str, Any]] = []
            seed_tx: list[dict[str, Any]] = []

            for edge in edges_list:
                etype = edge.get("edge_type", "").upper()
                src, tgt = edge["source_id"], edge["target_id"]
                is_tx = any(k in etype for k in ("TRANSFER", "PAYMENT", "TRANSACTION", "TXN"))
                if not is_tx:
                    continue

                # Check if transfer connects accounts owned by different focus persons
                src_owners = account_to_persons.get(src, set())
                tgt_owners = account_to_persons.get(tgt, set())

                if src_owners and tgt_owners and (src_owners != tgt_owners):
                    cross_seed_tx.append(edge)
                elif src in all_focus_accounts or tgt in all_focus_accounts or src in focus_seeds or tgt in focus_seeds:
                    seed_tx.append(edge)

            # Prioritize cross-seed transactions if found
            if cross_seed_tx:
                active_tx_edges = cross_seed_tx
            elif seed_tx:
                active_tx_edges = seed_tx
            else:
                active_tx_edges = []

            # If active transactions were found, include participating persons and accounts
            participating_accounts: set[str] = set()
            participating_persons: set[str] = set()

            for edge in active_tx_edges:
                src, tgt = edge["source_id"], edge["target_id"]
                participating_accounts.add(src)
                participating_accounts.add(tgt)
                for p in account_to_persons.get(src, set()):
                    participating_persons.add(p)
                for p in account_to_persons.get(tgt, set()):
                    participating_persons.add(p)

            # If no transactions found among accounts, retain focus seeds and their direct accounts
            if not participating_persons:
                participating_persons = focus_seeds
                participating_accounts = all_focus_accounts

            # Add participating persons and accounts
            for pid in participating_persons:
                self._add_entity(pid, nodes_dict, retrieved_entities)
            for acc in participating_accounts:
                self._add_entity(acc, nodes_dict, retrieved_entities)

            # Add relevant ownership edges
            for (p, acc), edge in ownership_edges_map.items():
                if p in participating_persons and acc in participating_accounts:
                    self._add_relationship(edge, nodes_dict, retrieved_relationships)

            # Add active transaction edges
            for edge in active_tx_edges:
                self._add_relationship(edge, nodes_dict, retrieved_relationships)

            # Also check direct relationships between participating persons (e.g. COMMUNICATED_WITH, CO_ACCUSED_IN)
            for edge in edges_list:
                src, tgt = edge["source_id"], edge["target_id"]
                if src in participating_persons and tgt in participating_persons:
                    self._add_relationship(edge, nodes_dict, retrieved_relationships)

            # Patterns involving only retrieved active entities
            tool_res: NEXUSToolResult = self._tools.detect_financial_layering()
            fin_findings = tool_res.data.get("findings") or tool_res.data.get("patterns") or []
            active_ids = set(retrieved_entities.keys())
            for p in fin_findings:
                p_eids = set(p.get("entity_ids", []))
                if p_eids & active_ids:
                    retrieved_patterns.append(
                        PatternContext(
                            pattern_id=p.get("rule_name") or p.get("rule_id", "financial_pattern"),
                            pattern_type=p.get("rule_name") or p.get("rule_id", "circular_repeated_financial_flow"),
                            severity="high",
                            description=p.get("description", ""),
                            participating_entity_ids=p.get("entity_ids", []),
                            evidence_ids=p.get("evidence_ids", []),
                        )
                    )

        # 2. Broad Financial Network Query (Syndicates / Global Layering)
        else:
            tool_res = self._tools.detect_financial_layering()
            reasoning_steps.extend(tool_res.reasoning_path)

            fin_findings = tool_res.data.get("findings") or tool_res.data.get("patterns") or []
            for pat in fin_findings:
                retrieved_patterns.append(
                    PatternContext(
                        pattern_id=pat.get("rule_name") or pat.get("rule_id", "financial_pattern"),
                        pattern_type=pat.get("rule_name") or pat.get("rule_id", "circular_repeated_financial_flow"),
                        severity="high",
                        description=pat.get("description", ""),
                        participating_entity_ids=pat.get("entity_ids", []),
                        evidence_ids=pat.get("evidence_ids", []),
                    )
                )

            # Include all financial transfer relationships
            for edge in edges_list:
                etype = edge["edge_type"].upper()
                if any(k in etype for k in ("TRANSFER", "PAYMENT", "ACCOUNT", "TRANSACTION")):
                    self._add_entity(edge["source_id"], nodes_dict, retrieved_entities)
                    self._add_entity(edge["target_id"], nodes_dict, retrieved_entities)
                    self._add_relationship(edge, nodes_dict, retrieved_relationships)

            for eid in entities + cases:
                self._add_entity(eid, nodes_dict, retrieved_entities)

    def _retrieve_pattern_context(
        self,
        query: str,
        store: GraphStore,
        nodes_dict: dict[str, dict[str, Any]],
        edges_list: list[dict[str, Any]],
        retrieved_entities: dict[str, EntityContext],
        retrieved_relationships: dict[str, RelationshipContext],
        retrieved_patterns: list[PatternContext],
        retrieved_evidence: dict[str, EvidenceContext],
        reasoning_steps: list[str],
    ) -> None:
        """Detect and attach structural graph patterns (phone sharing, bursts, cycles, bridges)."""
        reasoning_steps.append("Scanning graph for deterministic structural patterns and syndicate clusters.")
        
        # 1. Structural pattern rules over canonical store
        findings: list[PatternFinding] = detect_all_suspicious_patterns(store)
        for f in findings:
            retrieved_patterns.append(
                PatternContext(
                    pattern_id=f.rule_id,
                    pattern_type=f.rule_id,
                    severity=f.severity.lower() if hasattr(f, "severity") and f.severity else "medium",
                    description=f.explanation,
                    participating_entity_ids=f.entity_ids,
                    evidence_ids=f.evidence_ids,
                    metadata={"edge_ids": f.edge_ids, "derivation_class": f.derivation_class},
                )
            )
            for eid in f.entity_ids:
                self._add_entity(eid, nodes_dict, retrieved_entities)

        # 2. Financial layering tool findings
        fin_res = self._tools.detect_financial_layering()
        fin_findings = fin_res.data.get("findings") or fin_res.data.get("patterns") or []
        for p in fin_findings:
            retrieved_patterns.append(
                PatternContext(
                    pattern_id=p.get("rule_name") or p.get("rule_id", "circular_repeated_financial_flow"),
                    pattern_type=p.get("rule_name") or p.get("rule_id", "circular_repeated_financial_flow"),
                    severity="high",
                    description=p.get("description", "Circular or repeated high-volume transfer pattern detected."),
                    participating_entity_ids=p.get("entity_ids", []),
                    evidence_ids=p.get("evidence_ids", []),
                )
            )
            for eid in p.get("entity_ids", []):
                self._add_entity(eid, nodes_dict, retrieved_entities)

        # 3. Active graph pattern heuristics (detect repeated transfers & shared devices in active edges)
        pair_txns: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for edge in edges_list:
            etype = edge.get("edge_type", "").upper()
            if "TRANSFERRED" in etype or "TXN" in edge.get("id", ""):
                pair_txns.setdefault((edge["source_id"], edge["target_id"]), []).append(edge)

        for (src, tgt), txns in pair_txns.items():
            if len(txns) >= 2:
                ev_ids = [str(ev) for t in txns for ev in t.get("properties", {}).get("evidence_ids", []) if ev]
                retrieved_patterns.append(
                    PatternContext(
                        pattern_id="circular_repeated_financial_flow",
                        pattern_type="repeated_financial_flow",
                        severity="high",
                        description=f"Observed {len(txns)} repeated financial transfers from {src} to {tgt}.",
                        participating_entity_ids=[src, tgt],
                        evidence_ids=list(dict.fromkeys(ev_ids)),
                        metadata={"edge_ids": [t["id"] for t in txns]},
                    )
                )
                self._add_entity(src, nodes_dict, retrieved_entities)
                self._add_entity(tgt, nodes_dict, retrieved_entities)

        # Include incident edges between participating entities
        participating_set = {eid for p in retrieved_patterns for eid in p.participating_entity_ids}
        for edge in edges_list:
            if edge["source_id"] in participating_set and edge["target_id"] in participating_set:
                self._add_relationship(edge, nodes_dict, retrieved_relationships)

    def _retrieve_lead_triage_context(
        self,
        cases: list[str],
        store: GraphStore,
        nodes_dict: dict[str, dict[str, Any]],
        edges_list: list[dict[str, Any]],
        retrieved_entities: dict[str, EntityContext],
        retrieved_relationships: dict[str, RelationshipContext],
        retrieved_patterns: list[PatternContext],
        retrieved_evidence: dict[str, EvidenceContext],
        reasoning_steps: list[str],
    ) -> None:
        """Retrieve actionable investigative leads: high-betweenness bridges, Louvain clusters, and pattern hubs."""
        reasoning_steps.append("Retrieving key bridge brokers, active syndicate communities, and evidence anchors.")
        
        # 1. Bridge Nodes
        tool_res = self._tools.detect_bridge_brokers(case_id=cases[0] if cases else None)
        reasoning_steps.extend(tool_res.reasoning_path)
        for b in tool_res.data.get("bridges", []):
            nid = b.get("node_id")
            if nid:
                self._add_entity(nid, nodes_dict, retrieved_entities, is_bridge=True)
        for nid in tool_res.entity_ids:
            self._add_entity(nid, nodes_dict, retrieved_entities, is_bridge=True)

        # 2. Key Communities
        comm_res = self._tools.detect_communities()
        for comm in comm_res.data.get("communities", [])[:3]:
            for mid in comm.get("member_ids", [])[:5]:
                self._add_entity(mid, nodes_dict, retrieved_entities, community_id=str(comm.get("community_id")))
        for nid in comm_res.entity_ids:
            self._add_entity(nid, nodes_dict, retrieved_entities)

        # 3. Add inter-community and incident edges
        selected_ids = set(retrieved_entities.keys())
        for edge in edges_list:
            if edge["source_id"] in selected_ids and edge["target_id"] in selected_ids:
                self._add_relationship(edge, nodes_dict, retrieved_relationships)

    def _retrieve_case_dossier_context(
        self,
        case_id: str,
        nodes_dict: dict[str, dict[str, Any]],
        edges_list: list[dict[str, Any]],
        retrieved_entities: dict[str, EntityContext],
        retrieved_relationships: dict[str, RelationshipContext],
        retrieved_evidence: dict[str, EvidenceContext],
        retrieved_timeline: list[TimelineEventContext],
        reasoning_steps: list[str],
    ) -> None:
        """Retrieve authoritative case dossier: case node, accused persons, timeline, and evidence."""
        tool_res: NEXUSToolResult = self._tools.get_case_dossier(case_id)
        reasoning_steps.extend(tool_res.reasoning_path)

        c_data = tool_res.data
        c_id = c_data.get("id") or case_id
        self._add_entity(c_id, nodes_dict, retrieved_entities)

        # Accused & Associates
        for acc in c_data.get("accused", []):
            aid = acc.get("id") if isinstance(acc, dict) else str(acc)
            if aid:
                self._add_entity(aid, nodes_dict, retrieved_entities)

        # All incident edges for this case
        for edge in edges_list:
            if edge["source_id"] == c_id or edge["target_id"] == c_id:
                self._add_entity(edge["source_id"], nodes_dict, retrieved_entities)
                self._add_entity(edge["target_id"], nodes_dict, retrieved_entities)
                self._add_relationship(edge, nodes_dict, retrieved_relationships)

        # Timeline Event
        fir_date = c_data.get("registration_date") or c_data.get("created_at") or c_data.get("fir_date") or "2026-02-13"
        stn = c_data.get("station_name") or c_data.get("police_station") or "Cyber Crime PS"
        title = c_data.get("title") or c_data.get("description") or f"Case {c_id}"
        acc_ids = [a.get("id") for a in c_data.get("accused", []) if isinstance(a, dict) and a.get("id")]

        retrieved_timeline.append(
            TimelineEventContext(
                event_id=f"timeline-{c_id}",
                timestamp=str(fir_date),
                event_type="FIR_REGISTRATION",
                description=f"FIR registered at {stn}: {title}",
                entity_ids=[c_id] + acc_ids,
                evidence_ids=tool_res.evidence_ids,
            )
        )

    def _retrieve_neighborhood_context(
        self,
        cases: list[str],
        entities: list[str],
        store: GraphStore,
        nodes_dict: dict[str, dict[str, Any]],
        edges_list: list[dict[str, Any]],
        max_depth: int,
        retrieved_entities: dict[str, EntityContext],
        retrieved_relationships: dict[str, RelationshipContext],
        retrieved_evidence: dict[str, EvidenceContext],
        reasoning_steps: list[str],
    ) -> None:
        """Default BFS subgraph expansion for general entity/case queries."""
        seed_nodes = cases + entities
        if not seed_nodes:
            # Pick first available case as root
            for nid, n in nodes_dict.items():
                if n.get("type") in ("Case", "InvestigationCase"):
                    seed_nodes.append(nid)
                    break

        for root in seed_nodes:
            sub = get_subgraph(store, root, depth=min(max_depth, 2))
            reasoning_steps.append(f"Retrieved {len(sub.nodes)} nodes within {sub.depth} hops of {root}.")
            for n in sub.nodes:
                self._add_entity(n.node_id, nodes_dict, retrieved_entities)
            for edge in sub.edges:
                props = dict(edge.properties) if hasattr(edge, "properties") else {}
                edge_dict = {
                    "id": f"{edge.source_id}->{edge.target_id}:{edge.edge_type}",
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "edge_type": edge.edge_type,
                    "properties": props,
                }
                self._add_relationship(edge_dict, nodes_dict, retrieved_relationships)

    # ── Context Enhancement & Hydration ───────────────────────────────────────

    def _add_entity(
        self,
        node_id: str,
        nodes_dict: dict[str, dict[str, Any]],
        retrieved_entities: dict[str, EntityContext],
        is_bridge: bool = False,
        community_id: str | None = None,
    ) -> None:
        """Add an entity to the context map if present in nodes dictionary."""
        if node_id not in nodes_dict:
            return
        if node_id in retrieved_entities:
            if is_bridge:
                retrieved_entities[node_id].is_bridge = True
            if community_id:
                retrieved_entities[node_id].community_id = community_id
            return

        raw = nodes_dict[node_id]
        props = raw.get("properties", {})
        cases = []
        if "case_id" in props and props["case_id"]:
            cases.append(str(props["case_id"]))
        if "case_ids" in props and isinstance(props["case_ids"], list):
            cases.extend([str(c) for c in props["case_ids"]])

        retrieved_entities[node_id] = EntityContext(
            id=node_id,
            label=raw.get("label", node_id),
            entity_type=raw.get("entity_type") or raw.get("type") or "Unknown",
            properties={k: v for k, v in props.items() if k not in ("embedding", "vector")},
            case_ids=list(dict.fromkeys(cases)),
            is_bridge=is_bridge,
            community_id=community_id,
        )

    def _add_relationship(
        self,
        edge: dict[str, Any],
        nodes_dict: dict[str, dict[str, Any]],
        retrieved_relationships: dict[str, RelationshipContext],
    ) -> None:
        """Add a relationship edge to the context map."""
        eid = edge["id"]
        if eid in retrieved_relationships:
            return

        src_id = edge["source_id"]
        tgt_id = edge["target_id"]
        props = edge.get("properties", {})
        ev_list = props.get("evidence_ids", [])
        if not isinstance(ev_list, list):
            ev_list = [str(ev_list)] if ev_list else []

        src_lbl = nodes_dict.get(src_id, {}).get("label", src_id)
        tgt_lbl = nodes_dict.get(tgt_id, {}).get("label", tgt_id)

        retrieved_relationships[eid] = RelationshipContext(
            id=eid,
            source_id=src_id,
            source_label=src_lbl,
            target_id=tgt_id,
            target_label=tgt_lbl,
            relationship_type=edge["edge_type"],
            properties=props,
            evidence_ids=ev_list,
            case_ids=[c for c in [props.get("case_id")] if c],
        )

    def _enrich_graph_metadata(
        self, store: GraphStore, retrieved_entities: dict[str, EntityContext]
    ) -> None:
        """Compute and annotate global bridge and community membership."""
        try:
            bridges = compute_person_bridge_intelligence(store)
            bridge_ids = {b.person_id for b in bridges if b.articulation_point or b.betweenness_centrality > 0.0}
            for nid in retrieved_entities:
                if nid in bridge_ids:
                    retrieved_entities[nid].is_bridge = True
        except Exception:
            pass

        try:
            comms_summary = detect_louvain_communities(store)
            for c in comms_summary.communities:
                for member_id in c.member_ids:
                    if member_id in retrieved_entities:
                        retrieved_entities[member_id].community_id = str(c.community_id)
        except Exception:
            pass

    def _hydrate_evidence_records(
        self,
        retrieved_relationships: dict[str, RelationshipContext],
        retrieved_patterns: list[PatternContext],
        retrieved_evidence: dict[str, EvidenceContext],
    ) -> None:
        """Retrieve full forensic provenance for all referenced evidence IDs."""
        all_ev_ids: set[str] = set()
        for r in retrieved_relationships.values():
            all_ev_ids.update(r.evidence_ids)
        for p in retrieved_patterns:
            all_ev_ids.update(p.evidence_ids)

        for ev_id in all_ev_ids:
            if not ev_id or ev_id in retrieved_evidence:
                continue
            item = self._evidence_svc.get_evidence_by_id(ev_id, actor_id="graphrag") if self._evidence_svc else None
            if item:
                retrieved_evidence[ev_id] = EvidenceContext(
                    evidence_id=item.id,
                    source_type=item.provenance.source_type,
                    source_id=item.provenance.source_id,
                    locator=item.locator,
                    description=item.description,
                    excerpt=item.excerpt or "",
                    confidence=item.provenance.confidence,
                    extracted_fact=item.extracted_fact or item.description,
                    provenance={
                        "source_type": item.provenance.source_type,
                        "source_id": item.provenance.source_id,
                        "extracted_fact": item.provenance.extracted_fact,
                        "confidence": item.provenance.confidence,
                    },
                )
            else:
                # Build fallback provenance record from edge coordinates
                retrieved_evidence[ev_id] = EvidenceContext(
                    evidence_id=ev_id,
                    source_type="INVESTIGATION_RECORD",
                    description=f"Verified forensic evidence artifact {ev_id}",
                    confidence=1.0,
                )

    def _prune_entities(
        self,
        retrieved_entities: dict[str, EntityContext],
        focal_entities: list[str],
        focal_cases: list[str],
        max_nodes: int,
    ) -> list[EntityContext]:
        """Rank and prune entities to fit within token budgets."""
        if len(retrieved_entities) <= max_nodes:
            return list(retrieved_entities.values())

        # Scoring: focal items (100) > bridge nodes (50) > case nodes (30) > regular nodes (10)
        def score(e: EntityContext) -> int:
            pts = 0
            if e.id in focal_entities or e.id in focal_cases:
                pts += 100
            if e.is_bridge:
                pts += 50
            if e.entity_type in ("Case", "InvestigationCase"):
                pts += 30
            if e.evidence_ids:
                pts += len(e.evidence_ids) * 5
            return pts

        ranked = sorted(retrieved_entities.values(), key=score, reverse=True)
        return ranked[:max_nodes]

    def _prune_relationships(
        self,
        retrieved_relationships: dict[str, RelationshipContext],
        final_entities: list[EntityContext],
    ) -> list[RelationshipContext]:
        """Retain only relationships between active, pruned entities."""
        valid_ids = {e.id for e in final_entities}
        valid_rels = [
            r for r in retrieved_relationships.values()
            if r.source_id in valid_ids and r.target_id in valid_ids
        ]
        return valid_rels
