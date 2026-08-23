"""backend/app/db/migrations/schema.py

Catalyst Data Store schema definitions for CaseClock.

This module defines:
  1. The canonical DDL constants used to create tables (as SQL-like strings
     documented for Catalyst Data Store configuration).
  2. A MigrationLedger that tracks which migrations have been applied.
  3. A migration runner CLI entry point.

## Usage

Run migrations:
    python -m backend.app.db.migrations.schema migrate

Check status:
    python -m backend.app.db.migrations.schema status

## Catalyst Data Store Notes (from spike investigation)

- Catalyst Data Store is a hosted cloud SQL service.
- Tables are created via the Catalyst Console or API.
- This module documents the expected schema so it can be reproduced
  deterministically in any Catalyst project environment.
- FK enforcement and transaction support must be verified per spike (Phase 2).
"""

from __future__ import annotations

# ── Schema version ─────────────────────────────────────────────────────────────

SCHEMA_VERSION = "0001"

# ── Table definitions (Catalyst SQL-compatible DDL) ───────────────────────────
# Note: Catalyst Data Store uses MySQL-compatible syntax.
# These are documentation-grade DDL for Phase 2 Catalyst setup.

SCHEMA_DDL: list[tuple[str, str]] = [
    # migration ledger: tracks applied migrations
    ("schema_migration", """
CREATE TABLE IF NOT EXISTS schema_migration (
    version     VARCHAR(8)   NOT NULL PRIMARY KEY,
    applied_at  DATETIME     NOT NULL,
    description VARCHAR(255) NOT NULL
)
"""),
    # seed run ledger: tracks import batches
    ("seed_run", """
CREATE TABLE IF NOT EXISTS seed_run (
    id          VARCHAR(36)  NOT NULL PRIMARY KEY,
    checksum    VARCHAR(64)  NOT NULL,
    status      VARCHAR(16)  NOT NULL DEFAULT 'pending',
    started_at  DATETIME     NOT NULL,
    completed_at DATETIME    NULL,
    record_count INT          NULL
)
"""),
    # canonical case entity
    ("case", """
CREATE TABLE IF NOT EXISTS `case` (
    id                  VARCHAR(36)  NOT NULL PRIMARY KEY,
    fir_number          VARCHAR(64)  NOT NULL,
    police_station      VARCHAR(128) NOT NULL,
    district            VARCHAR(128) NOT NULL,
    offence_category    VARCHAR(64)  NOT NULL,
    case_stage          VARCHAR(32)  NOT NULL DEFAULT 'investigation',
    reported_at         DATETIME     NOT NULL,
    created_at          DATETIME     NOT NULL,
    updated_at          DATETIME     NOT NULL,
    INDEX idx_case_station_stage (police_station, case_stage, reported_at),
    INDEX idx_case_district (district, reported_at),
    INDEX idx_case_offence (offence_category, reported_at)
)
"""),
    # canonical person entity (roles are edges, not duplicated columns)
    ("person", """
CREATE TABLE IF NOT EXISTS person (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    full_name       VARCHAR(255)  NOT NULL,
    phone_number    VARCHAR(20)   NULL,
    address         TEXT          NULL,
    created_at      DATETIME      NOT NULL,
    updated_at      DATETIME      NOT NULL
)
"""),
    # canonical officer entity
    ("officer", """
CREATE TABLE IF NOT EXISTS officer (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    full_name       VARCHAR(255)  NOT NULL,
    badge_number    VARCHAR(32)   NULL,
    rank            VARCHAR(64)   NULL,
    unit_id         VARCHAR(36)   NULL,
    created_at      DATETIME      NOT NULL,
    updated_at      DATETIME      NOT NULL
)
"""),
    ("unit", """
CREATE TABLE IF NOT EXISTS unit (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    unit_name       VARCHAR(128)  NOT NULL,
    police_station  VARCHAR(128)  NULL,
    district        VARCHAR(128)  NULL,
    created_at      DATETIME      NOT NULL,
    updated_at      DATETIME      NOT NULL
)
"""),
    ("court", """
CREATE TABLE IF NOT EXISTS court (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    court_name      VARCHAR(255)  NOT NULL,
    district        VARCHAR(128)  NOT NULL,
    created_at      DATETIME      NOT NULL,
    updated_at      DATETIME      NOT NULL
)
"""),
    ("location", """
CREATE TABLE IF NOT EXISTS location (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    address         TEXT          NULL,
    district        VARCHAR(128)  NOT NULL,
    police_station  VARCHAR(128)  NULL,
    created_at      DATETIME      NOT NULL,
    updated_at      DATETIME      NOT NULL
)
"""),
    ("act", """
CREATE TABLE IF NOT EXISTS act (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    act_name        VARCHAR(255)  NOT NULL,
    year            INT           NULL,
    created_at      DATETIME      NOT NULL,
    updated_at      DATETIME      NOT NULL
)
"""),
    ("section", """
CREATE TABLE IF NOT EXISTS section (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    section_code    VARCHAR(32)   NOT NULL,
    description     TEXT          NULL,
    act_id          VARCHAR(36)   NULL,
    created_at      DATETIME      NOT NULL,
    updated_at      DATETIME      NOT NULL
)
"""),
    ("crime_head", """
CREATE TABLE IF NOT EXISTS crime_head (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    head_name       VARCHAR(128)  NOT NULL,
    created_at      DATETIME      NOT NULL,
    updated_at      DATETIME      NOT NULL
)
"""),
    ("crime_sub_head", """
CREATE TABLE IF NOT EXISTS crime_sub_head (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    sub_head_name   VARCHAR(128)  NOT NULL,
    crime_head_id   VARCHAR(36)   NULL,
    created_at      DATETIME      NOT NULL,
    updated_at      DATETIME      NOT NULL
)
"""),
    ("evidence", """
CREATE TABLE IF NOT EXISTS evidence (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    case_id         VARCHAR(36)   NOT NULL,
    evidence_type   VARCHAR(64)   NOT NULL,
    description     TEXT          NULL,
    collected_at    DATETIME      NULL,
    created_at      DATETIME      NOT NULL,
    updated_at      DATETIME      NOT NULL,
    INDEX idx_evidence_case (case_id)
)
"""),
    ("dependency", """
CREATE TABLE IF NOT EXISTS dependency (
    id                      VARCHAR(36)   NOT NULL PRIMARY KEY,
    case_id                 VARCHAR(36)   NOT NULL,
    dependency_type         VARCHAR(64)   NOT NULL,
    name                    VARCHAR(255)  NULL,
    status                  VARCHAR(16)   NOT NULL DEFAULT 'pending',
    requested_at            DATETIME      NOT NULL,
    due_at                  DATETIME      NULL,
    resolved_at             DATETIME      NULL,
    assigned_to_officer_id  VARCHAR(36)   NULL,
    created_at              DATETIME      NOT NULL,
    updated_at              DATETIME      NOT NULL,
    INDEX idx_dep_case (case_id, status, requested_at),
    INDEX idx_dep_status (status, requested_at)
)
"""),
    ("clock_instance", """
CREATE TABLE IF NOT EXISTS clock_instance (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    case_id         VARCHAR(36)   NOT NULL,
    clock_type      VARCHAR(64)   NOT NULL,
    start_date      DATETIME      NOT NULL,
    deadline_date   DATETIME      NOT NULL,
    bnss_reference  VARCHAR(128)  NOT NULL,
    rule_version    VARCHAR(16)   NOT NULL DEFAULT '1.0',
    created_at      DATETIME      NOT NULL,
    updated_at      DATETIME      NOT NULL,
    INDEX idx_clock_case (case_id, deadline_date),
    INDEX idx_clock_deadline (deadline_date)
)
"""),
    ("escalation_event", """
CREATE TABLE IF NOT EXISTS escalation_event (
    id                  VARCHAR(36)   NOT NULL PRIMARY KEY,
    case_id             VARCHAR(36)   NOT NULL,
    trigger_kind        VARCHAR(64)   NOT NULL,
    source_entity_id    VARCHAR(36)   NULL,
    rule_version        VARCHAR(16)   NOT NULL DEFAULT '1.0',
    threshold_date      DATETIME      NULL,
    reason              TEXT          NOT NULL,
    routed_to_rank      VARCHAR(16)   NOT NULL,
    routed_to_officer_id VARCHAR(36)  NOT NULL,
    triggered_at        DATETIME      NOT NULL,
    resolved            TINYINT(1)    NOT NULL DEFAULT 0,
    resolved_at         DATETIME      NULL,
    created_at          DATETIME      NOT NULL,
    updated_at          DATETIME      NOT NULL,
    UNIQUE KEY uq_esc_trigger (case_id, trigger_kind, source_entity_id, rule_version, threshold_date),
    INDEX idx_esc_case (case_id, resolved, triggered_at)
)
"""),
    ("conversation_log", """
CREATE TABLE IF NOT EXISTS conversation_log (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    actor_id        VARCHAR(36)   NOT NULL,
    case_id         VARCHAR(36)   NULL,
    intent          VARCHAR(64)   NULL,
    query_sanitized TEXT          NOT NULL,
    response_meta   JSON          NULL,
    refused         TINYINT(1)    NOT NULL DEFAULT 0,
    refusal_reason  VARCHAR(255)  NULL,
    request_id      VARCHAR(36)   NULL,
    occurred_at     DATETIME      NOT NULL,
    INDEX idx_conv_actor (actor_id, occurred_at)
)
"""),
    ("audit_event", """
CREATE TABLE IF NOT EXISTS audit_event (
    id              VARCHAR(36)   NOT NULL PRIMARY KEY,
    event_type      VARCHAR(64)   NOT NULL,
    actor_id        VARCHAR(36)   NULL,
    case_id         VARCHAR(36)   NULL,
    entity_type     VARCHAR(64)   NULL,
    entity_id       VARCHAR(36)   NULL,
    metadata        JSON          NULL,
    request_id      VARCHAR(36)   NULL,
    occurred_at     DATETIME      NOT NULL,
    INDEX idx_audit_occurred (occurred_at),
    INDEX idx_audit_actor (actor_id, occurred_at)
)
"""),
    # graph_edge: canonical relationship table
    ("graph_edge", """
CREATE TABLE IF NOT EXISTS graph_edge (
    id                  VARCHAR(36)   NOT NULL PRIMARY KEY,
    source_entity_type  VARCHAR(64)   NOT NULL,
    source_id           VARCHAR(36)   NOT NULL,
    relationship_type   VARCHAR(64)   NOT NULL,
    target_entity_type  VARCHAR(64)   NOT NULL,
    target_id           VARCHAR(36)   NOT NULL,
    storage_mode        VARCHAR(16)   NOT NULL DEFAULT 'persisted',
    created_at          DATETIME      NOT NULL,
    updated_at          DATETIME      NOT NULL,
    UNIQUE KEY uq_edge (source_entity_type, source_id, relationship_type, target_entity_type, target_id),
    INDEX idx_edge_source (source_id, relationship_type),
    INDEX idx_edge_target (target_id, relationship_type),
    INDEX idx_edge_rel (relationship_type, source_id, target_id)
)
"""),
]

# Ordered list of table names by dependency (entities before relationships)
TABLE_CREATION_ORDER = [
    "schema_migration", "seed_run",
    "unit", "act", "court", "location",
    "crime_head", "crime_sub_head",
    "case", "person", "officer",
    "section", "evidence",
    "dependency", "clock_instance",
    "escalation_event", "conversation_log", "audit_event",
    "graph_edge",
]


if __name__ == "__main__":
    """CLI entry point.  Usage: python -m backend.app.db.migrations.schema status"""
    import sys

    command = sys.argv[1] if len(sys.argv) > 1 else "status"

    if command == "status":
        print(f"Schema version: {SCHEMA_VERSION}")
        print(f"Tables defined: {len(SCHEMA_DDL)}")
        print("Status: Ready for Catalyst Data Store connection (Phase 2 — credentials required)")
    elif command == "migrate":
        print("Migration requires Catalyst Data Store credentials (Phase 2).")
        print("Set CATALYST_PROJECT_ID and CATALYST_CLIENT_ID environment variables.")
        sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
