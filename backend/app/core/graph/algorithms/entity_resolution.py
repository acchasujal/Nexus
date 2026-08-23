"""backend/app/core/graph/algorithms/entity_resolution.py

Explainable, deterministic Entity Resolution (ER) engine for NEXUS.
Supports:
  - Text normalization & Indian phonetic normalization
  - Multi-attribute matching (Name, Aliases, Phone, Vehicle, Address, ID)
  - Explicit match status: MATCHED, PROBABLE_MATCH, REVIEW_REQUIRED, NOT_MATCHED
  - Structured evidence provenance explaining every match decision
  - Ground truth evaluation scoring (Precision, Recall, F1)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.app.core.graph.algorithms.utils import GraphStore
from backend.app.core.graph.enums import ResolutionStatus


@dataclass(frozen=True)
class ResolutionMatch:
    """Represents a resolved candidate entity with evidence."""
    matched_node_id: str
    confidence: float
    status: ResolutionStatus
    matched_fields: list[str]
    reason: str
    evidence_breakdown: dict[str, float] = field(default_factory=dict)
    properties: dict[str, Any] = field(default_factory=dict)


def normalize_text(text: str | None) -> str:
    """Normalize text: lowercase, strip punctuation, collapse whitespace."""
    if not text:
        return ""
    text = str(text).lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def phonetic_normalize(text: str | None) -> str:
    """Apply phonetic-friendly rules for common Indian spelling variations."""
    text = normalize_text(text)
    if not text:
        return ""

    # Normalize vowel representations
    text = text.replace("ee", "i").replace("oo", "u")
    text = text.replace("ou", "u").replace("ow", "o").replace("au", "o")
    text = text.replace("med", "mad").replace("mud", "mad")

    # Common sound-alike consonant mappings in Indian names
    text = text.replace("sh", "s")
    text = text.replace("w", "b")
    text = text.replace("v", "b")
    text = text.replace("z", "j")
    text = text.replace("y", "i")
    text = text.replace("gh", "g")
    text = text.replace("dh", "d")
    text = text.replace("th", "t")
    text = text.replace("bh", "b")
    text = text.replace("ph", "f")
    text = text.replace("ks", "x")
    text = text.replace("ch", "c")
    text = text.replace("ng", "n")

    # Remove 'h' except at the beginning of words
    words = []
    for word in text.split(" "):
        if len(word) > 1:
            word = word[0] + word[1:].replace("h", "")
        words.append(word)
    text = " ".join(words)

    # Deduplicate consecutive identical characters
    text = re.sub(r"(.)\1+", r"\1", text)
    return text


def get_bigrams(text: str) -> set[str]:
    """Return character bigrams for fuzzy Jaccard calculation."""
    if len(text) < 2:
        return {text} if text else set()
    return {text[i:i+2] for i in range(len(text) - 1)}


def jaccard_similarity(str1: str, str2: str) -> float:
    """Compute character-bigram Jaccard similarity."""
    bg1 = get_bigrams(str1)
    bg2 = get_bigrams(str2)
    if not bg1 and not bg2:
        return 1.0
    if not bg1 or not bg2:
        return 0.0
    intersection = len(bg1.intersection(bg2))
    union = len(bg1.union(bg2))
    return round(intersection / union, 4) if union > 0 else 0.0


def clean_phone(phone: str | None) -> str:
    """Normalize phone numbers to last 10 digits."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    return digits[-10:] if len(digits) >= 10 else digits


def clean_vehicle(veh: str | None) -> str:
    """Normalize vehicle registration numbers (remove hyphens, spaces, uppercase)."""
    if not veh:
        return ""
    return re.sub(r"[\s\-_]", "", str(veh)).upper()


def classify_match_status(confidence: float) -> ResolutionStatus:
    """Map confidence to resolution status tier."""
    if confidence >= 0.80:
        return ResolutionStatus.MATCHED
    elif confidence >= 0.60:
        return ResolutionStatus.PROBABLE_MATCH
    elif confidence >= 0.40:
        return ResolutionStatus.REVIEW_REQUIRED
    else:
        return ResolutionStatus.NOT_MATCHED


def resolve_person(
    store: GraphStore,
    query: dict[str, Any],
    confidence_threshold: float = 0.40,
    candidate_limit: int = 20,
) -> list[ResolutionMatch]:
    """Resolve a person query against entities in the GraphStore with full provenance."""
    matches: list[ResolutionMatch] = []

    query_name = query.get("full_name") or query.get("name") or ""
    query_phone = clean_phone(query.get("phone_number") or query.get("phone"))
    query_vehicle = clean_vehicle(query.get("vehicle_number") or query.get("vehicle") or query.get("registration_number"))
    query_address = normalize_text(query.get("address_text") or query.get("address") or "")
    query_id = query.get("national_id") or query.get("id_number")

    query_aliases = query.get("aliases", [])
    if isinstance(query_aliases, str):
        query_aliases = [query_aliases]
    norm_query_aliases = [normalize_text(a) for a in query_aliases if a]

    norm_query_name = normalize_text(query_name)
    phon_query_name = phonetic_normalize(query_name)

    # Scan Person nodes in store
    person_nodes = [n for n in store.nodes.values() if n.entity_type in ("Person", "PERSON")]

    for node in person_nodes:
        props = node.properties or {}
        node_name = props.get("full_name") or props.get("name") or ""
        norm_node_name = normalize_text(node_name)
        phon_node_name = phonetic_normalize(node_name)

        matched_fields: list[str] = []
        evidence_breakdown: dict[str, float] = {}
        reason_parts: list[str] = []

        # 1. National ID Check (Definitive 1.0)
        node_id_val = props.get("national_id") or props.get("id_number")
        if query_id and node_id_val and str(query_id).strip() == str(node_id_val).strip():
            matched_fields.append("national_id")
            evidence_breakdown["national_id"] = 1.0
            reason_parts.append(f"Exact National ID match ({query_id})")

        # 2. Direct Phone Match (1.0)
        node_phones = props.get("phone_numbers") or [props.get("phone_number")] or []
        if isinstance(node_phones, str):
            node_phones = [node_phones]
        node_phones_clean = {clean_phone(p) for p in node_phones if p}

        if query_phone and query_phone in node_phones_clean:
            matched_fields.append("phone_number")
            evidence_breakdown["phone_number"] = 1.0
            reason_parts.append(f"Matching phone ({query_phone})")

        # 3. Vehicle Match (0.85)
        node_vehicles = props.get("vehicles") or [props.get("vehicle_number")] or [props.get("registration_number")] or []
        if isinstance(node_vehicles, str):
            node_vehicles = [node_vehicles]
        node_vehicles_clean = {clean_vehicle(v) for v in node_vehicles if v}

        if query_vehicle and query_vehicle in node_vehicles_clean:
            matched_fields.append("vehicle_number")
            evidence_breakdown["vehicle_number"] = 0.85
            reason_parts.append(f"Matching vehicle reg ({query_vehicle})")

        # 4. Name Similarity (Exact, Phonetic, Prefix, or Fuzzy Bigram)
        name_score = 0.0
        if norm_query_name and norm_node_name:
            if norm_query_name == norm_node_name:
                name_score = 1.0
                matched_fields.extend(["full_name", "full_name_exact"])
                reason_parts.append(f"Exact name match '{node_name}'")
            elif phon_query_name == phon_node_name:
                name_score = 1.0
                matched_fields.extend(["full_name", "full_name_phonetic"])
                reason_parts.append(f"Phonetic name match '{node_name}'")
            elif norm_query_name in norm_node_name.split() or norm_node_name in norm_query_name.split():
                name_score = 0.85
                matched_fields.extend(["full_name", "full_name_prefix"])
                reason_parts.append(f"Word token match '{node_name}'")
            else:
                jaccard = jaccard_similarity(norm_query_name, norm_node_name)
                phon_jaccard = jaccard_similarity(phon_query_name, phon_node_name)
                best_sim = max(jaccard, phon_jaccard)
                if best_sim >= 0.40:
                    name_score = round(best_sim, 3)
                    matched_fields.append("full_name_fuzzy")
                    reason_parts.append(f"Fuzzy name match '{node_name}' (sim={best_sim:.2f})")

        # 5. Alias Check
        node_aliases = props.get("aliases") or []
        if isinstance(node_aliases, str):
            node_aliases = [node_aliases]
        norm_node_aliases = [normalize_text(a) for a in node_aliases if a]
        phon_node_aliases = [phonetic_normalize(a) for a in node_aliases if a]

        alias_match = False
        if norm_query_name and (norm_query_name in norm_node_aliases or phon_query_name in phon_node_aliases):
            alias_match = True
        elif any(a in norm_node_aliases or phonetic_normalize(a) in phon_node_aliases for a in norm_query_aliases):
            alias_match = True

        if alias_match:
            matched_fields.extend(["aliases", "alias_match"])
            evidence_breakdown["alias"] = 1.0
            reason_parts.append("Matched known alias/nickname")

        if name_score > 0 and "alias" not in evidence_breakdown:
            evidence_breakdown["name_score"] = name_score

        # 6. Address / Location Corroboration
        node_addresses = props.get("addresses") or [props.get("address_text")] or [props.get("address")] or []
        if isinstance(node_addresses, str):
            node_addresses = [node_addresses]
        norm_node_addresses = [normalize_text(a) for a in node_addresses if a]

        if query_address and norm_node_addresses:
            for addr in norm_node_addresses:
                addr_sim = jaccard_similarity(query_address, addr)
                if addr_sim >= 0.35:
                    matched_fields.append("address_text")
                    evidence_breakdown["address_text"] = round(0.30 * addr_sim, 3)
                    reason_parts.append(f"Corroborating address similarity ({addr_sim:.2f})")
                    break

        total_confidence = sum(evidence_breakdown.values())
        total_confidence = min(1.0, round(total_confidence, 3))

        if total_confidence >= confidence_threshold:
            status = classify_match_status(total_confidence)
            reason = "; ".join(reason_parts) if reason_parts else "Multiple corroborating attributes"
            matches.append(
                ResolutionMatch(
                    matched_node_id=str(getattr(node, "node_id", getattr(node, "id", ""))),
                    confidence=total_confidence,
                    status=status,
                    matched_fields=matched_fields,
                    reason=reason,
                    evidence_breakdown=evidence_breakdown,
                    properties=props,
                )
            )

    matches.sort(key=lambda m: m.confidence, reverse=True)
    return matches[:candidate_limit]


resolve_entity = resolve_person
phonetic_fingerprint = phonetic_normalize


class EntityResolutionEngine:
    """Object-oriented interface for Entity Resolution over a GraphStore."""

    def __init__(self, store: GraphStore):
        self.store = store

    def resolve(
        self,
        query: dict[str, Any],
        confidence_threshold: float = 0.40,
        candidate_limit: int = 20,
    ) -> list[ResolutionMatch]:
        return resolve_entity(
            self.store,
            query,
            confidence_threshold=confidence_threshold,
            candidate_limit=candidate_limit,
        )


def evaluate_entity_resolution(
    ground_truth_pairs: list[tuple[str, str]],
    predicted_pairs: list[tuple[str, str]],
) -> dict[str, float]:
    """Calculate Precision, Recall, and F1 score against ground truth pairs."""
    gt_set = {tuple(sorted(p)) for p in ground_truth_pairs}
    pred_set = {tuple(sorted(p)) for p in predicted_pairs}

    if not pred_set and not gt_set:
        return {"precision": 1.0, "recall": 1.0, "f1_score": 1.0, "f1": 1.0, "true_positives": 0}

    true_positives = len(gt_set.intersection(pred_set))
    precision = true_positives / len(pred_set) if pred_set else 0.0
    recall = true_positives / len(gt_set) if gt_set else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "f1": round(f1, 4),
        "true_positives": true_positives,
        "false_positives": len(pred_set) - true_positives,
        "false_negatives": len(gt_set) - true_positives,
    }


def evaluate_ground_truth_dataset(
    engine: EntityResolutionEngine,
    ground_truth: dict[str, Any],
) -> dict[str, float]:
    """Evaluate an EntityResolutionEngine against ground_truth.json dictionary."""
    planted = ground_truth.get("planted_resolved_entities", [])
    gt_pairs: list[tuple[str, str]] = []
    for item in planted:
        pair = item.get("pair")
        if pair and len(pair) == 2:
            gt_pairs.append((pair[0], pair[1]))

    pred_pairs: list[tuple[str, str]] = []
    for item in planted:
        pair = item.get("pair", [])
        if len(pair) == 2:
            root_id = pair[0]
            node = engine.store.nodes.get(root_id)
            if node:
                props = node.properties or {}
                matches = engine.resolve(
                    query={
                        "full_name": props.get("full_name"),
                        "phone_number": props.get("phone_number"),
                        "vehicle_number": props.get("vehicle_number"),
                    },
                    confidence_threshold=0.45,
                )
                for m in matches:
                    if m.matched_node_id != root_id:
                        pred_pairs.append((root_id, m.matched_node_id))

    return evaluate_entity_resolution(gt_pairs, pred_pairs)
