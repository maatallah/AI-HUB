# AI-Hub Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added (Phase 2 - Monitoring Engine)

- Monitoring engine package `monitoring/`:
  - `health.py` - HTTP reachability checks (urllib, no auth, no secrets,
    timeout and latency driven). Providers without a base_url report UNKNOWN.
  - `availability.py` - availability tracking + lifecycle transitions using
    the v1.2 Section 5 legal transition table through the existing registry.
  - `quota.py` - quota architecture (quota_type, reset detection,
    ACTIVE -> LIMITED on quota signal).
  - `validation.py` - provider seed metadata validation; results recorded
    only as events; providers never modified.
- Monitoring event types added to `core/events.py`:
  `HEALTH_CHECK_OK`, `HEALTH_CHECK_FAILED`, `HEALTH_CHECK_UNKNOWN`,
  `MONITOR_STATUS_CHANGED`, `QUOTA_SIGNAL`, `VALIDATION_PASSED`,
  `VALIDATION_FAILED`, `VALIDATION_UNKNOWN`.
- Monitoring configuration keys (v1.2 Section 10):
  `monitoring.timeout_seconds` (10), `monitoring.failure_threshold` (3),
  `monitoring.latency_threshold_ms` (10000). Global values only.
- CLI: `python -m app.main monitor run/status/validate`.
- Tests: 50 new tests (health, availability, quota, validation); 99 total.

### Added (Phase 1 - Repository Foundation)

- Repository skeleton: `app/`, `core/`, `database/`, `monitoring/`,
  `connectors/`, `dashboard/`, `tests/`, `scripts/`, `backup/`, `docs/`,
  `spec/`, `decisions/`, `templates/`, `handover/`.
- SQLite schema for `providers`, `models`, `availability`, `events`,
  `preferences` and `recommendations` (`database/schema.sql`).
- Database module with connection management, schema initialization and
  schema validation (`database/database.py`).
- Configuration system with documented defaults, TOML loading and validation
  (`app/config.py`). Secret-like keys are rejected.
- Manual provider registry: add, update, list, archive
  (`core/providers.py`).
- Append-only event log (`core/events.py`).
- Minimal CLI (`app/main.py`): `init-db`, `config show/validate`,
  `provider add/list/update/archive`.
- Initial provider seed dataset (`scripts/seed_providers.py`): OpenAI,
  Google Gemini, Anthropic, OpenRouter, Blackbox AI, DeepSeek, MiniMax,
  Qwen, GitHub Models. Metadata only, idempotent, no secrets.
- Test framework: 49 tests (database creation, schema validation,
  configuration loading, provider CRUD).

### Phase 1 Release Closure

- Added `handover/PHASE-1-CLOSURE.md`.
- Added `PROJECT-STATUS.md` (repository front-page dashboard).
- Added `LICENSE` placeholder (owner decision pending).
- Fixed ADR reference in `CHANGELOG.md`.
- Added `.pytest_cache/` to `.gitignore`.

### Phase 1 Release Finalization (2026-08-01)

- Git baseline initialized and committed (`7ceac80`, branch `main`); remote
  `origin` = `https://github.com/maatallah/AI-HUB.git`.
- Accepted ADR-0002 (agent logging) and ADR-0003 (project registry);
  related-document status labels updated.
- Aligned configuration keys `logging.log_root`, `workspace.root`,
  `registry.path` across v1.2 Section 10, `config.toml`,
  `templates/config.toml` and both specs.
- Set `LICENSE` to MIT (copyright line still requires owner attribution;
  change uncommitted).
- Added release package under `docs/release/` (manifest, release notes,
  closure summary, owner checklist, owner-action status).
- Refreshed living docs: `PROJECT-STATUS.md`, `START-HERE.md`,
  `handover/CURRENT-STATE.md`, `handover/NEXT-STEPS.md`,
  `handover/AGENT-HANDOVER.md`.
- Re-verified tests on committed baseline: 49/49 passed.

### Decisions

- `decisions/0001-model-score-representation.md` (PROPOSED) - assessed as
  ready for ACCEPTED status; final approval required before Phase 3.

### Not implemented (intentionally)

- Monitoring, scoring, recommendations, dashboard, connectors.
- Model seeding (deferred to Phase 2/3).
