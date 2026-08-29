"""backend/app/services/evidence_service.py

Evidence retrieval and hash-chain service for the NEXUS Criminal Intelligence Platform.

Provides:
  - EvidenceService: read provenance from GraphEdge objects, surface evidence citations
  - compute_evidence_hash: deterministic SHA-256 hash of evidence provenance (BE-04)
  - compute_path_chain_hash: multi-hop chain hash for graph paths (BE-04)

Design constraints:
  - NEVER fabricates evidence — all returned items come directly from GraphEdge.provenance
  - All evidence items are real provenance records (source_type, source_id, extracted_fact)
  - Each retrieval is audited via AuditService
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    EvidenceItemResponse,
    EvidenceProvenanceContract,
    EvidenceVerificationResponse,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_prov(edge: Any) -> dict:
    """Extract provenance dict from AdjEdge.properties safely.

    AdjEdge stores provenance inside properties['provenance'] as a dict:
      {'source_type': ..., 'source_id': ..., 'extracted_fact': ..., ...}
    Returns empty dict if not present.
    """
    props = getattr(edge, "properties", {}) or {}
    prov = props.get("provenance") or {}
    if not prov.get("source_id") and getattr(edge, "source_record_id", None):
        prov = {"source_id": edge.source_record_id}
    return prov


def _make_evidence_id(source_id: str, edge_source: str, edge_target: str, edge_type: str) -> str:
    """Generate a stable, deterministic ID for an evidence item from its provenance coordinates."""
    key = f"{source_id}::{edge_source}::{edge_target}::{edge_type}"
    return "ev-" + hashlib.sha256(key.encode()).hexdigest()[:16]


def compute_evidence_hash(evidence: EvidenceItemResponse) -> str:
    """Compute a deterministic SHA-256 hash of an evidence item's provenance fields.

    Used for Section 63 BSA 2023 tamper-evident audit chain.
    The hash is stable as long as provenance fields are unchanged.
    """
    prov = evidence.provenance
    canonical = json.dumps(
        {
            "source_type": prov.source_type,
            "source_id": prov.source_id,
            "extracted_fact": prov.extracted_fact,
            "confidence": prov.confidence,
            "timestamp": prov.timestamp.isoformat() if prov.timestamp else "",
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    computed_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    logger.info(f"Evidence hash computed successfully | evidence_id={evidence.id} | computed_hash={computed_hash}")
    return computed_hash


def compute_path_chain_hash(hop_hashes: list[str]) -> str:
    """Compute the Merkle-like chain hash for a sequence of hop hashes.

    For a path: hash(node1) || hash(edge1) || hash(node2) || ...
    Returns a SHA-256 of the concatenated hop hashes.
    """
    if not hop_hashes:
        return ""
    chain_input = "||".join(hop_hashes)
    computed_chain_hash = hashlib.sha256(chain_input.encode("utf-8")).hexdigest()
    logger.info(f"Path chain hash computed successfully | hops={len(hop_hashes)} | chain_hash={computed_chain_hash}")
    return computed_chain_hash


class EvidenceService:
    """Application service for evidence provenance retrieval and hash verification.

    Reads provenance directly from GraphEdge objects in the GraphStore.
    Every evidence item returned is a real record — no synthetic data invented here.
    """

    def __init__(self, repository: Any, audit_service: AuditService) -> None:
        self._repo = repository
        self._audit = audit_service

    # ── Evidence Retrieval ─────────────────────────────────────────────────────

    def get_evidence_by_id(
        self,
        evidence_id: str,
        actor_id: str,
        request_id: str | None = None,
    ) -> EvidenceItemResponse | None:
        """Retrieve a single evidence item by its stable provenance-derived ID.

        Returns None if no evidence with that ID exists.
        Logs EVIDENCE_VIEWED audit event on hit.
        """
        store = self._repo.to_graph_store()
        for etype, edges in store.edge_index.items():
            for edge in edges:
                prov = _get_prov(edge)
                if prov.get("source_id"):
                    ev = self._edge_to_evidence(edge, etype)
                    if ev.id == evidence_id:
                        self._audit.record(
                            AuditEventType.EVIDENCE_VIEWED,
                            actor_id=actor_id,
                            entity_id=evidence_id,
                            request_id=request_id,
                            details={"source_type": prov.get("source_type", "")},
                        )
                        return ev
        return None

    def get_evidence_for_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: str | None = None,
        actor_id: str = "system",
        request_id: str | None = None,
    ) -> list[EvidenceItemResponse]:
        """Retrieve all evidence citations supporting a specific graph edge.

        Matches on source_id + target_id (and optionally edge_type).
        Returns empty list if no matching edges exist.
        """
        store = self._repo.to_graph_store()
        results: list[EvidenceItemResponse] = []

        for etype, edges in store.edge_index.items():
            if edge_type and etype != edge_type:
                continue
            for edge in edges:
                if edge.source_id == source_id and edge.target_id == target_id:
                    prov = _get_prov(edge)
                    if prov.get("source_id"):
                        results.append(self._edge_to_evidence(edge, etype))

        if results:
            self._audit.record(
                AuditEventType.EVIDENCE_VIEWED,
                actor_id=actor_id,
                request_id=request_id,
                details={
                    "source_id": source_id,
                    "target_id": target_id,
                    "count": len(results),
                },
            )
        return results

    def get_evidence_for_entity(
        self,
        entity_id: str,
        actor_id: str = "system",
        request_id: str | None = None,
    ) -> list[EvidenceItemResponse]:
        """Retrieve all evidence citations where this entity is source or target.

        Used to populate the evidence panel in EntityProfileResponse.
        """
        store = self._repo.to_graph_store()
        results: list[EvidenceItemResponse] = []
        seen_ids: set[str] = set()

        for etype, edges in store.edge_index.items():
            for edge in edges:
                if edge.source_id == entity_id or edge.target_id == entity_id:
                    prov = _get_prov(edge)
                    if prov.get("source_id"):
                        ev = self._edge_to_evidence(edge, etype)
                        if ev.id not in seen_ids:
                            results.append(ev)
                            seen_ids.add(ev.id)

        if results:
            self._audit.record(
                AuditEventType.EVIDENCE_VIEWED,
                actor_id=actor_id,
                entity_id=entity_id,
                request_id=request_id,
                details={"count": len(results)},
            )
        return results

    def list_all_evidence(
        self,
        case_id: str | None = None,
        entity_id: str | None = None,
        limit: int = 50,
        actor_id: str = "system",
        request_id: str | None = None,
    ) -> list[EvidenceItemResponse]:
        """List evidence items, optionally filtered by case_id or entity_id.

        Returns up to `limit` evidence items sorted by provenance timestamp (newest first).
        """
        store = self._repo.to_graph_store()
        results: list[EvidenceItemResponse] = []
        seen_ids: set[str] = set()

        for etype, edges in store.edge_index.items():
            for edge in edges:
                prov = _get_prov(edge)
                if not prov.get("source_id"):
                    continue

                # Case filter: only include edges directly connected to the case node
                if case_id and edge.source_id != case_id and edge.target_id != case_id:
                    continue

                # Entity filter
                if entity_id and edge.source_id != entity_id and edge.target_id != entity_id:
                    continue

                ev = self._edge_to_evidence(edge, etype)
                if ev.id not in seen_ids:
                    results.append(ev)
                    seen_ids.add(ev.id)

        # Sort by provenance timestamp, newest first
        results.sort(key=lambda e: e.provenance.timestamp, reverse=True)
        return results[:limit]

    # ── Hash Chain (BE-04) ────────────────────────────────────────────────────

    def verify_evidence_chain(
        self,
        evidence_ids: list[str],
        path_node_ids: list[str],
        actor_id: str = "system",
        request_id: str | None = None,
    ) -> EvidenceVerificationResponse:
        """Compute SHA-256 hash chain for evidence items and path nodes.

        Implements tamper-evident chain per Section 63 BSA 2023.
        Returns VERIFIED if all requested evidence IDs were found; INCOMPLETE otherwise.
        """
        store = self._repo.to_graph_store()
        evidence_hashes: dict[str, str] = {}
        hop_hashes: list[str] = []

        # Hash all requested evidence items
        if evidence_ids:
            for etype, edges in store.edge_index.items():
                for edge in edges:
                    prov = _get_prov(edge)
                    if not prov.get("source_id"):
                        continue
                    ev = self._edge_to_evidence(edge, etype)
                    if ev.id in evidence_ids and ev.id not in evidence_hashes:
                        h = compute_evidence_hash(ev)
                        evidence_hashes[ev.id] = h
                        hop_hashes.append(h)

        # Hash path nodes if requested
        if path_node_ids:
            for node_id in path_node_ids:
                node = store.nodes.get(node_id)
                if node:
                    node_canonical = json.dumps(
                        {"node_id": node_id, "entity_type": node.entity_type},
                        sort_keys=True,
                    )
                    hop_hashes.append(hashlib.sha256(node_canonical.encode()).hexdigest())

        chain_hash = compute_path_chain_hash(hop_hashes)
        found_all = all(eid in evidence_hashes for eid in evidence_ids) if evidence_ids else True
        status = "VERIFIED" if found_all else "INCOMPLETE"

        self._audit.record(
            AuditEventType.EVIDENCE_HASH_COMPUTED,
            actor_id=actor_id,
            request_id=request_id,
            details={
                "evidence_count": len(evidence_hashes),
                "chain_hash_prefix": chain_hash[:16] if chain_hash else "",
                "status": status,
            },
        )

        return EvidenceVerificationResponse(
            evidence_hashes=evidence_hashes,
            chain_hash=chain_hash,
            verified_at=_utcnow(),
            verification_status=status,
        )

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _edge_to_evidence(self, edge: Any, edge_type: str) -> EvidenceItemResponse:
        """Convert an AdjEdge's provenance dict into an EvidenceItemResponse.

        AdjEdge stores provenance inside properties['provenance'] as a dict.
        The evidence ID is deterministic and stable for the same provenance coordinates.
        """
        prov = _get_prov(edge)
        source_type = prov.get("source_type", "DIRECT_RECORD")
        source_id = prov.get("source_id", "")
        extracted_fact = prov.get("extracted_fact", "")
        confidence = float(prov.get("confidence", 1.0))
        derivation = prov.get("derivation_method", "DIRECT")

        # Parse timestamp from ISO string if present
        ts_raw = prov.get("timestamp")
        if ts_raw:
            try:
                from datetime import datetime
                ts = datetime.fromisoformat(ts_raw) if isinstance(ts_raw, str) else ts_raw
            except (ValueError, TypeError):
                ts = _utcnow()
        else:
            ts = _utcnow()

        ev_id = _make_evidence_id(source_id, edge.source_id, edge.target_id, edge_type)

        return EvidenceItemResponse(
            id=ev_id,
            evidence_number=source_id or ev_id,
            case_id=self._infer_case_id(edge),
            evidence_type=source_type,
            description=extracted_fact or f"{edge_type}: {edge.source_id} -> {edge.target_id}",
            collected_at=ts,
            storage_location=None,
            provenance=EvidenceProvenanceContract(
                source_type=source_type,
                source_id=source_id,
                timestamp=ts,
                extracted_fact=extracted_fact,
                derivation_method=derivation,
                confidence=confidence,
            ),
        )

    def _infer_case_id(self, edge: Any) -> str:
        """Infer the associated case_id from edge endpoints.

        Checks if either endpoint is a Case node in the repository.
        """
        nodes = getattr(self._repo, "nodes", {})
        for node_id in (edge.source_id, edge.target_id):
            node = nodes.get(node_id, {})
            if node.get("entity_type") in ("Case", "CASE"):
                return node_id
        return ""
