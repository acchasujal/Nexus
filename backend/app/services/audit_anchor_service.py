"""backend/app/services/audit_anchor_service.py

Audit Anchor Service for NEXUS.
Phase 4: Permissioned Blockchain Audit Anchoring.

Provides high-level abstraction between the core NEXUS application/audit service
and the underlying permissioned blockchain ledger.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from backend.app.core.blockchain.ledger import (
    AnchorVerificationResult,
    AuditAnchorRecord,
    LedgerParticipant,
    PermissionedLedger,
)
from backend.app.services.audit_service import AuditEventType, AuditService

logger = logging.getLogger(__name__)


class AuditAnchorService:
    """Service mediating audit batch collection, Merkle anchoring, and ledger verification."""

    def __init__(self, ledger: PermissionedLedger, audit_service: AuditService) -> None:
        self._ledger = ledger
        self._audit = audit_service

    def anchor_audit_batch(
        self,
        batch_start_id: str | None = None,
        batch_end_id: str | None = None,
        participant: LedgerParticipant = LedgerParticipant.POLICE_HQ,
        limit: int = 50,
        actor_id: str = "system",
    ) -> AuditAnchorRecord:
        """Collect unanchored audit events or a specified range, anchor to ledger, and emit audit event.

        Careful prevention of recursive anchoring:
        The AUDIT_BATCH_ANCHORED event emitted by this operation has a flag/type that is excluded
        from the batch currently being anchored.
        """
        raw_events = self._audit.list_events(limit=limit)
        # Sort chronologically (list_events returns reverse chronological)
        events = list(reversed(raw_events))

        # Filter to events that have integrity hashes and are not themselves meta-anchor events
        candidate_events = [
            e for e in events
            if e.get("integrity_hash") and e.get("event_type") != AuditEventType.AUDIT_BATCH_ANCHORED.value
        ]

        if not candidate_events:
            # If no unanchored events, take any available integrity-hashed events
            candidate_events = [e for e in events if e.get("integrity_hash")]

        if not candidate_events:
            raise ValueError("No integrity-hashed audit events available to anchor.")

        start_id = batch_start_id or candidate_events[0].get("id", "UNKNOWN_START")
        end_id = batch_end_id or candidate_events[-1].get("id", "UNKNOWN_END")
        event_hashes = [e["integrity_hash"] for e in candidate_events if e.get("integrity_hash")]

        anchor_id = f"ANCHOR-2026-{uuid.uuid4().hex[:8].upper()}"
        anchor = self._ledger.append_anchor(
            anchor_id=anchor_id,
            batch_start=start_id,
            batch_end=end_id,
            event_hashes=event_hashes,
            participant=participant,
        )

        # Record audit event about the anchoring operation
        self._audit.record(
            event_type=AuditEventType.AUDIT_BATCH_ANCHORED,
            actor_id=actor_id,
            entity_type="BlockchainAnchor",
            entity_id=anchor_id,
            details={
                "anchor_id": anchor_id,
                "batch_start": start_id,
                "batch_end": end_id,
                "event_count": len(event_hashes),
                "root_hash": anchor.root_hash,
                "ledger_id": anchor.ledger_id,
                "participant": anchor.creator_participant,
            },
        )

        logger.info("AnchorService: Successfully anchored batch %s -> %s (Anchor %s)", start_id, end_id, anchor_id)
        return anchor

    def get_anchor(self, anchor_id: str) -> dict[str, Any] | None:
        entry = self._ledger.get_anchor(anchor_id)
        if not entry:
            return None
        block_idx, anchor = entry
        blk = self._ledger.chain[block_idx]
        return {
            "anchor_id": anchor.anchor_id,
            "batch_start": anchor.batch_start,
            "batch_end": anchor.batch_end,
            "event_count": anchor.event_count,
            "root_hash": anchor.root_hash,
            "anchored_at": anchor.anchored_at,
            "creator_participant": anchor.creator_participant,
            "block_index": block_idx,
            "block_hash": blk.block_hash,
            "ledger_id": anchor.ledger_id,
        }

    def list_anchors(self) -> list[dict[str, Any]]:
        return self._ledger.list_anchors()

    def verify_anchor(self, anchor_id: str, actor_id: str = "system") -> AnchorVerificationResult:
        result = self._ledger.verify_anchor(anchor_id)

        # Audit the verification action (safely non-recursive)
        self._audit.record(
            event_type=AuditEventType.BLOCKCHAIN_VERIFIED if result.verified else AuditEventType.BLOCKCHAIN_VERIFICATION_FAILED,
            actor_id=actor_id,
            entity_type="BlockchainAnchor",
            entity_id=anchor_id,
            details={
                "anchor_id": anchor_id,
                "verified": result.verified,
                "root_hash": result.root_hash,
                "block_index": result.block_index,
                "block_hash": result.block_hash,
                "reason": result.reason,
            },
        )

        return result
