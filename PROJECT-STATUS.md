# PROJECT-STATUS.md

# AI-Hub — Project Dashboard

> Open in 30 seconds and know where the project stands.

---

**Current version:** v1.2 (Architecture v1.1 + Implementation Spec v1.2)

**Current phase:** Phase 6 — Ecosystem Intelligence (planning baseline
approved 2026-08-18; Milestone 1 documentation complete; Milestone 2
(discovery + candidate workflow) implemented 2026-08-18; benchmark ingestion
+ persistent storage implemented 2026-08-19; approval materialization + model
registry (canonical Milestone 3) implemented and committed 2026-08-19;
remaining Phase 6 milestones not authorized)

**Completion %:** ~93% (Phases 1-5 released; Phase 6 planning + M1
documentation + M2 discovery/candidate workflow + benchmark ingestion +
approval materialization/model registry (canonical M3) complete; remaining
milestones pending authorization)

**Last update:** 2026-08-19

**Repository health:** Good (420/420 Python tests passing, no open defects;
adapter/MCP 48/48; connectors/vscode 28/28 TS unit tests + 2/2 integration
tests passing)

**Blocking issues:** None. Phase 5 released and closed (2026-08-18, baseline
`8231dce`). Phase 6 planning baseline approved (D-P1..D-P9), M1 doc-before-code
complete, M2 (discovery + candidate workflow) implemented, benchmark ingestion
+ persistent storage implemented, and approval materialization + model
registry (canonical M3) implemented; remaining milestones not yet authorized.

---

## Current Phase

Phase 1 released (baseline `7ceac80`). Phase 2 — Monitoring Engine released
(commit `ae0a6c2`, manifest `2c6e3eb`, 99/99 tests). ADR-0001 accepted
(commit `74d23b5`). Phase 3 — Scoring / Recommendation / Fallback implemented
and released (implementation `d6dd3c9`, manifest `ff4b8a7`, closure
`c6327f4`, approval `8370ba0`; 162/162 tests):

* Scoring engine (`scoring/`): normalized `scores` table (ADR-0001), aging,
  operational dimensions derived from monitoring, no fabricated values.
* Recommendation engine (`recommendation/`): built-in + custom profiles,
  deterministic ranking, explainability, provenance records.
* Fallback engine (`fallback/`): deterministic chain, eligibility from
  monitoring, recovery handling.
* CLI: `score`, `recommend`, `fallback` subcommands.
* Tests: 162/162 passing (59 new in Phase 3).

Phase 4 — Dashboard / Reporting / History authorized 2026-08-17 (plan
baseline `f9316e4`). Documentation step (Article 11 doc-before-code) completed
in `36d4aef`; implementation completed in `c49ea9b` (release commit):

* `dashboard/engine.py` - read-only aggregate views (overview, provider,
  score, recommendation, event).
* `dashboard/reports.py` - deterministic plain-text report builders
  (`providers`, `scores`, `recommendations`, `monitoring`, `overview`).
* `dashboard/history.py` - append-only event-derived score/availability
  history; point-in-time snapshots deferred pending ADR-0004.
* CLI: `dashboard status`, `dashboard report <name>`, `dashboard history`.
* No schema changes, no new dependencies, no new config keys/event types.
* Tests: 216/216 passing (54 new in Phase 4).
* Phase 4 release approved and closed (2026-08-17, commit `3c47c61`,
  manifest `docs/release/PHASE4-RELEASE-MANIFEST.md` status = closure
  accepted, baseline `c49ea9b`).

Phase 5 — Connectors (VS Code / MCP) approved 2026-08-17 (revised planning
proposal). Milestones 1-3 complete:

* Milestone 1 (docs): `docs/review/PHASE5-CONNECTORS-SPEC.md`, spec v1.2
  Section 19 - Connectors (Phase 5).
* Milestone 2 (adapter + MCP server): `connectors/adapter.py` (single
  read-only application interface delegating to Phase 1-4 modules,
  stdlib MCP subset over stdio, Tools capability only, legacy protocol era
  `2024-10-07`..`2025-11-25`), `connectors/mcp/` (`server.py`, `tools.py`).
  46 new tests (adapter 19, MCP 27); 262 Python tests total.
* Milestone 3 (VS Code extension): `connectors/vscode/` - 7 commands, reports
  tree view + webview panels, read-only CLI invocation, isolated npm graph
  (D-4). 27 offline TS unit tests + 2 real VS Code integration tests.
  Approved and closed by owner 2026-08-18.
* Milestone 4 (full connector regression) VERIFIED (2026-08-18): complete
  Python regression 262/262 (184s), Phase 5 MCP/adapter tests 46/46 (35s),
  VS Code offline unit tests 27/27, real VS Code integration tests 2/2;
  `git diff --check` clean; M1-M3 baseline `5cff03b` intact.
* Milestone 5 (hardening / release readiness) complete (2026-08-18): 3 new
  tests closing genuine coverage gaps (MCP `-32603` internal-error mapping;
  MCP empty database returns empty for every tool, never fabricated; VS Code
  `package.json` command/activationEvents consistency with `FEATURES`);
  living docs refreshed.

Milestones 1-4 are complete and closed; the Phase 5 release package (manifest
+ closure) was approved and the phase CLOSED 2026-08-18 (baseline `8231dce`,
manifest `docs/release/PHASE5-RELEASE-MANIFEST.md` status = closure accepted
in `handover/PHASE-5-CLOSURE.md`). The documented transitive npm
vulnerabilities (serialize-javascript / mocha via `@vscode/test-cli`) are
accepted; no unrelated dependency upgrades are performed.

Configuration alignment is maintained (`config.toml` == `templates/config.toml`).

Phase 6 — Ecosystem Intelligence authorized 2026-08-18. Planning baseline
approved (D-P1..D-P9) as commit `8f01b10`
(`docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md`). Milestone 1
(doc-before-code, Article 11) complete:

* `AI-Hub Project Specification v1.2.md` Section 20 - Ecosystem Intelligence
  (Phase 6): discovery candidates (D-P1), provenance-aware benchmark storage
  (D-P3), deterministic read-only trend analysis, security/mutation
  boundaries, config/events/dependencies.
* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md` - proposal spec
  (discovery + benchmark + trend + model registry; CLI-only D-P6; milestones
  and acceptance criteria).
* ADR-0005 (D-P1 discovery candidate representation) and ADR-0006 (D-P3
  benchmark result storage), both ACCEPTED. ADR-0004 remains reserved for the
  deferred score-snapshots decision (D-P8).
* Living docs refreshed. No implementation code changes.

Milestone 2 (discovery + candidate workflow) authorized and implemented
(2026-08-18, owner authorization against M1 baseline `d32324a`):

* Additive `discovery_candidates` table (ADR-0005 DDL; state CHECK
  `DISCOVERED/PENDING_REVIEW/APPROVED/REJECTED`; `provider_name` UNIQUE) in
  `database/schema.sql`, added to `EXPECTED_TABLES`.
* `discovery/` module - `sources.py` (curated JSON import, record validation,
  secret scanning, URL sanitization, injectable urllib transport) and
  `engine.py` (candidate lifecycle add/list/queue/approve/reject; per-dataset
  atomic validation; duplicate reporting; controlled network run with
  snapshot-before-analysis, D-P2).
* `discovery approve/reject` are deterministic candidate-state transitions
  only in M2; provider/model materialization belongs to Milestone 3.
* New whitelisted events: `DISCOVERY_CANDIDATE_ADDED`,
  `DISCOVERY_IMPORT_COMPLETE`, `DISCOVERY_IMPORT_ERROR`,
  `DISCOVERY_CANDIDATE_APPROVED`, `DISCOVERY_CANDIDATE_REJECTED`.
* `[discovery]` config keys validated and mirrored in `config.toml` /
  `templates/config.toml` (`enabled` master switch default false;
  `allowlisted_urls` default empty; `timeout_seconds`; `import_dir`).
* CLI (additive): `discovery import`, `discovery run --allow-network`,
  `discovery list [--state]`, `discovery approve`, `discovery reject`.
* Tests: `tests/test_discovery.py` + `tests/test_discovery_cli.py`; full
  Python suite 337/337 (264 base + 73 new); adapter/MCP 48/48; VS Code 28/28
  unit + 2/2 integration; `git diff --check` clean. No benchmark/trend/model
  registry code, no connectors changes (D-P6), `requirements.txt` and
  npm graph unchanged.

Milestone 3 (benchmark ingestion + persistent storage, D-P3/ADR-0006)
authorized and implemented (2026-08-19, owner authorization against the M2
baseline `a037dfd`):

* Additive `benchmark_runs` (name, version, origin, fetched_at, content_hash,
  imported_at, submitter, mapping) and `benchmark_results` (run_id, model_id,
  metric, raw_value, norm_value; UNIQUE (run_id, model_id, metric)) tables in
  `database/schema.sql`; added to `EXPECTED_TABLES` (ADR-0006 DDL).
* `benchmark/` module - `ingest.py`: curated JSON parsing + full validation
  (top-level/result/mapping keys, secret-key scanning, origin URL
  sanitization, documented deterministic formulas `identity` /
  `fraction_to_percent`), model resolution against the existing registry
  (D-P4; unknown models fail atomically), batch ingestion atomic per file
  (invalid row -> nothing written), `--dry-run` without mutation, replay
  appends a NEW run and reports `duplicate_of` (never silent, Article 5),
  scores mapped via `scoring.ingest.set_score` (source `BENCHMARK`,
  `scored_at` = run date), every import records `BENCHMARK_IMPORTED`.
* New whitelisted event: `BENCHMARK_IMPORTED`.
* `[benchmark] import_dir` config key (validated, default
  `data/benchmarks`) mirrored in `config.toml` / `templates/config.toml`.
* CLI (additive): `benchmark import --file <path> [--name <benchmark>]
  [--dry-run]`, `benchmark list [--run <id>]`.
* Tests: `tests/test_benchmark.py` (39) + `tests/test_benchmark_cli.py` (10);
  full Python suite 384/384 (337 + 47 new M3); adapter/MCP 48/48; VS Code
  28/28 unit + 2/2 integration; `git diff --check` clean. No approval
  materialization / model registry (not authorized), no connectors changes
  (D-P6), `requirements.txt` and npm graph unchanged.
* Living documentation refreshed (PROJECT-STATUS, CURRENT-STATE, NEXT-STEPS).

**Milestone-numbering note:** the owner authorized this work as Phase 6 "M3"
(benchmark ingestion + persistent storage). The approved planning baseline
(Section 12) and proposal spec (Section 9) number benchmark integration as
"M4" and approval materialization + model registry as "M3". This M3
implementation follows the owner's explicit content authorization
(benchmark); approval materialization + model registry (canonical "M3") was
subsequently re-authorized by the owner and implemented 2026-08-19 (next
section).

Approval materialization + model registry (canonical Milestone 3, spec
numbering) authorized and implemented (2026-08-19, owner re-authorization
after the read-only milestone reconciliation; baseline `eca910f`):

* `core/models.py` - governed model registry operations (add/get/list/update/
  archive), emitting the previously-reserved `MODEL_ADDED` / `MODEL_UPDATED` /
  `MODEL_ARCHIVED` events. `archive_model` follows the owner's Option A
  decision: event-only archival with a required reason; the `models` row is
  retained unchanged and `list_models` keeps returning it (Article 5; no
  schema column, no lifecycle state, no monitoring-availability coupling).
* `discovery approve` now materializes the approved candidate through governed
  registry operations only: `core.providers.add_provider` starting at `NEW`
  (lifecycle starts at NEW per v1.2 Section 5) with candidate provenance in
  notes, then `core.models.add_model` per candidate model. The candidate
  transition, the materialization and every audit event commit atomically
  (`_NoCommit` proxy defers inner auto-commits); any failure rolls back
  everything and the candidate stays `PENDING_REVIEW`. A provider name already
  registered fails deterministically before anything is written.
* CLI (additive): `model list [--provider <id>]`.
* Tests: `tests/test_models.py` (registry) + `tests/test_models_cli.py` (CLI)
  + M3 materialization tests in `tests/test_discovery.py`; full Python suite
  420/420 (384 + 36 new); adapter/MCP 48/48; VS Code 28/28 unit + 2/2
  integration; `git diff --check` clean. No trend code (not authorized), no
  connectors changes (D-P6), no schema/config changes, `requirements.txt` and
  npm graph unchanged.
* Living documentation refreshed (PROJECT-STATUS, CURRENT-STATE, NEXT-STEPS).

Remaining Phase 6 milestones (trend analysis, release package) each require a
separate owner authorization (D-P9 sequential gates).

Release documents:

* `docs/release/PHASE1-RELEASE-MANIFEST.md` (immutable, git SHA `7ceac80`)
* `docs/release/PHASE2-RELEASE-MANIFEST.md` (immutable, git SHA `ae0a6c2`)
* `docs/release/PHASE3-RELEASE-MANIFEST.md` (immutable, git SHA `ff4b8a7`)
* `docs/release/PHASE4-RELEASE-MANIFEST.md` (immutable, git SHA `c49ea9b`,
  closure accepted)
* `docs/release/PHASE5-RELEASE-MANIFEST.md` (immutable, git SHA `8231dce`,
  closure accepted)
* `docs/review/PHASE3-IMPLEMENTATION-PLAN.md`
* `docs/review/PHASE3-SCORING-SPEC.md`
* `docs/review/PHASE4-IMPLEMENTATION-PLAN.md`
* `docs/review/PHASE4-DASHBOARD-SPEC.md`
* `docs/review/PHASE5-CONNECTORS-SPEC.md`

## Architecture Maturity

* Specifications: v1.2 approved; agent-logging, project-registry, monitoring
  and scoring proposal specs documented.
* ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0005, ADR-0006 ACCEPTED (ADR-0004
  reserved for the deferred score-snapshots decision, D-P8).
* Reviews: R-01..R-08 amendments applied; final review PASS; Phase 2 and
  Phase 3 plans approved 2026-08-01; Phase 5 connectors spec in review.

## Pending Owner Decisions

* Authorize Phase 6 trend analysis (spec Section 9 milestone content; D-P9
  sequential gates) and the release milestone
* Owner-run `npm install` inside `connectors/vscode/` for local builds
  (already executed for verification; required for any later rebuilds)

## Next Milestone

Phase 6 trend analysis (read-only, deterministic; per the approved planning
baseline, spec Section 9) — once authorized by the owner. The release package
follows as a later, separately-authorized milestone.

## Open Documentation Items

* `projects/registry.json` seed conformance (`renamed_to`,
  `has_credentials_remote`) - non-blocking

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Provider API endpoints change rapidly | High | Seed is metadata only; `monitor validate` reports status |
| Architecture drift | Medium | ADRs + specs + reviews |
| Temporary outages mistaken for retirement | Medium | Lifecycle rules (v1.2 Section 5) enforced in Phase 2 |
| Schema drift between spec and implementation | Low | Schema tests assert spec columns |
| Network dependence of health checks | Medium | Injected transports; tests run offline |
| Score staleness | Medium | Aging multipliers (v1.2 Section 4) + configurable boundaries |
