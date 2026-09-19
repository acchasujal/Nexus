"""backend/app/services/document_extraction_service.py

Document Intelligence: Candidate Entity & Relationship Extraction Engine (Phase P1-B).

Architecture:
  Deterministic Extraction
    ↓
  Candidate Entities & Relationships
    ↓
  Optional LLM Enrichment (Strictly Non-Authoritative)
    ↓
  Deterministic Validation Against Source Text
    ↓
  Read-Only Candidate Entity Resolution (Against GraphStore)
    ↓
  Evidence-Backed Provenance & Persistence
    ↓
  STOP (No Graph Mutation, No Automatic Fusion)
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from backend.app.ai.llm_client import BaseLLMClient, get_llm_client
from backend.app.ai.schemas import ChatMessage, LLMRequest
from backend.app.core.graph.algorithms.entity_resolution import (
    clean_phone,
    clean_vehicle,
    jaccard_similarity,
    normalize_text,
    phonetic_normalize,
)
from backend.app.db.ingestion.normalization import (
    normalize_account,
    normalize_name,
)
from backend.app.services.audit_service import AuditEventType, AuditService
from shared.contracts.api import (
    CandidateEntity,
    CandidateEntityType,
    CandidateProvenance,
    CandidateRelationship,
    CandidateResolutionStatus,
    DocumentExtractionResult,
    ResolutionCandidateMatch,
    SourceSpan,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _compute_span_evidence(text: str, start: int, end: int, window: int = 80) -> str:
    """Extract a bounded snippet around a source span for human review."""
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    snippet = text[ctx_start:ctx_end].strip()
    if ctx_start > 0:
        snippet = f"...{snippet}"
    if ctx_end < len(text):
        snippet = f"{snippet}..."
    return snippet


class DocumentExtractionService:
    """Extracts candidate entities and evidence-backed candidate relationships from documents.

    Strict Non-Negotiable Invariants:
      1. Zero Graph Mutation: Does not create, modify, or delete graph nodes or edges.
      2. Deterministic Before Generative: Deterministic extraction is completely autonomous
         and self-sufficient. LLM enrichment is optional, non-authoritative, and strictly validated.
      3. Read-Only Resolution: Resolution queries graph nodes solely to surface candidate matches;
         never performs identity fusion or confirms identities.
      4. Mandatory Evidence: Candidate relationships require explicit textual evidence.
      5. Complete Provenance: Every candidate traces to document ID, SHA-256, and character span.
    """

    def __init__(
        self,
        repository: Any,
        audit_service: AuditService,
        llm_client: BaseLLMClient | None = None,
    ) -> None:
        self.repo = repository
        self.audit = audit_service
        self._llm_client = llm_client

    def _get_llm(self) -> BaseLLMClient | None:
        if self._llm_client is not None:
            return self._llm_client
        try:
            return get_llm_client()
        except Exception:
            return None

    # ── Deterministic Candidate Entity Extractors ───────────────────────────

    def _extract_deterministic_entities(
        self,
        text: str,
        document_id: str,
        document_sha256: str,
        case_id: str | None = None,
    ) -> list[CandidateEntity]:
        """High-precision deterministic extraction for phones, accounts, vehicles, dates, names, locations, and orgs."""
        entities: list[CandidateEntity] = []
        seen_spans: set[tuple[int, int, str]] = set()

        # 1. Phone Numbers (Indian Mobile format)
        phone_pattern = re.compile(r"(?:\+91[\-\s]?|91[\-\s]?|0)?([6-9]\d{9})\b")
        for match in phone_pattern.finditer(text):
            span_start, span_end = match.span()
            raw_phone = match.group(0)
            norm_phone = clean_phone(match.group(1))
            if not norm_phone or (span_start, span_end, "PHONE") in seen_spans:
                continue
            seen_spans.add((span_start, span_end, "PHONE"))

            cand_id = f"cand-ent-{hashlib.sha256(f'{document_id}:PHONE:{span_start}:{span_end}'.encode()).hexdigest()[:12]}"
            evidence_snippet = _compute_span_evidence(text, span_start, span_end)
            entities.append(
                CandidateEntity(
                    candidate_id=cand_id,
                    entity_type=CandidateEntityType.PHONE.value,
                    surface_text=raw_phone,
                    normalized_value=norm_phone,
                    confidence=0.98,
                    source_document_id=document_id,
                    case_id=case_id,
                    source_span=SourceSpan(start=span_start, end=span_end),
                    evidence_text=evidence_snippet,
                    extraction_method="DETERMINISTIC",
                    provenance=CandidateProvenance(
                        document_id=document_id,
                        document_sha256=document_sha256,
                        source_text_hash=hashlib.sha256(evidence_snippet.encode()).hexdigest(),
                        case_id=case_id,
                    ),
                    resolution_status=CandidateResolutionStatus.UNRESOLVED,
                )
            )

        # 2. Bank Accounts (Preceded by account keywords or IFSC)
        account_pattern = re.compile(
            r"(?:account(?:\s+no\.?|\s+number)?|a/c(?:\s+no\.?)?|acc(?:\s+no\.?)?)[\s#:]*([0-9]{9,18})\b",
            re.IGNORECASE,
        )
        for match in account_pattern.finditer(text):
            raw_num = match.group(1)
            span_start = match.start(1)
            span_end = match.end(1)
            try:
                norm_acc = normalize_account(raw_num)
            except Exception:
                norm_acc = raw_num

            if (span_start, span_end, "ACCOUNT") in seen_spans:
                continue
            seen_spans.add((span_start, span_end, "ACCOUNT"))

            cand_id = f"cand-ent-{hashlib.sha256(f'{document_id}:ACCOUNT:{span_start}:{span_end}'.encode()).hexdigest()[:12]}"
            evidence_snippet = _compute_span_evidence(text, span_start, span_end)
            entities.append(
                CandidateEntity(
                    candidate_id=cand_id,
                    entity_type=CandidateEntityType.ACCOUNT.value,
                    surface_text=raw_num,
                    normalized_value=norm_acc,
                    confidence=0.94,
                    source_document_id=document_id,
                    case_id=case_id,
                    source_span=SourceSpan(start=span_start, end=span_end),
                    evidence_text=evidence_snippet,
                    extraction_method="DETERMINISTIC",
                    provenance=CandidateProvenance(
                        document_id=document_id,
                        document_sha256=document_sha256,
                        source_text_hash=hashlib.sha256(evidence_snippet.encode()).hexdigest(),
                        case_id=case_id,
                    ),
                    resolution_status=CandidateResolutionStatus.UNRESOLVED,
                )
            )

        # 3. Vehicle Registration Numbers (Indian RTO pattern)
        vehicle_pattern = re.compile(r"\b([A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4})\b")
        for match in vehicle_pattern.finditer(text):
            raw_veh = match.group(1)
            span_start, span_end = match.span(1)
            norm_veh = clean_vehicle(raw_veh)
            if (span_start, span_end, "VEHICLE") in seen_spans:
                continue
            seen_spans.add((span_start, span_end, "VEHICLE"))

            cand_id = f"cand-ent-{hashlib.sha256(f'{document_id}:VEHICLE:{span_start}:{span_end}'.encode()).hexdigest()[:12]}"
            evidence_snippet = _compute_span_evidence(text, span_start, span_end)
            entities.append(
                CandidateEntity(
                    candidate_id=cand_id,
                    entity_type=CandidateEntityType.VEHICLE.value,
                    surface_text=raw_veh,
                    normalized_value=norm_veh,
                    confidence=0.92,
                    source_document_id=document_id,
                    case_id=case_id,
                    source_span=SourceSpan(start=span_start, end=span_end),
                    evidence_text=evidence_snippet,
                    extraction_method="DETERMINISTIC",
                    provenance=CandidateProvenance(
                        document_id=document_id,
                        document_sha256=document_sha256,
                        source_text_hash=hashlib.sha256(evidence_snippet.encode()).hexdigest(),
                        case_id=case_id,
                    ),
                    resolution_status=CandidateResolutionStatus.UNRESOLVED,
                )
            )

        # 4. Dates / Timestamps
        date_patterns = [
            re.compile(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b"),
            re.compile(
                r"\b(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{2,4})\b",
                re.IGNORECASE,
            ),
        ]
        for pat in date_patterns:
            for match in pat.finditer(text):
                raw_date = match.group(1)
                span_start, span_end = match.span(1)
                if (span_start, span_end, "DATE_TIME") in seen_spans:
                    continue
                seen_spans.add((span_start, span_end, "DATE_TIME"))

                cand_id = f"cand-ent-{hashlib.sha256(f'{document_id}:DATE_TIME:{span_start}:{span_end}'.encode()).hexdigest()[:12]}"
                evidence_snippet = _compute_span_evidence(text, span_start, span_end)
                entities.append(
                    CandidateEntity(
                        candidate_id=cand_id,
                        entity_type=CandidateEntityType.DATE_TIME.value,
                        surface_text=raw_date,
                        normalized_value=raw_date.strip(),
                        confidence=0.90,
                        source_document_id=document_id,
                        case_id=case_id,
                        source_span=SourceSpan(start=span_start, end=span_end),
                        evidence_text=evidence_snippet,
                        extraction_method="DETERMINISTIC",
                        provenance=CandidateProvenance(
                            document_id=document_id,
                            document_sha256=document_sha256,
                            source_text_hash=hashlib.sha256(evidence_snippet.encode()).hexdigest(),
                            case_id=case_id,
                        ),
                        resolution_status=CandidateResolutionStatus.UNRESOLVED,
                    )
                )

        # 5. High-Precision Person Name Mentions
        # Role prefixes: Inspector, SI, Accused, Suspect, Witness, Complainant, Shri, Mr., etc.
        person_patterns = [
            re.compile(
                r"\b(?:Inspector|Sub-Inspector|SI|ASI|Accused|Suspect|Witness|Complainant|Shri|Mr\.?|Mrs\.?|Ms\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"
            ),
            re.compile(r"\b(?:states\s+that|informant|arrested|driver|named)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"),
            re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s+(?:contacted|called|received|transferred|driving|visited|reported)\b"),
        ]
        for pat in person_patterns:
            for match in pat.finditer(text):
                raw_name = match.group(1).strip()
                # Exclude known false positives (e.g. "Police Station", months, etc.)
                if any(w in raw_name for w in ("Police", "Station", "Report", "Information", "Department", "Section", "Court")):
                    continue
                span_start = match.start(1)
                span_end = match.end(1)
                if (span_start, span_end, "PERSON") in seen_spans:
                    continue
                seen_spans.add((span_start, span_end, "PERSON"))

                try:
                    norm_name = normalize_name(raw_name)
                except Exception:
                    norm_name = normalize_text(raw_name)

                cand_id = f"cand-ent-{hashlib.sha256(f'{document_id}:PERSON:{span_start}:{span_end}'.encode()).hexdigest()[:12]}"
                evidence_snippet = _compute_span_evidence(text, span_start, span_end)
                entities.append(
                    CandidateEntity(
                        candidate_id=cand_id,
                        entity_type=CandidateEntityType.PERSON.value,
                        surface_text=raw_name,
                        normalized_value=norm_name,
                        confidence=0.88,
                        source_document_id=document_id,
                        case_id=case_id,
                        source_span=SourceSpan(start=span_start, end=span_end),
                        evidence_text=evidence_snippet,
                        extraction_method="DETERMINISTIC",
                        provenance=CandidateProvenance(
                            document_id=document_id,
                            document_sha256=document_sha256,
                            source_text_hash=hashlib.sha256(evidence_snippet.encode()).hexdigest(),
                            case_id=case_id,
                        ),
                        resolution_status=CandidateResolutionStatus.UNRESOLVED,
                    )
                )

        # 6. High-Precision Location Mentions
        location_patterns = [
            re.compile(r"\b(?:at|in|near|district|station)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"),
            re.compile(r"\b(Bengaluru|Mangaluru|Mysuru|Hubballi|Belagavi|Shivamogga|Udupi|Tumakuru|Bellary|Kolar|Electronic City|Koramangala|Indiranagar|Jayanagar|Whitefield)\b"),
        ]
        for pat in location_patterns:
            for match in pat.finditer(text):
                raw_loc = match.group(1).strip()
                if any(w in raw_loc for w in ("The", "This", "Account", "Case", "Report", "Inspector", "First", "Police")):
                    continue
                span_start = match.start(1)
                span_end = match.end(1)
                if (span_start, span_end, "LOCATION") in seen_spans:
                    continue
                seen_spans.add((span_start, span_end, "LOCATION"))

                cand_id = f"cand-ent-{hashlib.sha256(f'{document_id}:LOCATION:{span_start}:{span_end}'.encode()).hexdigest()[:12]}"
                evidence_snippet = _compute_span_evidence(text, span_start, span_end)
                entities.append(
                    CandidateEntity(
                        candidate_id=cand_id,
                        entity_type=CandidateEntityType.LOCATION.value,
                        surface_text=raw_loc,
                        normalized_value=normalize_text(raw_loc),
                        confidence=0.85,
                        source_document_id=document_id,
                        case_id=case_id,
                        source_span=SourceSpan(start=span_start, end=span_end),
                        evidence_text=evidence_snippet,
                        extraction_method="DETERMINISTIC",
                        provenance=CandidateProvenance(
                            document_id=document_id,
                            document_sha256=document_sha256,
                            source_text_hash=hashlib.sha256(evidence_snippet.encode()).hexdigest(),
                            case_id=case_id,
                        ),
                        resolution_status=CandidateResolutionStatus.UNRESOLVED,
                    )
                )

        return sorted(entities, key=lambda e: e.source_span.start)

    # ── Deterministic Candidate Relationship Extractors ─────────────────────

    def _extract_deterministic_relationships(
        self,
        text: str,
        entities: list[CandidateEntity],
        document_id: str,
        document_sha256: str,
        case_id: str | None = None,
    ) -> list[CandidateRelationship]:
        """Extract candidate relationships ONLY where explicit textual evidence connects the entities."""
        relationships: list[CandidateRelationship] = []
        rel_signatures: set[tuple[str, str, str]] = set()

        # Group entities by proximity (sentence or paragraph boundaries)
        # Sort entities by their start span so pairwise checks are strictly ordered
        sorted_entities = sorted(entities, key=lambda e: e.source_span.start)
        for i, ent1 in enumerate(sorted_entities):
            for ent2 in sorted_entities[i + 1 :]:
                span_dist = ent2.source_span.start - ent1.source_span.end
                if span_dist < 0 or span_dist > 250:
                    continue

                # The connective text snippet between the two entities
                between_text = text[ent1.source_span.end : ent2.source_span.start].lower()
                evidence_window = text[
                    max(0, ent1.source_span.start - 40) : min(len(text), ent2.source_span.end + 40)
                ].strip()
                span_start = min(ent1.source_span.start, ent2.source_span.start)
                span_end = max(ent1.source_span.end, ent2.source_span.end)

                # Relationship Rule 1: COMMUNICATED_WITH (Person -> Phone, Person -> Person)
                comm_triggers = ("contacted", "called", "spoke with", "communicated with", "sent sms", "telephoned", "messaged")
                if any(t in between_text or t in evidence_window.lower() for t in comm_triggers):
                    pair_types = {ent1.entity_type, ent2.entity_type}
                    if pair_types == {"PERSON", "PHONE"} or (ent1.entity_type == "PERSON" and ent2.entity_type == "PERSON"):
                        src = ent1 if ent1.entity_type == "PERSON" else ent2
                        tgt = ent2 if ent1.entity_type == "PERSON" else ent1
                        if ent1.entity_type == "PERSON" and ent2.entity_type == "PERSON":
                            src, tgt = ent1, ent2
                        sig = (src.candidate_id, tgt.candidate_id, "COMMUNICATED_WITH")
                        if sig not in rel_signatures:
                            rel_signatures.add(sig)
                            rel_id = f"cand-rel-{hashlib.sha256(f'{document_id}:{sig}'.encode()).hexdigest()[:12]}"
                            relationships.append(
                                CandidateRelationship(
                                    candidate_relationship_id=rel_id,
                                    source_candidate_id=src.candidate_id,
                                    target_candidate_id=tgt.candidate_id,
                                    source_text=src.surface_text,
                                    target_text=tgt.surface_text,
                                    relationship_type="COMMUNICATED_WITH",
                                    confidence=0.88,
                                    evidence_text=evidence_window,
                                    source_document_id=document_id,
                                    case_id=case_id,
                                    source_span=SourceSpan(start=span_start, end=span_end),
                                    provenance=CandidateProvenance(
                                        document_id=document_id,
                                        document_sha256=document_sha256,
                                        source_text_hash=hashlib.sha256(evidence_window.encode()).hexdigest(),
                                        case_id=case_id,
                                    ),
                                    status="CANDIDATE",
                                )
                            )

                # Relationship Rule 2: TRANSFERRED_TO (Account -> Account)
                transfer_triggers = (
                    "received a transfer of",
                    "transfer of",
                    "transferred to",
                    "transferred from",
                    "credited from",
                    "sent funds to",
                    "remitted to",
                    "received from",
                )
                if any(t in between_text or t in evidence_window.lower() for t in transfer_triggers):
                    if ent1.entity_type == "ACCOUNT" and ent2.entity_type == "ACCOUNT":
                        # Determine source and target order based on text
                        src, tgt = ent1, ent2
                        if "from account" in between_text or "received a transfer" in evidence_window.lower():
                            if "from account" in between_text or "from" in between_text:
                                src, tgt = ent2, ent1
                        sig = (src.candidate_id, tgt.candidate_id, "TRANSFERRED_TO")
                        if sig not in rel_signatures:
                            rel_signatures.add(sig)
                            rel_id = f"cand-rel-{hashlib.sha256(f'{document_id}:{sig}'.encode()).hexdigest()[:12]}"
                            relationships.append(
                                CandidateRelationship(
                                    candidate_relationship_id=rel_id,
                                    source_candidate_id=src.candidate_id,
                                    target_candidate_id=tgt.candidate_id,
                                    source_text=src.surface_text,
                                    target_text=tgt.surface_text,
                                    relationship_type="TRANSFERRED_TO",
                                    confidence=0.90,
                                    evidence_text=evidence_window,
                                    source_document_id=document_id,
                                    case_id=case_id,
                                    source_span=SourceSpan(start=span_start, end=span_end),
                                    provenance=CandidateProvenance(
                                        document_id=document_id,
                                        document_sha256=document_sha256,
                                        source_text_hash=hashlib.sha256(evidence_window.encode()).hexdigest(),
                                        case_id=case_id,
                                    ),
                                    status="CANDIDATE",
                                )
                            )

                # Relationship Rule 3: USED_PHONE (Person -> Phone)
                phone_usage_triggers = ("using phone", "used phone", "subscriber of", "sim card", "registered to")
                if any(t in between_text or t in evidence_window.lower() for t in phone_usage_triggers):
                    if {ent1.entity_type, ent2.entity_type} == {"PERSON", "PHONE"}:
                        src = ent1 if ent1.entity_type == "PERSON" else ent2
                        tgt = ent2 if ent1.entity_type == "PERSON" else ent1
                        sig = (src.candidate_id, tgt.candidate_id, "USED_PHONE")
                        if sig not in rel_signatures:
                            rel_signatures.add(sig)
                            rel_id = f"cand-rel-{hashlib.sha256(f'{document_id}:{sig}'.encode()).hexdigest()[:12]}"
                            relationships.append(
                                CandidateRelationship(
                                    candidate_relationship_id=rel_id,
                                    source_candidate_id=src.candidate_id,
                                    target_candidate_id=tgt.candidate_id,
                                    source_text=src.surface_text,
                                    target_text=tgt.surface_text,
                                    relationship_type="USED_PHONE",
                                    confidence=0.92,
                                    evidence_text=evidence_window,
                                    source_document_id=document_id,
                                    case_id=case_id,
                                    source_span=SourceSpan(start=span_start, end=span_end),
                                    provenance=CandidateProvenance(
                                        document_id=document_id,
                                        document_sha256=document_sha256,
                                        source_text_hash=hashlib.sha256(evidence_window.encode()).hexdigest(),
                                        case_id=case_id,
                                    ),
                                    status="CANDIDATE",
                                )
                            )

                # Relationship Rule 4: USED_VEHICLE (Person -> Vehicle)
                veh_triggers = ("driving vehicle", "driving", "used vehicle", "registered vehicle", "driver of", "travelling in", "vehicle")
                if any(t in between_text or t in evidence_window.lower() for t in veh_triggers):
                    if {ent1.entity_type, ent2.entity_type} == {"PERSON", "VEHICLE"}:
                        src = ent1 if ent1.entity_type == "PERSON" else ent2
                        tgt = ent2 if ent1.entity_type == "PERSON" else ent1
                        sig = (src.candidate_id, tgt.candidate_id, "USED_VEHICLE")
                        if sig not in rel_signatures:
                            rel_signatures.add(sig)
                            rel_id = f"cand-rel-{hashlib.sha256(f'{document_id}:{sig}'.encode()).hexdigest()[:12]}"
                            relationships.append(
                                CandidateRelationship(
                                    candidate_relationship_id=rel_id,
                                    source_candidate_id=src.candidate_id,
                                    target_candidate_id=tgt.candidate_id,
                                    source_text=src.surface_text,
                                    target_text=tgt.surface_text,
                                    relationship_type="USED_VEHICLE",
                                    confidence=0.89,
                                    evidence_text=evidence_window,
                                    source_document_id=document_id,
                                    case_id=case_id,
                                    source_span=SourceSpan(start=span_start, end=span_end),
                                    provenance=CandidateProvenance(
                                        document_id=document_id,
                                        document_sha256=document_sha256,
                                        source_text_hash=hashlib.sha256(evidence_window.encode()).hexdigest(),
                                        case_id=case_id,
                                    ),
                                    status="CANDIDATE",
                                )
                            )

                # Relationship Rule 5: LOCATED_AT / SEEN_AT (Person / Vehicle -> Location)
                loc_triggers = ("seen at", "located at", "residing in", "entered premises", "visited", "stopped at")
                if any(t in between_text or t in evidence_window.lower() for t in loc_triggers):
                    pair_types = {ent1.entity_type, ent2.entity_type}
                    if ("LOCATION" in pair_types) and (("PERSON" in pair_types) or ("VEHICLE" in pair_types)):
                        src = ent1 if ent1.entity_type != "LOCATION" else ent2
                        tgt = ent2 if ent1.entity_type != "LOCATION" else ent1
                        sig = (src.candidate_id, tgt.candidate_id, "LOCATED_AT")
                        if sig not in rel_signatures:
                            rel_signatures.add(sig)
                            rel_id = f"cand-rel-{hashlib.sha256(f'{document_id}:{sig}'.encode()).hexdigest()[:12]}"
                            relationships.append(
                                CandidateRelationship(
                                    candidate_relationship_id=rel_id,
                                    source_candidate_id=src.candidate_id,
                                    target_candidate_id=tgt.candidate_id,
                                    source_text=src.surface_text,
                                    target_text=tgt.surface_text,
                                    relationship_type="LOCATED_AT",
                                    confidence=0.85,
                                    evidence_text=evidence_window,
                                    source_document_id=document_id,
                                    case_id=case_id,
                                    source_span=SourceSpan(start=span_start, end=span_end),
                                    provenance=CandidateProvenance(
                                        document_id=document_id,
                                        document_sha256=document_sha256,
                                        source_text_hash=hashlib.sha256(evidence_window.encode()).hexdigest(),
                                        case_id=case_id,
                                    ),
                                    status="CANDIDATE",
                                )
                            )

        return relationships

    # ── Read-Only Candidate Entity Resolution Against Existing Graph Nodes ─

    def _resolve_candidates_against_graph(
        self,
        candidates: list[CandidateEntity],
    ) -> None:
        """Query existing graph nodes in a strictly READ-ONLY manner to identify candidate matches.

        Never mutates the graph, creates nodes, creates edges, or confirms identities.
        """
        nodes = getattr(self.repo, "nodes", {})

        for cand in candidates:
            matches: list[ResolutionCandidateMatch] = []

            # 1. Person Resolution
            if cand.entity_type == "PERSON":
                norm_query = cand.normalized_value or normalize_text(cand.surface_text)
                phon_query = phonetic_normalize(cand.surface_text)

                for nid, node in nodes.items():
                    if node.get("entity_type") not in ("Person", "PERSON"):
                        continue
                    props = node.get("properties", {})
                    node_name = props.get("full_name") or props.get("name") or ""
                    norm_node_name = normalize_text(node_name)
                    phon_node_name = phonetic_normalize(node_name)

                    match_reasons: list[str] = []
                    score = 0.0

                    if norm_query == norm_node_name:
                        score = 0.95
                        match_reasons.append("Exact name match")
                    elif phon_query == phon_node_name:
                        score = 0.88
                        match_reasons.append("Phonetic name match")
                    else:
                        jaccard = jaccard_similarity(norm_query, norm_node_name)
                        if jaccard >= 0.50:
                            score = round(jaccard, 2)
                            match_reasons.append(f"Fuzzy name similarity ({jaccard:.2f})")

                    if score >= 0.50:
                        matches.append(
                            ResolutionCandidateMatch(
                                canonical_entity_id=str(nid),
                                canonical_name=node_name,
                                entity_type="Person",
                                match_score=score,
                                match_reasons=match_reasons,
                            )
                        )

            # 2. Phone Resolution
            elif cand.entity_type == "PHONE":
                clean_target = cand.normalized_value or clean_phone(cand.surface_text)
                for nid, node in nodes.items():
                    if node.get("entity_type") not in ("Phone", "PHONE"):
                        continue
                    props = node.get("properties", {})
                    node_phone = clean_phone(props.get("phone_number") or props.get("msisdn") or "")
                    if clean_target and clean_target == node_phone:
                        matches.append(
                            ResolutionCandidateMatch(
                                canonical_entity_id=str(nid),
                                canonical_name=props.get("phone_number") or clean_target,
                                entity_type="Phone",
                                match_score=1.0,
                                match_reasons=["Exact MSISDN phone match"],
                            )
                        )

            # 3. Vehicle Resolution
            elif cand.entity_type == "VEHICLE":
                clean_target = cand.normalized_value or clean_vehicle(cand.surface_text)
                for nid, node in nodes.items():
                    if node.get("entity_type") not in ("Vehicle", "VEHICLE"):
                        continue
                    props = node.get("properties", {})
                    node_veh = clean_vehicle(props.get("registration_number") or props.get("vehicle_number") or "")
                    if clean_target and clean_target == node_veh:
                        matches.append(
                            ResolutionCandidateMatch(
                                canonical_entity_id=str(nid),
                                canonical_name=props.get("registration_number") or clean_target,
                                entity_type="Vehicle",
                                match_score=1.0,
                                match_reasons=["Exact vehicle registration match"],
                            )
                        )

            # 4. Account Resolution
            elif cand.entity_type == "ACCOUNT":
                clean_target = cand.normalized_value
                for nid, node in nodes.items():
                    if node.get("entity_type") not in ("Account", "ACCOUNT", "BankAccount"):
                        continue
                    props = node.get("properties", {})
                    node_acc = str(props.get("account_number") or "").strip().upper()
                    if clean_target and clean_target == node_acc:
                        matches.append(
                            ResolutionCandidateMatch(
                                canonical_entity_id=str(nid),
                                canonical_name=f"A/c {clean_target}",
                                entity_type="Account",
                                match_score=1.0,
                                match_reasons=["Exact bank account number match"],
                            )
                        )

            # Attach candidate matches and update status (strictly REVIEW_REQUIRED or NO_MATCH_FOUND)
            matches.sort(key=lambda m: m.match_score, reverse=True)
            cand.resolution_candidates = matches[:10]
            if matches:
                cand.resolution_status = CandidateResolutionStatus.REVIEW_REQUIRED
            else:
                cand.resolution_status = CandidateResolutionStatus.NO_MATCH_FOUND

    # ── Optional LLM Extraction Enrichment (Non-Authoritative) ───────────────

    def _enrich_with_llm(
        self,
        text: str,
        existing_entities: list[CandidateEntity],
        existing_relationships: list[CandidateRelationship],
        document_id: str,
        document_sha256: str,
        case_id: str | None = None,
    ) -> tuple[list[CandidateEntity], list[CandidateRelationship], list[str]]:
        """Optionally invoke LLM to propose candidates with strict source-text validation."""
        llm = self._get_llm()
        if llm is None:
            return existing_entities, existing_relationships, ["Deterministic extraction completed; LLM not configured."]

        notes: list[str] = []
        try:
            system_prompt = (
                "You are an evidence extraction assistant for police investigative documents. "
                "Extract entities and relationships from the provided text into strict JSON. "
                "Rules:\n"
                "1. Only extract entities explicitly mentioned in the text.\n"
                "2. Allowed entity types: PERSON, PHONE, ACCOUNT, VEHICLE, LOCATION, ORGANIZATION, DEVICE, DATE_TIME, EVENT.\n"
                "3. Allowed relationship types: COMMUNICATED_WITH, TRANSFERRED_TO, USED_PHONE, USED_VEHICLE, LOCATED_AT, OWNS_ACCOUNT, ASSOCIATED_WITH.\n"
                "4. Output JSON format:\n"
                '{"entities": [{"type": "...", "text": "...", "confidence": 0.85}], '
                '"relationships": [{"type": "...", "source_text": "...", "target_text": "...", "evidence": "...", "confidence": 0.85}]}\n'
                "Do not infer guilt, intent, or dangerousness."
            )
            req = LLMRequest(
                messages=[
                    ChatMessage(role="system", content=system_prompt),
                    ChatMessage(role="user", content=f"Document text:\n```\n{text[:4000]}\n```"),
                ],
                temperature=0.0,
                max_tokens=1000,
            )
            resp = llm.generate(req)
            raw_content = resp.content.strip()

            # Strip markdown json blocks if present
            if raw_content.startswith("```"):
                raw_content = re.sub(r"^```(?:json)?", "", raw_content)
                raw_content = re.sub(r"```$", "", raw_content).strip()

            parsed = json.loads(raw_content)
            if not isinstance(parsed, dict):
                return existing_entities, existing_relationships, ["LLM output was not a JSON object; ignored."]

            # Deterministically validate proposed LLM entities
            known_texts = {e.surface_text.lower(): e for e in existing_entities}
            enriched_entities = list(existing_entities)

            for ent_dict in parsed.get("entities", []):
                if not isinstance(ent_dict, dict):
                    continue
                surface = str(ent_dict.get("text") or "").strip()
                etype = str(ent_dict.get("type") or "").strip().upper()
                if not surface or surface.lower() in known_texts:
                    continue
                if etype not in CandidateEntityType.__members__:
                    continue

                # Verify surface text literally exists in document text
                idx = text.find(surface)
                if idx == -1:
                    continue  # Discard hallucinatory entity not in text

                span_start = idx
                span_end = idx + len(surface)
                conf = min(1.0, max(0.1, float(ent_dict.get("confidence") or 0.80)))
                evidence_snippet = _compute_span_evidence(text, span_start, span_end)
                cand_id = f"cand-ent-{hashlib.sha256(f'{document_id}:{etype}:{span_start}:{span_end}'.encode()).hexdigest()[:12]}"

                new_cand = CandidateEntity(
                    candidate_id=cand_id,
                    entity_type=etype,
                    surface_text=surface,
                    normalized_value=normalize_text(surface),
                    confidence=conf,
                    source_document_id=document_id,
                    case_id=case_id,
                    source_span=SourceSpan(start=span_start, end=span_end),
                    evidence_text=evidence_snippet,
                    extraction_method="LLM_ASSISTED",
                    provenance=CandidateProvenance(
                        document_id=document_id,
                        document_sha256=document_sha256,
                        source_text_hash=hashlib.sha256(evidence_snippet.encode()).hexdigest(),
                        case_id=case_id,
                    ),
                    resolution_status=CandidateResolutionStatus.UNRESOLVED,
                )
                enriched_entities.append(new_cand)
                known_texts[surface.lower()] = new_cand

            notes.append(f"LLM enrichment successfully validated and merged ({llm.provider_name}).")
            return enriched_entities, existing_relationships, notes

        except Exception as exc:
            logger.warning(f"Optional LLM extraction enrichment failed or bypassed: {exc}")
            return existing_entities, existing_relationships, [f"LLM enrichment bypassed: {exc}"]

    # ── Main Orchestration Pipeline ───────────────────────────────────────────

    def extract_document_candidates(
        self,
        document_id: str,
        actor_id: str,
        request_id: str | None = None,
        force_reextract: bool = False,
    ) -> DocumentExtractionResult:
        """Run candidate extraction pipeline for an authenticated and authorized document.

        Pipeline:
          1. Check Idempotency: Return existing run if identical content hash already extracted.
          2. Log DOCUMENT_EXTRACTION_STARTED audit event.
          3. Deterministic Extraction of entities and relationships.
          4. Optional LLM enrichment (validated against source text).
          5. Read-only candidate resolution against GraphStore.
          6. Record DOCUMENT_CANDIDATES_EXTRACTED audit event.
          7. Persist candidates in isolated repository collection.
        """
        # Fetch document record
        doc_record = self.repo.get_document(document_id)
        if not doc_record:
            raise ValueError(f"Document '{document_id}' not found.")

        content_hash = doc_record.get("content_hash", "")
        case_id = doc_record.get("case_id")
        extracted_text = doc_record.get("extracted_text", "")

        # 1. Idempotency Check
        if not force_reextract:
            existing = self.repo.get_candidate_extraction(document_id)
            if existing and existing.get("content_hash") == content_hash:
                logger.info(f"Returning cached candidate extraction for document {document_id}.")
                return DocumentExtractionResult(**existing)

        run_id = f"ext-{document_id}-{content_hash[:10]}"

        # 2. Record Start Audit Event
        self.audit.record(
            event_type=AuditEventType.DOCUMENT_EXTRACTION_STARTED,
            actor_id=actor_id,
            case_id=case_id,
            entity_id=document_id,
            entity_type="Document",
            request_id=request_id,
            details={"run_id": run_id, "content_hash": content_hash},
        )

        try:
            # 3. Deterministic Extraction
            deterministic_entities = self._extract_deterministic_entities(
                text=extracted_text,
                document_id=document_id,
                document_sha256=content_hash,
                case_id=case_id,
            )

            deterministic_relationships = self._extract_deterministic_relationships(
                text=extracted_text,
                entities=deterministic_entities,
                document_id=document_id,
                document_sha256=content_hash,
                case_id=case_id,
            )

            # 4. Optional LLM Enrichment
            entities, relationships, notes = self._enrich_with_llm(
                text=extracted_text,
                existing_entities=deterministic_entities,
                existing_relationships=deterministic_relationships,
                document_id=document_id,
                document_sha256=content_hash,
                case_id=case_id,
            )

            # 5. Read-Only Candidate Entity Resolution Against Existing GraphStore
            self._resolve_candidates_against_graph(entities)

            # 6. Build Result
            result = DocumentExtractionResult(
                document_id=document_id,
                case_id=case_id,
                content_hash=content_hash,
                extraction_run_id=run_id,
                extracted_at=_utcnow(),
                candidate_entities=entities,
                candidate_relationships=relationships,
                entity_count=len(entities),
                relationship_count=len(relationships),
                status="COMPLETED",
                extraction_notes=notes,
            )

            # 7. Record Completion Audit Event
            self.audit.record(
                event_type=AuditEventType.DOCUMENT_CANDIDATES_EXTRACTED,
                actor_id=actor_id,
                case_id=case_id,
                entity_id=document_id,
                entity_type="Document",
                request_id=request_id,
                details={
                    "run_id": run_id,
                    "content_hash": content_hash,
                    "entity_count": len(entities),
                    "relationship_count": len(relationships),
                },
            )

            # 8. Persist in isolated repository collection
            self.repo.store_candidate_extraction(result.model_dump())
            return result

        except Exception as exc:
            logger.error(f"Extraction failed for document {document_id}: {exc}", exc_info=True)
            self.audit.record(
                event_type=AuditEventType.DOCUMENT_EXTRACTION_FAILED,
                actor_id=actor_id,
                case_id=case_id,
                entity_id=document_id,
                entity_type="Document",
                request_id=request_id,
                details={"run_id": run_id, "error": str(exc)},
            )
            raise

    def get_candidate_extraction(self, document_id: str) -> DocumentExtractionResult | None:
        """Retrieve stored candidate extraction for a document."""
        data = self.repo.get_candidate_extraction(document_id)
        if not data:
            return None
        return DocumentExtractionResult(**data)

    def get_candidate_entity(self, candidate_id: str) -> CandidateEntity | None:
        """Retrieve a specific candidate entity by its ID."""
        ent = self.repo.get_candidate_entity(candidate_id)
        if not ent:
            return None
        return CandidateEntity(**ent)
