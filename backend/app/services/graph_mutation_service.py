"""backend/app/services/graph_mutation_service.py

Authoritative Graph Mutation Service for Phase P1-C.

Strict Architectural Safeguards:
  1. No LLM Calls: Mutation logic is 100% deterministic application code.
  2. Canonical ID Compatibility: Reuses existing NEXUS ID schemes (person-XXXX, phone-XXXX, etc.).
  3. Graph Schema Compatibility: Does not inject ad-hoc badges or incompatible node properties.
  4. Deduplication & Idempotency: Existing edges receive corroborating provenance rather than duplication.
  5. Rollback Support: Allows reverting in-memory mutations if downstream steps or audits fail.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GraphMutationService:
    """Provides validated, deterministic mutations against the authoritative investigation graph."""

    def __init__(self, repository: Any) -> None:
        self.repo = repository

    # ── Canonical ID Generation ──────────────────────────────────────────────

    def generate_canonical_id(self, entity_type: str) -> str:
        """Generate a canonical entity ID matching established NEXUS graph conventions.

        Conventions:
          Person              -> person-XXXX
          Phone               -> phone-XXXX
          Account             -> account-XXXX
          Case                -> case-XXXX
          Evidence            -> evidence-XXXX
          Location            -> location-XXXX
          Vehicle             -> vehicle-XXXX
          Organization        -> org-XXXX
          IntelligenceReport  -> intel-XXXX
        """
        type_prefix_map = {
            "person": "person",
            "phone": "phone",
            "account": "account",
            "bankaccount": "account",
            "case": "case",
            "evidence": "evidence",
            "location": "location",
            "vehicle": "vehicle",
            "organization": "org",
            "device": "device",
            "intelligencereport": "intel",
        }

        clean_type = entity_type.strip().lower()
        prefix = type_prefix_map.get(clean_type, clean_type)

        pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
        max_idx = 0
        nodes = getattr(self.repo, "nodes", {})

        for node_id in nodes:
            match = pattern.match(str(node_id))
            if match:
                try:
                    idx = int(match.group(1))
                    if idx > max_idx:
                        max_idx = idx
                except ValueError:
                    pass

        return f"{prefix}-{max_idx + 1:04d}"

    def generate_edge_id(self, source_id: str, target_id: str, edge_type: str) -> str:
        """Generate a deterministic edge ID adhering to NEXUS naming conventions."""
        clean_rel = edge_type.strip().upper().replace("_", "-").lower()
        base_id = f"edge-{clean_rel}-{source_id}-{target_id}"

        # Check existing edge IDs to prevent collision
        existing_ids = {str(e.get("id")) for e in getattr(self.repo, "edges", [])}
        if base_id not in existing_ids:
            return base_id

        # Disambiguate if edge already exists with different attributes
        counter = 1
        while f"{base_id}-{counter}" in existing_ids:
            counter += 1
        return f"{base_id}-{counter}"

    # ── Authoritative Graph Mutations ────────────────────────────────────────

    def create_canonical_entity(
        self,
        entity_type: str,
        canonical_name: str,
        properties: dict[str, Any] | None = None,
        document_id: str | None = None,
        case_id: str | None = None,
        officer_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new authoritative canonical entity in the graph.

        Deterministic, schema-compliant, and fully provenance-backed.
        """
        canonical_id = self.generate_canonical_id(entity_type)
        props: dict[str, Any] = dict(properties or {})

        # Standardize primary naming fields per schema
        clean_type = entity_type.strip().capitalize()
        if clean_type in ("Person", "Officer"):
            props.setdefault("full_name", canonical_name)
            props.setdefault("aliases", [])
        elif clean_type in ("Location", "Organization"):
            props.setdefault("name", canonical_name)
        elif clean_type == "Phone":
            props.setdefault("phone_number", canonical_name)
        elif clean_type in ("Account", "Bankaccount"):
            props.setdefault("account_number", canonical_name)
        elif clean_type == "Vehicle":
            props.setdefault("registration_number", canonical_name)
        else:
            props.setdefault("name", canonical_name)

        if case_id:
            props.setdefault("case_id", case_id)

        node_dict: dict[str, Any] = {
            "id": canonical_id,
            "entity_type": clean_type,
            "properties": props,
        }

        # Insert into repository
        self.repo.nodes[canonical_id] = node_dict
        if hasattr(self.repo, "_rebuild_indexes"):
            self.repo._rebuild_indexes()

        logger.info(
            "Created authoritative canonical entity %s (%s) by officer %s",
            canonical_id,
            clean_type,
            officer_id,
        )
        return node_dict

    def link_candidate_to_entity(
        self,
        canonical_id: str,
        candidate_entity: dict[str, Any],
        document_id: str,
        case_id: str | None = None,
        officer_id: str | None = None,
    ) -> dict[str, Any]:
        """Link a candidate entity extraction to an existing authoritative graph node.

        Safely enriches aliases and case associations without introducing arbitrary schema fields.
        """
        nodes = getattr(self.repo, "nodes", {})
        if canonical_id not in nodes:
            raise KeyError(f"Target canonical entity '{canonical_id}' does not exist in graph")

        node = nodes[canonical_id]
        props = node.setdefault("properties", {})

        # Enrich aliases if candidate surface text is novel
        surface_text = candidate_entity.get("surface_text", "").strip()
        if surface_text:
            existing_aliases = props.setdefault("aliases", [])
            primary_name = props.get("full_name") or props.get("name") or ""
            if surface_text != primary_name and surface_text not in existing_aliases:
                existing_aliases.append(surface_text)

        # Update case_id if absent
        effective_case = case_id or candidate_entity.get("case_id")
        if effective_case:
            if "case_ids" in props and isinstance(props["case_ids"], list):
                if effective_case not in props["case_ids"]:
                    props["case_ids"].append(effective_case)
            elif "case_id" not in props:
                props["case_id"] = effective_case

        if hasattr(self.repo, "_rebuild_indexes"):
            self.repo._rebuild_indexes()

        logger.info(
            "Linked candidate %s to canonical entity %s by officer %s",
            candidate_entity.get("candidate_id"),
            canonical_id,
            officer_id,
        )
        return node

    def create_authoritative_relationship(
        self,
        source_id: str,
        target_id: str,
        edge_type: str,
        properties: dict[str, Any] | None = None,
        document_id: str | None = None,
        case_id: str | None = None,
        officer_id: str | None = None,
    ) -> dict[str, Any]:
        """Create or corroborate an authoritative relationship edge in the graph.

        Prerequisites: Both source and target must exist as authoritative nodes.
        Deduplication: If an edge already exists between source and target with the same type,
        appends corroborating provenance rather than duplicating the link.
        """
        nodes = getattr(self.repo, "nodes", {})
        if source_id not in nodes:
            raise ValueError(f"Source entity '{source_id}' does not exist in authoritative graph")
        if target_id not in nodes:
            raise ValueError(f"Target entity '{target_id}' does not exist in authoritative graph")

        edges = getattr(self.repo, "edges", [])
        norm_type = edge_type.strip().upper()
        now_iso = _utcnow().isoformat()

        # Check for existing duplicate edge
        for existing in edges:
            if (
                str(existing.get("source_id")) == source_id
                and str(existing.get("target_id")) == target_id
                and str(existing.get("edge_type", "")).upper() == norm_type
            ):
                # Edge already exists -> corroborate provenance
                edge_props = existing.setdefault("properties", {})
                corroborations = edge_props.setdefault("corroborating_evidence", [])
                corroborations.append({
                    "document_id": document_id,
                    "case_id": case_id,
                    "confirmed_by": officer_id,
                    "confirmed_at": now_iso,
                })
                if hasattr(self.repo, "_rebuild_indexes"):
                    self.repo._rebuild_indexes()
                logger.info(
                    "Corroborated existing edge %s (%s -> %s) by officer %s",
                    existing.get("id"),
                    source_id,
                    target_id,
                    officer_id,
                )
                return existing

        # Create new edge
        edge_id = self.generate_edge_id(source_id, target_id, norm_type)
        new_edge: dict[str, Any] = {
            "id": edge_id,
            "source_id": source_id,
            "target_id": target_id,
            "edge_type": norm_type,
            "weight": 1.0,
            "confidence": 1.0,
            "derivation_class": "FACT",
            "properties": dict(properties or {}),
            "provenance": {
                "source_type": "DOCUMENT",
                "source_id": document_id or "UNKNOWN",
                "timestamp": now_iso,
                "extracted_fact": f"Investigator confirmed relationship from document {document_id or 'evidence'}",
                "derivation_method": "INVESTIGATOR_CONFIRMATION",
                "confidence": 1.0,
            },
        }

        if hasattr(self.repo, "edges"):
            self.repo.edges.append(new_edge)
        if hasattr(self.repo, "_rebuild_indexes"):
            self.repo._rebuild_indexes()

        logger.info(
            "Created authoritative edge %s (%s -[%s]-> %s) by officer %s",
            edge_id,
            source_id,
            norm_type,
            target_id,
            officer_id,
        )
        return new_edge

    # ── Rollback Helper ──────────────────────────────────────────────────────

    def rollback_entity_creation(self, node_id: str) -> None:
        """Revert node creation if subsequent transaction steps fail."""
        nodes = getattr(self.repo, "nodes", {})
        if node_id in nodes:
            del nodes[node_id]
            if hasattr(self.repo, "_rebuild_indexes"):
                self.repo._rebuild_indexes()
            logger.warning("Rolled back entity creation for node %s", node_id)

    def rollback_edge_creation(self, edge_id: str) -> None:
        """Revert edge creation if subsequent transaction steps fail."""
        edges = getattr(self.repo, "edges", [])
        self.repo.edges = [e for e in edges if str(e.get("id")) != edge_id]
        if hasattr(self.repo, "_rebuild_indexes"):
            self.repo._rebuild_indexes()
        logger.warning("Rolled back edge creation for edge %s", edge_id)
