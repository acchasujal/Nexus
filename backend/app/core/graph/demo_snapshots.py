"""backend/app/core/graph/demo_snapshots.py

Canonical Snapshot Registry & Demo Graph Definitions for NEXUS (Phase 3).
Unifies BEFORE and AFTER graph state into a single authoritative registry.
Ensures network before/after, graph diff, and network pulses all derive
from the EXACT same GraphStore instances.
"""

from __future__ import annotations

from typing import Any, Literal

from backend.app.core.graph.algorithms.utils import AdjEdge, GraphStore, NodeRecord
from shared.contracts.api import (
    CANONICAL_DATASET_VERSION,
    CANONICAL_SNAPSHOT_BASELINE,
    CANONICAL_SNAPSHOT_CURRENT,
    NexusGraphEdge,
    NexusGraphNode,
)


def resolve_snapshot_id(snapshot_id: str | None) -> str:
    """Resolve user/query snapshot identifiers to canonical snapshot IDs."""
    if not snapshot_id:
        return CANONICAL_SNAPSHOT_BASELINE
    sid = str(snapshot_id).strip()
    if sid in ("before", "baseline", "SNAP-BEFORE-001", CANONICAL_SNAPSHOT_BASELINE):
        return CANONICAL_SNAPSHOT_BASELINE
    if sid in ("after", "current", "SNAP-AFTER-001", "SNAP-REAL", CANONICAL_SNAPSHOT_CURRENT):
        return CANONICAL_SNAPSHOT_CURRENT
    return sid


def make_edge(
    edge_id: str,
    src: str,
    tgt: str,
    edge_type: str,
    deriv: Literal["FACT", "DERIVED", "HYPOTHESIS"],
    conf: float,
    rec_at: str,
    case_ids: list[str],
    ev_ids: list[str],
) -> NexusGraphEdge:
    return NexusGraphEdge(
        id=edge_id,
        source_id=src,
        target_id=tgt,
        edge_type=edge_type,
        weight=1.0,
        confidence=conf,
        derivation_class=deriv,
        recorded_at=rec_at,
        case_ids=case_ids,
        properties={"evidence_ids": ev_ids},
    )


# ── Canonical Demonstration Graph Nodes ──────────────────────────────────────

CASE_141 = NexusGraphNode(
    id="CASE-141",
    entity_type="Case",
    label="FIR 141/2026 — Trafficking",
    case_ids=["CASE-141"],
    properties={"fir_number": "FIR 141/2026", "station": "Mysuru South WS PS", "district": "Mysuru", "offence": "Human Trafficking (BNS 143)"},
)
CASE_207 = NexusGraphNode(
    id="CASE-207",
    entity_type="Case",
    label="FIR 207/2026 — Fraud",
    case_ids=["CASE-207"],
    properties={"fir_number": "FIR 207/2026", "station": "Bengaluru CEN PS", "district": "Bengaluru", "offence": "Financial Fraud (BNS 318)"},
)
P_MEENA = NexusGraphNode(
    id="P-MEENA",
    entity_type="Person",
    label="Meena Devi (Victim)",
    case_ids=["CASE-141"],
    properties={"role": "Victim", "statement": "dated 2026-02-13"},
)
P_DEEPAK = NexusGraphNode(
    id="P-DEEPAK",
    entity_type="Person",
    label="Deepak Rao (Associate)",
    case_ids=["CASE-207"],
    properties={"role": "Co-accused", "phone": "+91 99801 55210"},
)
ACC_7731 = NexusGraphNode(
    id="ACC-7731",
    entity_type="Account",
    label="ACC-7731 (Axis)",
    case_ids=["CASE-141"],
    properties={"bank": "Axis Bank", "holder": "Rafiq Khan"},
)
ACC_9914 = NexusGraphNode(
    id="ACC-9914",
    entity_type="Account",
    label="ACC-9914 (Axis)",
    case_ids=["CASE-207"],
    properties={"bank": "Axis Bank", "holder": "Deepak Rao"},
)
PH_A = NexusGraphNode(
    id="PH-A",
    entity_type="Phone",
    label="+91 98450 11223 (CDR: Mysuru)",
    case_ids=["CASE-141"],
    properties={"number": "+91 98450 11223", "seen_in": "cdr_mysuru_feb.csv"},
)
PH_B = NexusGraphNode(
    id="PH-B",
    entity_type="Phone",
    label="+91 98450 11223 (CDR: Bengaluru)",
    case_ids=["CASE-207"],
    properties={"number": "+91 98450 11223", "seen_in": "cdr_bengaluru_mar.csv"},
)

CASE_305 = NexusGraphNode(
    id="CASE-305",
    entity_type="Case",
    label="FIR 305/2026 — Cyber Fraud",
    case_ids=["CASE-305"],
    properties={"fir_number": "FIR 305/2026", "station": "Indiranagar PS", "district": "Bengaluru", "offence": "IT Act 66D & Fraud"},
)
CASE_412 = NexusGraphNode(
    id="CASE-412",
    entity_type="Case",
    label="FIR 412/2026 — Hawala Syndicate",
    case_ids=["CASE-412"],
    properties={"fir_number": "FIR 412/2026", "station": "Domlur Cyber PS", "district": "Bengaluru", "offence": "Organized Crime (BNS 111)"},
)
P_VIKRAM_S = NexusGraphNode(
    id="P-VIKRAM-S",
    entity_type="Person",
    label="Vikram Sharma (Accused)",
    case_ids=["CASE-305"],
    properties={"role": "Accused", "phone": "+91 98450 77310", "national_id": "XXXX-XXXX-4491"},
)
P_BIKRAM_S = NexusGraphNode(
    id="P-BIKRAM-S",
    entity_type="Person",
    label="Bikram Sarma (Accused)",
    case_ids=["CASE-412"],
    properties={"role": "Accused", "phone": "+91 98450 77310", "national_id": "XXXX-XXXX-4491"},
)
ACC_4491 = NexusGraphNode(
    id="ACC-4491",
    entity_type="Account",
    label="ACC-4491 (HDFC)",
    case_ids=["CASE-412"],
    properties={"bank": "HDFC Bank", "holder": "Bikram Sarma"},
)

CASE_501 = NexusGraphNode(
    id="CASE-501",
    entity_type="Case",
    label="FIR 501/2026 — Narcotics Ring",
    case_ids=["CASE-501"],
    properties={"fir_number": "FIR 501/2026", "station": "Jayanagar PS", "district": "Bengaluru", "offence": "NDPS Act 21(c)"},
)
CASE_502 = NexusGraphNode(
    id="CASE-502",
    entity_type="Case",
    label="FIR 502/2026 — Smuggling Ring",
    case_ids=["CASE-502"],
    properties={"fir_number": "FIR 502/2026", "station": "Commercial Street PS", "district": "Bengaluru", "offence": "Customs & Contraband"},
)
P_SUNIEL_S = NexusGraphNode(
    id="P-SUNIEL-S",
    entity_type="Person",
    label="Suniel Shetty (Accused)",
    case_ids=["CASE-501"],
    properties={"role": "Accused", "vehicle": "KA-01-AB-1001", "address": "BTM 2nd Stage"},
)
P_SUNIL_S = NexusGraphNode(
    id="P-SUNIL-S",
    entity_type="Person",
    label="Sunil Shetty (Accused)",
    case_ids=["CASE-502"],
    properties={"role": "Accused", "vehicle": "KA-01-AB-1001", "address": "4th Block Jayanagar"},
)
VEH_1001 = NexusGraphNode(
    id="VEH-1001",
    entity_type="Vehicle",
    label="KA-01-AB-1001 (Toyota Fortuner)",
    case_ids=["CASE-501", "CASE-502"],
    properties={"registration": "KA-01-AB-1001", "vehicle": "KA-01-AB-1001"},
)

# ── Baseline Snapshot State (BEFORE) ─────────────────────────────────────────

BEFORE_NODES: list[NexusGraphNode] = [
    CASE_141, CASE_207, CASE_305, CASE_412, CASE_501, CASE_502,
    P_MEENA, P_DEEPAK, ACC_7731, ACC_9914, ACC_4491, VEH_1001, PH_A, PH_B,
    NexusGraphNode(id="P-RAFIQ-K", entity_type="Person", label="Rafiq Khan (Accused)", case_ids=["CASE-141"], properties={"role": "Accused", "phone": "+91 98450 11223"}),
    NexusGraphNode(id="P-RAFIQ-A", entity_type="Person", label="Rafiq Ahmed (Accused)", case_ids=["CASE-207"], properties={"role": "Accused", "phone": "+91 98450 11223"}),
    P_VIKRAM_S, P_BIKRAM_S,
    P_SUNIEL_S, P_SUNIL_S,
]

BEFORE_EDGES: list[NexusGraphEdge] = [
    make_edge("E-ACCUSE-141", "P-RAFIQ-K", "CASE-141", "ACCUSED_IN", "FACT", 1.0, "2026-02-11T09:30:00Z", ["CASE-141"], ["SRC-FIR-141"]),
    make_edge("E-VICTIM-141", "P-MEENA", "CASE-141", "VICTIM_IN", "FACT", 1.0, "2026-02-11T09:30:00Z", ["CASE-141"], ["SRC-FIR-141"]),
    make_edge("E-USEPH-A", "P-RAFIQ-K", "PH-A", "USES_PHONE", "FACT", 0.98, "2026-02-14T22:41:05Z", ["CASE-141"], ["SRC-CDR-A12"]),
    make_edge("E-OWN-7731", "P-RAFIQ-K", "ACC-7731", "OWNS_ACCOUNT", "FACT", 0.95, "2026-02-12T10:00:00Z", ["CASE-141"], ["SRC-FIR-141"]),
    make_edge("E-ACCUSE-207", "P-RAFIQ-A", "CASE-207", "ACCUSED_IN", "FACT", 1.0, "2026-03-02T14:15:00Z", ["CASE-207"], ["SRC-FIR-207"]),
    make_edge("E-COACC-207", "P-DEEPAK", "CASE-207", "CO_ACCUSED_IN", "FACT", 1.0, "2026-03-02T14:15:00Z", ["CASE-207"], ["SRC-FIR-207"]),
    make_edge("E-USEPH-B", "P-RAFIQ-A", "PH-B", "USES_PHONE", "FACT", 0.98, "2026-03-05T02:12:44Z", ["CASE-207"], ["SRC-CDR-B31"]),
    make_edge("E-OWN-9914", "P-DEEPAK", "ACC-9914", "OWNS_ACCOUNT", "FACT", 0.95, "2026-03-02T14:15:00Z", ["CASE-207"], ["SRC-FIR-207"]),
    make_edge("E-TXN-55", "ACC-9914", "ACC-7731", "TRANSFERRED_TO", "FACT", 1.0, "2026-03-09T11:03:00Z", ["CASE-207", "CASE-141"], ["SRC-TXN-55"]),
    make_edge("E-TXN-71", "ACC-9914", "ACC-7731", "TRANSFERRED_TO", "FACT", 1.0, "2026-03-11T16:47:00Z", ["CASE-207", "CASE-141"], ["SRC-TXN-71"]),
    make_edge("E-ACCUSE-305", "P-VIKRAM-S", "CASE-305", "ACCUSED_IN", "FACT", 1.0, "2026-03-15T11:00:00Z", ["CASE-305"], ["SRC-FIR-305"]),
    make_edge("E-ACCUSE-412", "P-BIKRAM-S", "CASE-412", "ACCUSED_IN", "FACT", 1.0, "2026-03-22T16:30:00Z", ["CASE-412"], ["SRC-FIR-412"]),
    make_edge("E-OWN-4491", "P-BIKRAM-S", "ACC-4491", "OWNS_ACCOUNT", "FACT", 0.95, "2026-03-22T16:30:00Z", ["CASE-412"], ["SRC-FIR-412"]),
    make_edge("E-TXN-HWL", "ACC-4491", "ACC-9914", "TRANSFERRED_TO", "FACT", 0.90, "2026-03-25T12:00:00Z", ["CASE-412", "CASE-207"], ["SRC-FIR-412"]),
    make_edge("E-ACCUSE-501", "P-SUNIEL-S", "CASE-501", "ACCUSED_IN", "FACT", 1.0, "2026-04-02T10:15:00Z", ["CASE-501"], ["SRC-FIR-501"]),
    make_edge("E-ACCUSE-502", "P-SUNIL-S", "CASE-502", "ACCUSED_IN", "FACT", 1.0, "2026-04-18T14:40:00Z", ["CASE-502"], ["SRC-FIR-502"]),
    make_edge("E-VEH-501", "P-SUNIEL-S", "VEH-1001", "OPERATES_VEHICLE", "FACT", 0.95, "2026-04-02T10:15:00Z", ["CASE-501"], ["SRC-FIR-501"]),
    make_edge("E-VEH-502", "P-SUNIL-S", "VEH-1001", "OPERATES_VEHICLE", "FACT", 0.95, "2026-04-18T14:40:00Z", ["CASE-502"], ["SRC-FIR-502"]),
]

# ── Target Snapshot State (AFTER) ────────────────────────────────────────────

AFTER_NODES: list[NexusGraphNode] = [
    CASE_141, CASE_207, CASE_305, CASE_412, CASE_501, CASE_502,
    P_MEENA, P_DEEPAK, ACC_7731, ACC_9914, ACC_4491, VEH_1001,
    NexusGraphNode(
        id="P-RAFIQ",
        entity_type="Person",
        label="Rafiq Khan / Rafiq Ahmed",
        case_ids=["CASE-141", "CASE-207"],
        badges=["CROSS_CASE_BRIDGE", "COMMUNITY-C1"],
        properties={"role": "Accused in both FIRs", "phone": "+91 98450 11223", "aliases": ["Rafiq Khan", "Rafiq Ahmed"]},
    ),
    NexusGraphNode(
        id="PH-UNIFIED",
        entity_type="Phone",
        label="+91 98450 11223 (shared)",
        case_ids=["CASE-141", "CASE-207"],
        properties={"number": "+91 98450 11223", "seen_in": "cdr_mysuru_feb.csv, cdr_bengaluru_mar.csv"},
    ),
    NexusGraphNode(
        id="P-VIKRAM",
        entity_type="Person",
        label="Vikram Sharma / Bikram Sarma",
        case_ids=["CASE-305", "CASE-412"],
        badges=["CROSS_CASE_BRIDGE", "COMMUNITY-C2"],
        properties={"role": "Hawala Operator & Cyber Fraudster", "phone": "+91 98450 77310", "national_id": "XXXX-XXXX-4491"},
    ),
    NexusGraphNode(
        id="P-SUNIEL",
        entity_type="Person",
        label="Suniel Shetty / Sunil Shetty",
        case_ids=["CASE-501", "CASE-502"],
        badges=["CROSS_CASE_BRIDGE", "COMMUNITY-C3"],
        properties={"role": "Syndicate Logistics Coordinator", "vehicle": "KA-01-AB-1001", "aliases": ["Suniel Shetty", "Sunil Shetty"]},
    ),
]

AFTER_EDGES: list[NexusGraphEdge] = [
    make_edge("E-ACCUSE-141", "P-RAFIQ", "CASE-141", "ACCUSED_IN", "FACT", 1.0, "2026-02-11T09:30:00Z", ["CASE-141"], ["SRC-FIR-141"]),
    make_edge("E-VICTIM-141", "P-MEENA", "CASE-141", "VICTIM_IN", "FACT", 1.0, "2026-02-11T09:30:00Z", ["CASE-141"], ["SRC-FIR-141"]),
    make_edge("E-USEPH-1", "P-RAFIQ", "PH-UNIFIED", "USES_PHONE", "FACT", 0.98, "2026-02-14T22:41:05Z", ["CASE-141"], ["SRC-CDR-A12"]),
    make_edge("E-USEPH-2", "P-RAFIQ", "PH-UNIFIED", "USES_PHONE", "FACT", 0.98, "2026-03-05T02:12:44Z", ["CASE-207"], ["SRC-CDR-B31"]),
    make_edge("E-OWN-7731", "P-RAFIQ", "ACC-7731", "OWNS_ACCOUNT", "FACT", 0.95, "2026-02-12T10:00:00Z", ["CASE-141"], ["SRC-FIR-141"]),
    make_edge("E-ACCUSE-207", "P-RAFIQ", "CASE-207", "ACCUSED_IN", "FACT", 1.0, "2026-03-02T14:15:00Z", ["CASE-207"], ["SRC-FIR-207"]),
    make_edge("E-COACC-207", "P-DEEPAK", "CASE-207", "CO_ACCUSED_IN", "FACT", 1.0, "2026-03-02T14:15:00Z", ["CASE-207"], ["SRC-FIR-207"]),
    make_edge("E-OWN-9914", "P-DEEPAK", "ACC-9914", "OWNS_ACCOUNT", "FACT", 0.95, "2026-03-02T14:15:00Z", ["CASE-207"], ["SRC-FIR-207"]),
    make_edge("E-COMM-DK", "P-RAFIQ", "P-DEEPAK", "COMMUNICATED_WITH", "DERIVED", 0.91, "2026-03-05T02:12:44Z", ["CASE-141", "CASE-207"], ["SRC-CDR-B31"]),
    make_edge("E-TXN-55", "ACC-9914", "ACC-7731", "TRANSFERRED_TO", "FACT", 1.0, "2026-03-09T11:03:00Z", ["CASE-207", "CASE-141"], ["SRC-TXN-55"]),
    make_edge("E-TXN-71", "ACC-9914", "ACC-7731", "TRANSFERRED_TO", "FACT", 1.0, "2026-03-11T16:47:00Z", ["CASE-207", "CASE-141"], ["SRC-TXN-71"]),
    make_edge("E-BRIDGE", "CASE-141", "CASE-207", "CONNECTS_CASES", "DERIVED", 0.86, "2026-08-24T18:00:00Z", ["CASE-141", "CASE-207"], ["SRC-FIR-141", "SRC-FIR-207", "SRC-CDR-A12", "SRC-CDR-B31"]),
    make_edge("E-ACCUSE-305-A", "P-VIKRAM", "CASE-305", "ACCUSED_IN", "FACT", 1.0, "2026-03-15T11:00:00Z", ["CASE-305"], ["SRC-FIR-305"]),
    make_edge("E-ACCUSE-412-A", "P-VIKRAM", "CASE-412", "ACCUSED_IN", "FACT", 1.0, "2026-03-22T16:30:00Z", ["CASE-412"], ["SRC-FIR-412"]),
    make_edge("E-OWN-4491-A", "P-VIKRAM", "ACC-4491", "OWNS_ACCOUNT", "FACT", 0.95, "2026-03-22T16:30:00Z", ["CASE-412"], ["SRC-FIR-412"]),
    make_edge("E-TXN-HWL", "ACC-4491", "ACC-9914", "TRANSFERRED_TO", "FACT", 0.90, "2026-03-25T12:00:00Z", ["CASE-412", "CASE-207"], ["SRC-FIR-412"]),
    make_edge("E-BRIDGE-2", "CASE-305", "CASE-412", "CONNECTS_CASES", "DERIVED", 0.92, "2026-08-24T18:00:00Z", ["CASE-305", "CASE-412"], ["SRC-FIR-305", "SRC-FIR-412"]),
    make_edge("E-ACCUSE-501-A", "P-SUNIEL", "CASE-501", "ACCUSED_IN", "FACT", 1.0, "2026-04-02T10:15:00Z", ["CASE-501"], ["SRC-FIR-501"]),
    make_edge("E-ACCUSE-502-A", "P-SUNIEL", "CASE-502", "ACCUSED_IN", "FACT", 1.0, "2026-04-18T14:40:00Z", ["CASE-502"], ["SRC-FIR-502"]),
    make_edge("E-VEH-UNIFIED", "P-SUNIEL", "VEH-1001", "OPERATES_VEHICLE", "FACT", 0.95, "2026-04-18T14:40:00Z", ["CASE-501", "CASE-502"], ["SRC-FIR-501", "SRC-FIR-502"]),
    make_edge("E-BRIDGE-3", "CASE-501", "CASE-502", "CONNECTS_CASES", "DERIVED", 0.88, "2026-08-24T18:00:00Z", ["CASE-501", "CASE-502"], ["SRC-FIR-501", "SRC-FIR-502"]),
]


def get_canonical_snapshot_store(snapshot_id: str, repo: Any | None = None) -> GraphStore:
    """
    Build a unified GraphStore for a given snapshot ID.
    Merges base repository store with deterministic point-in-time demo topology.
    """
    sid = resolve_snapshot_id(snapshot_id)
    store = GraphStore()

    # Seed base repository nodes/edges if available
    if repo is not None and hasattr(repo, "to_graph_store"):
        base = repo.to_graph_store()
        store.nodes.update(base.nodes)
        for k, v in base.adj.items():
            store.adj.setdefault(k, []).extend(v)
        for k, v in base.radj.items():
            store.radj.setdefault(k, []).extend(v)
        for k, v in base.edge_index.items():
            store.edge_index.setdefault(k, []).extend(v)

    # Apply canonical demo slice
    nodes = AFTER_NODES if sid == CANONICAL_SNAPSHOT_CURRENT else BEFORE_NODES
    edges = AFTER_EDGES if sid == CANONICAL_SNAPSHOT_CURRENT else BEFORE_EDGES

    for n in nodes:
        store.nodes[n.id] = NodeRecord(
            node_id=n.id,
            entity_type=n.entity_type,
            properties=dict(n.properties, case_ids=n.case_ids, badges=n.badges),
        )

    for e in edges:
        adj_edge = AdjEdge(
            source_id=e.source_id,
            target_id=e.target_id,
            edge_type=e.edge_type,
            properties=dict(
                e.properties,
                id=e.id,
                weight=e.weight,
                confidence=e.confidence,
                derivation_class=e.derivation_class,
                recorded_at=e.recorded_at,
                case_ids=e.case_ids,
            ),
        )
        store.adj.setdefault(e.source_id, []).append(adj_edge)
        store.radj.setdefault(e.target_id, []).append(adj_edge)
        store.edge_index.setdefault(e.edge_type, []).append(adj_edge)

    return store
