"""backend/app/api/nexus_routes.py

FastAPI routes for the frozen NEXUS prototype contract (/api/v1/nexus/*).
Implements:
  - Ingest & Demo Reset (/nexus/ingest, /nexus/demo/reset)
  - Entity Fusion Candidates & Decisions (/nexus/resolution/*)
  - Global Network Explorer & Diff (/nexus/network, /nexus/network/diff)
  - Edge Evidence Inspection (/nexus/relationships/{id}/evidence)
  - Cross-Case Pathfinder (/nexus/path)
  - Lead Inbox & Decisions (/nexus/leads/*)
  - Grounded Copilot with Refusal Gate (/nexus/copilot/query)
  - Global Search (/nexus/search)
  - Source Record Registry (/nexus/sources/{id})
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.app.api.dependencies import get_audit_service, get_principal, get_repository
from backend.app.auth.principal import Principal
from backend.app.db.in_memory import InMemoryBackendRepository
from backend.app.services.audit_service import AuditEventType, AuditService

# ── Pydantic Models ────────────────────────────────────────────────────────────

class NexusSourceRecord(BaseModel):
    id: str
    batch_id: str
    source_type: str
    locator: str
    raw_excerpt: str
    occurred_at: str


class NexusGraphNode(BaseModel):
    id: str
    entity_type: str
    label: str
    case_ids: list[str]
    badges: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class NexusGraphEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    edge_type: str
    weight: float = 1.0
    confidence: float = 1.0
    derivation_class: Literal["FACT", "DERIVED", "HYPOTHESIS"] = "FACT"
    recorded_at: str
    case_ids: list[str]
    properties: dict[str, Any] = Field(default_factory=dict)


class NexusNetworkResponse(BaseModel):
    snapshot_id: str
    state: Literal["before", "after"]
    nodes: list[NexusGraphNode]
    edges: list[NexusGraphEdge]
    total_nodes: int
    total_edges: int


class SnapshotDiffResponse(BaseModel):
    before_snapshot_id: str
    after_snapshot_id: str
    added_node_ids: list[str]
    removed_node_ids: list[str]
    changed_node_ids: list[str]
    added_edge_ids: list[str]
    removed_edge_ids: list[str]
    changed_edge_ids: list[str]


class ResolutionCandidateRecord(BaseModel):
    node_id: str
    entity_type: str
    label: str
    case_ids: list[str]
    properties: dict[str, Any]
    source_records: list[NexusSourceRecord]


class CandidateReason(BaseModel):
    field: str
    detail: str
    weight: float


class CandidateConflict(BaseModel):
    field: str
    left_value: str
    right_value: str


class ResolutionCandidate(BaseModel):
    id: str
    score: float
    status: Literal["PENDING", "CONFIRMED", "REJECTED", "DEFERRED"]
    left: ResolutionCandidateRecord
    right: ResolutionCandidateRecord
    reasons: list[CandidateReason]
    conflicts: list[CandidateConflict]
    decided_at: str | None = None
    decided_by: str | None = None


class ResolutionDecisionRequest(BaseModel):
    decision: Literal["CONFIRM", "REJECT", "DEFER"]
    decided_by: str = "Investigating Officer"
    note: str | None = None


class ResolutionDecisionResponse(BaseModel):
    candidate_id: str
    status: str
    affected_node_ids: list[str]
    new_snapshot_id: str | None = None


class DerivationStep(BaseModel):
    step: int
    rule: str
    inputs: list[str]


class NexusEdgeEvidenceResponse(BaseModel):
    relationship_id: str
    edge_type: str
    source_label: str
    target_label: str
    derivation_class: Literal["FACT", "DERIVED", "HYPOTHESIS"]
    confidence: float
    recorded_at: str
    source_records: list[NexusSourceRecord]
    derivation_chain: list[DerivationStep]


class NexusPathResponse(BaseModel):
    found: bool
    source_id: str
    target_id: str
    node_ids: list[str]
    edge_ids: list[str]
    hops: int
    explanation: str
    evidence_ids: list[str]


class NexusLeadPath(BaseModel):
    node_ids: list[str]
    edge_ids: list[str]


class NexusLead(BaseModel):
    id: str
    title: str
    rule_id: str
    explanation: str
    severity: str
    derivation_class: Literal["FACT", "DERIVED", "HYPOTHESIS"]
    case_ids: list[str]
    status: Literal["NEW", "ACCEPTED", "REJECTED"]
    path: NexusLeadPath
    evidence_ids: list[str]
    created_at: str
    decided_at: str | None = None
    decided_by: str | None = None
    decision_note: str | None = None


class NexusLeadDecisionRequest(BaseModel):
    decision: Literal["ACCEPT", "REJECT"]
    decided_by: str = "Investigating Officer"
    note: str | None = None


class NexusCopilotResponse(BaseModel):
    query: str
    answer: str
    is_refusal: bool
    refusal_reason: str | None = None
    evidence_ids: list[str]
    reasoning_path: list[str]


class SearchCaseItem(BaseModel):
    id: str
    fir_number: str
    title: str
    score: float = 1.0


class SearchEntityItem(BaseModel):
    id: str
    label: str
    entity_type: str
    case_ids: list[str]
    score: float = 1.0
    subtext: str | None = None


class NexusSearchResponse(BaseModel):
    query: str
    cases: list[SearchCaseItem]
    entities: list[SearchEntityItem]


class ExtractionSummary(BaseModel):
    persons: int
    phones: int
    accounts: int
    events: int
    relationships: int


class IngestFileItem(BaseModel):
    source_type: str
    file_name: str


class NexusIngestRequest(BaseModel):
    files: list[IngestFileItem]


class NexusIngestResponse(BaseModel):
    batch_id: str
    source_type: str
    ingested_count: int = 3
    extraction_summary: ExtractionSummary
    snapshot_id: str


# ── Golden Demo Fixture ────────────────────────────────────────────────────────

RAW_SOURCES: dict[str, NexusSourceRecord] = {
    "SRC-FIR-141": NexusSourceRecord(
        id="SRC-FIR-141",
        batch_id="BATCH-2026-08-24",
        source_type="FIR",
        locator="fir_141_2026.pdf — page 2, row 4 (accused list)",
        raw_excerpt="Accused: Rafiq Khan, s/o Iqbal Khan, age 35, res. Hootagalli, Mysuru. Mobile disclosed: +91 98450 11223.",
        occurred_at="2026-02-11T09:30:00Z",
    ),
    "SRC-FIR-207": NexusSourceRecord(
        id="SRC-FIR-207",
        batch_id="BATCH-2026-08-24",
        source_type="FIR",
        locator="fir_207_2026.pdf — page 1, row 7 (accused list)",
        raw_excerpt="Accused: Rafiq Ahmed, s/o Iqbal Khan, age 35, res. Hootagalli Colony, Mysuru. Mobile: +91 98450 11223.",
        occurred_at="2026-03-02T14:15:00Z",
    ),
    "SRC-CDR-A12": NexusSourceRecord(
        id="SRC-CDR-A12",
        batch_id="BATCH-2026-08-24",
        source_type="CDR",
        locator="cdr_mysuru_feb.csv — row 1287 (A-party +91 98450 11223)",
        raw_excerpt="2026-02-14T22:41:05Z, +91 98450 11223 → +91 99801 55210, duration 412s, cell 4701-Hootagalli.",
        occurred_at="2026-02-14T22:41:05Z",
    ),
    "SRC-CDR-B31": NexusSourceRecord(
        id="SRC-CDR-B31",
        batch_id="BATCH-2026-08-24",
        source_type="CDR",
        locator="cdr_bengaluru_mar.csv — row 4402 (A-party +91 98450 11223)",
        raw_excerpt="2026-03-05T02:12:44Z, +91 98450 11223 → +91 98450 77310, duration 96s, cell 6112-Whitefield.",
        occurred_at="2026-03-05T02:12:44Z",
    ),
    "SRC-TXN-55": NexusSourceRecord(
        id="SRC-TXN-55",
        batch_id="BATCH-2026-08-24",
        source_type="BANK_TXN",
        locator="txns_axis_9914.csv — row 55",
        raw_excerpt="2026-03-09T11:03:00Z, ACC-9914 → ACC-7731, ₹4,80,000, ref NIFT/20260309/5521.",
        occurred_at="2026-03-09T11:03:00Z",
    ),
    "SRC-TXN-71": NexusSourceRecord(
        id="SRC-TXN-71",
        batch_id="BATCH-2026-08-24",
        source_type="BANK_TXN",
        locator="txns_axis_9914.csv — row 71",
        raw_excerpt="2026-03-11T16:47:00Z, ACC-9914 → ACC-7731, ₹2,15,000, ref NIFT/20260311/8830.",
        occurred_at="2026-03-11T16:47:00Z",
    ),
}

INITIAL_CANDIDATE = ResolutionCandidate(
    id="RC-1",
    score=0.86,
    status="PENDING",
    left=ResolutionCandidateRecord(
        node_id="P-RAFIQ-K",
        entity_type="Person",
        label="Rafiq Khan",
        case_ids=["CASE-141"],
        properties={
            "full_name": "Rafiq Khan",
            "father_name": "Iqbal Khan",
            "age": 35,
            "dob": "1991-03-14",
            "address": "Hootagalli, Mysuru",
            "phone": "+91 98450 11223",
            "role": "Accused (FIR 141/2026)",
        },
        source_records=[RAW_SOURCES["SRC-FIR-141"], RAW_SOURCES["SRC-CDR-A12"]],
    ),
    right=ResolutionCandidateRecord(
        node_id="P-RAFIQ-A",
        entity_type="Person",
        label="Rafiq Ahmed",
        case_ids=["CASE-207"],
        properties={
            "full_name": "Rafiq Ahmed",
            "father_name": "Iqbal Khan",
            "age": 35,
            "dob": "1991-04-13",
            "address": "Hootagalli Colony, Mysuru",
            "phone": "+91 98450 11223",
            "role": "Accused (FIR 207/2026)",
        },
        source_records=[RAW_SOURCES["SRC-FIR-207"], RAW_SOURCES["SRC-CDR-B31"]],
    ),
    reasons=[
        CandidateReason(field="phone", detail="Identical primary mobile +91 98450 11223 appears in both CDR pulls", weight=0.40),
        CandidateReason(field="father_name", detail="Father's name 'Iqbal Khan' matches exactly in both FIRs", weight=0.25),
        CandidateReason(field="address", detail="Address locality 'Hootagalli, Mysuru' matches with granularity difference", weight=0.21),
    ],
    conflicts=[
        CandidateConflict(field="name", left_value="Rafiq Khan", right_value="Rafiq Ahmed"),
        CandidateConflict(field="dob", left_value="1991-03-14", right_value="1991-04-13 (day/month transposition)"),
        CandidateConflict(field="age", left_value="35", right_value="35 (consistent)"),
    ],
)

CASE_141 = NexusGraphNode(
    id="CASE-141",
    entity_type="Case",
    label="FIR 141/2026 — Trafficking",
    case_ids=["CASE-141"],
    properties={"fir_number": "141/2026", "station": "Mysuru South WS PS", "district": "Mysuru", "offence": "Human Trafficking (BNS 143)"},
)
CASE_207 = NexusGraphNode(
    id="CASE-207",
    entity_type="Case",
    label="FIR 207/2026 — Fraud",
    case_ids=["CASE-207"],
    properties={"fir_number": "207/2026", "station": "Bengaluru CEN PS", "district": "Bengaluru", "offence": "Financial Fraud (BNS 318)"},
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

BEFORE_NODES = [
    CASE_141, CASE_207, P_MEENA, P_DEEPAK, ACC_7731, ACC_9914, PH_A, PH_B,
    NexusGraphNode(id="P-RAFIQ-K", entity_type="Person", label="Rafiq Khan (Accused)", case_ids=["CASE-141"], properties={"role": "Accused", "phone": "+91 98450 11223"}),
    NexusGraphNode(id="P-RAFIQ-A", entity_type="Person", label="Rafiq Ahmed (Accused)", case_ids=["CASE-207"], properties={"role": "Accused", "phone": "+91 98450 11223"}),
]

def make_edge(
    edge_id: str, src: str, tgt: str, edge_type: str, deriv: Literal["FACT", "DERIVED", "HYPOTHESIS"],
    conf: float, rec_at: str, case_ids: list[str], ev_ids: list[str],
) -> NexusGraphEdge:
    return NexusGraphEdge(
        id=edge_id, source_id=src, target_id=tgt, edge_type=edge_type, weight=1.0, confidence=conf,
        derivation_class=deriv, recorded_at=rec_at, case_ids=case_ids, properties={"evidence_ids": ev_ids},
    )

BEFORE_EDGES = [
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
]

AFTER_NODES = [
    CASE_141, CASE_207, P_MEENA, P_DEEPAK, ACC_7731, ACC_9914,
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
]

AFTER_EDGES = [
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
]

SNAPSHOT_DIFF = SnapshotDiffResponse(
    before_snapshot_id="SNAP-BEFORE-001",
    after_snapshot_id="SNAP-AFTER-001",
    added_node_ids=["P-RAFIQ", "PH-UNIFIED"],
    removed_node_ids=["P-RAFIQ-K", "P-RAFIQ-A", "PH-A", "PH-B"],
    changed_node_ids=[],
    added_edge_ids=["E-USEPH-1", "E-USEPH-2", "E-COMM-DK", "E-BRIDGE"],
    removed_edge_ids=["E-ACCUSE-141", "E-USEPH-A", "E-ACCUSE-207", "E-USEPH-B"],
    changed_edge_ids=[],
)

BRIDGE_LEAD = NexusLead(
    id="LEAD-1",
    title="Cross-case bridge: Rafiq connects FIR 141/2026 with FIR 207/2026",
    rule_id="CROSS_CASE_BRIDGE",
    explanation=(
        "After the confirmed alias (RC-1), one person ('Rafiq Khan / Rafiq Ahmed') is accused in both cases, "
        "uses the same phone +91 98450 11223 in both CDR pulls, and receives repeated transfers from ACC-9914 "
        "(co-accused Deepak Rao) into ACC-7731. This is an investigative lead, not a determination of guilt."
    ),
    severity="HIGH",
    derivation_class="HYPOTHESIS",
    case_ids=["CASE-141", "CASE-207"],
    status="NEW",
    path=NexusLeadPath(
        node_ids=["CASE-141", "P-RAFIQ", "PH-UNIFIED", "P-DEEPAK", "CASE-207"],
        edge_ids=["E-ACCUSE-141", "E-USEPH-1", "E-USEPH-2", "E-COMM-DK", "E-COACC-207"],
    ),
    evidence_ids=["SRC-FIR-141", "SRC-FIR-207", "SRC-CDR-A12", "SRC-CDR-B31", "SRC-TXN-55"],
    created_at="2026-08-24T18:00:05Z",
)

# ── Mutable State Store ────────────────────────────────────────────────────────

CANDIDATE_RC1_INIT = ResolutionCandidate(
    id="RC-1",
    score=0.86,
    status="PENDING",
    left=ResolutionCandidateRecord(
        node_id="P-RAFIQ-K",
        entity_type="Person",
        label="Rafiq Khan",
        case_ids=["CASE-141"],
        properties={
            "full_name": "Rafiq Khan",
            "father_name": "Iqbal Khan",
            "age": 35,
            "dob": "1991-03-14",
            "address": "Hootagalli, Mysuru",
            "phone": "+91 98450 11223",
            "role": "Accused (FIR 141/2026)",
        },
        source_records=[RAW_SOURCES["SRC-FIR-141"], RAW_SOURCES["SRC-CDR-A12"]],
    ),
    right=ResolutionCandidateRecord(
        node_id="P-RAFIQ-A",
        entity_type="Person",
        label="Rafiq Ahmed",
        case_ids=["CASE-207"],
        properties={
            "full_name": "Rafiq Ahmed",
            "father_name": "Iqbal Khan",
            "age": 35,
            "dob": "1991-04-13",
            "address": "Hootagalli Colony, Mysuru",
            "phone": "+91 98450 11223",
            "role": "Accused (FIR 207/2026)",
        },
        source_records=[RAW_SOURCES["SRC-FIR-207"], RAW_SOURCES["SRC-CDR-B31"]],
    ),
    reasons=[
        CandidateReason(field="phone", detail="Identical primary mobile +91 98450 11223 appears in both CDR pulls", weight=0.40),
        CandidateReason(field="father_name", detail="Father's name 'Iqbal Khan' matches exactly in both FIRs", weight=0.25),
        CandidateReason(field="address", detail="Address locality 'Hootagalli, Mysuru' matches with granularity difference", weight=0.21),
    ],
    conflicts=[
        CandidateConflict(field="name", left_value="Rafiq Khan", right_value="Rafiq Ahmed"),
        CandidateConflict(field="dob", left_value="1991-03-14", right_value="1991-04-13 (day/month transposition)"),
        CandidateConflict(field="age", left_value="35", right_value="35 (consistent)"),
    ],
)

CANDIDATE_RC2_INIT = ResolutionCandidate(
    id="RC-2",
    score=0.92,
    status="PENDING",
    left=ResolutionCandidateRecord(
        node_id="P-VIKRAM-S",
        entity_type="Person",
        label="Vikram Sharma",
        case_ids=["CASE-305"],
        properties={
            "full_name": "Vikram Sharma",
            "age": 32,
            "address": "Indiranagar Bengaluru",
            "phone": "+91 98450 77310",
            "national_id": "XXXX-XXXX-4491",
            "role": "Accused (FIR 305/2026)",
        },
        source_records=[
            NexusSourceRecord(
                id="SRC-FIR-305",
                batch_id="BATCH-2026-08-24",
                source_type="FIR",
                locator="fir_305_2026.pdf — page 2, row 3",
                raw_excerpt="Accused: Vikram Sharma, age 32, res. Indiranagar Bengaluru. Mobile: +91 98450 77310. Aadhaar: XXXX-XXXX-4491.",
                occurred_at="2026-03-15T11:00:00Z",
            )
        ],
    ),
    right=ResolutionCandidateRecord(
        node_id="P-BIKRAM-S",
        entity_type="Person",
        label="Bikram Sarma",
        case_ids=["CASE-412"],
        properties={
            "full_name": "Bikram Sarma",
            "age": 32,
            "address": "Domlur Layout Bengaluru",
            "phone": "+91 98450 77310",
            "national_id": "XXXX-XXXX-4491",
            "role": "Accused (FIR 412/2026)",
        },
        source_records=[
            NexusSourceRecord(
                id="SRC-FIR-412",
                batch_id="BATCH-2026-08-24",
                source_type="FIR",
                locator="fir_412_2026.pdf — page 1, row 5",
                raw_excerpt="Accused: Bikram Sarma, age 32, res. Domlur Layout Bengaluru. Mobile: +91 98450 77310. Aadhaar: XXXX-XXXX-4491.",
                occurred_at="2026-03-22T16:30:00Z",
            )
        ],
    ),
    reasons=[
        CandidateReason(field="national_id", detail="Aadhaar suffix XXXX-XXXX-4491 matches exactly in both police reports", weight=0.45),
        CandidateReason(field="phone", detail="Shared operational contact number +91 98450 77310", weight=0.35),
        CandidateReason(field="age", detail="Age 32 matches perfectly across both state jurisdictions", weight=0.12),
    ],
    conflicts=[
        CandidateConflict(field="name", left_value="Vikram Sharma", right_value="Bikram Sarma (Phonetic spelling)"),
        CandidateConflict(field="address", left_value="Indiranagar Bengaluru", right_value="Domlur Layout Bengaluru (Adjacent sectors)"),
    ],
)

CANDIDATE_RC3_INIT = ResolutionCandidate(
    id="RC-3",
    score=0.88,
    status="PENDING",
    left=ResolutionCandidateRecord(
        node_id="P-SUNIEL-S",
        entity_type="Person",
        label="Suniel Shetty",
        case_ids=["CASE-501"],
        properties={
            "full_name": "Suniel Shetty",
            "father_name": "R. Shetty",
            "age": 41,
            "vehicle": "KA-01-AB-1001",
            "address": "Jayanagar Bengaluru",
            "role": "Accused (FIR 501/2026)",
        },
        source_records=[
            NexusSourceRecord(
                id="SRC-FIR-501",
                batch_id="BATCH-2026-08-24",
                source_type="FIR",
                locator="fir_501_2026.pdf — page 3, row 2",
                raw_excerpt="Accused: Suniel Shetty, s/o R. Shetty, age 41, res. Jayanagar Bengaluru. Vehicle: KA-01-AB-1001.",
                occurred_at="2026-04-02T10:15:00Z",
            )
        ],
    ),
    right=ResolutionCandidateRecord(
        node_id="P-SUNIL-S",
        entity_type="Person",
        label="Sunil Shetty",
        case_ids=["CASE-502"],
        properties={
            "full_name": "Sunil Shetty",
            "father_name": "R. Shetty",
            "age": 41,
            "vehicle": "KA-01-AB-1001",
            "address": "4th Block Jayanagar",
            "role": "Accused (FIR 502/2026)",
        },
        source_records=[
            NexusSourceRecord(
                id="SRC-FIR-502",
                batch_id="BATCH-2026-08-24",
                source_type="FIR",
                locator="fir_502_2026.pdf — page 2, row 8",
                raw_excerpt="Accused: Sunil Shetty, s/o R. Shetty, age 41, res. 4th Block Jayanagar. Vehicle: KA-01-AB-1001.",
                occurred_at="2026-04-18T14:40:00Z",
            )
        ],
    ),
    reasons=[
        CandidateReason(field="vehicle", detail="Vehicle registration KA-01-AB-1001 matches across both seizure reports", weight=0.42),
        CandidateReason(field="father_name", detail="Father name 'R. Shetty' identical in both FIR accused sheets", weight=0.30),
        CandidateReason(field="locality", detail="Jayanagar locality match with sub-block specification", weight=0.16),
    ],
    conflicts=[
        CandidateConflict(field="name", left_value="Suniel Shetty", right_value="Sunil Shetty"),
    ],
)

ALL_INITIAL_CANDIDATES = [CANDIDATE_RC1_INIT, CANDIDATE_RC2_INIT, CANDIDATE_RC3_INIT]

class DemoState:
    def __init__(self) -> None:
        self.candidates = [copy.deepcopy(c) for c in ALL_INITIAL_CANDIDATES]
        self.lead = copy.deepcopy(BRIDGE_LEAD)
        self.decision_count = 0

    @property
    def candidate(self) -> ResolutionCandidate:
        return self.candidates[0]

    def reset(self) -> None:
        self.candidates = [copy.deepcopy(c) for c in ALL_INITIAL_CANDIDATES]
        self.lead = copy.deepcopy(BRIDGE_LEAD)
        self.decision_count = 0

    @property
    def is_resolved(self) -> bool:
        return any(c.status == "CONFIRMED" for c in self.candidates)

_demo_state = DemoState()

# ── Router Definition ──────────────────────────────────────────────────────────

def create_nexus_router() -> APIRouter:
    router = APIRouter(tags=["nexus"])

    @router.post("/nexus/ingest", response_model=NexusIngestResponse)
    def ingest_demo_files(
        req: NexusIngestRequest | None = None,
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
    ) -> NexusIngestResponse:
        _demo_state.reset()
        audit.record(
            event_type=AuditEventType.INGESTION_COMPLETED,
            actor_id=principal.user_id,
            entity_type="Batch",
            entity_id="BATCH-2026-08-24",
            details={"files_count": len(req.files) if req else 3},
        )
        return NexusIngestResponse(
            batch_id="BATCH-2026-08-24",
            source_type="GOLDEN_FUSION",
            ingested_count=3,
            extraction_summary=ExtractionSummary(
                persons=6, phones=3, accounts=2, events=1, relationships=10
            ),
            snapshot_id=SNAPSHOT_DIFF.before_snapshot_id,
        )

    @router.post("/nexus/demo/reset")
    def reset_demo_state(
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
    ) -> dict[str, str]:
        _demo_state.reset()
        audit.record(
            event_type=AuditEventType.SEED_COMPLETED,
            actor_id=principal.user_id,
            details={"status": "reset"},
        )
        return {"status": "reset"}

    @router.get("/nexus/resolution/candidates", response_model=list[ResolutionCandidate])
    def get_resolution_candidates(
        principal: Principal = Depends(get_principal),
    ) -> list[ResolutionCandidate]:
        return _demo_state.candidates

    @router.post("/nexus/resolution/{candidate_id}/decision", response_model=ResolutionDecisionResponse)
    def decide_resolution_candidate(
        candidate_id: str,
        body: ResolutionDecisionRequest,
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
    ) -> ResolutionDecisionResponse:
        target_cand = next((c for c in _demo_state.candidates if c.id == candidate_id), None)
        if not target_cand:
            raise HTTPException(status_code=404, detail="Candidate not found")

        status_map = {"CONFIRM": "CONFIRMED", "REJECT": "REJECTED", "DEFER": "DEFERRED"}
        target_cand.status = status_map[body.decision]
        target_cand.decided_at = datetime.now(timezone.utc).isoformat()
        target_cand.decided_by = body.decided_by or principal.user_id
        _demo_state.decision_count += 1

        audit.record(
            event_type=AuditEventType.ENTITY_RESOLUTION_EXECUTED,
            actor_id=principal.user_id,
            entity_type="ResolutionCandidate",
            entity_id=candidate_id,
            details={"decision": body.decision, "note": body.note},
        )

        return ResolutionDecisionResponse(
            candidate_id=target_cand.id,
            status=target_cand.status,
            affected_node_ids=SNAPSHOT_DIFF.added_node_ids if body.decision == "CONFIRM" else [],
            new_snapshot_id=SNAPSHOT_DIFF.after_snapshot_id if body.decision == "CONFIRM" else None,
        )

    @router.get("/nexus/network", response_model=NexusNetworkResponse)
    def get_nexus_network(
        snapshot: Literal["before", "after"] = Query("before"),
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
    ) -> NexusNetworkResponse:
        use_after = snapshot == "after" and _demo_state.is_resolved
        if snapshot == "after" and not _demo_state.is_resolved:
            raise HTTPException(
                status_code=409,
                detail='The "after" snapshot only exists after a resolution is confirmed.',
            )

        nodes = AFTER_NODES if use_after else BEFORE_NODES
        edges = AFTER_EDGES if use_after else BEFORE_EDGES
        snapshot_id = SNAPSHOT_DIFF.after_snapshot_id if use_after else SNAPSHOT_DIFF.before_snapshot_id

        audit.record(
            event_type=AuditEventType.NETWORK_EXPLORED,
            actor_id=principal.user_id,
            details={"snapshot": snapshot, "total_nodes": len(nodes), "total_edges": len(edges)},
        )

        return NexusNetworkResponse(
            snapshot_id=snapshot_id,
            state="after" if use_after else "before",
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
        )

    @router.get("/nexus/network/diff", response_model=SnapshotDiffResponse)
    def get_snapshot_diff(
        principal: Principal = Depends(get_principal),
    ) -> SnapshotDiffResponse:
        if not _demo_state.is_resolved:
            raise HTTPException(
                status_code=409,
                detail="No diff available yet — confirm a resolution candidate first.",
            )
        return SNAPSHOT_DIFF

    @router.get("/nexus/relationships/{rel_id}/evidence", response_model=NexusEdgeEvidenceResponse)
    def get_relationship_evidence(
        rel_id: str,
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
    ) -> NexusEdgeEvidenceResponse:
        edge_map = {e.id: e for e in AFTER_EDGES + BEFORE_EDGES}
        edge = edge_map.get(rel_id)
        if not edge:
            raise HTTPException(
                status_code=404,
                detail=f"Evidence chain for relationship {rel_id} is unavailable in this snapshot.",
            )

        rec_ids = edge.properties.get("evidence_ids", [])
        records = [RAW_SOURCES[rid] for rid in rec_ids if rid in RAW_SOURCES]

        node_labels = {n.id: n.label for n in BEFORE_NODES + AFTER_NODES}

        derivation_chain: list[DerivationStep] = (
            [DerivationStep(step=1, rule="direct_import", inputs=rec_ids)]
            if edge.derivation_class == "FACT"
            else [
                DerivationStep(step=1, rule="entity_resolution.confirm", inputs=["RC-1"]),
                DerivationStep(step=2, rule="projection.link_entities", inputs=rec_ids),
            ]
        )

        audit.record(
            event_type=AuditEventType.EVIDENCE_VIEWED,
            actor_id=principal.user_id,
            entity_type="Relationship",
            entity_id=rel_id,
            details={"derivation_class": edge.derivation_class, "records_count": len(records)},
        )

        return NexusEdgeEvidenceResponse(
            relationship_id=edge.id,
            edge_type=edge.edge_type,
            source_label=node_labels.get(edge.source_id, edge.source_id),
            target_label=node_labels.get(edge.target_id, edge.target_id),
            derivation_class=edge.derivation_class,
            confidence=edge.confidence,
            recorded_at=edge.recorded_at,
            source_records=records,
            derivation_chain=derivation_chain,
        )

    @router.get("/nexus/path", response_model=NexusPathResponse)
    def find_nexus_path(
        source: str = Query("", description="Source node or case identifier"),
        target: str = Query("", description="Target node or case identifier"),
        max_depth: int = Query(6, ge=1, le=10, description="Maximum BFS traversal depth"),
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
    ) -> NexusPathResponse:
        src = (source or "").strip()
        tgt = (target or "").strip()

        if not src or not tgt:
            return NexusPathResponse(
                found=False,
                source_id=src,
                target_id=tgt,
                node_ids=[],
                edge_ids=[],
                hops=0,
                explanation="Source and target entity identifiers are required.",
                evidence_ids=[],
            )

        if src == tgt:
            return NexusPathResponse(
                found=False,
                source_id=src,
                target_id=tgt,
                node_ids=[src],
                edge_ids=[],
                hops=0,
                explanation=f"Source and target entities are identical ('{src}'). No traversal required.",
                evidence_ids=[],
            )

        current_nodes = AFTER_NODES if _demo_state.is_resolved else BEFORE_NODES
        current_edges = AFTER_EDGES if _demo_state.is_resolved else BEFORE_EDGES
        nodes_by_id = {n.id: n for n in current_nodes}

        # Case-insensitive / label fallback lookup
        def find_node(val: str) -> NexusGraphNode | None:
            if val in nodes_by_id:
                return nodes_by_id[val]
            val_lower = val.lower()
            for n in current_nodes:
                if n.id.lower() == val_lower or n.label.lower() == val_lower:
                    return n
                if n.properties.get("fir_number", "").lower() == val_lower:
                    return n
            return None

        src_node = find_node(src)
        tgt_node = find_node(tgt)

        if not src_node:
            return NexusPathResponse(
                found=False,
                source_id=src,
                target_id=tgt,
                node_ids=[],
                edge_ids=[],
                hops=0,
                explanation=f"Source entity '{src}' was not found in the active investigation graph snapshot.",
                evidence_ids=[],
            )

        if not tgt_node:
            return NexusPathResponse(
                found=False,
                source_id=src,
                target_id=tgt,
                node_ids=[],
                edge_ids=[],
                hops=0,
                explanation=f"Target entity '{tgt}' was not found in the active investigation graph snapshot.",
                evidence_ids=[],
            )

        resolved_src_id = src_node.id
        resolved_tgt_id = tgt_node.id

        if resolved_src_id == resolved_tgt_id:
            return NexusPathResponse(
                found=False,
                source_id=resolved_src_id,
                target_id=resolved_tgt_id,
                node_ids=[resolved_src_id],
                edge_ids=[],
                hops=0,
                explanation="Source and target resolve to the same node in the graph.",
                evidence_ids=[],
            )

        # Build bidirectional adjacency map from active snapshot edges
        # adj[node_id] = list of (neighbor_id, edge_id, edge_type, evidence_ids)
        adj: dict[str, list[tuple[str, str, str, list[str]]]] = {}
        for edge in current_edges:
            ev_list = edge.properties.get("evidence_ids", []) if edge.properties else []
            if not isinstance(ev_list, list):
                ev_list = [str(ev_list)]
            adj.setdefault(edge.source_id, []).append((edge.target_id, edge.id, edge.edge_type, ev_list))
            adj.setdefault(edge.target_id, []).append((edge.source_id, edge.id, edge.edge_type, ev_list))

        # BFS shortest path search
        from collections import deque
        queue: deque[tuple[str, list[str], list[str], list[str]]] = deque([
            (resolved_src_id, [resolved_src_id], [], [])
        ])
        visited: set[str] = {resolved_src_id}
        found_path: tuple[list[str], list[str], list[str]] | None = None

        while queue:
            curr, path_nodes, path_edges, path_evs = queue.popleft()
            if len(path_nodes) - 1 >= max_depth:
                continue

            for nxt, edge_id, edge_type, evs in adj.get(curr, []):
                if nxt in visited:
                    continue
                next_nodes = [*path_nodes, nxt]
                next_edges = [*path_edges, edge_id]
                next_evs = [*path_evs, *evs]

                if nxt == resolved_tgt_id:
                    found_path = (next_nodes, next_edges, next_evs)
                    break

                visited.add(nxt)
                queue.append((nxt, next_nodes, next_edges, next_evs))

            if found_path:
                break

        if found_path:
            p_nodes, p_edges, p_evs = found_path
            hops = len(p_nodes) - 1
            unique_evidence = list(dict.fromkeys(p_evs))

            # Golden demo narrative when resolved FIR 141 <-> FIR 207 is matched
            if _demo_state.is_resolved and (
                (resolved_src_id in ("CASE-141", "CASE-207"))
                and (resolved_tgt_id in ("CASE-141", "CASE-207"))
            ):
                explanation = (
                    "FIR 141/2026 and FIR 207/2026 are connected through the confirmed entity "
                    "'Rafiq Khan / Rafiq Ahmed' (candidate RC-1), accused in both cases and reachable "
                    "on phone +91 98450 11223 in both CDR pulls."
                )
            else:
                labels = [nodes_by_id[nid].label if nid in nodes_by_id else nid for nid in p_nodes]
                explanation = f"Discovered {hops}-hop evidence connection: {' ➔ '.join(labels)}."

            audit.record(
                event_type=AuditEventType.GRAPH_QUERY_EXECUTED,
                actor_id=principal.user_id,
                details={
                    "path_found": True,
                    "source": resolved_src_id,
                    "target": resolved_tgt_id,
                    "hops": hops,
                    "nodes": p_nodes,
                },
            )

            return NexusPathResponse(
                found=True,
                source_id=resolved_src_id,
                target_id=resolved_tgt_id,
                node_ids=p_nodes,
                edge_ids=p_edges,
                hops=hops,
                explanation=explanation,
                evidence_ids=unique_evidence,
            )

        # Path not found within depth limit
        if not _demo_state.is_resolved:
            explanation = (
                f"No connection found between '{src_node.label}' and '{tgt_node.label}' in the unresolved graph state. "
                "Confirm pending entity resolution candidate RC-1 to reveal the hidden cross-case bridge."
            )
        else:
            explanation = (
                f"No connection found between '{src_node.label}' and '{tgt_node.label}' within {max_depth} hops "
                "in the current investigation snapshot."
            )

        return NexusPathResponse(
            found=False,
            source_id=resolved_src_id,
            target_id=resolved_tgt_id,
            node_ids=[],
            edge_ids=[],
            hops=0,
            explanation=explanation,
            evidence_ids=[],
        )

    @router.get("/nexus/leads", response_model=list[NexusLead])
    def get_leads(
        principal: Principal = Depends(get_principal),
    ) -> list[NexusLead]:
        return [_demo_state.lead] if _demo_state.is_resolved else []

    @router.post("/nexus/leads/{lead_id}/decision", response_model=NexusLead)
    def decide_lead(
        lead_id: str,
        body: NexusLeadDecisionRequest,
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
    ) -> NexusLead:
        if lead_id != _demo_state.lead.id:
            raise HTTPException(status_code=404, detail="Lead not found")

        _demo_state.lead.status = "ACCEPTED" if body.decision == "ACCEPT" else "REJECTED"
        _demo_state.lead.decided_at = datetime.now(timezone.utc).isoformat()
        _demo_state.lead.decided_by = body.decided_by or principal.user_id
        _demo_state.lead.decision_note = body.note

        audit.record(
            event_type=AuditEventType.ENTITY_RESOLUTION_EXECUTED,
            actor_id=principal.user_id,
            entity_type="Lead",
            entity_id=lead_id,
            details={"decision": body.decision, "note": body.note},
        )

        return _demo_state.lead

    @router.post("/nexus/copilot/query", response_model=NexusCopilotResponse)
    def query_copilot(
        body: dict[str, Any],
        principal: Principal = Depends(get_principal),
        audit: AuditService = Depends(get_audit_service),
    ) -> NexusCopilotResponse:
        q = (body.get("query") or "").lower()

        # Refusal Gate Check
        if re.search(r"(guilt|guilty|criminal|mastermind|convict|punish)", q):
            audit.record(
                event_type=AuditEventType.COPILOT_REFUSED,
                actor_id=principal.user_id,
                details={"query": body.get("query"), "reason": "Guilt prediction prohibited"},
            )
            return NexusCopilotResponse(
                query=body.get("query", ""),
                answer="I cannot infer guilt, innocence, or risk of reoffending. These are matters of judicial determination.",
                is_refusal=True,
                refusal_reason="Deterministic refusal gate: predictive guilt scoring is prohibited.",
                evidence_ids=[],
                reasoning_path=[],
            )

        # Connection Explanation Intent
        if re.search(r"(connect|link|bridge|relat)", q):
            if _demo_state.is_resolved:
                ans = (
                    "FIR 141/2026 and FIR 207/2026 connect through the confirmed alias 'Rafiq Khan / Rafiq Ahmed': "
                    "same phone +91 98450 11223 in both CDR pulls, same father's name in both FIRs, and repeated transfers "
                    "from ACC-9914 (Deepak Rao) into ACC-7731 held by Rafiq."
                )
                ev_ids = ["SRC-FIR-141", "SRC-FIR-207", "SRC-CDR-A12", "SRC-CDR-B31", "SRC-TXN-55"]
                rpath = [
                    "Entity resolution RC-1 CONFIRMED → person unified (P-RAFIQ)",
                    "P-RAFIQ —ACCUSED_IN→ CASE-141 and CASE-207",
                    "ACC-9914 —TRANSFERRED_TO→ ACC-7731 (2 transactions)",
                ]
            else:
                ans = "No connection is currently visible. There is one pending entity-resolution candidate (RC-1) that, if confirmed, may link the two cases."
                ev_ids = ["SRC-FIR-141", "SRC-FIR-207"]
                rpath = ["Resolution candidate RC-1 status: PENDING"]

            audit.record(
                event_type=AuditEventType.COPILOT_ANSWERED,
                actor_id=principal.user_id,
                details={"query": body.get("query"), "resolved": _demo_state.is_resolved},
            )
            return NexusCopilotResponse(
                query=body.get("query", ""),
                answer=ans,
                is_refusal=False,
                evidence_ids=ev_ids,
                reasoning_path=rpath,
            )

        # General Intent
        audit.record(
            event_type=AuditEventType.COPILOT_ANSWERED,
            actor_id=principal.user_id,
            details={"query": body.get("query")},
        )
        return NexusCopilotResponse(
            query=body.get("query", ""),
            answer="This query was parsed against the investigation graph. Ask 'How are the two cases connected?' for the grounded connection explanation.",
            is_refusal=False,
            evidence_ids=[],
            reasoning_path=["Intent: general_info — no specific graph claim to ground"],
        )

    @router.get("/nexus/search", response_model=NexusSearchResponse)
    def nexus_search(
        q: str = Query(""),
        principal: Principal = Depends(get_principal),
        repo: InMemoryBackendRepository = Depends(get_repository),
    ) -> NexusSearchResponse:
        query_raw = q.strip()
        query_str = query_raw.lower()
        if not query_str:
            return NexusSearchResponse(query="", cases=[], entities=[])

        norm_query = re.sub(r"[^\w]", "", query_str)

        # Build candidate nodes list starting with demo nodes, then appending repo GraphStore nodes (deduplicated by ID)
        candidate_nodes: list[NexusGraphNode] = []
        seen_ids: set[str] = set()

        demo_nodes = AFTER_NODES if _demo_state.is_resolved else BEFORE_NODES
        for n in demo_nodes:
            if n.id not in seen_ids:
                seen_ids.add(n.id)
                candidate_nodes.append(n)

        graph_store = repo.to_graph_store()
        for nid, node_rec in graph_store.nodes.items():
            if nid in seen_ids:
                continue
            seen_ids.add(nid)

            props = node_rec.properties or {}
            etype = node_rec.entity_type

            # Derive primary label for GraphStore node records
            if etype == "Case":
                label = str(props.get("fir_number") or props.get("title") or nid)
            elif etype == "Person":
                label = str(props.get("full_name") or nid)
            elif etype == "Phone":
                label = str(props.get("phone_number") or props.get("number") or nid)
            elif etype == "Account":
                label = str(props.get("account_number") or props.get("bank") or nid)
            elif etype == "Vehicle":
                label = str(props.get("vehicle_number") or props.get("registration") or nid)
            elif etype == "Location":
                label = str(props.get("address_text") or props.get("district") or nid)
            elif etype == "Evidence":
                label = str(props.get("evidence_number") or props.get("description") or nid)
            else:
                label = str(props.get("full_name") or props.get("title") or props.get("name") or props.get("label") or nid)

            case_ids_list = [str(props["case_id"])] if "case_id" in props and props["case_id"] else []

            candidate_nodes.append(
                NexusGraphNode(
                    id=nid,
                    entity_type=etype,
                    label=label,
                    case_ids=case_ids_list,
                    properties=props,
                )
            )

        def matches_node(n: NexusGraphNode) -> bool:
            # 1. Substring match on node ID, label, and property values
            if query_str in n.id.lower() or query_str in n.label.lower():
                return True
            for v in n.properties.values():
                val_str = str(v).lower()
                if query_str in val_str:
                    return True

            # 2. Normalized alphanumeric match for identifiers (phones, accounts, vehicles, FIRs, IDs)
            if norm_query and len(norm_query) >= 2:
                norm_id = re.sub(r"[^\w]", "", n.id.lower())
                if norm_query in norm_id:
                    return True
                norm_label = re.sub(r"[^\w]", "", n.label.lower())
                if norm_query in norm_label:
                    return True
                for v in n.properties.values():
                    norm_val = re.sub(r"[^\w]", "", str(v).lower())
                    if norm_query in norm_val:
                        return True
            return False

        def build_subtext(n: NexusGraphNode) -> str | None:
            props = n.properties or {}
            etype = n.entity_type
            case_info = f" • FIR: {', '.join(n.case_ids)}" if n.case_ids else ""

            if etype == "Phone":
                num = props.get("phone_number") or props.get("number") or props.get("phone") or n.label
                seen = props.get("seen_in")
                return f"Phone: {num}{f' ({seen})' if seen else ''}{case_info}"
            elif etype == "Account":
                holder = props.get("holder")
                bank = props.get("bank")
                parts = []
                if holder:
                    parts.append(f"Holder: {holder}")
                if bank:
                    parts.append(bank)
                txt = " • ".join(parts) if parts else "Bank Account"
                return f"{txt}{case_info}"
            elif etype == "Person":
                role = props.get("role")
                phone = props.get("phone_number") or props.get("phone")
                vehicle = props.get("vehicle_number") or props.get("vehicle")
                aliases = props.get("aliases")
                parts = []
                if role:
                    parts.append(str(role))
                if phone:
                    parts.append(f"Phone: {phone}")
                if vehicle:
                    parts.append(f"Vehicle: {vehicle}")
                if aliases and isinstance(aliases, list) and aliases:
                    parts.append(f"Aliases: {', '.join(aliases)}")
                txt = " • ".join(parts) if parts else "Person"
                return f"{txt}{case_info}"
            elif etype == "Vehicle":
                reg = props.get("vehicle_number") or props.get("registration")
                owner = props.get("owner")
                parts = []
                if reg:
                    parts.append(f"Reg: {reg}")
                if owner:
                    parts.append(f"Owner: {owner}")
                txt = " • ".join(parts) if parts else "Vehicle"
                return f"{txt}{case_info}"
            elif etype == "Location":
                district = props.get("district")
                addr = props.get("address_text") or props.get("address")
                parts = [p for p in (district, addr) if p]
                txt = " • ".join(parts) if parts else "Location"
                return f"{txt}{case_info}"

            desc = props.get("description") or props.get("role")
            if desc:
                return f"{desc}{case_info}"
            return f"{etype}{case_info}" if n.case_ids else None

        cases = [
            SearchCaseItem(
                id=n.id,
                fir_number=str(n.properties.get("fir_number") or n.label),
                title=str(n.properties.get("title") or n.properties.get("fir_number") or n.label),
                score=1.0,
            )
            for n in candidate_nodes
            if n.entity_type == "Case" and matches_node(n)
        ]

        entities = [
            SearchEntityItem(
                id=n.id,
                label=n.label,
                entity_type=n.entity_type,
                case_ids=n.case_ids,
                score=1.0,
                subtext=build_subtext(n),
            )
            for n in candidate_nodes
            if n.entity_type != "Case" and matches_node(n)
        ]

        return NexusSearchResponse(query=q, cases=cases, entities=entities)

    @router.get("/nexus/sources/{source_id}", response_model=NexusSourceRecord)
    def get_source_record(
        source_id: str,
        principal: Principal = Depends(get_principal),
    ) -> NexusSourceRecord:
        record = RAW_SOURCES.get(source_id)
        if not record:
            raise HTTPException(status_code=404, detail="Source record not found")
        return record

    return router
