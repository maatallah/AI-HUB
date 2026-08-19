# AI-Hub Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added (Phase 6 - Ecosystem Intelligence - trend analysis)

- Trend analysis milestone implemented (2026-08-19, owner-authorized against
  the canonical M3 baseline `98696d1`; the pre-implementation inspection
  report and the governing decisions below were approved by the owner).
- `trend/` module - read-only, deterministic trend analysis over the
  append-only event-derived history (v1.2 Section 20.4; proposal spec
  Section 5): `analysis.py` (public `score_trend`, `availability_trend`,
  `TrendError`) and `__init__.py` (public API + governed semantics). Derives
  direction (`up` / `down` / `stable` / `insufficient_data`), magnitude and
  stability over an explicit request window. Strictly derived/read-only: no
  DB writes, no tables, no `TREND_*` events (core/events.py untouched),
  ADR-0004 / D-P8 snapshots remain deferred.
- Owner-authorized trend semantics: Option A availability scalar
  (`HEALTH_CHECK_OK` -> 1.0, `HEALTH_CHECK_FAILED` -> 0.0; `HEALTH_CHECK_*
  UNKNOWN` excluded from the numeric scalar; `MONITOR_STATUS_CHANGED` is never
  a numeric point); window anchored to the most recent series point (not
  wall-clock); per-dimension grouping (a dimension filter restricts the
  calculation); stable band `abs(normalized delta) <= 5%` applied
  symmetrically; magnitude `(last - first) / domain` where the domain is 100
  for scores (exactly `(last - first) / 100`) and 1 for the availability
  scalar (domain-relative normalization, owner Option 1); stability =
  population standard deviation (documented in the module); `min_points = 3`
  minimum, fewer points -> `insufficient_data` with the threshold exposed,
  never fabricated (Article 10); the complete raw history is passed through
  unchanged. Latency is not part of the availability scalar.
- `[trend]` configuration (validated, defaults `window_days 90`,
  `min_points 3`) in `app/config.py` (DEFAULT_CONFIG, Config, validate,
  effective_config_text) and mirrored in `config.toml` +
  `templates/config.toml`.
- CLI (additive, existing commands unchanged): `trend scores --model <id>
  [--dimension <d>] [--days N]`, `trend availability [--provider <id>]
  [--days N]`; `--days` overrides the analysis window (0 or negative rejected).
- Tests: `tests/test_trend.py` (31) + `tests/test_trend_cli.py` (14) + 2 new
  config tests covering
  up/down/stable, exact +/- 5% boundaries, magnitude, population stability,
  insufficient-data threshold exposure, 90-day default window anchoring,
  explicit window/days, per-dimension grouping, OK/FAILED mapping, UNKNOWN and
  transition exclusion, determinism, read-only/no-write, CLI + invalid input;
  minimal config-test and CLI-fixture updates for the additive `[trend]`
  section. Full Python suite 467/467 (420 base + 47 new); adapter/MCP 48/48;
  VS Code 28/28 unit + 2/2 integration; `git diff --check` clean. No schema
  changes, no new event types, no connectors changes (D-P6), `requirements.txt`
  and npm graph unchanged.
- Living documentation refreshed (PROJECT-STATUS, CURRENT-STATE, NEXT-STEPS).
  The release package milestone remains gated on a separate owner
  authorization (D-P9).

### Added (Phase 6 - Ecosystem Intelligence - canonical Milestone 3 - approval materialization + model registry)

- Milestone 3 (approval materialization + model registry, canonical Phase 6
  M3 per the approved planning baseline Section 12 / proposal spec Section 9)
  - owner re-authorized 2026-08-19 against the baseline `eca910f` after the
  read-only milestone reconciliation. `archive_model` semantics resolved by
  the owner (Option A): event-only archival - the `MODEL_ARCHIVED` event
  carries the required, non-empty reason and the `models` row is retained
  unchanged (Article 5); no schema column, no lifecycle state, no
  monitoring-availability coupling.
- `core/models.py` - governed model registry operations (add_model,
  get_model, list_models, update_model, archive_model), emitting the
  previously-reserved `MODEL_ADDED` / `MODEL_UPDATED` / `MODEL_ARCHIVED`
  events. `list_models` joins the owning provider and always returns retained
  rows (no hidden filtering).
- `discovery/engine.py` - `approve_candidate` materializes the approved
  candidate through governed registry operations only (`core.providers.
  add_provider` starting at `NEW` with candidate provenance in notes, then
  `core.models.add_model` per candidate model). The candidate transition, the
  materialization and every audit event commit together atomically (the
  `_NoCommit` proxy defers the inner modules' auto-commits to the single outer
  commit); any failure rolls back everything and the candidate stays
  `PENDING_REVIEW`; a provider name already registered fails deterministically
  before anything is written. No raw SQL write path in the new module.
- CLI (additive, existing commands unchanged): `model list [--provider <id>]`.
- Tests: `tests/test_models.py` and `tests/test_models_cli.py` (new);
  `tests/test_discovery.py` M2 no-materialization pins superseded with M3
  materialization/event/atomicity/provenance tests; `tests/test_discovery_cli.py`
  approve flow updated. Full Python suite 420/420 (384 base + 36 new);
  adapter/MCP 48/48; VS Code 28/28 unit + 2/2 integration; `git diff --check`
  clean. No trend code (not authorized), no connectors changes (D-P6), no
  schema/config changes, `requirements.txt` and npm graph unchanged.
- Living documentation refreshed (PROJECT-STATUS, CURRENT-STATE, NEXT-STEPS).

### Added (Phase 6 - Ecosystem Intelligence - Milestone 3 implementation)

- Milestone 3 (benchmark ingestion + persistent benchmark-result storage,
  D-P3/ADR-0006) - owner authorized 2026-08-19 against the M2 baseline
  `a037dfd`. Replay semantics resolved by the owner: importing an identical
  file again appends a NEW run and reports the prior run id (`duplicate_of`)
  - never silent. Milestone-numbering note: the owner authorized benchmark
  integration as "M3"; the approved planning baseline (Section 12) and
  proposal spec (Section 9) number benchmark as M4 and approval
  materialization as M3 - implementation follows the owner's explicit content
  authorization.
- Additive `benchmark_runs` table (name, version, origin, fetched_at,
  content_hash, imported_at, submitter, mapping) and `benchmark_results`
  table (run_id -> benchmark_runs, model_id -> models, metric, raw_value,
  norm_value 0-100 CHECK, UNIQUE (run_id, model_id, metric)) in
  `database/schema.sql` (ADR-0006 DDL); added to `EXPECTED_TABLES`.
- `benchmark/` module: `ingest.py` (curated JSON benchmark file parsing,
  full validation, secret-key scanning reusing the `app.config` pattern,
  origin URL sanitization, documented deterministic formulas `identity` /
  `fraction_to_percent`, model resolution against the existing registry,
  atomic batch ingestion per file with rollback on any invalid row,
  `--dry-run` without mutation, replay appends a NEW run + reports
  `duplicate_of`, scores via `scoring.ingest.set_score` with source
  `BENCHMARK` and `scored_at` = run date, `BENCHMARK_IMPORTED` event).
- New whitelisted event type: `BENCHMARK_IMPORTED`.
- `[benchmark] import_dir` configuration key (validated, default
  `data/benchmarks`); mirrored in `config.toml` and `templates/config.toml`.
- CLI (additive, existing commands unchanged): `benchmark import --file
  <path> [--name <benchmark>] [--dry-run]`, `benchmark list [--run <id>]`.
- Tests: `tests/test_benchmark.py` and `tests/test_benchmark_cli.py`; schema/
  config/CLI fixtures updated for the additive tables and `[benchmark]`
  config. Full Python suite 384/384 (337 base + 47 new); adapter/MCP 48/48;
  VS Code 28/28 unit + 2/2 integration; `git diff --check` clean. No approval
  materialization / model registry code (not authorized), no trend/trend
  storage (not authorized), no connectors changes (D-P6), `requirements.txt`
  and npm graph unchanged.
- Living documentation refreshed (PROJECT-STATUS, CURRENT-STATE, NEXT-STEPS).

### Added (Phase 6 - Ecosystem Intelligence - Milestone 2 implementation)

- Milestone 2 (discovery + candidate workflow, D-P1/ADR-0005, D-P2) - owner
  authorized 2026-08-18 against the M1 baseline `d32324a`.
- Additive `discovery_candidates` table (ADR-0005 DDL) in
  `database/schema.sql`; added to `EXPECTED_TABLES`; state CHECK
  `DISCOVERED/PENDING_REVIEW/APPROVED/REJECTED`; `provider_name` UNIQUE;
  retained, never deleted (Article 5).
- `discovery/` module: `sources.py` (curated JSON import reader, candidate
  record validation, secret-key scanning reusing the `app.config` pattern,
  URL sanitization, injectable `urllib` transport) and `engine.py` (candidate
  lifecycle: add/list/queue/approve/reject, per-dataset atomic validation,
  duplicate reporting, network `run` with snapshot-before-analysis).
- `discovery approve/reject` are deterministic candidate-state transitions
  ONLY in M2; provider/model materialization belongs to Milestone 3.
- Controlled network fetch (D-P2): non-empty allowlist required, explicit
  `--allow-network` CLI flag, immutable snapshot (URL, fetched_at, content
  hash, size) recorded before analysis, best-effort per-URL with
  `DISCOVERY_IMPORT_ERROR` events, offline-tested via injected transports.
- New whitelisted event types: `DISCOVERY_CANDIDATE_ADDED`,
  `DISCOVERY_IMPORT_COMPLETE`, `DISCOVERY_IMPORT_ERROR`,
  `DISCOVERY_CANDIDATE_APPROVED`, `DISCOVERY_CANDIDATE_REJECTED`.
- `[discovery]` configuration keys (validated): `enabled` (master switch,
  default false, gates acquisition), `allowlisted_urls` (default empty =
  network disabled; credentials/secret query keys rejected), `timeout_seconds`
  (default 10), `import_dir` (default `data/discovery`). Mirrored in
  `config.toml` and `templates/config.toml`.
- CLI (additive, existing commands unchanged): `discovery import [path]`,
  `discovery run [--allow-network] [--timeout N]`,
  `discovery list [--state ...]`, `discovery approve <id> [--reason]`,
  `discovery reject <id> --reason`.
- Tests: `tests/test_discovery.py` (lifecycle, review discipline, curated
  import, network fetch with fake transports, security) and
  `tests/test_discovery_cli.py`; schema/config/CLI fixtures updated for the
  additive table and `[discovery]` config. Full Python suite 337/337 (264
  base + 73 new); adapter/MCP 48/48; VS Code 28/28 unit + 2/2 integration;
  `git diff --check` clean. No benchmark/trend/model-registry code (M3-M5),
  no connectors changes (D-P6), `requirements.txt` and npm graph unchanged.
- Living documentation refreshed (PROJECT-STATUS, CURRENT-STATE, NEXT-STEPS).

### Added (Phase 6 - Ecosystem Intelligence - Milestone 1 documentation)

- Phase 6 planning baseline approved by owner 2026-08-18 (commit `8f01b10`,
  `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md`):
  planning decisions D-P1..D-P9 (D-P1 dedicated discovery-candidate table;
  D-P2 controlled network for discovery/benchmark ingestion; D-P3 persistent
  provenance-aware benchmark storage; D-P4 provider/model registry scope
  only; D-P5 ADR-0003 workspace discovery deferred; D-P6 CLI-only; D-P7
  on-demand only; D-P8 ADR-0004 snapshots deferred; D-P9 sequential milestone
  gates).
- Milestone 1 (doc-before-code, Article 11): `AI-Hub Project Specification
  v1.2.md` Section 20 - Ecosystem Intelligence (Phase 6);
  `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md` (proposal spec);
  ADR-0005 (D-P1 discovery candidate representation) and ADR-0006 (D-P3
  benchmark result storage), both ACCEPTED. ADR-0004 remains reserved for the
  deferred point-in-time score snapshots decision (D-P8); Phase 6 decisions
  therefore occupy numbers 0005 and 0006.
- Living documentation refreshed (PROJECT-STATUS, CURRENT-STATE,
  NEXT-STEPS, decisions/README). No implementation code changed; no schema
  changes; M1 is documentation only per the milestone gate (D-P9).

### Added (Phase 5 - Connectors - release)

- Phase 5 RELEASED and CLOSED (2026-08-18, baseline `8231dce`).
- `docs/release/PHASE5-RELEASE-MANIFEST.md` (immutable reference baseline)
  and `handover/PHASE-5-CLOSURE.md` (closure accepted by owner 2026-08-18).
- Release records the Phase 5 test evidence: 264/264 Python, 48/48
  adapter/MCP, 28/28 VS Code offline unit, 2/2 VS Code real integration;
  `git diff --check` clean; boundaries (read-only, no network, no API keys,
  no decision logic in connectors) verified and documented.

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
