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
-- The v1.1 scalar score columns below are superseded by the normalized
-- `scores` table (ADR-0001, accepted 2026-08-01) and are retained for
-- backward compatibility only. New scores are stored in `scores`.
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
-- scores
-- Normalized per-dimension model scores (ADR-0001, accepted 2026-08-01).
-- Satisfies v1.2 Section 1.2: every score records value, confidence,
-- timestamp and source. Any dimension (including custom benchmarks) is a
-- row, never a migration (Constitution Article 9).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scores (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id   INTEGER NOT NULL REFERENCES models (id),
    dimension  TEXT    NOT NULL,
    value      REAL    NOT NULL CHECK (value >= 0),
    confidence REAL    CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    source     TEXT    NOT NULL
        CHECK (source IN ('MANUAL', 'BENCHMARK', 'AUTOMATED_TEST', 'USER_FEEDBACK', 'OFFICIAL_INFORMATION')),
    scored_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    UNIQUE (model_id, dimension),
    FOREIGN KEY (model_id) REFERENCES models (id)
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
-- discovery_candidates
-- Review-gated automatic/discovered provider candidates (Phase 6, ADR-0005,
-- decision D-P1). Candidates are NEVER `providers` rows; the provider
-- lifecycle and its status CHECK stay unchanged. Only explicit human approval
-- (`discovery approve`) materializes a candidate as a registered provider
-- (and its models). Rows are retained, never deleted (Article 5).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS discovery_candidates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_name TEXT    NOT NULL UNIQUE,
    source_type   TEXT    NOT NULL,
    source_ref    TEXT,
    payload       TEXT    NOT NULL,
    state         TEXT    NOT NULL DEFAULT 'DISCOVERED'
        CHECK (state IN ('DISCOVERED', 'PENDING_REVIEW', 'APPROVED', 'REJECTED')),
    content_hash  TEXT    NOT NULL,
    imported_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    reviewed_at   TEXT,
    reason        TEXT,
    submitter     TEXT    NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- -----------------------------------------------------------------------------
-- benchmark_runs
-- Persistent, provenance-aware benchmark ingestion (Phase 6, ADR-0006,
-- decision D-P3). One row per imported benchmark file/run: identity, version,
-- source attribution (origin), retrieval metadata (fetched_at), integrity
-- stamp (content_hash), who imported it and when, and the documented
-- metric -> (dimension, formula) mapping used for normalization. Rows are
-- retained, never deleted (Article 5). Raw values live in benchmark_results.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS benchmark_runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    version      TEXT    NOT NULL,
    origin       TEXT    NOT NULL,
    fetched_at   TEXT,
    content_hash TEXT    NOT NULL,
    imported_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    submitter    TEXT    NOT NULL,
    mapping      TEXT    NOT NULL
);

-- -----------------------------------------------------------------------------
-- benchmark_results
-- Raw benchmark metric values plus the deterministic normalized value
-- (0-100) per (run, model, metric). Every raw value is preserved and remains
-- queryable - benchmark data is never fabricated (Article 10). Scores derived
-- from these rows are mapped into `scores` with source = 'BENCHMARK'.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS benchmark_results (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     INTEGER NOT NULL REFERENCES benchmark_runs (id),
    model_id   INTEGER NOT NULL REFERENCES models (id),
    metric     TEXT    NOT NULL,
    raw_value  REAL    NOT NULL,
    norm_value REAL    NOT NULL CHECK (norm_value >= 0),
    UNIQUE (run_id, model_id, metric),
    FOREIGN KEY (run_id) REFERENCES benchmark_runs (id),
    FOREIGN KEY (model_id) REFERENCES models (id)
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_models_provider            ON models (provider_id);
CREATE INDEX IF NOT EXISTS idx_scores_model               ON scores (model_id);
CREATE INDEX IF NOT EXISTS idx_availability_provider      ON availability (provider_id);
CREATE INDEX IF NOT EXISTS idx_events_occurred            ON events (occurred_at);
CREATE INDEX IF NOT EXISTS idx_events_type                ON events (event_type);
CREATE INDEX IF NOT EXISTS idx_recommendations_requested  ON recommendations (requested_at);
CREATE INDEX IF NOT EXISTS idx_benchmark_runs_name        ON benchmark_runs (name);
CREATE INDEX IF NOT EXISTS idx_benchmark_results_run      ON benchmark_results (run_id);
CREATE INDEX IF NOT EXISTS idx_benchmark_results_model    ON benchmark_results (model_id);
