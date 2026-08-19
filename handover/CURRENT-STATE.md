# handover/CURRENT-STATE.md

# AI-Hub Current State

Last Updated:

2026-08-19 (Phase 5 RELEASED and CLOSED; Phase 6 planning baseline approved,
Milestone 1 documentation, Milestone 2 discovery + candidate workflow, and
Milestone 3 benchmark ingestion + persistent storage implemented and
committed; remaining Phase 6 implementation milestones not authorized)

---

# Overall Status

Phase 1 (Repository Foundation) released.

Phase 2 (Monitoring Engine) released: health checks, availability/lifecycle
tracking, quota architecture, seed validation. 99/99 tests passing.

Phase 3 (Scoring / Recommendation / Fallback) released: scoring,
recommendation with provenance and fallback chain. 162/162 tests passing.

Phase 4 (Dashboard / Reporting / History) implemented (`c49ea9b`) and
released: read-only dashboard engine, deterministic reports, append-only
event-derived history. 216/216 tests passing. Release approved and closure
accepted 2026-08-17 (commit `3c47c61`).

Phase 5 (Connectors - VS Code / MCP) authorized 2026-08-17 (revised planning
proposal approved). Milestones 1-3 complete and closed: documentation
(doc-before-code), shared read-only adapter + MCP server, and VS Code
extension. Milestone 4 (full regression) VERIFIED 2026-08-18. Milestone 5
hardening, documentation and release readiness complete; the Phase 5 release
package (manifest + closure) approved and closed 2026-08-18 (baseline
`8231dce`).

Phase 6 (Ecosystem Intelligence) authorized 2026-08-18. Planning baseline
approved (D-P1..D-P9, commit `8f01b10`) and Milestone 1 (doc-before-code)
complete: v1.2 Section 20, `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md`,
ADR-0005 (D-P1 discovery candidates) and ADR-0006 (D-P3 benchmark storage).
Milestone 2 (discovery + candidate workflow) and Milestone 3 (benchmark
ingestion + persistent storage) implemented and committed. The remaining
implementation milestones require separate owner authorizations (D-P9).

Architecture approved.

Git baseline committed and pushed (`main` == `origin/main`).

---

# Completed

## Phase 5 (Milestones 1-3 complete) - Connectors (VS Code / MCP)

Authorized:

* Owner approval 2026-08-17 of the revised Phase 5 planning proposal.

Completed (Milestone 1 - documentation):

* Spec v1.2 Section 19 - Connectors (Phase 5): bounded MCP subset (legacy
  handshake era, primary `2025-11-25`), stdio-only transport, Tools
  capability only, no MCP Python dependency (D-1), isolated VS Code npm
  graph (D-4), shared read-only adapter, no connector decision logic, no
  network/mutation/API-key/config/environment changes.
* `docs/review/PHASE5-CONNECTORS-SPEC.md` - proposal spec (MCP architecture,
  dependencies, adapter delegation map, security boundaries, milestones,
  test acceptance criteria, risks, owner actions).

Completed (Milestone 2 - shared adapter + MCP server):

* `connectors/adapter.py` - single read-only application interface
  delegating to Phase 1-4 modules only (dashboard engine/reports/history,
  recommendation.recommend, fallback.build_chain, core.providers).
* `connectors/mcp/` - bounded MCP subset over stdio (legacy era
  `2024-10-07`..`2025-11-25`, primary `2025-11-25`), stdlib only:
  `server.py` (initialize handshake, ping, tools/list, tools/call) and
  `tools.py` (7 fixed tools, deterministic ordering).
* Tests: 46 new (adapter 19, MCP 27); approved and closed by owner.

Completed (Milestone 3 - VS Code extension):

* `connectors/vscode/` - 7 commands (`ai-hub.status`, `ai-hub.modelScores`,
  `ai-hub.recommendations`, `ai-hub.fallbackChain`, `ai-hub.scoreHistory`,
  `ai-hub.availabilityHistory`, `ai-hub.dashboardReport`), activity bar
  view container + reports tree view, webview panels rendering escaped CLI
  output deterministically.
* Data access: no SQLite access; invokes the read-only AI-Hub CLI
  (`python -m app.main ...`) via `execFile`. Never mutates, never contacts
  the network, never handles API keys, contains no decision logic.
* Isolated npm graph (D-4): self-contained Node/TypeScript workspace with
  owner-run `npm install`; `package-lock.json` tracked, `node_modules/`,
  `out/`, `out-test/`, `.vscode-test/` git-ignored.
* Tests: 27 offline TS unit tests + 2 real VS Code integration tests.
* Owner verification (2026-08-18): real-@types compile, offline compile,
  27/27 unit, 2/2 integration, 262/262 Python regression, `git diff --check`
  clean. Approved and closed by owner.

Completed (Milestone 4 - full connector regression):

* Full Python regression: 262/262 passed (184s); Phase 5 MCP/adapter tests
  46/46 passed (35s); VS Code offline unit tests 27/27; VS Code real
  integration tests 2/2. `git diff --check` clean; M1-M3 baseline `5cff03b`
  intact; no generated/unintended files tracked. No M4 files were modified.
* VERIFIED 2026-08-18.

Completed (Milestone 5 - hardening / release readiness):

* 3 new tests closing genuine coverage gaps: MCP `-32603` internal-error
  mapping (documented in the spec, previously untested); MCP empty database
  returns empty results for every tool (never fabricated, spec criterion
  9.7); VS Code `package.json` `contributes.commands` + `activationEvents`
  consistency with the `FEATURES` registry.
* Living docs refreshed (PROJECT-STATUS, CURRENT-STATE, NEXT-STEPS,
  CHANGELOG). Full verification re-run green. No Phase 1-4 or connector
  implementation changes.

Completed (Phase 5 - release):

* `docs/release/PHASE5-RELEASE-MANIFEST.md` (baseline `8231dce`) and
  `handover/PHASE-5-CLOSURE.md` created; closure accepted by owner
  2026-08-18.

## Phase 6 (Milestones 1-3) - Ecosystem Intelligence

Authorized:

* Owner approval 2026-08-18 of the Phase 6 planning baseline (D-P1..D-P9),
  Milestone 1 (doc-before-code, Article 11), and Milestone 2 (discovery +
  candidate workflow, against M1 baseline `d32324a`).
* Owner approval 2026-08-19 of Milestone 3 (benchmark ingestion +
  persistent benchmark-result storage, against M2 baseline `a037dfd`).
  Milestone-numbering note: the owner authorized benchmark integration as
  "M3"; the approved planning baseline (Section 12) and proposal spec
  (Section 9) number benchmark as M4 and approval materialization as M3.
  Implementation follows the owner's explicit content authorization
  (benchmark).

Completed (Milestone 1 - documentation):

* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md` (planning baseline,
  commit `8f01b10`) - approved planning decisions 2026-08-18.
* `AI-Hub Project Specification v1.2.md` Section 20 - Ecosystem Intelligence
  (Phase 6).
* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md` - proposal spec
  (discovery candidates ADR-0005; provenance-aware benchmark storage
  ADR-0006; read-only trend analysis; CLI-only D-P6; milestones + acceptance
  criteria).
* ADR-0005 (D-P1) and ADR-0006 (D-P3), ACCEPTED. ADR-0004 reserved for the
  deferred score-snapshots decision (D-P8).

Completed (Milestone 2 - discovery + candidate workflow, 2026-08-18):

* Additive `discovery_candidates` table (ADR-0005 DDL; state CHECK; UNIQUE
  provider_name) + `EXPECTED_TABLES` update.
* `discovery/` module: `sources.py` (curated import, record validation,
  secret scan, URL sanitization, injectable urllib transport) and `engine.py`
  (add/list/queue/approve/reject lifecycle, per-dataset atomic validation,
  duplicate reporting, controlled network `run` with snapshot-before-analysis
  D-P2).
* `discovery approve/reject` = deterministic candidate-state transitions only;
  provider/model materialization is Milestone 3.
* New whitelisted events: `DISCOVERY_CANDIDATE_ADDED`,
  `DISCOVERY_IMPORT_COMPLETE`, `DISCOVERY_IMPORT_ERROR`,
  `DISCOVERY_CANDIDATE_APPROVED`, `DISCOVERY_CANDIDATE_REJECTED`.
* `[discovery]` config (`enabled` master switch default false,
  `allowlisted_urls` default empty, `timeout_seconds`, `import_dir`),
  mirrored in `config.toml` + `templates/config.toml`.
* CLI (additive): `discovery import`, `discovery run --allow-network`,
  `discovery list [--state]`, `discovery approve <id> [--reason]`,
  `discovery reject <id> --reason`.
* Tests: `tests/test_discovery.py`, `tests/test_discovery_cli.py`; full Python
  suite 337/337; adapter/MCP 48/48; VS Code 28/28 + 2/2; `git diff --check`
  clean. No M3-M5 code, no connectors changes (D-P6).

Completed (Milestone 3 - benchmark ingestion + persistent storage, 2026-08-19):

* Additive `benchmark_runs` (name, version, origin, fetched_at, content_hash,
  imported_at, submitter, mapping) and `benchmark_results` (run_id, model_id,
  metric, raw_value, norm_value 0-100 CHECK; UNIQUE (run_id, model_id,
  metric)) tables (ADR-0006 DDL) + `EXPECTED_TABLES` update.
* `benchmark/` module: `ingest.py` - curated JSON benchmark file parsing +
  full validation (top-level/result/mapping keys, secret-key scanning, origin
  URL sanitization, documented deterministic formulas `identity` /
  `fraction_to_percent`), model resolution against the existing registry
  (D-P4), batch ingestion atomic per file (invalid row -> nothing written),
  `--dry-run` without mutation, replay appends a NEW run + reports
  `duplicate_of` (never silent), scores via `scoring.ingest.set_score`
  (source `BENCHMARK`, `scored_at` = run date), `BENCHMARK_IMPORTED` event.
* New whitelisted event: `BENCHMARK_IMPORTED`.
* `[benchmark] import_dir` config (default `data/benchmarks`), mirrored in
  `config.toml` + `templates/config.toml`.
* CLI (additive): `benchmark import --file <path> [--name <benchmark>]
  [--dry-run]`, `benchmark list [--run <id>]`.
* Tests: `tests/test_benchmark.py` (39), `tests/test_benchmark_cli.py` (10);
  full Python suite 384/384; adapter/MCP 48/48; VS Code 28/28 + 2/2;
  `git diff --check` clean. No approval materialization / model registry (not
  authorized), no trend code (not authorized), no connectors changes (D-P6).

Pending:

* Phase 6 approval materialization + model registry (spec Section 9 content;
  "M3" in the approved spec numbering) - requires a separate owner
  authorization (D-P9). Trend analysis and the release package follow as
  later, separately-authorized milestones.

## Phase 4 - Dashboard / Reporting / History (RELEASED)

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
* Released and closed 2026-08-17 (commit `3c47c61`).

Pending:

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
  discovery/      __init__.py, sources.py, engine.py (Phase 6 M2)
  benchmark/      __init__.py, ingest.py (Phase 6 M3)
  connectors/     adapter.py, __init__.py, vscode/ (extension workspace),
                  mcp/ (server.py, tools.py) (Phase 5)
  dashboard/      __init__.py, engine.py, reports.py, history.py (Phase 4)
  tests/          conftest.py, test_database.py, test_schema.py,
                  test_config.py, test_providers.py, test_health.py,
                  test_availability.py, test_quota.py, test_validation.py,
                  test_scoring_engine.py, test_recommendation.py,
                  test_fallback.py, test_provenance.py,
                  test_dashboard_engine.py, test_dashboard_reports.py,
                  test_dashboard_history.py, test_dashboard_cli.py,
                  test_connectors_adapter.py, test_connectors_mcp.py,
                  test_discovery.py, test_discovery_cli.py,
                  test_benchmark.py, test_benchmark_cli.py
                  (384 Python tests total)
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
ADR-0001 for `scores`), `discovery_candidates` (ADR-0005, Phase 6 M2),
`benchmark_runs` + `benchmark_results` (ADR-0006, Phase 6 M3).

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
and `handover/PHASE-4-CLOSURE.md`. Released and closed 2026-08-17.

## Connectors (Phase 5)

Authorized 2026-08-17 (revised planning proposal approved). Milestones 1-3
complete and closed:

* Milestone 1: v1.2 Section 19 and `docs/review/PHASE5-CONNECTORS-SPEC.md`.
* Milestone 2: `connectors/adapter.py` (single read-only application
  interface delegating to existing Phase 1-4 modules) + `connectors/mcp/`
  (bounded MCP subset: legacy protocol era, stdio-only, Tools capability
  only, stdlib, no Python dependency D-1). 46 new tests.
* Milestone 3: `connectors/vscode/` (VS Code extension). Own isolated npm
  graph (D-4): self-contained Node/TypeScript workspace with owner-run
  `npm install`; read-only CLI invocation (`python -m app.main ...` via
  `execFile`), no SQLite access, no mutation, no network, no API-key
  handling, no decision logic. 27 offline TS unit tests + 2 real VS Code
  integration tests. Owner verification passed 2026-08-18; approved and
  closed.

Connectors contain no decision logic and perform no network/mutation/API-key/
config/environment changes. The documented transitive npm vulnerabilities
(via `@vscode/test-cli` dev toolchain) are accepted; no unrelated upgrades.
Phase 5 RELEASED and CLOSED 2026-08-18 (baseline `8231dce`, manifest
`docs/release/PHASE5-RELEASE-MANIFEST.md`, closure
`handover/PHASE-5-CLOSURE.md`).

---

# Not Yet Implemented

* Phase 6 remaining milestones (planning baseline + M1 documentation + M2
  discovery + M3 benchmark ingestion complete; each further milestone requires
  separate owner authorization): approval materialization / model registry,
  trend analysis, release package
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

Phase 4 implementation: High (216 tests passing; released and closed
2026-08-17)

Phase 5 documentation: High (plan approved, spec written; Milestones 2-3
implemented and closed; M4/M5 status and release recorded)

Phase 5 implementation: High (RELEASED and CLOSED 2026-08-18; 264 Python
tests + 48 MCP/adapter + 28/28 TS unit + 2/2 integration tests passing;
Milestone 5 release package accepted)

Phase 6 documentation: High (planning baseline approved 2026-08-18; M1
doc-before-code complete - v1.2 Section 20, proposal spec, ADR-0005/0006)

Phase 6 implementation: Milestone 2 (discovery + candidate workflow) and
Milestone 3 (benchmark ingestion + persistent storage) implemented, tested
(384/384 Python, adapter/MCP 48/48, VS Code 28/28 + 2/2) and committed;
remaining milestones require separate owner authorization (D-P9)

Concept: Validated
