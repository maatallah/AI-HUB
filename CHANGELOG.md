# AI-Hub Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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

### Decisions

- `decisions/0001-model-score-representation.md` (PROPOSED) - assessed as
  ready for ACCEPTED status; final approval required before Phase 3.

### Not implemented (intentionally)

- Monitoring, scoring, recommendations, dashboard, connectors.
- Model seeding (deferred to Phase 2/3).
