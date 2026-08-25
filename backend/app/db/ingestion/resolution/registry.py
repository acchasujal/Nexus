"""Deterministic, non-destructive registry for identity claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.app.core.graph.algorithms.entity_resolution import clean_phone, clean_vehicle, normalize_text, phonetic_normalize
from synthetic_data.configs import stable_uuid

from ..contracts import SourceType
from .matcher import IdentityClaim


@dataclass
class IdentityProfile:
    """Claims retained for one canonical or provisional person identity."""

    person_id: str
    claims: list[IdentityClaim] = field(default_factory=list)
    aliases: set[str] = field(default_factory=set)
    source_record_ids: set[str] = field(default_factory=set)


class IdentityRegistry:
    """In-memory indexes for deterministic identity candidate generation."""

    def __init__(self) -> None:
        self.profiles: dict[str, IdentityProfile] = {}
        self.by_national_id: dict[str, set[str]] = {}
        self.by_phone: dict[str, set[str]] = {}
        self.by_vehicle: dict[str, set[str]] = {}
        self.by_name: dict[str, set[str]] = {}

    @staticmethod
    def _stable_person_id(claim: IdentityClaim) -> str:
        if claim.national_id:
            key = ("canonical", "national", claim.national_id)
        elif claim.phone_number:
            key = ("canonical", "phone", clean_phone(claim.phone_number))
        elif claim.vehicle_number:
            key = ("canonical", "vehicle", clean_vehicle(claim.vehicle_number))
        else:
            key = ("provisional", claim.source_type.value, claim.source_record_id)
        return str(stable_uuid(*key))

    def register_claim(self, claim: IdentityClaim, person_id: str | None = None) -> str:
        """Add a claim and indexes without merging existing profiles."""
        normalized = claim.normalized()
        resolved_id = person_id or self._stable_person_id(normalized)
        profile = self.profiles.setdefault(resolved_id, IdentityProfile(person_id=resolved_id))
        profile.claims.append(normalized)
        profile.aliases.update(normalize_text(alias) for alias in normalized.aliases if alias)
        profile.source_record_ids.add(normalized.source_record_id)
        if normalized.national_id:
            self.by_national_id.setdefault(normalized.national_id, set()).add(resolved_id)
        if normalized.phone_number:
            self.by_phone.setdefault(clean_phone(normalized.phone_number), set()).add(resolved_id)
        if normalized.vehicle_number:
            self.by_vehicle.setdefault(clean_vehicle(normalized.vehicle_number), set()).add(resolved_id)
        name_key = normalize_text(normalized.full_name)
        if name_key:
            self.by_name.setdefault(name_key, set()).add(resolved_id)
        return resolved_id

    def candidate_person_ids(self, claim: IdentityClaim) -> list[str]:
        """Return deterministic candidate IDs from strong and name indexes."""
        normalized = claim.normalized()
        ids: set[str] = set()
        if normalized.national_id:
            ids.update(self.by_national_id.get(normalized.national_id, set()))
        if normalized.phone_number:
            ids.update(self.by_phone.get(clean_phone(normalized.phone_number), set()))
        if normalized.vehicle_number:
            ids.update(self.by_vehicle.get(clean_vehicle(normalized.vehicle_number), set()))
        name_key = normalize_text(normalized.full_name)
        ids.update(self.by_name.get(name_key, set()))
        phonetic_key = phonetic_normalize(normalized.full_name)
        if phonetic_key:
            for name, profile_ids in self.by_name.items():
                if phonetic_normalize(name) == phonetic_key:
                    ids.update(profile_ids)
        for alias in normalized.aliases:
            alias_key = normalize_text(alias)
            ids.update(self.by_name.get(alias_key, set()))
        return sorted(ids)

    def get_profile(self, person_id: str) -> IdentityProfile:
        """Return a registered profile or raise KeyError."""
        return self.profiles[person_id]


__all__ = ["IdentityProfile", "IdentityRegistry"]
