"""backend/app/core/crypto/audit_integrity.py

Cryptographic Tamper-Evidence & Canonical Audit Event Integrity for NEXUS.
Phase 3: Cryptographic Audit Integrity (SHA-256 & Canonical JSON Serialization).

Provides deterministic canonical serialization, SHA-256 hash generation,
and mathematical tamper-evidence verification for NEXUS audit events.

IMPORTANT SECURITY RULE:
The integrity hash is NOT proof that the underlying event or evidence is truthful.
It only establishes that the canonical audit record currently matches the
fingerprint that was stored when it was created.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any


def _normalize_timestamp(ts: Any) -> str:
    """Normalize timestamp to ISO 8601 UTC string format: YYYY-MM-DDTHH:MM:SS.ffffff+00:00 or Z."""
    if isinstance(ts, datetime):
        utc_dt = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        return utc_dt.astimezone(timezone.utc).isoformat()
    if isinstance(ts, str) and ts:
        try:
            # Parse and canonicalize to ISO UTC
            cleaned = ts.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            utc_dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            return utc_dt.astimezone(timezone.utc).isoformat()
        except (ValueError, TypeError):
            return ts
    return ""


def canonicalize_audit_payload(event: dict[str, Any]) -> str:
    """Produce a deterministic, canonical UTF-8 JSON string of an audit event.

    Canonicalization Rules:
      1. Excludes 'integrity_hash', 'signature', or None values from the hashed payload.
      2. Stabilizes top-level keys in strict alphabetical order.
      3. Normalizes timestamp / occurred_at to canonical UTC ISO-8601 string.
      4. Recursively sorts dictionary keys (separators: (',', ':') with no whitespace).
      5. Normalizes null/None fields consistently.
    """
    # Extract authoritative canonical fields
    event_id = str(event.get("id") or event.get("event_id") or "")
    event_type = str(event.get("event_type") or event.get("action") or "")
    actor_id = str(event.get("actor_id") or event.get("user_id") or "")
    timestamp = _normalize_timestamp(event.get("timestamp") or event.get("occurred_at") or "")

    entity_id = event.get("entity_id")
    if entity_id is None and event.get("case_id"):
        entity_id = event.get("case_id")
    entity_id_str = str(entity_id) if entity_id is not None else None

    entity_type = event.get("entity_type")
    entity_type_str = str(entity_type) if entity_type is not None else None

    case_id = event.get("case_id")
    case_id_str = str(case_id) if case_id is not None else None

    request_id = event.get("request_id")
    request_id_str = str(request_id) if request_id is not None else None

    previous_hash = event.get("previous_hash")
    previous_hash_str = str(previous_hash) if previous_hash is not None else None

    # Clean and sort details dictionary
    raw_details = event.get("details")
    clean_details: dict[str, Any] = {}
    if isinstance(raw_details, dict):
        # Exclude integrity_hash if accidentally embedded in details
        for k, v in raw_details.items():
            if k not in ("integrity_hash", "previous_hash"):
                clean_details[k] = v

    canonical_dict: dict[str, Any] = {
        "actor_id": actor_id,
        "case_id": case_id_str,
        "details": clean_details,
        "entity_id": entity_id_str,
        "entity_type": entity_type_str,
        "event_id": event_id,
        "event_type": event_type,
        "previous_hash": previous_hash_str,
        "request_id": request_id_str,
        "timestamp": timestamp,
    }

    # Deterministic JSON representation: sorted keys, compact separators, no indentation
    return json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_audit_event_hash(event: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hexadecimal digest of canonical audit event representation."""
    canonical_json = canonicalize_audit_payload(event)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditIntegrityVerificationResult:
    """Structured result of cryptographic audit event verification."""
    event_id: str
    verified: bool
    stored_hash: str | None
    computed_hash: str
    reason: str
    previous_hash: str | None = None
    canonical_payload: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "verified": self.verified,
            "stored_hash": self.stored_hash,
            "computed_hash": self.computed_hash,
            "reason": self.reason,
            "previous_hash": self.previous_hash,
        }


def verify_audit_event_integrity(event: dict[str, Any]) -> AuditIntegrityVerificationResult:
    """Verify whether the audit event's current state cryptographically matches its stored hash.

    Fail-closed policy: If stored hash is absent or hashes do not match, returns verified=False.
    """
    event_id = str(event.get("id") or event.get("event_id") or "")
    stored_hash = event.get("integrity_hash")
    previous_hash = event.get("previous_hash")

    canonical_payload = canonicalize_audit_payload(event)
    computed_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    if not stored_hash:
        return AuditIntegrityVerificationResult(
            event_id=event_id,
            verified=False,
            stored_hash=None,
            computed_hash=computed_hash,
            reason="Audit event does not contain a stored integrity hash.",
            previous_hash=previous_hash,
            canonical_payload=canonical_payload,
        )

    if stored_hash.lower() == computed_hash.lower():
        return AuditIntegrityVerificationResult(
            event_id=event_id,
            verified=True,
            stored_hash=stored_hash,
            computed_hash=computed_hash,
            reason="Hash matches canonical audit event.",
            previous_hash=previous_hash,
            canonical_payload=canonical_payload,
        )

    return AuditIntegrityVerificationResult(
        event_id=event_id,
        verified=False,
        stored_hash=stored_hash,
        computed_hash=computed_hash,
        reason="Audit event integrity mismatch: content has been altered since creation.",
        previous_hash=previous_hash,
        canonical_payload=canonical_payload,
    )
