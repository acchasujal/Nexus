"""backend/app/core/graph/algorithms/pattern_rules.py

Deterministic, Explainable Suspicious-Pattern Detection Rules for NEXUS (Schema V2).

Developer Documentation:
1. Rule #1 — Shared Phone / Device (shared_phone_device):
   Detects multiple Person entities associated with the same Phone or Device node.

2. Rule #2 — Communication Burst Near an Event (communication_burst_near_event):
   Detects an unusually concentrated burst of Person-to-Person communications
   within a defined temporal window (+/- 15 minutes) around a known Event node.

3. Rule #3 — Circular / Repeated Financial Flow (circular_repeated_financial_flow):
   Detects directed circular transfer paths (A -> B -> C -> A) or repeated high-volume
   transfers in the financial subgraph.

Safety & Contract Non-Negotiables:
- All findings are structural derived findings (derivation_class = "DERIVED").
- ZERO predictive guilt scoring (no criminal_score, guilt_score, mastermind_score,
  or criminal_probability).
- Every finding contains real evidence_ids resolved from source_record_id or CITES_SOURCE graph edges.
  Findings lacking source evidence are suppressed.
- 100% deterministic output ordering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, List, Set

try:
    import networkx as nx  # type: ignore[import]
    _NX_AVAILABLE = True
except ImportError:  # pragma: no cover
    nx = None  # type: ignore[assignment]
    _NX_AVAILABLE = False

from backend.app.core.graph.algorithms.utils import GraphStore
from backend.app.core.graph.enums import GraphEntityType, GraphRelationshipType

# Configurable defaults for Rule #2 (Communication Burst)
DEFAULT_COMMUNICATION_BURST_WINDOW_MINUTES: int = 15
DEFAULT_COMMUNICATION_BURST_MIN_CALLS: int = 3

# Configurable defaults for Rule #3 (Financial Cycle & Repeated Flow)
DEFAULT_FINANCIAL_MIN_CYCLE_LENGTH: int = 3
DEFAULT_FINANCIAL_MIN_REPEATED_TRANSFERS: int = 3


@dataclass
class PatternFinding:
    """
    Typed, explainable structural pattern finding.

    Attributes
    ----------
    rule_id : str
        Unique rule identifier ('shared_phone_device', 'communication_burst_near_event',
        'circular_repeated_financial_flow').
    explanation : str
        Deterministic natural language structural explanation (no LLM, no guilt bias).
    entity_ids : list[str]
        IDs of nodes involved in the pattern.
    edge_ids : list[str]
        IDs of edges/relationships involved in the pattern.
    evidence_ids : list[str]
        Source record / evidence IDs backing the underlying graph relationships.
    derivation_class : str
        Always "DERIVED" for rule-based findings.
    severity : str
        Severity level ("MEDIUM", "HIGH", "CRITICAL").
    """

    rule_id: str
    explanation: str
    entity_ids: list[str]
    edge_ids: list[str]
    evidence_ids: list[str]
    derivation_class: str = "DERIVED"
    severity: str = "MEDIUM"


def _extract_edge_evidence_ids(edge: Any, store: GraphStore | None = None) -> set[str]:
    """
    Extract real source record IDs from a relationship object or CITES_SOURCE graph edges.
    Does NOT fabricate IDs.
    """
    evidence_ids: set[str] = set()

    # 1. Direct attribute on Relationship model
    if hasattr(edge, "source_record_id") and edge.source_record_id:
        evidence_ids.add(str(edge.source_record_id))

    # 2. Properties dictionary
    props = getattr(edge, "properties", {}) or {}
    if "properties" in props and isinstance(props["properties"], dict):
        props = {**props, **props["properties"]}

    if props.get("source_record_id"):
        evidence_ids.add(str(props["source_record_id"]))

    prov = props.get("provenance")
    if isinstance(prov, dict) and prov.get("source_record_id"):
        evidence_ids.add(str(prov["source_record_id"]))
    elif hasattr(prov, "source_record_id") and getattr(prov, "source_record_id", None):
        evidence_ids.add(str(getattr(prov, "source_record_id")))

    # 3. Canonical CITES_SOURCE graph edges connecting relationship -> SourceRecord
    if store is not None:
        edge_id = props.get("id") or getattr(edge, "id", None)
        if edge_id:
            cites_type = GraphRelationshipType.CITES_SOURCE.value
            for cites_edge in store.edge_index.get(cites_type, []):
                if cites_edge.source_id == edge_id:
                    target_node = store.nodes.get(cites_edge.target_id)
                    if target_node and target_node.entity_type in (
                        GraphEntityType.SOURCE_RECORD.value,
                        "SourceRecord",
                    ):
                        evidence_ids.add(cites_edge.target_id)

    return evidence_ids


def _extract_node_evidence_ids(node: Any, store: GraphStore | None = None) -> set[str]:
    """
    Extract real source record IDs for a node via source_id or CITES_SOURCE graph edges.
    """
    evidence_ids: set[str] = set()

    if hasattr(node, "source_id") and node.source_id:
        evidence_ids.add(str(node.source_id))

    props = getattr(node, "properties", {}) or {}
    if "properties" in props and isinstance(props["properties"], dict):
        props = {**props, **props["properties"]}

    if props.get("source_id"):
        evidence_ids.add(str(props["source_id"]))
    if props.get("source_record_id"):
        evidence_ids.add(str(props["source_record_id"]))

    nid = getattr(node, "node_id", None) or getattr(node, "id", None)

    # Canonical CITES_SOURCE graph edges connecting node -> SourceRecord
    if store is not None and nid:
        cites_type = GraphRelationshipType.CITES_SOURCE.value
        for cites_edge in store.edge_index.get(cites_type, []):
            if cites_edge.source_id == nid:
                target_node = store.nodes.get(cites_edge.target_id)
                if target_node and target_node.entity_type in (
                    GraphEntityType.SOURCE_RECORD.value,
                    "SourceRecord",
                ):
                    evidence_ids.add(cites_edge.target_id)

    return evidence_ids


# ── Rule 1: Shared Phone / Device ───────────────────────────────────────────────

def detect_shared_phone_device(
    store: GraphStore,
    min_persons: int = 2,
) -> list[PatternFinding]:
    """
    Detect when multiple Person entities are associated with the same Phone or Device entity.

    Parameters
    ----------
    store : GraphStore
        Input investigation graph.
    min_persons : int, default 2
        Minimum distinct Person nodes sharing the phone/device.

    Returns
    -------
    list[PatternFinding]
        Deterministic list of PatternFinding objects.
    """
    shared_map: dict[str, list[tuple[str, Any]]] = {}

    phone_device_types = {
        GraphEntityType.PHONE.value,
        GraphEntityType.DEVICE.value,
        "Phone",
        "Device",
    }

    person_types = {
        GraphEntityType.PERSON.value,
        "Person",
    }

    # Canonical V2 relationship types for phone/device associations (strictly excluding vehicles)
    valid_rel_types = {
        GraphRelationshipType.USED_PHONE.value,
        GraphRelationshipType.SHARED_PHONE.value,
    }

    for etype in sorted(store.edge_index.keys()):
        if etype not in valid_rel_types:
            continue

        for edge in store.edge_index[etype]:
            src_node = store.nodes.get(edge.source_id)
            tgt_node = store.nodes.get(edge.target_id)

            if not src_node or not tgt_node:
                continue

            person_id = None
            target_device_id = None

            if src_node.entity_type in person_types and tgt_node.entity_type in phone_device_types:
                person_id = edge.source_id
                target_device_id = edge.target_id
            elif tgt_node.entity_type in person_types and src_node.entity_type in phone_device_types:
                person_id = edge.target_id
                target_device_id = edge.source_id

            if person_id and target_device_id:
                shared_map.setdefault(target_device_id, []).append((person_id, edge))

    findings: list[PatternFinding] = []

    for device_id in sorted(shared_map.keys()):
        entries = shared_map[device_id]

        person_ids = sorted({p_id for p_id, _ in entries})
        if len(person_ids) < min_persons:
            continue

        edge_ids: set[str] = set()
        evidence_ids: set[str] = set()

        for p_id, edge in entries:
            props = getattr(edge, "properties", {}) or {}
            if "properties" in props and isinstance(props["properties"], dict):
                props = {**props, **props["properties"]}
            eid = (
                props.get("id")
                or getattr(edge, "id", None)
                or f"rel_{edge.source_id}_{edge.edge_type}_{edge.target_id}"
            )
            edge_ids.add(eid)

            ev_ids = _extract_edge_evidence_ids(edge, store)
            evidence_ids.update(ev_ids)

        # STRICT PROVENANCE REQUIREMENT: Suppress finding if no real source evidence exists
        if not evidence_ids:
            continue

        sorted_person_ids = sorted(person_ids)
        sorted_edge_ids = sorted(edge_ids)
        sorted_evidence_ids = sorted(evidence_ids)

        p_str = ", ".join(sorted_person_ids[:3]) + ("..." if len(sorted_person_ids) > 3 else "")
        explanation = (
            f"Persons ({p_str}) are associated with the same phone/device '{device_id}' "
            f"via {len(sorted_edge_ids)} relationship(s)."
        )

        findings.append(
            PatternFinding(
                rule_id="shared_phone_device",
                explanation=explanation,
                entity_ids=sorted_person_ids + [device_id],
                edge_ids=sorted_edge_ids,
                evidence_ids=sorted_evidence_ids,
                derivation_class="DERIVED",
                severity="HIGH" if len(person_ids) >= 3 else "MEDIUM",
            )
        )

    findings.sort(
        key=lambda f: (f.rule_id, tuple(f.entity_ids), tuple(f.evidence_ids), tuple(f.edge_ids))
    )
    return findings


# ── Rule 2: Communication Burst Near an Event ───────────────────────────────────

def _parse_timestamp(ts_val: Any) -> datetime | None:
    """Helper to parse ISO-8601 string or datetime into UTC datetime."""
    if isinstance(ts_val, datetime):
        return ts_val if ts_val.tzinfo else ts_val.replace(tzinfo=timezone.utc)
    if isinstance(ts_val, str) and ts_val:
        try:
            dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def detect_communication_burst_near_event(
    store: GraphStore,
    window_minutes: int = DEFAULT_COMMUNICATION_BURST_WINDOW_MINUTES,
    min_calls: int = DEFAULT_COMMUNICATION_BURST_MIN_CALLS,
) -> list[PatternFinding]:
    """
    Detect unusually concentrated bursts of communications inside a time window
    around a known Event node.

    Parameters
    ----------
    store : GraphStore
        Input investigation graph.
    window_minutes : int, default 15
        Time window (+/- minutes) around event timestamp.
    min_calls : int, default 3
        Minimum communication edges required within window.

    Returns
    -------
    list[PatternFinding]
        Deterministic list of PatternFinding objects.
    """
    event_types = {GraphEntityType.EVENT.value, "Event"}
    comm_types = {
        GraphRelationshipType.COMMUNICATED_WITH.value,
        GraphRelationshipType.CONNECTED_TO.value,
    }

    # 1. Collect Event nodes with valid timestamps
    events: list[tuple[str, datetime, Any]] = []
    for nid in sorted(store.nodes.keys()):
        node = store.nodes[nid]
        if node.entity_type in event_types:
            props = getattr(node, "properties", {}) or {}
            if "properties" in props and isinstance(props["properties"], dict):
                props = {**props, **props["properties"]}

            ts_val = (
                props.get("timestamp")
                or props.get("occurred_at")
                or props.get("event_time")
            )
            parsed_dt = _parse_timestamp(ts_val)
            if parsed_dt:
                events.append((nid, parsed_dt, node))

    if not events:
        return []

    # 2. Collect communication edges with valid timestamps
    comm_edges: list[tuple[datetime, Any]] = []
    for etype in sorted(store.edge_index.keys()):
        if etype in comm_types:
            for edge in store.edge_index[etype]:
                props = getattr(edge, "properties", {}) or {}
                if "properties" in props and isinstance(props["properties"], dict):
                    props = {**props, **props["properties"]}

                ts_val = (
                    props.get("start_time")
                    or props.get("timestamp")
                    or props.get("occurred_at")
                )
                parsed_dt = _parse_timestamp(ts_val)
                if parsed_dt:
                    comm_edges.append((parsed_dt, edge))

    if not comm_edges:
        return []

    findings: list[PatternFinding] = []
    window_delta = timedelta(minutes=window_minutes)

    # 3. For each event, evaluate communication burst
    for event_id, event_dt, event_node in events:
        window_start = event_dt - window_delta
        window_end = event_dt + window_delta

        matching_edges = []
        matching_persons: set[str] = set()
        evidence_ids: set[str] = set()

        # Check event's canonical evidence
        evidence_ids.update(_extract_node_evidence_ids(event_node, store))

        for comm_dt, edge in comm_edges:
            if window_start <= comm_dt <= window_end:
                matching_edges.append(edge)
                matching_persons.add(edge.source_id)
                matching_persons.add(edge.target_id)

                evidence_ids.update(_extract_edge_evidence_ids(edge, store))

        if len(matching_edges) >= min_calls:
            # STRICT PROVENANCE REQUIREMENT: Suppress if no real source evidence present
            if not evidence_ids:
                continue

            sorted_persons = sorted(matching_persons)
            sorted_edge_ids = sorted({
                (getattr(e, "properties", {}) or {}).get("id")
                or getattr(e, "id", None)
                or f"rel_{e.source_id}_{e.edge_type}_{e.target_id}"
                for e in matching_edges
            })
            sorted_evidence_ids = sorted(evidence_ids)

            explanation = (
                f"{len(matching_edges)} communication record(s) involving persons ({', '.join(sorted_persons[:3])}) "
                f"occurred within {window_minutes} minutes of event '{event_id}' at {event_dt.isoformat()}."
            )

            findings.append(
                PatternFinding(
                    rule_id="communication_burst_near_event",
                    explanation=explanation,
                    entity_ids=sorted_persons + [event_id],
                    edge_ids=sorted_edge_ids,
                    evidence_ids=sorted_evidence_ids,
                    derivation_class="DERIVED",
                    severity="HIGH" if len(matching_edges) >= 5 else "MEDIUM",
                )
            )

    findings.sort(
        key=lambda f: (f.rule_id, tuple(f.entity_ids), tuple(f.evidence_ids), tuple(f.edge_ids))
    )
    return findings


# ── Rule 3: Circular / Repeated Financial Flow ──────────────────────────────────

def _rotate_to_canonical_min(cycle: list[str]) -> tuple[str, ...]:
    """Rotate a node cycle list so that the lexicographically smallest node is first."""
    if not cycle:
        return ()
    min_idx = cycle.index(min(cycle))
    return tuple(cycle[min_idx:] + cycle[:min_idx])


def detect_circular_repeated_financial_flow(
    store: GraphStore,
    min_cycle_length: int = DEFAULT_FINANCIAL_MIN_CYCLE_LENGTH,
    min_repeated_transfers: int = DEFAULT_FINANCIAL_MIN_REPEATED_TRANSFERS,
) -> list[PatternFinding]:
    """
    Detect directed circular financial transfer paths (A -> B -> C -> A) or repeated
    financial transfers in the financial subgraph.

    Parameters
    ----------
    store : GraphStore
        Input investigation graph.
    min_cycle_length : int, default 3
        Minimum distinct account/person nodes in a circular flow.
    min_repeated_transfers : int, default 3
        Minimum repeated transfer edges between the same pair of nodes.

    Returns
    -------
    list[PatternFinding]
        Deterministic list of PatternFinding objects.
    """
    # Canonical V2 financial relationship types
    fin_rel_types = {
        GraphRelationshipType.TRANSFERRED_FUNDS.value,
        GraphRelationshipType.TRANSFERRED_TO.value,
    }

    fin_edges: list[Any] = []
    pair_transfers: dict[tuple[str, str], list[Any]] = {}

    for etype in sorted(store.edge_index.keys()):
        if etype in fin_rel_types:
            for edge in store.edge_index[etype]:
                # Self-loops explicitly ignored for financial transfer flow analysis
                if edge.source_id == edge.target_id:
                    continue

                fin_edges.append(edge)
                pair_transfers.setdefault((edge.source_id, edge.target_id), []).append(edge)

    if not fin_edges:
        return []

    findings: list[PatternFinding] = []
    seen_canonical_cycles: set[tuple[str, ...]] = set()

    # 1. Circular Flow Detection using NetworkX simple_cycles
    if _NX_AVAILABLE:
        G_fin = nx.DiGraph()
        for edge in fin_edges:
            G_fin.add_edge(edge.source_id, edge.target_id)

        try:
            cycles = list(nx.simple_cycles(G_fin))
        except Exception:
            cycles = []

        for cyc in cycles:
            if len(cyc) < min_cycle_length:
                continue

            canonical_cyc = _rotate_to_canonical_min(cyc)
            if canonical_cyc in seen_canonical_cycles:
                continue
            seen_canonical_cycles.add(canonical_cyc)

            cycle_edge_ids: set[str] = set()
            cycle_evidence_ids: set[str] = set()

            for i in range(len(cyc)):
                src = cyc[i]
                tgt = cyc[(i + 1) % len(cyc)]
                edges_between = pair_transfers.get((src, tgt), [])
                for edge in edges_between:
                    props = getattr(edge, "properties", {}) or {}
                    if "properties" in props and isinstance(props["properties"], dict):
                        props = {**props, **props["properties"]}
                    eid = (
                        props.get("id")
                        or getattr(edge, "id", None)
                        or f"rel_{edge.source_id}_{edge.edge_type}_{edge.target_id}"
                    )
                    cycle_edge_ids.add(eid)

                    cycle_evidence_ids.update(_extract_edge_evidence_ids(edge, store))

            # Suppress finding if no real source evidence exists
            if not cycle_evidence_ids:
                continue

            sorted_entity_ids = sorted(cyc)
            sorted_edge_ids = sorted(cycle_edge_ids)
            sorted_evidence_ids = sorted(cycle_evidence_ids)

            path_str = " -> ".join(cyc) + f" -> {cyc[0]}"
            explanation = (
                f"Observed circular financial flow path across accounts ({path_str}) "
                f"involving {len(sorted_edge_ids)} transfer relationship(s). Requires investigator review."
            )

            findings.append(
                PatternFinding(
                    rule_id="circular_repeated_financial_flow",
                    explanation=explanation,
                    entity_ids=sorted_entity_ids,
                    edge_ids=sorted_edge_ids,
                    evidence_ids=sorted_evidence_ids,
                    derivation_class="DERIVED",
                    severity="HIGH",
                )
            )

    # 2. Repeated Financial Flow Detection
    for (src, tgt), edges in sorted(pair_transfers.items()):
        if len(edges) >= min_repeated_transfers:
            rep_edge_ids: set[str] = set()
            rep_evidence_ids: set[str] = set()

            for edge in edges:
                props = getattr(edge, "properties", {}) or {}
                if "properties" in props and isinstance(props["properties"], dict):
                    props = {**props, **props["properties"]}
                eid = (
                    props.get("id")
                    or getattr(edge, "id", None)
                    or f"rel_{edge.source_id}_{edge.edge_type}_{edge.target_id}"
                )
                rep_edge_ids.add(eid)

                rep_evidence_ids.update(_extract_edge_evidence_ids(edge, store))

            if not rep_evidence_ids:
                continue

            sorted_entities = sorted([src, tgt])
            sorted_edge_ids = sorted(rep_edge_ids)
            sorted_evidence_ids = sorted(rep_evidence_ids)

            explanation = (
                f"Observed {len(edges)} repeated financial transfers between account '{src}' and account '{tgt}'."
            )

            findings.append(
                PatternFinding(
                    rule_id="circular_repeated_financial_flow",
                    explanation=explanation,
                    entity_ids=sorted_entities,
                    edge_ids=sorted_edge_ids,
                    evidence_ids=sorted_evidence_ids,
                    derivation_class="DERIVED",
                    severity="MEDIUM",
                )
            )

    findings.sort(
        key=lambda f: (f.rule_id, tuple(f.entity_ids), tuple(f.evidence_ids), tuple(f.edge_ids))
    )
    return findings


# ── Unified Scanner ────────────────────────────────────────────────────────────

def detect_all_suspicious_patterns(store: GraphStore) -> list[PatternFinding]:
    """
    Execute all three deterministic suspicious pattern rules on the input GraphStore.

    Returns
    -------
    list[PatternFinding]
        Combined list of all detected pattern findings sorted deterministically.
    """
    findings: list[PatternFinding] = []
    findings.extend(detect_shared_phone_device(store))
    findings.extend(detect_communication_burst_near_event(store))
    findings.extend(detect_circular_repeated_financial_flow(store))

    findings.sort(
        key=lambda f: (f.rule_id, tuple(f.entity_ids), tuple(f.evidence_ids), tuple(f.edge_ids))
    )
    return findings
