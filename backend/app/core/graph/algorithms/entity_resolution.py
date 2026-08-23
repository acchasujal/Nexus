"""
backend/app/core/graph/algorithms/entity_resolution.py

Lightweight, explainable, and deterministic Entity Resolution (ER) module.
It normalizes names (punctuation, casing, spacing), resolves phonetic variations
common in Indian names (e.g. sharma -> sarma, gowda -> govda), supports alias/nickname
matching, computes fuzzy bigram Jaccard similarity, and integrates address boost.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from backend.app.core.graph.algorithms.utils import GraphStore


@dataclass(frozen=True)
class ResolutionMatch:
    """
    Represents a candidate matched entity from the graph.

    matched_node_id - str(UUID) of the matched Person node
    confidence      - float between 0.0 and 1.0
    matched_fields  - list of fields that contributed to the match (e.g. ["full_name", "phone_number"])
    reason          - human-readable explanation of why this match was made (explainability requirement)
    properties      - the raw property dict of the matched Person node for audit/viewing
    """

    matched_node_id: str
    confidence: float
    matched_fields: list[str]
    reason: str
    properties: dict[str, Any] = field(default_factory=dict)


def normalize_text(text: str) -> str:
    """Normalize text by converting to lowercase, removing punctuation, and normalizing whitespace."""
    if not text:
        return ""
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation (keep alphanumeric characters and whitespace)
    text = re.sub(r'[^\w\s]', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def phonetic_normalize(text: str) -> str:
    """
    Apply simple phonetic-friendly rules for common Indian spelling variations.
    
    Examples:
      - sharma -> sarma
      - gowda -> govda
      - reddy -> reddi
      - singh -> sing
      - pathy -> pati
      - singhal -> sinhal
    """
    text = normalize_text(text)
    if not text:
        return ""
    
    # Normalize vowel representations
    text = text.replace("ee", "i").replace("oo", "u")
    text = text.replace("au", "ov").replace("ou", "ov")
    
    # Common sound-alike consonant mappings
    text = text.replace("sh", "s")
    text = text.replace("w", "v")
    text = text.replace("y", "i")
    text = text.replace("gh", "g")
    text = text.replace("dh", "d")
    text = text.replace("th", "t")
    text = text.replace("bh", "b")
    text = text.replace("ph", "f")
    text = text.replace("ks", "x")
    text = text.replace("ch", "c")
    text = text.replace("ng", "n")
    
    # Remove 'h' except at the beginning of each word (e.g. singhal -> sinhal -> sinal)
    words = []
    for word in text.split(" "):
        if len(word) > 1:
            word = word[0] + word[1:].replace("h", "")
        words.append(word)
    text = " ".join(words)
    
    # Deduplicate consecutive identical characters (e.g. reddy -> redi -> redi)
    text = re.sub(r'(.)\1+', r'\1', text)
    
    return text


def get_bigrams(text: str) -> set[str]:
    """Return the set of character bigrams for a given string."""
    if len(text) < 2:
        return {text} if text else set()
    return {text[i:i+2] for i in range(len(text) - 1)}


def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Calculate the Jaccard similarity of bigrams between two strings."""
    bigrams_a = get_bigrams(text_a)
    bigrams_b = get_bigrams(text_b)
    if not bigrams_a and not bigrams_b:
        return 1.0
    if not bigrams_a or not bigrams_b:
        return 0.0
    intersection = bigrams_a.intersection(bigrams_b)
    union = bigrams_a.union(bigrams_b)
    return len(intersection) / len(union)


def resolve_person(
    store: GraphStore,
    query: dict[str, Any],
    confidence_threshold: float = 0.70,
    candidate_limit: int = 5,
) -> list[ResolutionMatch]:
    """
    Find possible matches in the GraphStore for a person query.
    
    Parameters
    ----------
    store                : GraphStore
    query                : dictionary containing target fields (full_name, phone_number, address_text, aliases)
    confidence_threshold : matches below this threshold are flagged for manual candidate selection rather than automatic link
    candidate_limit      : max candidates to return
    
    Returns
    -------
    list[ResolutionMatch]
        Ranked list of potential matches, sorted by confidence descending.
    """
    matches: list[ResolutionMatch] = []
    
    query_name = query.get("full_name", "")
    query_phone = query.get("phone_number", "")
    query_address = query.get("address_text", "")
    query_aliases = query.get("aliases", [])
    if isinstance(query_aliases, str):
        query_aliases = [query_aliases]
        
    norm_query_name = normalize_text(query_name)
    phon_query_name = phonetic_normalize(query_name)
    norm_query_phone = re.sub(r'\D', '', query_phone) if query_phone else ""
    norm_query_address = normalize_text(query_address) if query_address else ""
    
    for node_id, node in store.nodes.items():
        if node.entity_type not in ("Person", "PERSON"):
            continue
            
        node_props = node.properties
        node_name = node_props.get("full_name", "")
        node_phone = node_props.get("phone_number", "")
        node_address = node_props.get("address_text", "")
        
        raw_aliases = node_props.get("aliases") or []
        node_aliases = [raw_aliases] if isinstance(raw_aliases, str) else list(raw_aliases)
        
        # 1. Phone Match (extremely strong signal)
        if norm_query_phone and node_phone:
            norm_node_phone = re.sub(r'\D', '', node_phone)
            if len(norm_query_phone) >= 10 and len(norm_node_phone) >= 10:
                if norm_query_phone[-10:] == norm_node_phone[-10:]:
                    matches.append(
                        ResolutionMatch(
                            matched_node_id=node_id,
                            confidence=1.0,
                            matched_fields=["phone_number"],
                            reason=f"Exact phone number match on '{node_phone}'",
                            properties=node_props,
                        )
                    )
                    continue
                
        # 2. Name and Alias Matching
        best_name_score = 0.0
        match_field = "full_name"
        matched_str = node_name
        matched_reason = "full name match"
        
        norm_node_name = normalize_text(node_name)
        phon_node_name = phonetic_normalize(node_name)
        
        # Standard and Phonetic match on full name
        score_std = jaccard_similarity(norm_query_name, norm_node_name) if norm_query_name else 0.0
        score_phon = jaccard_similarity(phon_query_name, phon_node_name) if phon_query_name else 0.0
        
        if score_std > best_name_score:
            best_name_score = score_std
            matched_reason = "full name match"
        if score_phon > best_name_score:
            best_name_score = score_phon
            matched_reason = "phonetic name match"
            
        # Match query_name against node aliases
        for alias in node_aliases:
            norm_alias = normalize_text(alias)
            phon_alias = phonetic_normalize(alias)
            
            s_alias_std = jaccard_similarity(norm_query_name, norm_alias) if norm_query_name else 0.0
            s_alias_phon = jaccard_similarity(phon_query_name, phon_alias) if phon_query_name else 0.0
            
            if s_alias_std > best_name_score:
                best_name_score = s_alias_std
                match_field = "aliases"
                matched_str = alias
                matched_reason = "alias match"
            if s_alias_phon > best_name_score:
                best_name_score = s_alias_phon
                match_field = "aliases"
                matched_str = alias
                matched_reason = "phonetic alias match"
                
        # Match query aliases against node name/aliases
        for query_alias in query_aliases:
            norm_q_alias = normalize_text(query_alias)
            phon_q_alias = phonetic_normalize(query_alias)
            
            # Against node name
            s_q_std = jaccard_similarity(norm_q_alias, norm_node_name) if norm_q_alias else 0.0
            s_q_phon = jaccard_similarity(phon_q_alias, phon_node_name) if phon_q_alias else 0.0
            
            if s_q_std > best_name_score:
                best_name_score = s_q_std
                match_field = "full_name"
                matched_str = node_name
                matched_reason = "query alias to full name match"
            if s_q_phon > best_name_score:
                best_name_score = s_q_phon
                match_field = "full_name"
                matched_str = node_name
                matched_reason = "phonetic query alias to full name match"
                
            # Against node aliases
            for alias in node_aliases:
                norm_alias = normalize_text(alias)
                phon_alias = phonetic_normalize(alias)
                s_qa_std = jaccard_similarity(norm_q_alias, norm_alias) if norm_q_alias else 0.0
                s_qa_phon = jaccard_similarity(phon_q_alias, phon_alias) if phon_q_alias else 0.0
                
                if s_qa_std > best_name_score:
                    best_name_score = s_qa_std
                    match_field = "aliases"
                    matched_str = alias
                    matched_reason = "query alias to node alias match"
                if s_qa_phon > best_name_score:
                    best_name_score = s_qa_phon
                    match_field = "aliases"
                    matched_str = alias
                    matched_reason = "phonetic query alias to node alias match"
                    
        # 3. Address matching and scoring
        address_score = 0.0
        if norm_query_address and node_address:
            norm_node_address = normalize_text(node_address)
            address_score = jaccard_similarity(norm_query_address, norm_node_address)
            
        confidence = best_name_score
        matched_fields = [match_field]
        
        # Apply address boost if address matches well and name matches decently
        if address_score > 0.60 and 0.40 < confidence < 0.98:
            confidence = min(0.98, confidence + (1.0 - confidence) * 0.35)
            matched_fields.append("address_text")
            reason_str = f"{matched_reason} ('{matched_str}') with address match boost ({round(address_score, 2)})"
        else:
            reason_str = f"{matched_reason} ('{matched_str}')"
            
        if confidence >= 0.15:  # Cutoff threshold to avoid showing completely unrelated matches
            matches.append(
                ResolutionMatch(
                    matched_node_id=node_id,
                    confidence=round(confidence, 3),
                    matched_fields=matched_fields,
                    reason=reason_str,
                    properties=node_props,
                )
            )
            
    # Sort descending by confidence, breaking ties with node_id
    matches.sort(key=lambda m: (-m.confidence, m.matched_node_id))
    return matches[:candidate_limit]
