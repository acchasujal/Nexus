"""
shared/contracts/api.py

Authoritative Python-side API contract types for CaseClock.
This file is owned by Lane 4 (Sujal). No other lane may modify it without Lane 4 sign-off.

RULE: If you need a type that doesn't exist here, open an issue tagged risk/contract-change.
Do NOT define local types that duplicate or diverge from these — import from here instead.

Kept in sync with shared/contracts/api.ts (TypeScript mirror).
Every change is logged in shared/contracts/CHANGELOG.md.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel


# ── Enums ─────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    IO = "IO"     # Investigating Officer
    SHO = "SHO"   # Station House Officer
    SP = "SP"     # Superintendent of Police / DCP


class ClockStatus(str, Enum):
    GREEN = "green"    # > 14 days remaining
    AMBER = "amber"    # 7–14 days remaining
    RED = "red"        # < 7 days remaining
    OVERDUE = "overdue"  # Deadline passed without chargesheet


class DependencyStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


# ── Clock Instance ─────────────────────────────────────────────────────────────

class ClockInstanceResponse(BaseModel):
    """A single statutory deadline instance attached to a case."""
    id: str
    case_id: str
    clock_type: str             # from shared/constants/clock_types.ClockType
    start_date: datetime        # Date of arrest / triggering event
    deadline_date: datetime     # Computed deadline (start + duration_days)
    days_remaining: int         # Computed at query time, not stored
    status: ClockStatus
    bnss_reference: str         # Must include [VERIFIED] or [UNVERIFIED]


# ── Dependency ─────────────────────────────────────────────────────────────────

class DependencyResponse(BaseModel):
    """A named, specific outstanding evidentiary item blocking chargesheet filing."""
    id: str
    case_id: str
    name: str               # e.g. "FSL report", "CDR analysis", "Section 183 statement"
    status: DependencyStatus
    days_stale: int         # How long this dependency has been unresolved
    assigned_to: Optional[str] = None


# ── Case ──────────────────────────────────────────────────────────────────────

class CaseSummaryResponse(BaseModel):
    """Lightweight case representation for the risk-ranked worklist."""
    id: str
    fir_number: str
    station_name: str
    offence_category: str
    updated_at: datetime
    clock: ClockInstanceResponse
    unresolved_dependency_count: int
    risk_rank: int          # Computed: lower = more urgent


class CaseDetailResponse(BaseModel):
    """Full case object for the Case Detail screen."""
    id: str
    fir_number: str
    station_name: str
    offence_category: str
    clocks: list[ClockInstanceResponse]
    dependencies: list[DependencyResponse]
    # Network and similarity populated by separate endpoints to avoid over-fetching
    # co_accused populated from graph traversal — never LLM-inferred


# ── Escalation ────────────────────────────────────────────────────────────────

class EscalationResponse(BaseModel):
    """An auto-generated escalation notice."""
    id: str
    case_id: str
    triggered_at: datetime
    reason: str             # Templated from graph-derived facts, never LLM prose
    routed_to_rank: str     # Supervisor rank derived from Officer/Unit hierarchy
    routed_to_officer_id: str
    resolved: bool


# ── Copilot ───────────────────────────────────────────────────────────────────

class CopilotQueryRequest(BaseModel):
    """NL query from the investigator."""
    query: str
    case_id: Optional[str] = None   # If scoped to a specific case
    user_role: UserRole


class CopilotQueryResponse(BaseModel):
    """
    Grounded copilot response.
    If confidence is low, the system refuses rather than guesses.
    Refusal is a first-class, tested behavior — not an afterthought.
    """
    answer: Optional[str] = None    # None if refused
    refused: bool
    refusal_reason: Optional[str] = None   # Templated, not LLM-generated
    reasoning_path: Optional[list[str]] = None   # Node/edge path that produced the answer
    confidence: float       # 0.0–1.0; below threshold → refused


# ── Auth ──────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole


# ── District Rollup ────────────────────────────────────────────────────────────

class StationRanking(BaseModel):
    station_name: str
    total: int
    critical: int


class DistrictRollupResponse(BaseModel):
    total_cases: int
    red_clocks: int
    amber_clocks: int
    stale_dependencies: int
    station_rankings: list[StationRanking]


# ── System Deadline Monitor ───────────────────────────────────────────────────

class CronScheduleInfo(BaseModel):
    type: str = "recursive"
    interval_minutes: int = 15


class CronLastRunSummary(BaseModel):
    run_id: str
    completed_at: str
    cases_scanned: int
    clocks_evaluated: int
    state_transitions: int
    escalations_created: int
    errors: int
    duration_ms: float


class DeadlineMonitorStatusResponse(BaseModel):
    status: str  # "active" | "delayed" | "unavailable"
    schedule: CronScheduleInfo
    last_run: Optional[CronLastRunSummary] = None


# ── Document Intelligence ─────────────────────────────────────────────────────

class CandidateFactField(BaseModel):
    value: str
    confidence: Optional[float] = None
    source_text: Optional[str] = None


class DocumentCandidateFacts(BaseModel):
    fir_number: Optional[CandidateFactField] = None
    police_station: Optional[CandidateFactField] = None
    incident_date: Optional[CandidateFactField] = None
    fir_registration_date: Optional[CandidateFactField] = None
    offence_sections: list[str] = []
    offence_category: Optional[CandidateFactField] = None
    accused_names: list[str] = []
    complainant_name: Optional[CandidateFactField] = None


class ClockPreviewResponse(BaseModel):
    applicable_rule: str
    duration_days: int
    calculated_deadline: str
    days_remaining: int
    predicted_status: ClockStatus
    bnss_reference: str
    requires_confirmation: bool = True


class DocumentScanRequest(BaseModel):
    """JSON body for document scan — file encoded as base64 to avoid python-multipart dependency."""
    filename: str
    content_type: str = "application/pdf"
    document_type: str = "fir"
    file_base64: str  # base64-encoded file bytes


class DocumentScanResponse(BaseModel):
    document_id: str
    case_id: str
    document_type: str
    original_filename: str
    storage_reference: str
    uploaded_at: str
    ocr_status: str  # "success" | "failed" | "partial"
    ocr_text: str
    ocr_confidence: Optional[float] = None
    candidate_facts: DocumentCandidateFacts
    clock_preview: Optional[ClockPreviewResponse] = None
    review_status: str  # "pending_review" | "confirmed"


class DocumentConfirmRequest(BaseModel):
    fir_number: Optional[str] = None
    police_station: Optional[str] = None
    fir_registration_date: Optional[str] = None
    offence_category: Optional[str] = None
    offence_sections: Optional[list[str]] = None


class DocumentConfirmResponse(BaseModel):
    status: str = "ok"
    document_id: str
    case_id: str
    review_status: str = "confirmed"
    updated_clock: ClockInstanceResponse
    message: str
