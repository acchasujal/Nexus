"""backend/app/core/graph/algorithms/cross_case.py

Deterministic Cross-Case Bridge Detection for NEXUS (Schema V2).

Cross-case bridge analysis identifies canonical entities (Person, Phone, Account, Vehicle,
Location, Organization, Device, etc.) that create source-backed connections between otherwise
separate investigation cases.

Design Non-Negotiables:
1. Operates over the HETEROGENEOUS investigation graph (GraphStore). Does NOT mutate Person-Only projection or GraphStore.
2. Requires canonical entity identity + source-backed evidence per case association.
   If case association lacks provenance, it is SUPPRESSED.
3. Minimum 2 distinct cases required (Case A + Case B). Same case count = 1 is ignored.
4. Aggregates multiple cases for the same entity into ONE deterministic finding.
5. Zero predictive guilt / criminality / mastermind scoring.
6. 100% deterministic output ordering.
"""

from __future__ import annotations

from typing import Any

from backend.app.core.graph.algorithms.pattern_rules import (
    PatternFinding,
    _extract_edge_evidence_ids,
    _extract_node_evidence_ids,
)
from backend.app.core.graph.algorithms.utils import GraphStore
from backend.app.core.graph.enums import GraphEntityType, GraphRelationshipType

EXCLUDED_ENTITY_TYPES = {
    GraphEntityType.CASE.value,
    GraphEntityType.SOURCE_RECORD.value,
    "Case",
    "SourceRecord",
}


def _get_node_label(node: Any) -> str:
    """Helper to retrieve human-readable canonical label or name of a node."""
    if hasattr(node, "canonical_label") and node.canonical_label:
        return str(node.canonical_label)
    props = getattr(node, "properties", {}) or {}
    if "properties" in props and isinstance(props["properties"], dict):
        props = {**props, **props["properties"]}
    return (
        props.get("canonical_label")
        or props.get("name")
        or props.get("full_name")
        or props.get("title")
        or getattr(node, "id", "")
        or getattr(node, "node_id", "")
    )


def detect_cross_case_bridges(
    store: GraphStore,
    min_cases: int = 2,
) -> list[PatternFinding]:
    """
    Detect canonical entities connecting 2 or more distinct investigation cases
    with source-backed evidence.

    Parameters
    ----------
    store : GraphStore
        Input heterogeneous investigation graph.
    min_cases : int, default 2
        Minimum distinct cases required for a cross-case bridge finding.

    Returns
    -------
    list[PatternFinding]
        Deterministic list of PatternFinding objects with rule_id='cross_case_bridge'.
    """
    # Map: entity_id -> dict[case_id -> dict("edge_ids": set, "evidence_ids": set)]
    entity_case_map: dict[str, dict[str, dict[str, set[str]]]] = {}

    case_types = {GraphEntityType.CASE.value, "Case"}
    source_record_types = {GraphEntityType.SOURCE_RECORD.value, "SourceRecord"}

    # Canonical relationship types that establish direct Case membership
    valid_direct_case_rel_types = {
        GraphRelationshipType.INVOLVED_IN.value,
        GraphRelationshipType.ACCUSED_IN.value,
        GraphRelationshipType.VICTIM_IN.value,
        GraphRelationshipType.COMPLAINANT_IN.value,
        GraphRelationshipType.WITNESS_IN.value,
        GraphRelationshipType.INVESTIGATED_BY.value,
        GraphRelationshipType.PARTICIPATED_IN.value,
        GraphRelationshipType.MENTIONED_IN.value,
        GraphRelationshipType.HAS_EVIDENCE.value,
        "INVOLVED_IN",
        "ACCUSED_IN",
        "VICTIM_IN",
        "COMPLAINANT_IN",
        "WITNESS_IN",
        "INVESTIGATED_BY",
        "PARTICIPATED_IN",
        "MENTIONED_IN",
        "HAS_EVIDENCE",
    }

    for etype in sorted(store.edge_index.keys()):
        for edge in store.edge_index[etype]:
            src_node = store.nodes.get(edge.source_id)
            tgt_node = store.nodes.get(edge.target_id)

            if not src_node or not tgt_node:
                continue

            # Direct Case <-> Entity relationship (must be a valid case relationship type)
            if etype in valid_direct_case_rel_types:
                entity_node = None
                case_node = None

                if src_node.entity_type in case_types and tgt_node.entity_type not in EXCLUDED_ENTITY_TYPES:
                    case_node = src_node
                    entity_node = tgt_node
                elif tgt_node.entity_type in case_types and src_node.entity_type not in EXCLUDED_ENTITY_TYPES:
                    case_node = tgt_node
                    entity_node = src_node

                if entity_node and case_node:
                    entity_id = getattr(entity_node, "node_id", getattr(entity_node, "id", None))
                    case_id = getattr(case_node, "node_id", getattr(case_node, "id", None))

                    if entity_id and case_id:
                        props = getattr(edge, "properties", {}) or {}
                        if "properties" in props and isinstance(props["properties"], dict):
                            props = {**props, **props["properties"]}

                        edge_id = (
                            props.get("id")
                            or getattr(edge, "id", None)
                            or f"rel_{edge.source_id}_{edge.edge_type}_{edge.target_id}"
                        )

                        # Extract relationship evidence + node evidence
                        ev_ids = _extract_edge_evidence_ids(edge, store)
                        ev_ids.update(_extract_node_evidence_ids(case_node, store))
                        ev_ids.update(_extract_node_evidence_ids(entity_node, store))

                        # Track association
                        if entity_id not in entity_case_map:
                            entity_case_map[entity_id] = {}

                        if case_id not in entity_case_map[entity_id]:
                            entity_case_map[entity_id][case_id] = {"edge_ids": set(), "evidence_ids": set()}

                        entity_case_map[entity_id][case_id]["edge_ids"].add(edge_id)
                        entity_case_map[entity_id][case_id]["evidence_ids"].update(ev_ids)
                        continue

            # Secondary path: Entity <-> SourceRecord <-> Case
            elif src_node.entity_type in source_record_types and tgt_node.entity_type not in EXCLUDED_ENTITY_TYPES:
                sr_node = src_node
                e_node = tgt_node
                _link_entity_via_sourcerecord(e_node, sr_node, edge, store, entity_case_map)
            elif tgt_node.entity_type in source_record_types and src_node.entity_type not in EXCLUDED_ENTITY_TYPES:
                sr_node = tgt_node
                e_node = src_node
                _link_entity_via_sourcerecord(e_node, sr_node, edge, store, entity_case_map)

    findings: list[PatternFinding] = []

    # Evaluate candidate bridge entities
    for entity_id in sorted(entity_case_map.keys()):
        entity_node = store.nodes.get(entity_id)
        if not entity_node:
            continue

        case_dict = entity_case_map[entity_id]

        # Filter case associations to strictly EVIDENCE-BACKED cases
        valid_case_ids: list[str] = []
        all_edge_ids: set[str] = set()
        all_evidence_ids: set[str] = set()

        for case_id in sorted(case_dict.keys()):
            assoc = case_dict[case_id]
            # MANDATORY PROVENANCE REQUIREMENT: Association must be source-backed
            if assoc["evidence_ids"]:
                valid_case_ids.append(case_id)
                all_edge_ids.update(assoc["edge_ids"])
                all_evidence_ids.update(assoc["evidence_ids"])

        # Check distinct case count requirement (min_cases >= 2)
        if len(valid_case_ids) < min_cases:
            continue

        sorted_case_ids = sorted(valid_case_ids)
        sorted_edge_ids = sorted(all_edge_ids)
        sorted_evidence_ids = sorted(all_evidence_ids)

        etype_label = str(entity_node.entity_type)
        if hasattr(entity_node.entity_type, "value"):
            etype_label = entity_node.entity_type.value

        label = _get_node_label(entity_node)
        cases_str = ", ".join(sorted_case_ids)

        explanation = (
            f"{etype_label} '{label}' is supported by source-backed relationships across cases "
            f"({cases_str}), creating a cross-case bridge."
        )

        findings.append(
            PatternFinding(
                rule_id="cross_case_bridge",
                explanation=explanation,
                entity_ids=[entity_id],
                case_ids=sorted_case_ids,
                edge_ids=sorted_edge_ids,
                evidence_ids=sorted_evidence_ids,
                derivation_class="DERIVED",
                severity="HIGH" if len(sorted_case_ids) >= 3 else "MEDIUM",
            )
        )

    # Deterministic sorting: by entity_type, entity_id, first case_id
    findings.sort(
        key=lambda f: (
            store.nodes[f.entity_ids[0]].entity_type if f.entity_ids[0] in store.nodes else "",
            f.entity_ids[0],
            f.case_ids[0] if f.case_ids else "",
        )
    )
    return findings


def _link_entity_via_sourcerecord(
    entity_node: Any,
    sr_node: Any,
    edge: Any,
    store: GraphStore,
    entity_case_map: dict[str, dict[str, dict[str, set[str]]]],
) -> None:
    """Helper to link an entity to cases via SourceRecord metadata or SourceRecord -> Case graph edges."""
    entity_id = getattr(entity_node, "node_id", getattr(entity_node, "id", None))
    sr_id = getattr(sr_node, "node_id", getattr(sr_node, "id", None))

    if not entity_id or not sr_id:
        return

    sr_props = getattr(sr_node, "properties", {}) or {}
    if "properties" in sr_props and isinstance(sr_props["properties"], dict):
        sr_props = {**sr_props, **sr_props["properties"]}

    linked_case_ids: set[str] = set()

    for k in ("case_id", "case_number", "fir_number"):
        val = sr_props.get(k)
        if val:
            linked_case_ids.add(str(val))

    # Also check graph edges from SourceRecord -> Case
    for etype in sorted(store.edge_index.keys()):
        for case_edge in store.edge_index[etype]:
            if case_edge.source_id == sr_id:
                target = store.nodes.get(case_edge.target_id)
                if target and target.entity_type in (GraphEntityType.CASE.value, "Case"):
                    linked_case_ids.add(case_edge.target_id)
            elif case_edge.target_id == sr_id:
                src = store.nodes.get(case_edge.source_id)
                if src and src.entity_type in (GraphEntityType.CASE.value, "Case"):
                    linked_case_ids.add(case_edge.source_id)

    if not linked_case_ids:
        return

    props = getattr(edge, "properties", {}) or {}
    if "properties" in props and isinstance(props["properties"], dict):
        props = {**props, **props["properties"]}

    edge_id = props.get("id") or getattr(edge, "id", None) or f"rel_{edge.source_id}_{edge.edge_type}_{edge.target_id}"

    ev_ids = _extract_edge_evidence_ids(edge, store)
    ev_ids.add(sr_id)

    if entity_id not in entity_case_map:
        entity_case_map[entity_id] = {}

    for case_id in sorted(linked_case_ids):
        if case_id not in entity_case_map[entity_id]:
            entity_case_map[entity_id][case_id] = {"edge_ids": set(), "evidence_ids": set()}

        entity_case_map[entity_id][case_id]["edge_ids"].add(edge_id)
        entity_case_map[entity_id][case_id]["evidence_ids"].update(ev_ids)
