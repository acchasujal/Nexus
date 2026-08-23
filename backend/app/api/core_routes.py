"""backend/app/api/core_routes.py

FastAPI API routers for the NEXUS Criminal Intelligence Platform.
Wires together all core endpoints:
  - Investigations & Cases (/investigations, /cases)
  - Entity Resolution (/entity-resolution, /entities)
  - Network & Subgraph Explorer (/network)
  - Communities & Centrality (/communities, /influence)
  - Pattern & Anomalies (/patterns)
  - Timeline & Provenance (/timeline, /evidence)
  - Grounded Copilot (/copilot)
  - RBAC Authentication (/auth)
  - Audit Trail (/audit)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.app.api.dependencies import (
    get_audit_service,
    get_case_service,
    get_copilot_service,
    get_principal,
    get_repository,
    get_request_id,
)
from backend.app.auth.principal import Principal
from backend.app.config import Settings, get_settings
from backend.app.core.graph.algorithms.clustering import detect_communities, find_bridge_nodes, betweenness_centrality, degree_centrality
from backend.app.core.graph.algorithms.entity_resolution import resolve_person
from backend.app.core.graph.algorithms.pattern_detection import find_repeat_accused, find_shared_clusters
from backend.app.services.audit_service import AuditEventType, AuditService
from backend.app.services.case_service import InvestigationService
from backend.app.services.copilot_service import CopilotService
from shared.contracts.api import (
    AuditLogEntry,
    AuthLoginRequest,
    AuthTokenResponse,
    BridgeNodeResponse,
    CommunityResponse,
    CopilotQueryRequest,
    CopilotQueryResponse,
    EntityResolutionMatchResponse,
    EntityResolutionQuery,
    EntityResolutionResponse,
    EvidenceItemResponse,
    InfluenceRankingResponse,
    InvestigationDetailResponse,
    InvestigationSummaryResponse,
    NetworkGraphResponse,
    RepeatOffenderResponse,
    SharedClusterResponse,
    TimelineEventResponse,
    UserRole,
)


def create_core_router() -> APIRouter:
    router = APIRouter()

    # ── System Health & Root ──────────────────────────────────────────────────

    @router.get("/")
    def root() -> dict[str, str]:
        cfg = get_settings()
        return {
            "service": "NEXUS Criminal Intelligence Platform API",
            "status": "ok",
            "version": cfg.app_version,
            "architecture": "Evidence-Grounded Intelligence Graph",
        }

    @router.get("/health")
    def health() -> dict[str, str]:
        cfg = get_settings()
        return {
            "status": "ok",
            "service": "nexus-backend",
            "version": cfg.app_version,
            "environment": cfg.environment,
        }

    # ── Authentication ────────────────────────────────────────────────────────

    @router.post("/auth/login", response_model=AuthTokenResponse)
    def login(req: AuthLoginRequest, settings: Settings = Depends(get_settings)) -> AuthTokenResponse:
        role = req.role or UserRole.INVESTIGATOR
        token_payload = {
            "sub": req.username,
            "email": f"{req.username}@nexus.internal",
            "role": role.value,
        }
        token = jwt.encode(token_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        return AuthTokenResponse(
            access_token=token,
            token_type="bearer",
            user_id=req.username,
            role=role,
            expires_in=settings.jwt_expire_seconds,
        )

    # ── Investigations & Cases ────────────────────────────────────────────────

    @router.get("/investigations", response_model=list[InvestigationSummaryResponse])
    def list_investigations(
        district: Optional[str] = Query(None),
        category: Optional[str] = Query(None),
        status: Optional[str] = Query(None),
        principal: Principal = Depends(get_principal),
        service: InvestigationService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> list[InvestigationSummaryResponse]:
        return service.list_investigations(
            principal=principal,
            district=district,
            category=category,
            status=status,
            request_id=request_id,
        )

    @router.get("/investigations/{case_id}", response_model=InvestigationDetailResponse)
    def get_investigation(
        case_id: str,
        principal: Principal = Depends(get_principal),
        service: InvestigationService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> InvestigationDetailResponse:
        detail = service.get_investigation_detail(case_id, principal=principal, request_id=request_id)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"Investigation '{case_id}' not found")
        return detail

    # Backward compatibility worklist endpoint
    @router.get("/worklist")
    def worklist_legacy(
        principal: Principal = Depends(get_principal),
        service: InvestigationService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> list[Any]:
        return service.list_worklist(principal=principal, request_id=request_id)

    @router.get("/cases/{case_id}")
    def case_detail_legacy(
        case_id: str,
        principal: Principal = Depends(get_principal),
        service: InvestigationService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> Any:
        detail = service.get_case_detail(case_id, principal=principal, request_id=request_id)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found")
        return detail

    # ── Network & Graph Explorer ──────────────────────────────────────────────

    @router.get("/network/cases/{case_id}", response_model=NetworkGraphResponse)
    @router.get("/cases/{case_id}/network", response_model=NetworkGraphResponse)
    def case_network(
        case_id: str,
        depth: int = Query(2, ge=1, le=4),
        principal: Principal = Depends(get_principal),
        service: InvestigationService = Depends(get_case_service),
        request_id: str = Depends(get_request_id),
    ) -> NetworkGraphResponse:
        return service.get_case_network(case_id, principal=principal, depth=depth, request_id=request_id)

    # ── Entity Resolution ─────────────────────────────────────────────────────

    @router.post("/entity-resolution/resolve", response_model=EntityResolutionResponse)
    def resolve_entities(
        query: EntityResolutionQuery,
        repo: Any = Depends(get_repository),
        audit: AuditService = Depends(get_audit_service),
        principal: Principal = Depends(get_principal),
        request_id: str = Depends(get_request_id),
    ) -> EntityResolutionResponse:
        store = repo.to_graph_store()
        matches = resolve_person(
            store=store,
            query=query.model_dump(),
            confidence_threshold=query.confidence_threshold,
            candidate_limit=query.candidate_limit,
        )
        audit.record(
            AuditEventType.ENTITY_RESOLUTION_EXECUTED,
            actor_id=principal.user_id,
            request_id=request_id,
            details={"query": query.model_dump(), "match_count": len(matches)},
        )
        return EntityResolutionResponse(
            query=query.model_dump(),
            matches=[
                EntityResolutionMatchResponse(
                    matched_node_id=m.matched_node_id,
                    confidence=m.confidence,
                    status=m.status,
                    matched_fields=m.matched_fields,
                    reason=m.reason,
                    evidence_breakdown=m.evidence_breakdown,
                    properties=m.properties,
                )
                for m in matches
            ],
            total_matches=len(matches),
        )

    # ── Communities & Bridge Analysis ─────────────────────────────────────────

    @router.get("/communities", response_model=list[CommunityResponse])
    def get_communities(
        repo: Any = Depends(get_repository),
        audit: AuditService = Depends(get_audit_service),
        principal: Principal = Depends(get_principal),
        request_id: str = Depends(get_request_id),
    ) -> list[CommunityResponse]:
        store = repo.to_graph_store()
        comms = detect_communities(store)
        audit.record(
            AuditEventType.COMMUNITY_DETECTION_EXECUTED,
            actor_id=principal.user_id,
            request_id=request_id,
            details={"community_count": len(comms)},
        )
        return [
            CommunityResponse(
                community_id=c.community_id,
                size=c.size,
                member_ids=c.member_ids,
                dominant_entity_type=c.dominant_entity_type,
                top_influencer_id=c.top_influencer_id,
                reason=c.reason,
            )
            for c in comms
        ]

    @router.get("/influence/bridges", response_model=list[BridgeNodeResponse])
    def get_bridge_nodes(
        repo: Any = Depends(get_repository),
        audit: AuditService = Depends(get_audit_service),
        principal: Principal = Depends(get_principal),
        request_id: str = Depends(get_request_id),
    ) -> list[BridgeNodeResponse]:
        store = repo.to_graph_store()
        bridges = find_bridge_nodes(store)
        audit.record(
            AuditEventType.BRIDGE_ANALYSIS_EXECUTED,
            actor_id=principal.user_id,
            request_id=request_id,
            details={"bridge_count": len(bridges)},
        )
        return [
            BridgeNodeResponse(
                node_id=b.node_id,
                entity_type=b.entity_type,
                label=b.label,
                connected_components_count=b.connected_components_count,
                betweenness_score=b.betweenness_score,
                reason=b.reason,
            )
            for b in bridges
        ]

    @router.get("/influence/rankings", response_model=list[InfluenceRankingResponse])
    def get_influence_rankings(
        limit: int = Query(20, ge=1, le=100),
        repo: Any = Depends(get_repository),
    ) -> list[InfluenceRankingResponse]:
        store = repo.to_graph_store()
        deg = degree_centrality(store)
        btw = betweenness_centrality(store)

        ranked = []
        for nid, node in store.nodes.items():
            deg_score = deg.get(nid, 0.0)
            btw_score = btw.get(nid, 0.0)
            props = node.properties or {}
            label = props.get("full_name") or props.get("fir_number") or props.get("phone_number") or nid
            ranked.append({
                "node_id": nid,
                "label": label,
                "entity_type": node.entity_type,
                "degree_centrality": round(deg_score, 4),
                "betweenness_centrality": round(btw_score, 4),
                "combined": deg_score + btw_score * 2,
            })

        ranked.sort(key=lambda r: r["combined"], reverse=True)
        return [
            InfluenceRankingResponse(
                node_id=r["node_id"],
                label=r["label"],
                entity_type=r["entity_type"],
                degree_centrality=r["degree_centrality"],
                betweenness_centrality=r["betweenness_centrality"],
                rank=idx,
            )
            for idx, r in enumerate(ranked[:limit], start=1)
        ]

    # ── Patterns & Repeat Entities ────────────────────────────────────────────

    @router.get("/patterns/repeat-offenders", response_model=list[RepeatOffenderResponse])
    def get_repeat_offenders(
        min_cases: int = Query(2, ge=2),
        repo: Any = Depends(get_repository),
    ) -> list[RepeatOffenderResponse]:
        store = repo.to_graph_store()
        repeats = find_repeat_accused(store, min_cases=min_cases)
        results = []
        for r in repeats:
            p_node = store.nodes.get(r.person_id)
            name = p_node.properties.get("full_name", r.person_id) if p_node else r.person_id
            results.append(
                RepeatOffenderResponse(
                    person_id=r.person_id,
                    person_name=name,
                    case_ids=r.case_ids,
                    case_count=r.case_count,
                    reason=r.reason,
                )
            )
        return results

    @router.get("/patterns/shared-clusters", response_model=list[SharedClusterResponse])
    def get_shared_clusters(
        cluster_type: Optional[str] = Query(None),
        repo: Any = Depends(get_repository),
    ) -> list[SharedClusterResponse]:
        store = repo.to_graph_store()
        clusters = find_shared_clusters(store, cluster_type=cluster_type)
        return [
            SharedClusterResponse(
                cluster_id=c.cluster_id,
                cluster_type=c.cluster_type,
                person_ids=c.person_ids,
                case_ids=c.case_ids,
                reason=c.reason,
            )
            for c in clusters
        ]

    # ── Timeline ──────────────────────────────────────────────────────────────

    @router.get("/timeline", response_model=list[TimelineEventResponse])
    def get_timeline_events(
        case_id: Optional[str] = Query(None),
        repo: Any = Depends(get_repository),
        audit: AuditService = Depends(get_audit_service),
        principal: Principal = Depends(get_principal),
        request_id: str = Depends(get_request_id),
    ) -> list[TimelineEventResponse]:
        events: list[TimelineEventResponse] = []
        for nid, node in repo.nodes.items():
            if node.get("entity_type") in ("Event", "EVENT", "Case", "CASE"):
                props = node.get("properties", {})
                ts = props.get("timestamp") or props.get("incident_date") or props.get("created_at") or "2026-01-15T10:00:00Z"
                desc = props.get("description") or props.get("summary") or props.get("title") or "Logged graph event"
                events.append(
                    TimelineEventResponse(
                        id=nid,
                        event_type=props.get("event_type", node.get("entity_type")),
                        timestamp=ts,
                        description=desc,
                        participant_ids=props.get("participant_ids", []),
                        case_id=case_id or props.get("case_id"),
                    )
                )

        audit.record(
            AuditEventType.TIMELINE_VIEWED,
            actor_id=principal.user_id,
            case_id=case_id,
            request_id=request_id,
        )
        return sorted(events, key=lambda e: e.timestamp, reverse=True)[:50]

    # ── Investigator Copilot ──────────────────────────────────────────────────

    @router.post("/copilot/query", response_model=CopilotQueryResponse)
    def copilot_query(
        req: CopilotQueryRequest,
        principal: Principal = Depends(get_principal),
        copilot_svc: CopilotService = Depends(get_copilot_service),
        request_id: str = Depends(get_request_id),
    ) -> CopilotQueryResponse:
        return copilot_svc.handle_query(req, principal=principal, request_id=request_id)

    # ── Audit Trail ───────────────────────────────────────────────────────────

    @router.get("/audit", response_model=list[AuditLogEntry])
    def get_audit_trail(
        case_id: Optional[str] = Query(None),
        limit: int = Query(50, ge=1, le=200),
        principal: Principal = Depends(get_principal),
        audit_svc: AuditService = Depends(get_audit_service),
    ) -> list[AuditLogEntry]:
        if not principal.can_view_audit_log():
            raise HTTPException(status_code=403, detail="Forbidden: Insufficient privileges to view audit log.")
        raw_events = audit_svc.list_events(case_id=case_id, limit=limit)
        return [
            AuditLogEntry(
                id=e["id"],
                user_id=e["actor_id"],
                user_role=e.get("details", {}).get("role", "INVESTIGATOR"),
                action=e["event_type"],
                entity_type=e.get("entity_type"),
                entity_id=e.get("entity_id") or e.get("case_id"),
                details=e.get("details", {}),
                timestamp=e.get("timestamp") or e.get("occurred_at"),
            )
            for e in raw_events
        ]

    return router
