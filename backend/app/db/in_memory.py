"""In-memory backend repository seeded from the synthetic graph artifact.

This is the Dev 1 storage adapter boundary. It gives the FastAPI app working
backend APIs now, while keeping the Catalyst Data Store integration swappable.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.core.clock.engine import ClockEngine
from backend.app.core.dependency.engine import DependencyEngine
from backend.app.core.escalation.engine import EscalationEngine
from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord
from backend.app.core.graph.repositories.graph_repository import GraphRepository
from shared.contracts.api import (
    CaseDetailResponse,
    CaseSummaryResponse,
    ClockInstanceResponse,
    ClockStatus,
    CopilotQueryResponse,
    DependencyResponse,
    DependencyStatus,
    EscalationResponse,
)


class InMemoryBackendRepository:
    """Read/write repository for the prototype backend API surface."""

    def __init__(
        self,
        artifact_path: Path | None = None,
        state_path: Path | None = None,
        reference_time: datetime | None = None,
    ) -> None:
        self.reference_time = reference_time or datetime.now(timezone.utc)
        if self.reference_time.tzinfo is None:
            self.reference_time = self.reference_time.replace(tzinfo=timezone.utc)

        self.clock_engine = ClockEngine(self.reference_time)
        self.dependency_engine = DependencyEngine(self.reference_time)
        self.escalation_engine = EscalationEngine(self.reference_time)

        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self.incident_edges: dict[str, list[dict[str, Any]]] = {}
        self.manual_escalations: dict[str, EscalationResponse] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.documents: dict[str, dict[str, Any]] = {}
        self.state_path = state_path

        self._load_artifact(artifact_path or self._default_artifact_path())
        self._load_state()
        self._rebuild_indexes()

    def _default_artifact_path(self) -> Path:
        local_resource = Path(__file__).resolve().parent / "synthetic_graph.json"
        if local_resource.exists():
            return local_resource
        return Path(__file__).resolve().parents[3] / "artifacts" / "synthetic_graph" / "synthetic_graph.json"

    def _load_artifact(self, artifact_path: Path) -> None:
        if not artifact_path.exists():
            raise FileNotFoundError(f"Synthetic graph artifact not found: {artifact_path}")

        raw = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.nodes = {str(node["id"]): dict(node) for node in raw.get("nodes", [])}
        self.edges = [dict(edge) for edge in raw.get("edges", [])]

    def _load_state(self) -> None:
        if self.state_path is None or not self.state_path.exists():
            return

        raw = json.loads(self.state_path.read_text(encoding="utf-8"))
        for node_id, patch in raw.get("node_patches", {}).items():
            if node_id in self.nodes:
                self.nodes[node_id].update(patch)

        self.manual_escalations = {
            escalation_id: EscalationResponse(**payload)
            for escalation_id, payload in raw.get("manual_escalations", {}).items()
        }
        self.audit_events = list(raw.get("audit_events", []))
        self.documents = {
            str(document_id): dict(document)
            for document_id, document in raw.get("documents", {}).items()
        }

    def _save_state(self) -> None:
        if self.state_path is None:
            return

        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        node_patches = {
            node_id: {
                key: node.get(key)
                for key in ("status", "resolved_at", "days_stale")
                if key in node
            }
            for node_id, node in self.nodes.items()
            if node.get("entity_type") == "Dependency"
        }
        payload = {
            "node_patches": node_patches,
            "manual_escalations": {
                escalation_id: escalation.model_dump(mode="json")
                for escalation_id, escalation in self.manual_escalations.items()
            },
            "audit_events": self.audit_events[-500:],
            "documents": self.documents,
        }
        self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _rebuild_indexes(self) -> None:
        self.case_ids = [node_id for node_id, node in self.nodes.items() if node.get("entity_type") == "Case"]
        self.case_to_clocks = self._targets_by_edge("CASE_HAS_CLOCK")
        self.case_to_dependencies = self._targets_by_edge("CASE_HAS_DEPENDENCY")
        self.incident_edges = {}
        for edge in self.edges:
            source_id = str(edge.get("source_id", ""))
            target_id = str(edge.get("target_id", ""))
            if source_id:
                self.incident_edges.setdefault(source_id, []).append(edge)
            if target_id and target_id != source_id:
                self.incident_edges.setdefault(target_id, []).append(edge)
        self.case_to_officer = {
            edge["source_id"]: edge["target_id"]
            for edge in self.edges
            if edge.get("edge_type") == "INVESTIGATED_BY"
        }
        self.graph_store = self._build_graph_store()
        self.graph_repository = GraphRepository(self.graph_store)

    def _targets_by_edge(self, edge_type: str) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for edge in self.edges:
            if edge.get("edge_type") == edge_type:
                result.setdefault(str(edge["source_id"]), []).append(str(edge["target_id"]))
        return result

    def _build_graph_store(self) -> GraphStore:
        store = GraphStore()
        for node_id, node in self.nodes.items():
            properties = {key: value for key, value in node.items() if key not in {"id", "entity_type"}}
            store.nodes[node_id] = NodeRecord(
                node_id=node_id,
                entity_type=str(node.get("entity_type")),
                properties=properties,
            )
        for edge in self.edges:
            adj_edge = AdjEdge(
                edge_type=str(edge.get("edge_type")),
                source_id=str(edge.get("source_id")),
                target_id=str(edge.get("target_id")),
                properties={key: value for key, value in edge.items() if key not in {"edge_type", "source_id", "target_id", "storage_mode"}},
            )
            store.adj.setdefault(adj_edge.source_id, []).append(adj_edge)
            store.radj.setdefault(adj_edge.target_id, []).append(adj_edge)
            store.edge_index.setdefault(adj_edge.edge_type, []).append(adj_edge)
            store.adj.setdefault(adj_edge.target_id, [])
            store.radj.setdefault(adj_edge.source_id, [])
        return store

    def list_worklist(self, role: str = "IO") -> list[CaseSummaryResponse]:
        self._audit("worklist_viewed", role=role)
        summaries = [self._case_summary(case_id) for case_id in self.case_ids]
        visible = self._filter_by_role(summaries, role)
        return sorted(visible, key=lambda item: (item.risk_rank, item.clock.days_remaining, item.fir_number))

    def get_case_detail(self, case_id: str) -> CaseDetailResponse | None:
        case = self.nodes.get(case_id)
        if not case or case.get("entity_type") != "Case":
            return None
        self._audit("case_viewed", case_id=case_id)
        clocks = self._case_clocks(case_id, case)
        dependencies = self._case_dependencies(case_id)
        return CaseDetailResponse(
            id=case_id,
            fir_number=str(case.get("fir_number", case_id)),
            station_name=str(case.get("police_station", "Unknown station")),
            offence_category=str(case.get("offence_category", "unknown")),
            clocks=clocks,
            dependencies=dependencies,
        )

    def update_dependency(self, dependency_id: str, status: DependencyStatus) -> DependencyResponse | None:
        node = self.nodes.get(dependency_id)
        if not node or node.get("entity_type") != "Dependency":
            return None
        node["status"] = status.value
        if status == DependencyStatus.RESOLVED:
            node["resolved_at"] = self.reference_time.isoformat()
            node["days_stale"] = 0
        if status == DependencyStatus.ESCALATED:
            self._record_manual_escalation(node)
        dependency = self.dependency_engine.from_node(dependency_id, node)
        self._audit(
            "dependency_updated",
            dependency_id=dependency_id,
            case_id=dependency.case_id,
            status=status.value,
        )
        self._save_state()
        return dependency

    def list_escalations(self) -> list[EscalationResponse]:
        generated: dict[str, EscalationResponse] = {}
        for case_id in self.case_ids:
            case = self.nodes[case_id]
            clocks = self._case_clocks(case_id, case)
            dependencies = self._case_dependencies(case_id)
            officer_id = self.case_to_officer.get(case_id)
            for escalation in self.escalation_engine.evaluate_case(case_id, clocks, dependencies, officer_id):
                generated[escalation.id] = escalation
        generated.update(self.manual_escalations)
        self._audit("escalations_viewed", count=len(generated))
        return sorted(
            generated.values(),
            key=lambda item: (item.resolved, item.triggered_at),
            reverse=True,
        )

    def record_escalation(self, escalation: EscalationResponse) -> bool:
        """Persist an escalation idempotently. Returns True if newly added, False if already exists."""
        if escalation.id in self.manual_escalations:
            return False
        self.manual_escalations[escalation.id] = escalation
        self._save_state()
        return True

    def get_district_rollup(self, district: str) -> dict[str, Any]:
        district_normalized = district.strip().lower()
        district_case_ids = []
        for case_id in self.case_ids:
            case_node = self.nodes.get(case_id)
            if case_node and case_node.get("district", "").strip().lower() == district_normalized:
                district_case_ids.append(case_id)
                
        total_cases = len(district_case_ids)
        red_clocks = 0
        amber_clocks = 0
        stale_dependencies = 0
        
        station_data: dict[str, dict[str, int]] = {}
        
        for case_id in district_case_ids:
            case_node = self.nodes[case_id]
            station_name = str(case_node.get("police_station", "Unknown station"))
            station_entry = station_data.setdefault(station_name, {"total": 0, "critical": 0})
            station_entry["total"] += 1
            
            clocks = self._case_clocks(case_id, case_node)
            is_case_critical = False
            for clock in clocks:
                if clock.status == ClockStatus.RED:
                    red_clocks += 1
                    is_case_critical = True
                elif clock.status == ClockStatus.OVERDUE:
                    is_case_critical = True
                elif clock.status == ClockStatus.AMBER:
                    amber_clocks += 1
            
            dependencies = self._case_dependencies(case_id)
            for dep in dependencies:
                if dep.status != DependencyStatus.RESOLVED and dep.days_stale > 0:
                    stale_dependencies += 1
                    
            if is_case_critical:
                station_entry["critical"] += 1
                
        station_rankings = [
            {
                "station_name": name,
                "total": stats["total"],
                "critical": stats["critical"],
            }
            for name, stats in station_data.items()
        ]
        station_rankings.sort(key=lambda s: (-s["critical"], -s["total"], s["station_name"]))
        
        return {
            "total_cases": total_cases,
            "red_clocks": red_clocks,
            "amber_clocks": amber_clocks,
            "stale_dependencies": stale_dependencies,
            "station_rankings": station_rankings,
        }

    def case_network(self, case_id: str) -> dict[str, Any] | None:
        if case_id not in self.nodes:
            return None
        self._audit("case_network_viewed", case_id=case_id)
        node_ids: list[str] = [case_id]
        edge_rows: list[dict[str, Any]] = []
        for edge in self.incident_edges.get(case_id, []):
            peer = edge["target_id"] if edge["source_id"] == case_id else edge["source_id"]
            if peer in self.nodes and len(node_ids) < 18:
                node_ids.append(peer)
                edge_rows.append(edge)
        unique_node_ids = list(dict.fromkeys(node_ids))
        return {
            "nodes": [self._flow_node(node_id, index) for index, node_id in enumerate(unique_node_ids)],
            "edges": [self._flow_edge(edge, index) for index, edge in enumerate(edge_rows) if edge["source_id"] in unique_node_ids and edge["target_id"] in unique_node_ids],
        }

    def copilot_query(self, query: str, case_id: str | None) -> CopilotQueryResponse:
        normalized = query.lower()
        if any(term in normalized for term in ("guilty", "culpable", "reoffend", "criminal mindset")):
            self._audit("copilot_refused", case_id=case_id, reason="prohibited_inference")
            return CopilotQueryResponse(
                refused=True,
                refusal_reason="I cannot infer guilt, innocence, culpability, or reoffense risk. I can only summarize recorded case facts.",
                confidence=0.95,
            )

        if case_id and case_id in self.nodes:
            detail = self.get_case_detail(case_id)
            if detail:
                clock = min(detail.clocks, key=lambda item: item.days_remaining) if detail.clocks else None
                blocker = max(detail.dependencies, key=lambda item: item.days_stale, default=None)
                answer_parts: list[str] = []
                path: list[str] = [f"Case({case_id})"]
                if clock:
                    answer_parts.append(f"the most urgent clock has {clock.days_remaining} day(s) remaining")
                    path.append(f"ClockInstance({clock.id}) [status={clock.status.value}, days_remaining={clock.days_remaining}]")
                if blocker and blocker.status != DependencyStatus.RESOLVED:
                    answer_parts.append(f"{blocker.name} is pending for {blocker.days_stale} day(s)")
                    path.append(f"Dependency({blocker.id}) [status={blocker.status.value}, days_stale={blocker.days_stale}]")
                answer = f"Case {detail.fir_number}: " + ("; ".join(answer_parts) if answer_parts else "no active statutory blocker is recorded.")
                self._audit("copilot_answered", case_id=case_id, confidence=0.82)
                return CopilotQueryResponse(answer=answer, refused=False, reasoning_path=path, confidence=0.82)

        self._audit("copilot_answered", case_id=case_id, confidence=0.55)
        return CopilotQueryResponse(
            answer="I can answer case-clock, dependency, escalation, and graph-fact questions when they map to the current investigation graph.",
            refused=False,
            reasoning_path=["Query parsed -> supported fallback response"],
            confidence=0.55,
        )

    def _case_summary(self, case_id: str) -> CaseSummaryResponse:
        case = self.nodes[case_id]
        clocks = self._case_clocks(case_id, case)
        primary_clock = min(clocks, key=lambda item: item.days_remaining) if clocks else self.clock_engine.from_case(case_id, case)
        unresolved = [dep for dep in self._case_dependencies(case_id) if dep.status != DependencyStatus.RESOLVED]
        return CaseSummaryResponse(
            id=case_id,
            fir_number=str(case.get("fir_number", case_id)),
            station_name=str(case.get("police_station", "Unknown station")),
            offence_category=str(case.get("offence_category", "unknown")),
            updated_at=case["updated_at"],
            clock=primary_clock,
            unresolved_dependency_count=len(unresolved),
            risk_rank=self._risk_rank(primary_clock, len(unresolved)),
        )

    def _case_clocks(self, case_id: str, case: dict[str, Any]) -> list[ClockInstanceResponse]:
        clocks: list[ClockInstanceResponse] = []
        for clock_id in self.case_to_clocks.get(case_id, []):
            node = self.nodes.get(clock_id)
            if node:
                clock = self.clock_engine.from_clock_node(clock_id, node)
                if not clock.case_id:
                    clock.case_id = case_id
                clocks.append(clock)
        if not clocks:
            try:
                clocks.append(self.clock_engine.from_case(case_id, case))
            except KeyError:
                pass
        return sorted(clocks, key=lambda item: item.days_remaining)

    def _case_dependencies(self, case_id: str) -> list[DependencyResponse]:
        dependencies: list[DependencyResponse] = []
        for dependency_id in self.case_to_dependencies.get(case_id, []):
            node = self.nodes.get(dependency_id)
            if node:
                dependency = self.dependency_engine.from_node(dependency_id, node)
                if not dependency.case_id:
                    dependency.case_id = case_id
                dependencies.append(dependency)
        return sorted(dependencies, key=lambda item: (-item.days_stale, item.name))

    def _record_manual_escalation(self, dependency_node: dict[str, Any]) -> None:
        case_id = str(dependency_node.get("case_id", ""))
        if not case_id:
            return
        escalation_id = f"manual-esc-{dependency_node['id']}"
        self.manual_escalations[escalation_id] = EscalationResponse(
            id=escalation_id,
            case_id=case_id,
            triggered_at=self.reference_time,
            reason=f"{dependency_node.get('dependency_type', 'Dependency')} was manually escalated by the investigating officer.",
            routed_to_rank="SHO",
            routed_to_officer_id=self.case_to_officer.get(case_id, "SHO"),
            resolved=False,
        )
        self._audit(
            "manual_escalation_created",
            escalation_id=escalation_id,
            case_id=case_id,
            dependency_id=str(dependency_node["id"]),
        )

    def list_audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.audit_events[-limit:]

    def _audit(self, event_type: str, **details: Any) -> None:
        self.audit_events.append(
            {
                "id": f"audit-{len(self.audit_events) + 1}",
                "event_type": event_type,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "details": details,
            }
        )

    def _filter_by_role(self, summaries: list[CaseSummaryResponse], role: str) -> list[CaseSummaryResponse]:
        if role == "IO":
            return summaries[:100]
        if role == "SHO":
            return summaries[:250]
        return summaries

    def _risk_rank(self, clock: ClockInstanceResponse, unresolved_count: int) -> int:
        base = 0 if clock.days_remaining < 0 else max(clock.days_remaining, 0)
        return base * 10 + min(unresolved_count, 9)

    def _flow_node(self, node_id: str, index: int) -> dict[str, Any]:
        node = self.nodes[node_id]
        entity_type = str(node.get("entity_type", "unknown"))
        angle_bucket = index % 8
        radius = 170 if index else 0
        return {
            "id": node_id,
            "type": entity_type.lower().replace("clockinstance", "clock").replace("crimehead", "crime-head"),
            "data": {"label": self._node_label(node_id, node)},
            "position": {
                "x": 300 + (angle_bucket - 4) * radius // 2,
                "y": 220 + ((index // 8) * 120) + (0 if index else -150),
            },
        }

    def _flow_edge(self, edge: dict[str, Any], index: int) -> dict[str, Any]:
        return {
            "id": f"edge-{index}-{edge['source_id']}-{edge['target_id']}",
            "source": edge["source_id"],
            "target": edge["target_id"],
            "label": edge["edge_type"],
        }

    def _node_label(self, node_id: str, node: dict[str, Any]) -> str:
        entity_type = node.get("entity_type")
        if entity_type == "Case":
            return str(node.get("fir_number", node_id))
        if entity_type == "Person":
            return str(node.get("full_name", node_id))
        if entity_type == "Officer":
            return str(node.get("full_name") or node.get("badge_number") or node_id)
        if entity_type == "Dependency":
            return str(node.get("dependency_type", "Dependency"))
        if entity_type == "ClockInstance":
            return str(node.get("clock_type", "Clock"))
        return str(node.get("unit_name") or node.get("head_name") or node.get("section_code") or node_id)
