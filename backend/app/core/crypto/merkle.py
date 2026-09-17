"""backend/app/core/crypto/merkle.py

Deterministic Merkle Tree & Batch Root Hash Construction for NEXUS Audit Anchoring.
Phase 4: Permissioned Blockchain Audit Anchoring.

Provides RFC 6962-compliant prefix-hardened binary Merkle tree root hash calculation
over list of canonical SHA-256 event fingerprints.
"""

from __future__ import annotations

import hashlib
from typing import Sequence


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_merkle_root(leaf_hashes: Sequence[str]) -> str:
    """Compute deterministic binary Merkle Tree root hash over an ordered sequence of leaf hashes.

    Rules:
      1. Empty list returns 64 zeros ("0" * 64).
      2. Single leaf hash is pre-hashed with leaf prefix (RFC 6962 leaf domain separator: b'\\x00').
      3. For pairs, intermediate nodes use interior prefix (RFC 6962 interior domain separator: b'\\x01').
      4. If the number of leaves in an iteration is odd, the last node is promoted / duplicated deterministically.
      5. Output is standard lowercase 64-char hexadecimal string.
    """
    if not leaf_hashes:
        return "0" * 64

    # Domain separator prefix for leaves to prevent second-preimage attacks
    current_level = [
        hashlib.sha256(b"\x00" + bytes.fromhex(h)).hexdigest() if len(h) == 64 else hashlib.sha256(b"\x00" + h.encode("utf-8")).hexdigest()
        for h in leaf_hashes
    ]

    if len(current_level) == 1:
        return current_level[0]

    while len(current_level) > 1:
        next_level: list[str] = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            # If odd number of nodes, duplicate the last node
            right = current_level[i + 1] if (i + 1 < len(current_level)) else current_level[i]
            # Interior node domain separator \x01 + left_bytes + right_bytes
            combined = b"\x01" + bytes.fromhex(left) + bytes.fromhex(right)
            next_level.append(hashlib.sha256(combined).hexdigest())
        current_level = next_level

    return current_level[0]


def generate_merkle_proof(leaf_hashes: Sequence[str], target_index: int) -> list[dict[str, str]]:
    """Generate an audit inclusion proof (list of sibling hashes and positions) for a leaf index.

    Each step in the proof contains:
      - 'sibling_hash': hex string of sibling node
      - 'direction': 'left' or 'right' indicating sibling position relative to target
    """
    if not leaf_hashes or target_index < 0 or target_index >= len(leaf_hashes):
        return []

    # Calculate initial leaf hashes with leaf domain separator
    current_level = [
        hashlib.sha256(b"\x00" + bytes.fromhex(h)).hexdigest() if len(h) == 64 else hashlib.sha256(b"\x00" + h.encode("utf-8")).hexdigest()
        for h in leaf_hashes
    ]

    proof: list[dict[str, str]] = []
    idx = target_index

    while len(current_level) > 1:
        next_level: list[str] = []
        # If odd number of nodes, duplicate the last node
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])

        # Find sibling for idx
        if idx % 2 == 0:
            sibling_idx = idx + 1
            direction = "right"
        else:
            sibling_idx = idx - 1
            direction = "left"

        proof.append({
            "sibling_hash": current_level[sibling_idx],
            "direction": direction,
        })

        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i + 1]
            combined = b"\x01" + bytes.fromhex(left) + bytes.fromhex(right)
            next_level.append(hashlib.sha256(combined).hexdigest())

        idx = idx // 2
        current_level = next_level

    return proof


def verify_merkle_proof(leaf_hash: str, proof: Sequence[dict[str, str]], expected_root: str) -> bool:
    """Verify an RFC 6962 prefix-hardened Merkle audit inclusion proof against expected root."""
    if not leaf_hash or not expected_root:
        return False

    current = (
        hashlib.sha256(b"\x00" + bytes.fromhex(leaf_hash)).hexdigest()
        if len(leaf_hash) == 64
        else hashlib.sha256(b"\x00" + leaf_hash.encode("utf-8")).hexdigest()
    )

    for step in proof:
        sibling = step["sibling_hash"]
        direction = step["direction"]

        if direction == "right":
            combined = b"\x01" + bytes.fromhex(current) + bytes.fromhex(sibling)
        else:
            combined = b"\x01" + bytes.fromhex(sibling) + bytes.fromhex(current)

        current = hashlib.sha256(combined).hexdigest()

    return current.lower() == expected_root.lower()

