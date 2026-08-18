# AI-Hub Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added (Phase 5 - Connectors - Milestone 4 regression + Milestone 5 hardening)

- Milestone 4 (full connector regression) VERIFIED (2026-08-18): complete
  Python regression 262/262 passed (184s); Phase 5 MCP/adapter tests 46/46
  passed (35s); VS Code offline unit tests 27/27 passed; VS Code real
  integration tests 2/2 passed; `git diff --check` clean; M1-M3 baseline
  `5cff03b` intact; no generated/unintended files tracked. No M4 files were
  modified.
- Milestone 5 (hardening / release readiness): 3 new tests where genuine
  coverage gaps existed:
  - MCP: non-`McpError` dispatch exceptions map to JSON-RPC `-32603`
    (documented in the Phase 5 spec error codes, previously untested).
  - MCP: an empty database returns empty results for every tool (never
    fabricated; spec acceptance criterion 9.7 at the connector boundary).
  - VS Code: `package.json` `contributes.commands` and `activationEvents`
    match the `FEATURES` registry (documentation/implementation consistency).
- Living docs refreshed for M4/M5: `PROJECT-STATUS.md`,
  `handover/CURRENT-STATE.md`, `handover/NEXT-STEPS.md`.
- Known limitations (recorded, unchanged from earlier milestones): transitive
  npm vulnerabilities via `@vscode/test-cli` accepted (no unrelated upgrades);
  MCP modern era `2026-07-28` out of scope; the Phase 5 spec and v1.2 Section
  19 list the four base commands while seven are implemented and documented -
  the additional three (`ai-hub.modelScores`, `ai-hub.recommendations`,
  `ai-hub.fallbackChain`) are tested and recorded in the living docs
  (non-blocking).
- No Phase 1-4, adapter, MCP or extension implementation changes.

### Added (Phase 5 - Connectors - VS Code extension / Milestone 3)

- `connectors/vscode/` VS Code extension implemented and verified under the
  approved Phase 5 scope (presentation/integration only, no decision logic,
  no mutation, no network access, no API-key handling).
- Commands (7): `ai-hub.status`, `ai-hub.modelScores`,
  `ai-hub.recommendations`, `ai-hub.fallbackChain`, `ai-hub.scoreHistory`,
  `ai-hub.availabilityHistory`, `ai-hub.dashboardReport`; activity bar view
  container `ai-hub` with reports tree view (`ai-hub.reports`).
- Data access: the extension invokes the read-only AI-Hub CLI
  (`python -m app.main ...`) via `execFile`; it never opens SQLite directly
  and never issues a mutating command (recommendations use `recommend chain`,
  never `recommend top`).
- Isolated Node/TypeScript workspace (decision D-4): own `package.json`,
  `tsconfig*.json`, `src/`, `test/`, local ambient type stubs for offline
  verification. devDependencies: `typescript`, `@types/vscode`,
  `@types/node`, `@vscode/test-cli`, `@vscode/test-electron`.
  `connectors/vscode/node_modules/`, `out/`, `out-test/`, `.vscode-test/`
  are git-ignored; `package-lock.json` is a tracked artifact; `npm install`
  is owner-run (documented in `connectors/vscode/README.md`).
- Tests: 27 offline unit tests (`node:test`, fake vscode) + 2 real VS Code
  integration tests (`@vscode/test-cli`); all passing.
- Owner verification (2026-08-18): real-@types compile clean, offline
  compile clean, 27/27 unit tests, 2/2 integration tests, full Python
  regression 262/262, `git diff --check` clean. Milestone 3 approved and
  closed by owner.
- No Python, MCP, Phase 1-4, requirements.txt or architecture changes.

### Added (Phase 5 - Connectors - documentation / doc-before-code)

- Phase 5 revised planning proposal approved (2026-08-17 by owner).
- Spec v1.2 Section 19 - Connectors (Phase 5): bounded MCP subset (legacy
  handshake era, `2024-10-07`..`2025-11-25`; primary target `2025-11-25`),
  stdio-only transport, Tools capability only, no MCP Python dependency
  (D-1), isolated VS Code npm graph (D-4), shared read-only adapter,
  connectors contain no decision logic, no network/mutation/API-key/config/
  environment changes.
- New proposal spec `docs/review/PHASE5-CONNECTORS-SPEC.md` covering MCP
  architecture (protocol versions, transport, primitives, tool discovery,
  error semantics, bounded-subset statement), dependency decisions (D-1/D-4),
  shared adapter delegation map (existing Phase 1-4 modules only: dashboard
  engine/reports/history, recommendation.recommend, fallback.build_chain,
  core.providers.list_providers), decision-logic boundary, security/mutation
  boundaries, VS Code scope, milestones, test acceptance criteria, risks and
  owner actions.
- Milestone 1 only (doc-before-code). No implementation: no `connectors/mcp/`,
  no `connectors/vscode/`, no `connectors/adapter.py` created.

### Added (Phase 4 - Dashboard / Reporting / History - implementation)

- Dashboard engine package `dashboard/`:
  - `engine.py` - read-only aggregate views: `overview` (provider/model/
    score counts, lifecycle status counts, available providers),
    `provider_view` (status, availability, failures, model/score counts),
    `score_view` (current scores joined with model/provider),
    `recommendation_view` (provenance ordered by requested_at DESC),
    `event_view` (append-only event log with optional type filter + limit).
  - `reports.py` - deterministic plain-text report builders:
    `report_providers`, `report_scores`, `report_recommendations`,
    `report_monitoring`, `report_overview` (tab-separated, self-describing
    headers, caller-injected optional generated_at timestamp).
  - `history.py` - append-only event-derived history: per-model score series
    from `SCORE_RECORDED` / `SCORE_UPDATED` events, availability series from
    `MONITOR_STATUS_CHANGED` / `HEALTH_CHECK_*`. Never fabricates data;
    snapshots deferred pending ADR-0004.
- CLI: `python -m app.main dashboard status`, `dashboard report
  <providers|scores|recommendations|monitoring|overview>`, `dashboard
  history --model N [--dimension D]`, `dashboard history --availability
  [--provider P]`.
- No schema changes (7 tables unchanged), no new dependencies, no new config
  keys, no new event types, no network access.
- Docs: `docs/release/PHASE4-RELEASE-MANIFEST.md` (release baseline, pending
  approval), `handover/PHASE-4-CLOSURE.md`.
- Tests: 54 new tests (engine 17, reports 14, history 12, CLI 11); 216 total.

### Added (Phase 4 - Dashboard / Reporting / History - documentation)

- Owner approval granted (2026-08-17) for PHASE4-IMPLEMENTATION-PLAN.md
  (baseline `f9316e4`); Phase 4 authorized.
- New proposal spec `docs/review/PHASE4-DASHBOARD-SPEC.md` covering the
  read-only dashboard aggregation layer (`dashboard/engine.py`),
  deterministic plain-text reports (`dashboard/reports.py`), and
  event-derived history (`dashboard/history.py`).
- Spec v1.2 Section 18 - Dashboard / Reporting / History (Phase 4):
  read-only views, exact counts/sums, explicit ordering (Article 7), no
  fabricated values (Article 10), append-only history reconstruction
  (Article 5), snapshots deferred pending ADR-0004.

### Added (Phase 3 - Scoring / Recommendation / Fallback)

- Scoring engine package `scoring/`:
  - `engine.py` - effective aged per-dimension scores (v1.2 Section 4 aging:
    fresh 1.00 / aging 0.90 / old 0.75 / stale 0.50).
  - `ingest.py` - score ingestion into the ADR-0001 `scores` table (sources:
    MANUAL, BENCHMARK, AUTOMATED_TEST, USER_FEEDBACK, OFFICIAL_INFORMATION);
    value 0-100, confidence 0-1 validation; SCORE_RECORDED / SCORE_UPDATED
    events.
  - `derive.py` - operational dimensions derived at read time from monitoring:
    availability (state map), reliability (failures), latency (health event),
    context_window (models table). Never fabricated (Article 10).
- Recommendation engine package `recommendation/`:
  - `profiles.py` - built-in profiles (coding, reasoning, free, long_context)
    with exact v1.2 Section 2 weights; custom profiles from `preferences`
    (JSON), validated to sum to 1.0.
  - `engine.py` - deterministic ranking (Section 7 Step 4 ordering), filtering
    (eligible status, context, capabilities), no hidden weighting.
  - `explain.py` - human-readable explanations (Article 4).
  - `provenance.py` - `recommendations` records (UUID id, decision_version,
    score_breakdown, explanation, confidence) + RECOMMENDATION_CREATED events.
- Fallback engine package `fallback/engine.py`: chain = primary +
  `fallback.max_chain_length` fallbacks; eligibility from monitoring
  (ACTIVE/LIMITED preferred, DEGRADED last resort); FALLBACK_TRIGGERED /
  FALLBACK_RECOVERED events; never mutates providers.
- Phase 3 event types added to `core/events.py`: `SCORE_RECORDED`,
  `SCORE_UPDATED`, `RECOMMENDATION_CREATED`, `FALLBACK_TRIGGERED`,
  `FALLBACK_RECOVERED`, `PROFILE_UPDATED`.
- Phase 3 configuration keys (v1.2 Section 10): `scoring.aging_*_days`
  (30/90/180), `scoring.derive_operational` (true),
  `recommendation.decision_version` (`3.0.0`).
- CLI: `python -m app.main score list/set`, `recommend top/chain`,
  `fallback status`.
- Docs: `docs/review/PHASE3-SCORING-SPEC.md`, spec v1.2 Sections 3/7/8/10
  updated, `docs/release/PHASE3-RELEASE-MANIFEST.md` (pending approval).
- Tests: 59 new tests (scoring 24, recommendation 16, fallback 10,
  provenance 6, config 3); 162 total.

### Added (ADR-0001 acceptance - 2026-08-01)

- ADR-0001 (Model Score Representation) ACCEPTED.
- Normalized `scores` table added to `database/schema.sql`:
  `id, model_id, dimension, value, confidence, source, scored_at, created_at`
  (one row per model/dimension; satisfies v1.2 Section 1.2).
- `EXPECTED_TABLES` in `database/database.py` includes `scores`.
- v1.2 Section 1.2 updated to reference the `scores` table.
- The v1.1 scalar score columns on `models` are superseded and retained for
  backward compatibility (retirement deferred to a cleanup migration).
- Tests: 4 new schema tests (scores columns, FK, unique dimension, source
  constraint); 103 total.

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
