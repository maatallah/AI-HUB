-- =============================================================================
-- AI-Hub Database Schema
-- Reference: AI-Hub Project Specification v1.1 (Section 8 - Data Model)
--            AI-Hub Implementation Specification v1.2 (Sections 5, 6, 8, 12)
--
-- Governing principles:
--   * Providers are archived, never deleted (Constitution Article 5).
--   * Events are append-only (Specification v1.1 Section 8).
--   * Unknown information remains NULL, never fabricated (Constitution Article 10).
--   * Raw secrets are never stored (Constitution Article 6).
-- =============================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- -----------------------------------------------------------------------------
-- providers
-- One row per AI service.
-- status follows the lifecycle defined in v1.2 Section 5.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS providers (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT    NOT NULL UNIQUE,
    company           TEXT,
    api_type          TEXT,
    base_url          TEXT,
    documentation_url TEXT,
    status            TEXT    NOT NULL DEFAULT 'NEW'
        CHECK (status IN ('NEW', 'EVALUATING', 'ACTIVE', 'LIMITED', 'DEGRADED', 'OFFLINE', 'ARCHIVED')),
    status_reason     TEXT,
    notes             TEXT,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- -----------------------------------------------------------------------------
-- models
-- One row per model belonging to a provider.
-- Scores are scalar dimensions defined by v1.1 Section 8.
-- Every score records its source and confidence (v1.2 Section 1.2).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS models (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id       INTEGER NOT NULL REFERENCES providers (id),
    model_name        TEXT    NOT NULL,
    model_identifier  TEXT    NOT NULL,
    context_window    INTEGER CHECK (context_window IS NULL OR context_window > 0),
    supports_tools    INTEGER NOT NULL DEFAULT 0 CHECK (supports_tools IN (0, 1)),
    supports_streaming INTEGER NOT NULL DEFAULT 0 CHECK (supports_streaming IN (0, 1)),
    supports_json     INTEGER NOT NULL DEFAULT 0 CHECK (supports_json IN (0, 1)),
    supports_vision   INTEGER NOT NULL DEFAULT 0 CHECK (supports_vision IN (0, 1)),
    coding_score      REAL,
    reasoning_score   REAL,
    latency_score     REAL,
    reliability_score REAL,
    score_source      TEXT
        CHECK (score_source IS NULL OR score_source IN ('MANUAL', 'BENCHMARK', 'AUTOMATED_TEST', 'USER_FEEDBACK', 'OFFICIAL_INFORMATION')),
    confidence_level  REAL CHECK (confidence_level IS NULL OR (confidence_level >= 0 AND confidence_level <= 1)),
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (provider_id, model_identifier),
    FOREIGN KEY (provider_id) REFERENCES providers (id)
);

-- -----------------------------------------------------------------------------
-- availability
-- Tracks runtime state per provider and optionally per model (v1.1 Section 8).
-- Runtime states exclude NEW and EVALUATING (v1.2 Section 6).
-- Reason is mandatory whenever state is not ACTIVE (enforced in application).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS availability (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_id          INTEGER NOT NULL REFERENCES providers (id),
    model_id             INTEGER REFERENCES models (id),
    state                TEXT    NOT NULL DEFAULT 'ACTIVE'
        CHECK (state IN ('ACTIVE', 'LIMITED', 'DEGRADED', 'OFFLINE', 'ARCHIVED')),
    reason               TEXT,
    quota_type           TEXT,
    reset_at             TEXT,
    last_success         TEXT,
    last_failure         TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0 CHECK (consecutive_failures >= 0),
    created_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (provider_id, model_id),
    FOREIGN KEY (provider_id) REFERENCES providers (id),
    FOREIGN KEY (model_id) REFERENCES models (id)
);

-- -----------------------------------------------------------------------------
-- events
-- Append-only history of activity (v1.1 Section 8).
-- No UPDATE or DELETE operations are exposed by the application layer.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT    NOT NULL,
    entity_type TEXT,
    entity_id   INTEGER,
    payload     TEXT,
    occurred_at TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- -----------------------------------------------------------------------------
-- preferences
-- AI-Hub user preferences (v1.1 Section 8; v1.2 Section 2 custom profiles).
-- Stored as typed key/value pairs so new preferences never require a migration.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS preferences (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'string'
        CHECK (value_type IN ('string', 'integer', 'boolean', 'float', 'json')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- -----------------------------------------------------------------------------
-- recommendations
-- Decision provenance records (v1.2 Section 8).
-- Enables auditing and reproducibility. Populated from Phase 3 onwards.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS recommendations (
    id               TEXT PRIMARY KEY,
    task             TEXT    NOT NULL,
    profile          TEXT    NOT NULL,
    provider_id      INTEGER REFERENCES providers (id),
    model_id         INTEGER REFERENCES models (id),
    decision_version TEXT    NOT NULL,
    score_breakdown  TEXT,
    explanation      TEXT,
    confidence       REAL CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    requested_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (provider_id) REFERENCES providers (id),
    FOREIGN KEY (model_id) REFERENCES models (id)
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_models_provider            ON models (provider_id);
CREATE INDEX IF NOT EXISTS idx_availability_provider      ON availability (provider_id);
CREATE INDEX IF NOT EXISTS idx_events_occurred            ON events (occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_type                ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_recommendations_requested  ON recommendations (requested_at);
