"""Explainable identity-claim matching for ingestion records."""

from __future__ import annotations


from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from backend.app.core.graph.algorithms.entity_resolution import clean_phone, clean_vehicle, jaccard_similarity, normalize_text, phonetic_normalize
from backend.app.core.graph.enums import ResolutionStatus

from ..contracts import SourceType

if TYPE_CHECKING:
    from .registry import IdentityRegistry


class IdentityClaim(BaseModel):
    """A source-backed identity assertion about an incoming record."""

    source_record_id: str
    record_id: str
    full_name: str = ""
    aliases: list[str] = Field(default_factory=list)
    phone_number: str = ""
    vehicle_number: str = ""
    address: str = ""
    national_id: str = ""
    source_type: SourceType

    def normalized(self) -> IdentityClaim:
        """Return a normalized copy used only for deterministic matching."""
        return self.model_copy(update={
            "full_name": normalize_text(self.full_name),
            "aliases": [normalize_text(alias) for alias in self.aliases if normalize_text(alias)],
            "phone_number": clean_phone(self.phone_number),
            "vehicle_number": clean_vehicle(self.vehicle_number),
            "address": normalize_text(self.address),
            "national_id": self.national_id.strip(),
        })


class CandidateDecision(BaseModel):
    """Explainable match decision; review candidates remain unlinked."""

    candidate_person_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    status: ResolutionStatus
    matched_fields: list[str] = Field(default_factory=list)
    conflicting_fields: list[str] = Field(default_factory=list)
    reason: str
    supporting_source_record_ids: list[str] = Field(default_factory=list)
    auto_link_allowed: bool = False
    requires_human_review: bool = True


def _name_match(incoming: IdentityClaim, existing: IdentityClaim) -> tuple[bool, bool, float]:
    incoming_name = normalize_text(incoming.full_name)
    existing_name = normalize_text(existing.full_name)
    if incoming_name and incoming_name == existing_name:
        return True, False, 1.0
    if incoming_name and phonetic_normalize(incoming_name) == phonetic_normalize(existing_name):
        return False, True, 0.9
    incoming_aliases = {normalize_text(alias) for alias in incoming.aliases}
    existing_aliases = {normalize_text(alias) for alias in existing.aliases}
    if incoming_name in existing_aliases or existing_name in incoming_aliases or incoming_aliases.intersection(existing_aliases):
        return False, True, 0.8
    similarity = jaccard_similarity(incoming_name, existing_name) if incoming_name and existing_name else 0.0
    return False, False, similarity


def decide_candidates(registry: IdentityRegistry, claim: IdentityClaim, review_threshold: float = 0.40) -> list[CandidateDecision]:
    """Score indexed candidates under conservative automatic-link rules."""
    from .registry import IdentityRegistry

    if not isinstance(registry, IdentityRegistry):
        raise TypeError("registry must be an IdentityRegistry")
    incoming = claim.normalized()
    decisions: list[CandidateDecision] = []
    for person_id in registry.candidate_person_ids(incoming):
        profile = registry.get_profile(person_id)
        matched: set[str] = set()
        conflicts: set[str] = set()
        best_name_score = 0.0
        exact_name = phonetic_name = alias_match = False
        for existing in profile.claims:
            existing = existing.normalized()
            name_exact, name_phonetic, name_score = _name_match(incoming, existing)
            exact_name |= name_exact
            phonetic_name |= name_phonetic
            alias_match |= name_score == 0.8
            best_name_score = max(best_name_score, name_score)
            if incoming.national_id and existing.national_id:
                if incoming.national_id == existing.national_id:
                    matched.add("national_id")
                else:
                    conflicts.add("national_id")
            if incoming.phone_number and existing.phone_number:
                if incoming.phone_number == existing.phone_number:
                    matched.add("phone_number")
                else:
                    conflicts.add("phone_number")
            if incoming.vehicle_number and existing.vehicle_number:
                if incoming.vehicle_number == existing.vehicle_number:
                    matched.add("vehicle_number")
                else:
                    conflicts.add("vehicle_number")
            if incoming.address and existing.address and jaccard_similarity(incoming.address, existing.address) >= 0.35:
                matched.add("address")
        if exact_name:
            matched.add("full_name_exact")
        elif phonetic_name:
            matched.add("full_name_phonetic")
        elif alias_match:
            matched.add("alias")
        if incoming.address and "address" not in matched and best_name_score >= review_threshold:
            matched.add("name_similarity")

        strong = len({field for field in matched if field in {"national_id", "phone_number", "vehicle_number"}})
        compatible_name = bool({"full_name_exact", "full_name_phonetic", "alias", "name_similarity"}.intersection(matched))
        
        has_nid_conflict = "national_id" in conflicts
        has_phone_conflict = "phone_number" in conflicts
        
        name_alone = compatible_name and strong == 0 and "address" not in matched
        phone_alone = "phone_number" in matched and not compatible_name and strong == 1
        address_alone = "address" in matched and strong == 0 and not compatible_name
        
        if has_nid_conflict:
            status = ResolutionStatus.NOT_MATCHED
            reason = "Different verified national IDs prevent matching."
            auto = False
        elif "national_id" in matched and not has_phone_conflict:
            status = ResolutionStatus.MATCHED
            reason = "Exact verified national ID with no strong conflict."
            auto = True
        elif "national_id" in matched and has_phone_conflict:
            status = ResolutionStatus.REVIEW_REQUIRED
            reason = "Matched national ID but conflicting phone requires review."
            auto = False
        elif "phone_number" in matched and compatible_name and not conflicts:
            status = ResolutionStatus.MATCHED
            reason = "Exact normalized phone plus compatible name with no verified conflict."
            auto = True
        elif strong >= 2 and not conflicts:
            status = ResolutionStatus.MATCHED
            reason = "At least two independent strong corroborating fields."
            auto = True
        elif conflicts:
            if compatible_name or strong > 0:
                status = ResolutionStatus.REVIEW_REQUIRED
                reason = "Conflicting or ambiguous evidence requires human review."
                auto = False
            else:
                status = ResolutionStatus.NOT_MATCHED
                reason = "Strong contradictory identifiers."
                auto = False
        elif name_alone:
            status = ResolutionStatus.REVIEW_REQUIRED
            reason = "Name alone requires human review and cannot auto-match."
            auto = False
        elif phone_alone:
            status = ResolutionStatus.REVIEW_REQUIRED
            reason = "Phone alone requires human review and cannot auto-match."
            auto = False
        elif address_alone:
            status = ResolutionStatus.REVIEW_REQUIRED
            reason = "Address alone requires human review and cannot auto-match."
            auto = False
        elif matched or best_name_score >= review_threshold:
            status = ResolutionStatus.REVIEW_REQUIRED
            reason = "Evidence requires human review."
            auto = False
        else:
            status = ResolutionStatus.NOT_MATCHED
            reason = "Available identity similarity is below the review threshold."
            auto = False

        confidence = min(1.0, max(best_name_score, 0.55 + 0.2 * len(matched)))
        decisions.append(CandidateDecision(candidate_person_id=person_id, confidence=round(confidence, 3), status=status, matched_fields=sorted(matched), conflicting_fields=sorted(conflicts), reason=reason, supporting_source_record_ids=sorted(profile.source_record_ids), auto_link_allowed=auto, requires_human_review=not auto))
    return sorted(decisions, key=lambda decision: (-decision.confidence, decision.candidate_person_id))

__all__ = ["CandidateDecision", "IdentityClaim", "decide_candidates"]
