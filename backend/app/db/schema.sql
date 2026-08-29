-- ============================================================================
-- NEXUS Criminal Intelligence Platform — PostgreSQL Schema (SIH 2026 PS 26189)
-- Compatible with PostgreSQL 15+ / 18+ on Render
-- ============================================================================

-- 1. Nodes Table
CREATE TABLE IF NOT EXISTS nodes (
    id VARCHAR(255) PRIMARY KEY,
    entity_type VARCHAR(64) NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_nodes_entity_type ON nodes(entity_type);
CREATE INDEX IF NOT EXISTS idx_nodes_properties_gin ON nodes USING GIN (properties);

-- 2. Edges Table
CREATE TABLE IF NOT EXISTS edges (
    id VARCHAR(255) PRIMARY KEY,
    source_id VARCHAR(255) NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id VARCHAR(255) NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(64) NOT NULL,
    weight DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    start_time TIMESTAMPTZ,
    end_time TIMESTAMPTZ,
    source_record_id VARCHAR(255),
    derivation_class VARCHAR(64),
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    provenance JSONB NOT NULL DEFAULT '{}'::jsonb,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type);
CREATE INDEX IF NOT EXISTS idx_edges_properties_gin ON edges USING GIN (properties);

-- 3. Source Records Table (FIRs, CDR rows, Bank transaction receipts)
CREATE TABLE IF NOT EXISTS source_records (
    id VARCHAR(255) PRIMARY KEY,
    batch_id VARCHAR(255),
    source_type VARCHAR(64) NOT NULL,
    locator VARCHAR(512),
    raw_excerpt TEXT,
    hash VARCHAR(128),
    occurred_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_source_records_batch ON source_records(batch_id);
CREATE INDEX IF NOT EXISTS idx_source_records_type ON source_records(source_type);

-- 4. Audit Events Table (Immutable Section 63 BSA 2023 Audit Trail)
CREATE TABLE IF NOT EXISTS audit_events (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    user_role VARCHAR(64) NOT NULL,
    action VARCHAR(128) NOT NULL,
    entity_type VARCHAR(64),
    entity_id VARCHAR(255),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action);

-- 5. Review Candidates Table (Entity Resolution Review Queue)
CREATE TABLE IF NOT EXISTS review_candidates (
    id VARCHAR(255) PRIMARY KEY,
    incoming_record_id VARCHAR(255) NOT NULL,
    candidate_node_id VARCHAR(255) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'PENDING',
    matched_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_breakdown JSONB NOT NULL DEFAULT '{}'::jsonb,
    incoming_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_candidates_status ON review_candidates(status);

-- 6. Ingestion Batches Table
CREATE TABLE IF NOT EXISTS ingestion_batches (
    batch_id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(64) NOT NULL DEFAULT 'COMPLETED',
    summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. System Metadata Table (Key-Value configuration & versioning)
CREATE TABLE IF NOT EXISTS system_metadata (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
