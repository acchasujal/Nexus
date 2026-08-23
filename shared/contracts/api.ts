/**
 * shared/contracts/api.ts
 *
 * Authoritative TypeScript-side API contract types for CaseClock.
 * This file is owned by Lane 4 (Sujal). No other lane may modify it without Lane 4 sign-off.
 *
 * RULE: Import types from here — do NOT redeclare them in frontend/src/types/.
 * If you need a type that doesn't exist here, open an issue tagged risk/contract-change.
 *
 * Kept in sync with shared/contracts/api.py (Python mirror).
 * Every change is logged in shared/contracts/CHANGELOG.md.
 */

// ── Enums ────────────────────────────────────────────────────────────────────

export type UserRole = "IO" | "SHO" | "SP";

export type ClockStatus = "green" | "amber" | "red" | "overdue";

export type DependencyStatus = "pending" | "resolved" | "escalated";

// ── Clock Instance ────────────────────────────────────────────────────────────

export interface ClockInstanceResponse {
  id: string;
  case_id: string;
  clock_type: string;        // from shared/constants/clock_types.ClockType
  start_date: string;        // ISO 8601
  deadline_date: string;     // ISO 8601
  days_remaining: number;    // Computed at query time
  status: ClockStatus;
  bnss_reference: string;    // Must include [VERIFIED] or [UNVERIFIED]
}

// ── Dependency ────────────────────────────────────────────────────────────────

export interface DependencyResponse {
  id: string;
  case_id: string;
  name: string;              // e.g. "FSL report", "CDR analysis"
  status: DependencyStatus;
  days_stale: number;
  assigned_to?: string;
}

// ── Case ──────────────────────────────────────────────────────────────────────

export interface CaseSummaryResponse {
  id: string;
  fir_number: string;
  station_name: string;
  offence_category: string;
  updated_at: string;        // ISO 8601
  clock: ClockInstanceResponse;
  unresolved_dependency_count: number;
  risk_rank: number;         // Lower = more urgent
}

export interface CaseDetailResponse {
  id: string;
  fir_number: string;
  station_name: string;
  offence_category: string;
  clocks: ClockInstanceResponse[];
  dependencies: DependencyResponse[];
}

// ── Escalation ────────────────────────────────────────────────────────────────

export interface EscalationResponse {
  id: string;
  case_id: string;
  triggered_at: string;      // ISO 8601
  reason: string;            // Templated from graph-derived facts, never LLM prose
  routed_to_rank: string;
  routed_to_officer_id: string;
  resolved: boolean;
}

// ── Copilot ───────────────────────────────────────────────────────────────────

export interface CopilotQueryRequest {
  query: string;
  case_id?: string;
  user_role: UserRole;
}

export interface CopilotQueryResponse {
  answer?: string;           // undefined if refused
  refused: boolean;
  refusal_reason?: string;   // Templated, not LLM-generated
  reasoning_path?: string[]; // Node/edge path that produced the answer
  confidence: number;        // 0.0–1.0
}

// ── AI Chat (POST /api/chat) ──────────────────────────────────────────────────

export interface ChatMessage {
  role: "system" | "user" | "assistant" | "tool";
  content: string;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  case_id?: string;
  history?: ChatMessage[];
  metadata?: Record<string, unknown>;
}

export interface ChatResponse {
  message: string;
  conversation_id: string;
  intent?: {
    name: string;
    confidence?: number;
    entities?: Array<{ type: string; value: unknown }>;
  };
  entities?: Array<{ type: string; value: unknown }>;
  data?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}


// ── Auth ──────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  role: UserRole;
}

// ── System Deadline Monitor ───────────────────────────────────────────────────

export interface CronScheduleInfo {
  type: string;
  interval_minutes: number;
}

export interface CronLastRunSummary {
  run_id: string;
  completed_at: string;
  cases_scanned: number;
  clocks_evaluated: number;
  state_transitions: number;
  escalations_created: number;
  errors: number;
  duration_ms: number;
}

export interface DeadlineMonitorStatusResponse {
  status: "active" | "delayed" | "unavailable";
  schedule: CronScheduleInfo;
  last_run: CronLastRunSummary | null;
}

// ── Document Intelligence ─────────────────────────────────────────────────────

export interface CandidateFactField {
  value: string;
  confidence?: number;
  source_text?: string;
}

export interface DocumentCandidateFacts {
  fir_number?: CandidateFactField;
  police_station?: CandidateFactField;
  incident_date?: CandidateFactField;
  fir_registration_date?: CandidateFactField;
  offence_sections: string[];
  offence_category?: CandidateFactField;
  accused_names: string[];
  complainant_name?: CandidateFactField;
}

export interface ClockPreviewResponse {
  applicable_rule: string;
  duration_days: number;
  calculated_deadline: string;
  days_remaining: number;
  predicted_status: ClockStatus;
  bnss_reference: string;
  requires_confirmation: boolean;
}

export interface DocumentScanRequest {
  filename: string;
  content_type?: string;
  document_type?: string;
  file_base64: string; // base64-encoded file bytes
}

export interface DocumentScanResponse {
  document_id: string;
  case_id: string;
  document_type: string;
  original_filename: string;
  storage_reference: string;
  uploaded_at: string;
  ocr_status: "success" | "failed" | "partial";
  ocr_text: string;
  ocr_confidence: number | null;
  candidate_facts: DocumentCandidateFacts;
  clock_preview?: ClockPreviewResponse | null;
  review_status: "pending_review" | "confirmed";
}

export interface DocumentConfirmRequest {
  fir_number?: string;
  police_station?: string;
  fir_registration_date?: string;
  offence_category?: string;
  offence_sections?: string[];
}

export interface DocumentConfirmResponse {
  status: string;
  document_id: string;
  case_id: string;
  review_status: string;
  updated_clock: ClockInstanceResponse;
  message: string;
}
