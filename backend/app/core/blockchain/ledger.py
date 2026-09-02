"""backend/app/core/blockchain/ledger.py

Permissioned Local Chained Ledger & Audit Anchoring Engine for NEXUS.
Phase 4: Permissioned Blockchain Audit Anchoring.

Provides an authentic append-only chained block ledger with deterministic block hashing,
cryptographic linkage, and verifiable anchor transactions.

CORE SECURITY MODEL:
Actual sensitive evidence remains strictly OFF-CHAIN.
Only minimal provenance metadata (anchor_id, audit batch range, event count, Merkle root hash)
is anchored into the permissioned blocks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import logging
from typing import Any, Sequence

from backend.app.core.crypto.merkle import compute_merkle_root

logger = logging.getLogger(__name__)


class LedgerParticipant(str, Enum):
    """Deterministic authorized permissioned nodes participating in the NEXUS ledger prototype."""
    POLICE_HQ = "NEXUS-POLICE-HQ"
    CYBER_CELL = "NEXUS-CYBER-CELL"
    DISTRICT_HQ = "NEXUS-DISTRICT-HQ"


@dataclass(frozen=True)
class AuditAnchorRecord:
    """Minimal cryptographic provenance metadata anchored into a block.

    Zero PII or raw evidence contents are included.
    """
    anchor_id: str
    batch_start: str
    batch_end: str
    event_count: int
    root_hash: str
    anchored_at: str
    creator_participant: str
    ledger_id: str = "NEXUS-PERMISSIONED-LEDGER"
    event_hashes: list[str] = field(default_factory=list)

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "anchor_id": self.anchor_id,
            "anchored_at": self.anchored_at,
            "batch_end": self.batch_end,
            "batch_start": self.batch_start,
            "creator_participant": self.creator_participant,
            "event_count": self.event_count,
            "ledger_id": self.ledger_id,
            "root_hash": self.root_hash,
        }


@dataclass
class LedgerBlock:
    """Verifiable immutable block in the permissioned ledger chain."""
    index: int
    timestamp: str
    previous_hash: str
    anchors: list[AuditAnchorRecord]
    participant: str
    block_hash: str = ""

    def compute_hash(self) -> str:
        """Compute deterministic SHA-256 hash across canonical representation of block contents."""
        block_dict = {
            "anchors": [a.to_canonical_dict() for a in self.anchors],
            "index": self.index,
            "participant": self.participant,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
        }
        canonical_bytes = json.dumps(block_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(canonical_bytes).hexdigest()

    def seal(self) -> None:
        """Seal block with computed cryptographic block hash."""
        self.block_hash = self.compute_hash()

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "participant": self.participant,
            "block_hash": self.block_hash,
            "anchors": [
                {
                    "anchor_id": a.anchor_id,
                    "batch_start": a.batch_start,
                    "batch_end": a.batch_end,
                    "event_count": a.event_count,
                    "root_hash": a.root_hash,
                    "anchored_at": a.anchored_at,
                    "creator_participant": a.creator_participant,
                    "ledger_id": a.ledger_id,
                }
                for a in self.anchors
            ],
        }


@dataclass(frozen=True)
class AnchorVerificationResult:
    """Structured result of verifying an anchor against ledger blocks and audit root."""
    verified: bool
    anchor_id: str
    root_hash: str
    block_index: int | None
    block_hash: str | None
    ledger_id: str
    reason: str
    chain_valid: bool
    anchored_event_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "verified": self.verified,
            "anchor_id": self.anchor_id,
            "root_hash": self.root_hash,
            "block_index": self.block_index,
            "block_hash": self.block_hash,
            "ledger_id": self.ledger_id,
            "reason": self.reason,
            "chain_valid": self.chain_valid,
            "anchored_event_count": self.anchored_event_count,
        }


class PermissionedLedger:
    """Local chained ledger maintaining sequential tamper-evident blocks."""

    def __init__(self, ledger_id: str = "NEXUS-PERMISSIONED-LEDGER") -> None:
        self.ledger_id = ledger_id
        self.chain: list[LedgerBlock] = []
        self._anchor_index: dict[str, tuple[int, AuditAnchorRecord]] = {}
        self._init_genesis_block()

    def _init_genesis_block(self) -> None:
        """Initialize genesis block if chain is empty."""
        genesis_anchor = AuditAnchorRecord(
            anchor_id="ANCHOR-GENESIS-0000",
            batch_start="GENESIS",
            batch_end="GENESIS",
            event_count=0,
            root_hash="0" * 64,
            anchored_at="2026-01-01T00:00:00+00:00",
            creator_participant=LedgerParticipant.POLICE_HQ.value,
            ledger_id=self.ledger_id,
        )
        genesis_block = LedgerBlock(
            index=0,
            timestamp="2026-01-01T00:00:00+00:00",
            previous_hash="0" * 64,
            anchors=[genesis_anchor],
            participant=LedgerParticipant.POLICE_HQ.value,
        )
        genesis_block.seal()
        self.chain.append(genesis_block)
        self._anchor_index[genesis_anchor.anchor_id] = (0, genesis_anchor)

    def append_anchor(
        self,
        anchor_id: str,
        batch_start: str,
        batch_end: str,
        event_hashes: list[str],
        participant: LedgerParticipant = LedgerParticipant.POLICE_HQ,
    ) -> AuditAnchorRecord:
        """Create an anchor from audit hashes, compute Merkle root, and append to next block."""
        root_hash = compute_merkle_root(event_hashes)
        now_iso = datetime.now(timezone.utc).isoformat()

        anchor = AuditAnchorRecord(
            anchor_id=anchor_id,
            batch_start=batch_start,
            batch_end=batch_end,
            event_count=len(event_hashes),
            root_hash=root_hash,
            anchored_at=now_iso,
            creator_participant=participant.value if hasattr(participant, "value") else str(participant),
            ledger_id=self.ledger_id,
            event_hashes=list(event_hashes),
        )

        last_block = self.chain[-1]
        new_block = LedgerBlock(
            index=len(self.chain),
            timestamp=now_iso,
            previous_hash=last_block.block_hash,
            anchors=[anchor],
            participant=anchor.creator_participant,
        )
        new_block.seal()
        self.chain.append(new_block)
        self._anchor_index[anchor.anchor_id] = (new_block.index, anchor)
        return anchor

    def verify_ledger_chain(self) -> tuple[bool, str]:
        """Verify sequential index consistency and block hash linkages."""
        if not self.chain:
            return False, "Chain is empty."

        for i in range(len(self.chain)):
            block = self.chain[i]
            if block.index != i:
                return False, f"Block index mismatch at block {i}: expected {i}, got {block.index}."

            computed = block.compute_hash()
            if block.block_hash != computed:
                return False, f"Block {i} hash altered: recorded={block.block_hash}, computed={computed}."

            if i > 0:
                prev_block = self.chain[i - 1]
                if block.previous_hash != prev_block.block_hash:
                    return False, f"Broken chain link at block {i}: previous_hash does not match block {i-1} hash."

        return True, "Ledger chain fully valid and cryptographically linked."

    def get_anchor(self, anchor_id: str) -> tuple[int, AuditAnchorRecord] | None:
        return self._anchor_index.get(anchor_id)

    def list_anchors(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for blk in self.chain:
            for a in blk.anchors:
                results.append({
                    "anchor_id": a.anchor_id,
                    "batch_start": a.batch_start,
                    "batch_end": a.batch_end,
                    "event_count": a.event_count,
                    "root_hash": a.root_hash,
                    "anchored_at": a.anchored_at,
                    "creator_participant": a.creator_participant,
                    "block_index": blk.index,
                    "block_hash": blk.block_hash,
                    "ledger_id": self.ledger_id,
                })
        return results

    def verify_anchor(self, anchor_id: str) -> AnchorVerificationResult:
        """Verify an anchor against the permissioned ledger chain and its Merkle root."""
        chain_valid, chain_reason = self.verify_ledger_chain()
        if not chain_valid:
            return AnchorVerificationResult(
                verified=False,
                anchor_id=anchor_id,
                root_hash="",
                block_index=None,
                block_hash=None,
                ledger_id=self.ledger_id,
                reason=f"Ledger integrity failure: {chain_reason}",
                chain_valid=False,
            )

        entry = self.get_anchor(anchor_id)
        if not entry:
            return AnchorVerificationResult(
                verified=False,
                anchor_id=anchor_id,
                root_hash="",
                block_index=None,
                block_hash=None,
                ledger_id=self.ledger_id,
                reason=f"Anchor '{anchor_id}' not found in permissioned ledger.",
                chain_valid=chain_valid,
            )

        block_index, anchor = entry
        block = self.chain[block_index]

        # Verify anchor is in block
        if not any(a.anchor_id == anchor_id for a in block.anchors):
            return AnchorVerificationResult(
                verified=False,
                anchor_id=anchor_id,
                root_hash=anchor.root_hash,
                block_index=block_index,
                block_hash=block.block_hash,
                ledger_id=self.ledger_id,
                reason="Anchor mismatch in block structure.",
                chain_valid=chain_valid,
            )

        # Verify Merkle root matches event_hashes if present
        if anchor.event_hashes:
            recomputed_root = compute_merkle_root(anchor.event_hashes)
            if recomputed_root != anchor.root_hash:
                return AnchorVerificationResult(
                    verified=False,
                    anchor_id=anchor_id,
                    root_hash=anchor.root_hash,
                    block_index=block_index,
                    block_hash=block.block_hash,
                    ledger_id=self.ledger_id,
                    reason="Merkle root mismatch between anchored root and event hashes.",
                    chain_valid=chain_valid,
                    anchored_event_count=anchor.event_count,
                )

        return AnchorVerificationResult(
            verified=True,
            anchor_id=anchor_id,
            root_hash=anchor.root_hash,
            block_index=block_index,
            block_hash=block.block_hash,
            ledger_id=self.ledger_id,
            reason="Anchor and permissioned ledger chain verified.",
            chain_valid=True,
            anchored_event_count=anchor.event_count,
        )
