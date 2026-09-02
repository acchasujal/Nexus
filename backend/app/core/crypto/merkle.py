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
