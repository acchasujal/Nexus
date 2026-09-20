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
from typing import Any

from backend.app.core.graph.algorithms.utils import GraphStore
from backend.app.core.graph.enums import ResolutionStatus


# Evidence families for epistemic independence
NAME_FAMILY = "NAME_FAMILY"
TELECOM_FAMILY = "TELECOM_FAMILY"
VEHICLE_FAMILY = "VEHICLE_FAMILY"
IDENTIFIER_FAMILY = "IDENTIFIER_FAMILY"
LOCATION_FAMILY = "LOCATION_FAMILY"
RELATIONAL_FAMILY = "RELATIONAL_FAMILY"


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
    search_relevance: float = 1.0
    resolution_state: str = "CANDIDATE_NAME_ONLY"
    evidence_families: list[str] = field(default_factory=list)
    supporting_factors: list[str] = field(default_factory=list)
    conflicting_factors: list[str] = field(default_factory=list)
    independent_sources: int = 1
    explanation: str = ""


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
        supporting_factors: list[str] = []
        conflicting_factors: list[str] = []

        # 1. National ID Check (Definitive 1.0)
        node_id_val = props.get("national_id") or props.get("id_number")
        if query_id and node_id_val:
            if str(query_id).strip() == str(node_id_val).strip():
                matched_fields.append("national_id")
                evidence_breakdown["national_id"] = 1.0
                supporting_factors.append(f"Exact National ID match ({query_id})")
                reason_parts.append(f"Exact National ID match ({query_id})")
            else:
                conflicting_factors.append(f"National ID mismatch (query: {query_id} vs record: {node_id_val})")

        # 2. Direct Phone Match (1.0)
        node_phones = props.get("phone_numbers") or [props.get("phone_number")] or []
        if isinstance(node_phones, str):
            node_phones = [node_phones]
        node_phones_clean = {clean_phone(p) for p in node_phones if p}

        if query_phone and node_phones_clean:
            if query_phone in node_phones_clean:
                matched_fields.append("phone_number")
                evidence_breakdown["phone_number"] = 1.0
                supporting_factors.append(f"Matching phone ({query_phone})")
                reason_parts.append(f"Matching phone ({query_phone})")
            elif norm_query_name and norm_query_name == norm_node_name:
                conflicting_factors.append(f"Differing phone MSISDN on record ({next(iter(node_phones_clean))})")

        # 3. Vehicle Match (0.85)
        node_vehicles = props.get("vehicles") or [props.get("vehicle_number")] or [props.get("registration_number")] or []
        if isinstance(node_vehicles, str):
            node_vehicles = [node_vehicles]
        node_vehicles_clean = {clean_vehicle(v) for v in node_vehicles if v}

        if query_vehicle and node_vehicles_clean:
            if query_vehicle in node_vehicles_clean:
                matched_fields.append("vehicle_number")
                evidence_breakdown["vehicle_number"] = 0.85
                supporting_factors.append(f"Matching vehicle reg ({query_vehicle})")
                reason_parts.append(f"Matching vehicle reg ({query_vehicle})")
            elif norm_query_name and norm_query_name == norm_node_name:
                conflicting_factors.append("Differing vehicle registration on record")

        # 4. Name Similarity (Exact, Phonetic, Word Token Jaccard, or Fuzzy Bigram)
        name_score = 0.0
        if norm_query_name and norm_node_name:
            if norm_query_name == norm_node_name:
                name_score = 1.0
                matched_fields.extend(["full_name", "full_name_exact"])
                supporting_factors.append(f"Exact full-name match '{node_name}'")
                reason_parts.append(f"Exact name match '{node_name}'")
            elif phon_query_name == phon_node_name:
                name_score = 1.0
                matched_fields.extend(["full_name", "full_name_phonetic"])
                supporting_factors.append(f"Phonetic name match '{node_name}'")
                reason_parts.append(f"Phonetic name match '{node_name}'")
            else:
                query_words = set(norm_query_name.split())
                node_words = set(norm_node_name.split())
                common_words = query_words.intersection(node_words)
                if not common_words:
                    phon_query_words = set(phon_query_name.split())
                    phon_node_words = set(phon_node_name.split())
                    common_words = phon_query_words.intersection(phon_node_words)

                jaccard = jaccard_similarity(norm_query_name, norm_node_name)
                phon_jaccard = jaccard_similarity(phon_query_name, phon_node_name)
                best_sim = max(jaccard, phon_jaccard)

                token_sim = 0.0
                all_words: set[str] = set()
                if common_words:
                    all_words = query_words.union(node_words)
                    token_sim = len(common_words) / len(all_words) if all_words else 0.0
                    initial_match = any(
                        (len(qw) == 1 and nw.startswith(qw)) or (len(nw) == 1 and qw.startswith(nw))
                        for qw in query_words for nw in node_words
                    )
                    if initial_match:
                        token_sim = max(token_sim, 0.48)

                combined_sim = max(token_sim, best_sim)
                if combined_sim >= min(0.30, confidence_threshold):
                    name_score = round(combined_sim, 3)
                    if token_sim >= best_sim and common_words:
                        matched_fields.append("full_name_token")
                        supporting_factors.append(f"Word token match ({len(common_words)}/{len(all_words)} words) with '{node_name}'")
                        reason_parts.append(f"Word token match '{node_name}' ({len(common_words)}/{len(all_words)})")
                    else:
                        matched_fields.append("full_name_fuzzy")
                        supporting_factors.append(f"Fuzzy name match '{node_name}' (sim={best_sim:.2f})")
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
            supporting_factors.append("Matched known alias/nickname")
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
                    supporting_factors.append(f"Corroborating address similarity ({addr_sim:.2f})")
                    reason_parts.append(f"Corroborating address similarity ({addr_sim:.2f})")
                    break

        # Evidence families aggregation (epistemic orthogonality)
        matched_families_set: set[str] = set()
        for f in matched_fields:
            if f in ("full_name", "full_name_exact", "full_name_phonetic", "full_name_token", "full_name_fuzzy", "aliases", "alias_match"):
                matched_families_set.add(NAME_FAMILY)
            elif f in ("phone_number", "phone", "msisdn", "imei"):
                matched_families_set.add(TELECOM_FAMILY)
            elif f in ("vehicle_number", "vehicle", "registration_number"):
                matched_families_set.add(VEHICLE_FAMILY)
            elif f in ("national_id", "aadhaar", "pan", "passport"):
                matched_families_set.add(IDENTIFIER_FAMILY)
            elif f in ("address_text", "address", "district"):
                matched_families_set.add(LOCATION_FAMILY)
        evidence_families = sorted(matched_families_set)

        raw_confidence = sum(evidence_breakdown.values())
        if conflicting_factors:
            total_confidence = max(0.10, round(raw_confidence * 0.5, 3))
        else:
            total_confidence = min(1.0, round(raw_confidence, 3))

        # Resolution state & status tier
        if conflicting_factors:
            resolution_state = "AMBIGUOUS_CONFLICT"
            status = ResolutionStatus.REVIEW_REQUIRED
            explanation = f"Conflicting evidence detected ({'; '.join(conflicting_factors)}); human review required."
        elif IDENTIFIER_FAMILY in evidence_families:
            resolution_state = "EXACT_IDENTIFIER_MATCH"
            status = ResolutionStatus.MATCHED
            explanation = "Exact verified national identifier corroborated."
        elif len(evidence_families) >= 2:
            resolution_state = "STRONGLY_CORROBORATED"
            status = ResolutionStatus.MATCHED
            family_names = [f.replace("_FAMILY", "").title() for f in evidence_families]
            explanation = f"Multi-field corroborated across {len(evidence_families)} independent families ({', '.join(family_names)})."
        elif TELECOM_FAMILY in evidence_families:
            resolution_state = "TELECOM_CORROBORATED"
            status = ResolutionStatus.MATCHED
            explanation = "Direct MSISDN telephony match; uncorroborated by independent address or national ID."
        elif VEHICLE_FAMILY in evidence_families:
            resolution_state = "VEHICLE_CORROBORATED"
            status = ResolutionStatus.PROBABLE_MATCH
            explanation = "Vehicle registration corroborated; demographic review recommended."
        elif NAME_FAMILY in evidence_families:
            if "full_name_exact" in matched_fields or "full_name_phonetic" in matched_fields or "alias_match" in matched_fields:
                resolution_state = "CANDIDATE_NAME_ONLY"
                status = ResolutionStatus.REVIEW_REQUIRED
                explanation = "Name match candidate only; lacking independent telecom or address corroboration."
            else:
                resolution_state = "CANDIDATE_PARTIAL_NAME"
                status = ResolutionStatus.REVIEW_REQUIRED
                explanation = "Partial name/token match candidate only; unconfirmed without corroborating telemetry."
        else:
            resolution_state = "UNRESOLVED"
            status = ResolutionStatus.NOT_MATCHED
            explanation = "Insufficient evidence to corroborate candidate."

        if total_confidence >= confidence_threshold:
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
                    search_relevance=round(raw_confidence, 3),
                    resolution_state=resolution_state,
                    evidence_families=evidence_families,
                    supporting_factors=supporting_factors,
                    conflicting_factors=conflicting_factors,
                    independent_sources=max(1, len(evidence_families)),
                    explanation=explanation,
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
    seen_roots: set[str] = set()
    for item in planted:
        pair = item.get("pair", [])
        if len(pair) == 2:
            root_id = pair[0]
            if root_id in seen_roots:
                continue
            seen_roots.add(root_id)
            node = engine.store.nodes.get(root_id)
            if node:
                props = node.properties or {}
                matches = engine.resolve(
                    query={
                        "full_name": props.get("full_name"),
                        "phone_number": props.get("phone_number"),
                        "vehicle_number": props.get("vehicle_number"),
                    },
                    confidence_threshold=0.70,
                )
                for m in matches:
                    if m.matched_node_id != root_id:
                        pred_pairs.append((root_id, m.matched_node_id))

    return evaluate_entity_resolution(gt_pairs, pred_pairs)
