# handover/CURRENT-STATE.md

# AI-Hub Current State

Last Updated:

2026-08-17 (Phase 4 implemented; release review complete, awaiting owner
approval)

---

# Overall Status

Phase 1 (Repository Foundation) released.

Phase 2 (Monitoring Engine) released: health checks, availability/lifecycle
tracking, quota architecture, seed validation. 99/99 tests passing.

Phase 3 (Scoring / Recommendation / Fallback) released: scoring,
recommendation with provenance and fallback chain. 162/162 tests passing.

Phase 4 (Dashboard / Reporting / History) implemented (`c49ea9b`): read-only
dashboard engine, deterministic reports, append-only event-derived history.
216/216 tests passing. Release review complete; owner approval pending.

Architecture approved.

Git baseline committed and pushed (`main` == `origin/main`).

---

# Completed

## Phase 4 (awaiting owner approval) - Dashboard / Reporting / History

Authorized:

* Owner approval 2026-08-17 of `docs/review/PHASE4-IMPLEMENTATION-PLAN.md`
  (baseline `f9316e4`).

Completed:

* `docs/review/PHASE4-DASHBOARD-SPEC.md` - proposal spec (doc-before-code).
* Spec v1.2 Section 18 - Dashboard / Reporting / History (Phase 4).
* `dashboard/engine.py` - read-only aggregate views: overview, provider_view,
  score_view, recommendation_view, event_view.
* `dashboard/reports.py` - deterministic plain-text report builders
  (providers, scores, recommendations, monitoring, overview).
* `dashboard/history.py` - append-only score/availability history from
  `SCORE_*` / `MONITOR_STATUS_CHANGED` / `HEALTH_CHECK_*` events.
* CLI: `dashboard status`, `dashboard report <name>`, `dashboard history`.
* Tests: 216/216 passing (54 new).
* `docs/release/PHASE4-RELEASE-MANIFEST.md` (baseline `c49ea9b`) and
  `handover/PHASE-4-CLOSURE.md`.

Pending:

* Phase 4 release approval + closure sign-off (owner).
* Optional snapshots only if ADR-0004 is approved.

## Phase 3 - Scoring / Recommendation / Fallback

Completed:

* Scoring engine (`scoring/engine.py`, `scoring/ingest.py`,
  `scoring/derive.py`) - normalized `scores` table (ADR-0001), aging,
  operational dimensions derived from monitoring, no fabricated values
* Recommendation engine (`recommendation/`) - built-in + custom profiles,
  deterministic ranking, explainability, provenance records
* Fallback engine (`fallback/engine.py`) - deterministic chain, eligibility
  from monitoring, recovery handling
* Phase 3 event types (`core/events.py`)
* Phase 3 config keys (v1.2 Section 10): scoring.aging_*_days,
  scoring.derive_operational, recommendation.decision_version
* CLI: `python -m app.main score list/set`, `recommend top/chain`,
  `fallback status`
* Tests: 162/162 passing (59 new)

## Phase 2 - Monitoring Engine

Completed:

* Health checks (`monitoring/health.py`) - HTTP reachability, no auth/secrets,
  timeout + latency thresholds, UNKNOWN for missing base_url
* Availability + lifecycle (`monitoring/availability.py`) - v1.2 Section 5
  legal transitions, no automatic archival
* Quota architecture (`monitoring/quota.py`) - quota_type, reset detection,
  ACTIVE -> LIMITED on quota signal
* Seed validation (`monitoring/validation.py`) - metadata checks, results via
  events only, never mutates providers
* Monitoring event types (`core/events.py`)
* Monitoring config keys (v1.2 Section 10): timeout_seconds=10,
  failure_threshold=3, latency_threshold_ms=10000
* CLI: `python -m app.main monitor run/status/validate`
* Tests: 99/99 passing (50 new)

## Phase 1 - Repository Foundation

Completed:

* Repository skeleton (all specified folders present)
* SQLite database module and schema
* Configuration system with validation and documented defaults
* Manual provider registry (add / update / list / archive)
* Append-only event log
* Minimal CLI (`python -m app.main`)
* Test framework (49 tests, all passing)
* ADR-0002 / ADR-0003 accepted (2026-07-31)
* Initial provider seed dataset (`scripts/seed_providers.py`, 9 providers)
* Phase 1 closure (`handover/PHASE-1-CLOSURE.md`, `PROJECT-STATUS.md`,
  `docs/release/PHASE1-CLOSURE-SUMMARY.md`)
* `LICENSE` set to MIT

---

## Documentation

Completed:

* `START-HERE.md`
* `CONSTITUTION.md`
* Architecture Specification v1.1
* Implementation Specification v1.2
* Handover documents

---

# Current Repository Status

```
AI-Hub/
  app/            __init__.py, config.py, main.py
  core/           __init__.py, providers.py, events.py
  database/       __init__.py, database.py, schema.sql
  monitoring/     __init__.py, health.py, availability.py, quota.py,
                  validation.py (Phase 2)
  scoring/        __init__.py, engine.py, ingest.py, derive.py (Phase 3)
  recommendation/ __init__.py, engine.py, profiles.py, explain.py,
                  provenance.py (Phase 3)
  fallback/       __init__.py, engine.py (Phase 3)
  connectors/     vscode/, mcp/ (empty - Phase 5)
  dashboard/      __init__.py, engine.py, reports.py, history.py (Phase 4)
  tests/          conftest.py, test_database.py, test_schema.py,
                  test_config.py, test_providers.py, test_health.py,
                  test_availability.py, test_quota.py, test_validation.py,
                  test_scoring_engine.py, test_recommendation.py,
                  test_fallback.py, test_provenance.py,
                  test_dashboard_engine.py, test_dashboard_reports.py,
                  test_dashboard_history.py, test_dashboard_cli.py
                  (216 tests total)
  scripts/        seed_providers.py
  backup/         (empty)
  docs/           review/ (immutable + Phase 2 plan/spec), release/
                  (Phase 1 manifest, Phase 2 manifest draft, notes,
                  closure summaries, owner checklist)
  spec/           agent-logging.md, project-registry.md
  decisions/      README.md, 0001-model-score-representation.md (ACCEPTED),
                  0002-agent-logging.md (ACCEPTED),
                  0003-project-registry.md (ACCEPTED)
  templates/      config.toml
  handover/       AGENT-HANDOVER.md, CURRENT-STATE.md, NEXT-STEPS.md,
                  SESSION-SUMMARY.md, PHASE-1-CLOSURE.md
  config.toml     documented defaults
  requirements.txt
  CHANGELOG.md
  LICENSE         MIT
  PROJECT-STATUS.md
```

A database file (`database/ai_hub.db`) is created on demand by
`python -m app.main init-db`. It is ignored by git.

Agent session logs are written under `logs/` and the project registry lives
at `projects/registry.json` (ADR-0002 / ADR-0003, ACCEPTED).

---

## Decisions Already Made

ADR-0001 (Model Score Representation) is **ACCEPTED** (2026-08-01): the
normalized `scores` table is added to `database/schema.sql`; v1.1 scalar
score columns on `models` are superseded and retained for backward
compatibility.

ADR-0002 (Agent Logging Architecture) and ADR-0003 (Project Registry and
Workspace Discovery) are **ACCEPTED** (2026-07-31).

## Database

Technology: SQLite.

Schema: `providers`, `models`, `scores`, `availability`, `events`,
`preferences`, `recommendations` (v1.1 Section 8, v1.2 Section 8, and
ADR-0001 for `scores`).

## Configuration

TOML, local only, secret-like keys rejected at load time
(Constitution Article 6).

## Provider Registry

Manual only. No automatic discovery (v1.2 Section 9 - discoveries stay in
PENDING_REVIEW, deferred).

Providers are archived, never deleted (Constitution Article 5).

Reason is mandatory for runtime states LIMITED, DEGRADED, OFFLINE, ARCHIVED
(v1.2 Section 6).

## Monitoring (Phase 2)

Health checks, availability/lifecycle tracking, quota architecture and seed
validation implemented. Monitoring never modifies provider information
directly; transitions use the v1.2 Section 5 legal table. No automatic
archival.

## Scoring / Recommendation / Fallback (Phase 3)

Scores stored in the ADR-0001 `scores` table; operational dimensions derived
from monitoring at read time; recommendations deterministic + explainable
with provenance records; fallback chain consumes monitoring outputs only and
never mutates providers.

## Dashboard / Reporting / History (Phase 4)

Implemented in `c49ea9b`: read-only aggregation views, deterministic
plain-text reports and append-only event-derived history - all in
conformance with v1.2 Section 18. No schema changes (7 tables unchanged);
point-in-time snapshots deferred pending ADR-0004 approval. See
`docs/review/PHASE4-DASHBOARD-SPEC.md`, `docs/release/PHASE4-RELEASE-MANIFEST.md`
and `handover/PHASE-4-CLOSURE.md`.

---

# Not Yet Implemented

* Phase 5 Connectors (VS Code / MCP) - dashboard reports are plain-text and
  connector-safe
* Ecosystem intelligence (Phase 6)
* Model seeding

---

# Known Constraints

The project must work well on:

* Windows
* VS Code environment
* limited hardware
* no mandatory Docker dependency

Python 3.11+ is required (configuration uses stdlib `tomllib`).
Verified with Python 3.14.2.

---

# Current Risk Areas

## AI Ecosystem Changes

Providers evolve rapidly.

Solution: Monitoring and history preservation (`monitor validate` reports
endpoint status; availability history preserved in Phase 2).

## Multiple AI Agents

Risk: architecture drift.

Solution: ADRs + specifications.

## Provider Reliability

Risk: temporary outages mistaken for retirement.

Solution: lifecycle rules (v1.2 Section 5).

---

# Current Confidence

Architecture: High

Phase 1 implementation: High (49 tests passing, Phase 1 released)

Phase 2 implementation: High (99 tests passing, Phase 2 released)

Phase 3 implementation: High (162 tests passing, Phase 3 released)

Phase 4 documentation: High (plan approved, spec written; implementation
complete)

Phase 4 implementation: High (216 tests passing; release review complete,
awaiting owner approval)

Concept: Validated
