"""backend/app/ai/entity_resolver.py

Deterministic normalization layer for extracted AI intent entities.
Converts user-friendly natural language values into canonical graph values
before dispatching to GraphService.
"""

from __future__ import annotations

import re
from typing import Final

from backend.app.ai.schemas import Entity, Intent

# ── Canonical Dictionary & Alias Mappings ─────────────────────────────────────

_CANONICAL_POLICE_STATIONS: Final[tuple[str, ...]] = (
    "Ashok Nagar",
    "Jayanagar",
    "Malleshwaram",
    "Mysuru North",
    "Mysuru South",
    "Nanjangud",
    "Mangaluru North",
    "Mangaluru South",
    "Bantwal",
    "Belagavi North",
    "Belagavi South",
    "Bailhongal",
    "Hubballi Town",
    "Dharwad Town",
    "Navalgund",
    "Kalaburagi North",
    "Kalaburagi South",
    "Sedam",
)

_DISTRICT_ALIASES: Final[dict[str, str]] = {
    "bangalore": "Bengaluru City",
    "bengaluru": "Bengaluru City",
    "bengaluru city": "Bengaluru City",
    "mysore": "Mysuru",
    "mysuru": "Mysuru",
    "mangaluru": "Mangaluru",
    "mangalore": "Mangaluru",
    "belgaum": "Belagavi",
    "belagavi": "Belagavi",
    "hubballi": "Hubballi-Dharwad",
    "dharwad": "Hubballi-Dharwad",
    "hubballi-dharwad": "Hubballi-Dharwad",
    "kalaburagi": "Kalaburagi",
    "gulbarga": "Kalaburagi",
}

_OFFENCE_CATEGORY_ALIASES: Final[dict[str, str]] = {
    "vehicle theft": "vehicle_theft",
    "vehicle_theft": "vehicle_theft",
    "auto theft": "vehicle_theft",
    "cyber fraud": "cyber_fraud",
    "cyber_fraud": "cyber_fraud",
    "online fraud": "cyber_fraud",
    "theft": "theft",
    "fraud": "fraud",
    "burglary": "burglary",
    "robbery": "robbery",
    "drug case": "narcotics",
    "drug": "narcotics",
    "drugs": "narcotics",
    "narcotics": "narcotics",
    "ndps": "narcotics",
    "assault": "assault",
    "public order": "public_order",
    "public_order": "public_order",
    "forgery": "forgery",
    "harassment": "harassment",
    "murder": "murder",
    "homicide": "murder",
}

_CASE_STAGE_ALIASES: Final[dict[str, str]] = {
    "pending": "further_investigation",
    "further investigation": "further_investigation",
    "further-investigation": "further_investigation",
    "further_investigation": "further_investigation",
    "under investigation": "investigation",
    "investigation": "investigation",
    "chargesheet filed": "charge_sheet_filed",
    "charge sheet filed": "charge_sheet_filed",
    "charge-sheet filed": "charge_sheet_filed",
    "chargesheet_filed": "charge_sheet_filed",
    "charge_sheet_filed": "charge_sheet_filed",
    "chargesheeted": "charge_sheet_filed",
    "completed": "charge_sheet_filed",
    "closed": "charge_sheet_filed",
    "charge sheet draft": "charge_sheet_draft",
    "chargesheet draft": "charge_sheet_draft",
    "charge_sheet_draft": "charge_sheet_draft",
}

_POLICE_STATION_REGEX: Final[re.Pattern] = re.compile(
    r"\b(police\s*station|ps)\b", re.IGNORECASE
)
_IDENTIFIER_CLEANUP_REGEX: Final[re.Pattern] = re.compile(r"\s*([/\-])\s*")


class EntityResolver:
    """Deterministic entity normalization component for CaseClock.

    Converts natural language entity values extracted by NLU into canonical graph terms.
    Does not use LLMs, QuickML, or probabilistic inference.
    """

    def resolve(self, intent: Intent) -> Intent:
        """Return a new Intent with all extracted entities resolved to canonical values."""
        normalized_entities = [
            self.resolve_entity(entity) for entity in intent.entities
        ]
        return Intent(
            name=intent.name,
            confidence=intent.confidence,
            entities=normalized_entities,
        )

    def resolve_entity(self, entity: Entity) -> Entity:
        """Resolve a single entity to its canonical graph representation."""
        val = str(entity.value).strip()
        etype = entity.type

        if etype == "police_station":
            norm_val = self.normalize_police_station(val)
        elif etype == "district":
            norm_val = self.normalize_district(val)
        elif etype == "offence_category":
            norm_val = self.normalize_offence_category(val)
        elif etype == "case_stage":
            norm_val = self.normalize_case_stage(val)
        elif etype == "risk_band":
            norm_val = self.normalize_risk_band(val)
        elif etype in ("fir_number", "case_number", "case_id"):
            norm_val = self.normalize_identifier(val)
        else:
            norm_val = val

        return Entity(
            type=etype,
            value=norm_val,
        )

    def normalize_police_station(self, val: str) -> str:
        """Normalize police station variations to canonical station names.

        Examples:
            "Ashok Nagar Police Station" -> "Ashok Nagar"
            "Ashok Nagar PS" -> "Ashok Nagar"
            "PS Ashok Nagar" -> "Ashok Nagar"
        """
        cleaned = val.strip()
        cleaned = _POLICE_STATION_REGEX.sub("", cleaned).strip()
        cleaned = " ".join(cleaned.split())

        lower_cleaned = cleaned.lower()
        for canonical in _CANONICAL_POLICE_STATIONS:
            if canonical.lower() == lower_cleaned:
                return canonical

        return cleaned if cleaned else val

    def normalize_district(self, val: str) -> str:
        """Normalize district names to canonical graph districts.

        Examples:
            "Bangalore" -> "Bengaluru City"
            "Bengaluru" -> "Bengaluru City"
            "Belgaum" -> "Belagavi"
        """
        cleaned = val.strip()
        lower_cleaned = cleaned.lower()
        return _DISTRICT_ALIASES.get(lower_cleaned, cleaned)

    def normalize_offence_category(self, val: str) -> str:
        """Normalize offence category names to canonical graph snake_case values.

        Examples:
            "Vehicle Theft" -> "vehicle_theft"
            "cyber fraud" -> "cyber_fraud"
            "drug case" -> "narcotics"
        """
        cleaned = val.strip()
        lower_cleaned = " ".join(
            cleaned.lower().replace("-", " ").replace("_", " ").split()
        )
        if lower_cleaned in _OFFENCE_CATEGORY_ALIASES:
            return _OFFENCE_CATEGORY_ALIASES[lower_cleaned]
        return cleaned.lower().replace(" ", "_")

    def normalize_case_stage(self, val: str) -> str:
        """Normalize case stage descriptions to canonical graph stage values.

        Examples:
            "pending" -> "further_investigation"
            "completed" -> "charge_sheet_filed"
            "chargesheet filed" -> "charge_sheet_filed"
        """
        cleaned = val.strip()
        lower_cleaned = " ".join(
            cleaned.lower().replace("-", " ").replace("_", " ").split()
        )
        if lower_cleaned in _CASE_STAGE_ALIASES:
            return _CASE_STAGE_ALIASES[lower_cleaned]
        return cleaned

    def normalize_risk_band(self, val: str) -> str:
        """Normalize risk band values to canonical lowercase strings.

        Examples:
            "RED" -> "red"
            "Green" -> "green"
        """
        cleaned = val.strip().lower()
        if cleaned in ("green", "amber", "red", "overdue"):
            return cleaned
        return val.strip()

    def normalize_identifier(self, val: str) -> str:
        """Normalize formatting and whitespace for FIR and case numbers.

        Examples:
            " fir / bel / 0064 " -> "FIR/BEL/0064"
            "cc - 0043" -> "CC-0043"
        """
        cleaned = val.strip()
        cleaned = _IDENTIFIER_CLEANUP_REGEX.sub(r"\1", cleaned)

        parts = cleaned.split("/")
        if len(parts) > 1:
            normalized_parts = [
                p.upper() if not p.isdigit() else p for p in parts
            ]
            return "/".join(normalized_parts)
        return cleaned.upper()
