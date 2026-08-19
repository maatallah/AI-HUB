# handover/NEXT-STEPS.md

# AI-Hub Next Steps

## Immediate Goal

Phase 5 (Connectors - VS Code / MCP) is RELEASED and CLOSED (baseline
`8231dce`, closure accepted 2026-08-18). Phase 6 (Ecosystem Intelligence) is
authorized: planning baseline approved (D-P1..D-P9, commit `8f01b10`),
Milestone 1 (doc-before-code) complete (v1.2 Section 20, proposal spec,
ADR-0005/0006), Milestone 2 (discovery + candidate workflow) implemented and
committed (2026-08-18), benchmark ingestion + persistent storage implemented
and committed (2026-08-19, owner-authorized against M2 baseline `a037dfd`),
and approval materialization + model registry (canonical Milestone 3)
implemented and committed (2026-08-19, owner-authorized). The next defined
step is Phase 6 **trend analysis**, gated on a separate owner authorization
(D-P9). Prior released phases: Phase 4 (`c49ea9b`, 216/216 tests, closure
accepted 2026-08-17).

Phase 1 has been formally closed - see `handover/PHASE-1-CLOSURE.md` and
`docs/release/PHASE1-CLOSURE-SUMMARY.md`.

Phase 2 is released - see `handover/PHASE-2-CLOSURE.md`, plus
`docs/review/PHASE2-IMPLEMENTATION-PLAN.md`,
`docs/review/PHASE2-MONITORING-SPEC.md` and
`docs/release/PHASE2-RELEASE-MANIFEST.md`.

Phase 3 is released (162/162 tests) - see
`docs/review/PHASE3-IMPLEMENTATION-PLAN.md`,
`docs/review/PHASE3-SCORING-SPEC.md`,
`handover/PHASE-3-CLOSURE.md` and
`docs/release/PHASE3-RELEASE-MANIFEST.md` (status APPROVED).

Phase 4 is released (`c49ea9b`, 216/216 tests, closure accepted 2026-08-17) -
see `docs/review/PHASE4-IMPLEMENTATION-PLAN.md`,
`docs/review/PHASE4-DASHBOARD-SPEC.md`,
`docs/release/PHASE4-RELEASE-MANIFEST.md` (baseline `c49ea9b`) and
`handover/PHASE-4-CLOSURE.md`.

Phase 5 is RELEASED and CLOSED (2026-08-18, baseline `8231dce`, closure
accepted) - see `docs/review/PHASE5-CONNECTORS-SPEC.md`, v1.2 Section 19,
`connectors/adapter.py`, `connectors/mcp/`, `connectors/vscode/`,
`docs/release/PHASE5-RELEASE-MANIFEST.md` and `handover/PHASE-5-CLOSURE.md`.

Phase 6 (Ecosystem Intelligence) is authorized (2026-08-18). Planning
baseline `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md` approved
(D-P1..D-P9, commit `8f01b10`). Milestone 1 (doc-before-code) complete -
`docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md`, v1.2 Section 20,
`decisions/0005-*` and `decisions/0006-*`. Milestone 2 (discovery +
candidate workflow) implemented and committed 2026-08-18 - `discovery/`
module, additive `discovery_candidates` table, `[discovery]` config,
5 discovery event types, review CLI. Milestone 3 (benchmark ingestion +
persistent storage) implemented and committed 2026-08-19 - `benchmark/`
module, additive `benchmark_runs`/`benchmark_results` tables (ADR-0006),
`[benchmark]` config, `BENCHMARK_IMPORTED` event, `benchmark import|list`
CLI. Approval materialization + model registry (canonical Milestone 3)
implemented and committed 2026-08-19 - `core/models.py`, governed
materialization in `discovery/engine.py`, `MODEL_*` events, `model list`
CLI. The remaining implementation milestones require separate owner
authorizations (D-P9).

---

# Pre-Phase 5 Actions (owner)

- [x] Approve Phase 4 release (`docs/release/PHASE4-RELEASE-MANIFEST.md`,
  approved 2026-08-17)
- [x] Sign off Phase 4 closure (`handover/PHASE-4-CLOSURE.md`, accepted
  2026-08-17)
- [x] Authorize Phase 5 (Connectors - VS Code / MCP) planning (approved
  2026-08-17)

---

# Step 3 — Phase 4 Entry Conditions

Phase 4 (Dashboard / Reporting / History) must NOT start until a separate
owner authorization prompt is provided. Before coding, the Phase 4 plan must
be produced and approved (same pattern as Phase 2/3).

Entry conditions (all met as of 2026-08-01):

- [x] Phase 3 release approved (immutable baseline `d6dd3c9`, manifest
  APPROVED)
- [x] Phase 3 closure signed off (`handover/PHASE-3-CLOSURE.md`)
- [x] `main` synchronized with `origin/main`
- [x] 162/162 tests passing
- [x] ADR-0001 accepted (`scores` table) - scoring data model available

---

# Phase 4 Entry Authorization

Phase 4 authorized by owner 2026-08-17 (plan baseline `f9316e4`). Plan and
proposal spec:

* `docs/review/PHASE4-IMPLEMENTATION-PLAN.md` (approved)
* `docs/review/PHASE4-DASHBOARD-SPEC.md` (proposal spec)

---

# Phase 1 Completion Status

- [x] Create repository skeleton
- [x] Initialize SQLite database with documented schema
- [x] Implement configuration system
- [x] Implement manual provider registry
- [x] Create test framework
- [x] Create initial provider seed dataset (`scripts/seed_providers.py`)
- [x] Select a `LICENSE` (MIT)
- [x] Review ADR-0001 (PROPOSED, assessed ready for ACCEPTED)
- [x] Create `handover/PHASE-1-CLOSURE.md` and `PROJECT-STATUS.md`
- [x] Re-verify tests on a clean checkout (49/49 passed, 2026-08-01)

# Phase 2 Completion Status

- [x] Health check module (`monitoring/health.py`)
- [x] Availability + lifecycle tracking (`monitoring/availability.py`)
- [x] Quota architecture (`monitoring/quota.py`)
- [x] Seed validation (`monitoring/validation.py`)
- [x] Event vocabulary extension (`core/events.py`)
- [x] Monitoring config keys + docs (v1.2 Section 10)
- [x] CLI `monitor run/status/validate`
- [x] Tests: 99/99 passing (50 new)
- [x] Phase 2 release review + approval (owner)

# Phase 3 Completion Status

- [x] Scoring engine (`scoring/`) - scores, aging, derived operational dims
- [x] Recommendation engine (`recommendation/`) - profiles, ranking, explain
- [x] Fallback engine (`fallback/`) - chain, eligibility, recovery
- [x] Provenance records (`recommendations` table + events)
- [x] Event vocabulary extension (`core/events.py`)
- [x] Scoring config keys + docs (v1.2 Section 10)
- [x] CLI `score`, `recommend`, `fallback`
- [x] Tests: 162/162 passing (59 new)
- [x] Phase 3 release review + approval (owner, 2026-08-01)

# Phase 4 Completion Status

- [x] `docs/review/PHASE4-DASHBOARD-SPEC.md` + v1.2 Section 18
- [x] `dashboard/engine.py` aggregation views
- [x] `dashboard/reports.py` report builders
- [x] `dashboard/history.py` event-derived history
- [x] CLI `dashboard status/report/history`
- [x] Tests: dashboard engine, reports, history (54 new; 216/216 total)
- [x] Phase 4 release review + approval (owner, 2026-08-17) - released and
  closed (baseline `c49ea9b`)

---

# Phase 6 Entry Authorization

Phase 6 authorized by owner 2026-08-18 (planning baseline + M1 + M2). Planning and
proposal documents:

* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md` (planning baseline,
  approved D-P1..D-P9)
* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md` (proposal spec)
* `AI-Hub Project Specification v1.2.md` Section 20 (Ecosystem Intelligence)
* `decisions/0005-provider-model-discovery-candidates.md` (D-P1, ACCEPTED)
* `decisions/0006-benchmark-result-storage.md` (D-P3, ACCEPTED)

Milestone 1 (documentation / doc-before-code), Milestone 2 (discovery +
candidate workflow), Milestone 3 (benchmark ingestion + persistent storage)
and approval materialization + model registry (canonical Milestone 3) are
complete. The next milestone (trend analysis) must NOT start until a separate
owner authorization prompt is provided (D-P9 sequential gates).

Milestone-numbering note: the owner authorized benchmark integration as "M3";
the approved planning baseline (Section 12) and proposal spec (Section 9)
number benchmark as M4 and approval materialization as M3. The completion
checklist below follows the owner's milestone content labels.

---

# Phase 6 Completion Status

- [x] Planning baseline approved (D-P1..D-P9, commit `8f01b10`)
- [x] Milestone 1: v1.2 Section 20 + `docs/review/PHASE6-ECOSYSTEM-
      INTELLIGENCE-SPEC.md` + ADR-0005/0006 + living-doc refresh
- [x] Milestone 2: discovery + candidate workflow (2026-08-18; `discovery/`
      module, `discovery_candidates` table, `[discovery]` config, 5 event
      types, review CLI; 337/337 Python)
- [x] Milestone 3 (owner label; spec "M4"): benchmark ingestion + persistent
      storage (2026-08-19; `benchmark/` module, `benchmark_runs` /
      `benchmark_results` tables, `[benchmark]` config, `BENCHMARK_IMPORTED`
      event, `benchmark import|list` CLI; 384/384 Python)
- [x] Milestone 3 (canonical): approval materialization + model registry
      (2026-08-19; `core/models.py`, governed materialization in
      `discovery/engine.py`, `MODEL_*` events, `model list` CLI; 420/420
      Python)
- [ ] Milestone: trend analysis (requires owner authorization)
- [ ] Milestone: full regression + release package (requires owner
      authorization)

---

# Pre-Phase 6 Actions (owner)

- [x] Authorize Phase 6 planning (2026-08-18)
- [x] Approve planning decisions D-P1..D-P9 (2026-08-18)
- [x] Authorize Milestone 1 documentation (2026-08-18)
- [x] Authorize Milestone 2 implementation (2026-08-18)
- [x] Authorize Milestone 3 implementation (benchmark ingestion + persistent
      storage, 2026-08-19)
- [x] Authorize approval materialization + model registry (canonical Phase 6
      M3, 2026-08-19)

---

# Step 1 — Phase 6 Documentation (doc-before-code, Milestone 1)

Completed (2026-08-18): `AI-Hub Project Specification v1.2.md` Section 20,
`docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md`, `decisions/0005-*`,
`decisions/0006-*`, CHANGELOG.md, PROJECT-STATUS.md,
handover/CURRENT-STATE.md, handover/NEXT-STEPS.md.

---

# Step 2 — Phase 6 Milestone 2 (discovery + candidate workflow)

Completed (2026-08-18, owner authorization against M1 baseline `d32324a`):

* `discovery/sources.py` - curated JSON import, candidate record validation,
  secret-key scanning (app.config pattern), URL sanitization, injectable
  urllib transport.
* `discovery/engine.py` - candidate lifecycle (add/list/queue/approve/reject)
  with deterministic state transitions; per-dataset atomic validation; duplicate
  reporting; controlled network `run` (D-P2) with snapshot-before-analysis.
* Additive `discovery_candidates` table (ADR-0005) + `EXPECTED_TABLES`.
* New whitelisted events: `DISCOVERY_CANDIDATE_ADDED`,
  `DISCOVERY_IMPORT_COMPLETE`, `DISCOVERY_IMPORT_ERROR`,
  `DISCOVERY_CANDIDATE_APPROVED`, `DISCOVERY_CANDIDATE_REJECTED`.
* `[discovery]` config keys (validated; mirrored in `config.toml` +
  `templates/config.toml`); CLI subcommands `discovery import|run|list|
  approve|reject`.
* Tests: 337/337 Python (264 base + 73 new), adapter/MCP 48/48, VS Code
  28/28 + 2/2, `git diff --check` clean. No M3-M5 code; connectors untouched
  (D-P6).

Milestone 3 and every later implementation milestone must each be authorized
separately by the owner before it starts (D-P9).

---

# Step 3 — Phase 6 Milestone 3 (benchmark ingestion + persistent storage)

Completed (2026-08-19, owner authorization against M2 baseline `a037dfd`;
owner resolved replay semantics: append NEW run + report `duplicate_of`,
never silent):

* `benchmark/ingest.py` - curated JSON benchmark file parsing + full
  validation (top-level/result/mapping keys, secret-key scanning, origin URL
  sanitization, documented deterministic formulas `identity` /
  `fraction_to_percent`), model resolution against the existing registry
  (D-P4), batch ingestion atomic per file (invalid row -> nothing written),
  `--dry-run` without mutation, replay appends a NEW run + reports
  `duplicate_of`, scores via `scoring.ingest.set_score` (source `BENCHMARK`,
  `scored_at` = run date), `BENCHMARK_IMPORTED` event.
* Additive `benchmark_runs` (name, version, origin, fetched_at, content_hash,
  imported_at, submitter, mapping) + `benchmark_results` (run_id, model_id,
  metric, raw_value, norm_value 0-100 CHECK; UNIQUE (run_id, model_id,
  metric)) tables (ADR-0006) + `EXPECTED_TABLES`.
* New whitelisted event: `BENCHMARK_IMPORTED`.
* `[benchmark] import_dir` config (default `data/benchmarks`; mirrored in
  `config.toml` + `templates/config.toml`); CLI `benchmark import --file
  <path> [--name <benchmark>] [--dry-run]` and `benchmark list [--run <id>]`.
* Tests: `tests/test_benchmark.py` (39) + `tests/test_benchmark_cli.py` (10);
  384/384 Python (337 base + 47 new), adapter/MCP 48/48, VS Code 28/28 + 2/2,
  `git diff --check` clean. No approval materialization / model registry (not
  authorized), no trend code (not authorized), connectors untouched (D-P6),
  `requirements.txt` and npm graph unchanged.

The next milestone (trend analysis) and every later implementation milestone
must each be authorized separately by the owner before it starts (D-P9).

---

# Step 4 — Phase 6 Milestone 3 (canonical): approval materialization + model registry

Completed (2026-08-19, owner re-authorization after the read-only milestone
reconciliation; baseline `eca910f`):

* `core/models.py` - governed model registry operations (add/get/list/update/
  archive_model), emitting the previously-reserved `MODEL_ADDED` /
  `MODEL_UPDATED` / `MODEL_ARCHIVED` events. `archive_model` implements the
  owner's Option A decision: event-only archival with a required non-empty
  reason; the `models` row is retained unchanged and `list_models` continues
  to return it (Article 5). No schema column, no model lifecycle state, no
  monitoring-availability coupling.
* `discovery/engine.py` - `approve_candidate` materializes the approved
  candidate through governed registry operations only (`core.providers.
  add_provider` starting at `NEW` with candidate provenance in notes, then
  `core.models.add_model` per candidate model). Candidate transition +
  materialization + every audit event commit atomically (the `_NoCommit`
  proxy defers the inner modules' auto-commits to the single outer commit);
  any failure rolls back everything and the candidate stays `PENDING_REVIEW`;
  a provider name already registered fails deterministically before anything
  is written. No raw SQL write path in the new module.
* CLI (additive): `model list [--provider <id>]`.
* Tests: `tests/test_models.py`, `tests/test_models_cli.py`, M3
  materialization/event/atomicity/provenance tests in `tests/test_discovery.py`
  (M2 no-materialization pins superseded); 420/420 Python (384 + 36 new),
  adapter/MCP 48/48, VS Code 28/28 + 2/2, `git diff --check` clean. No trend
  code (not authorized), connectors untouched (D-P6), no schema/config
  changes, `requirements.txt` and npm graph unchanged.

The next milestone (trend analysis) and every later implementation milestone
must each be authorized separately by the owner before it starts (D-P9).

---

# Phase 5 Completion Status (historical)

- [x] Spec v1.2 Section 19 (Connectors) (Milestone 1)
- [x] `docs/review/PHASE5-CONNECTORS-SPEC.md` (Milestone 1)
- [x] `connectors/adapter.py` shared read-only adapter (Milestone 2)
- [x] `connectors/mcp/` MCP server (stdio, bounded subset) (Milestone 2)
- [x] `connectors/vscode/` VS Code extension (Milestone 3)
- [x] Tests: connectors adapter / MCP / vscode (46 Python + 27 TS unit +
      2 integration)
- [x] Milestone 4: full connector regression VERIFIED (2026-08-18) -
      262/262 Python, 46/46 MCP/adapter, 27/27 TS unit, 2/2 integration
- [x] Milestone 5: hardening / release readiness (3 new tests + living-doc
      refresh) - complete
- [x] Milestone 5: release package (manifest + closure) + owner approval -
      approved and closed 2026-08-18 (baseline `8231dce`)

# Step 2 — Phase 4 Documentation (doc-before-code)

Completed in `36d4aef`: `docs/review/PHASE4-DASHBOARD-SPEC.md`, v1.2 Section
18, CHANGELOG.md, PROJECT-STATUS.md, handover/CURRENT-STATE.md,
handover/NEXT-STEPS.md.

# Step 3 — Phase 4 Implementation

Completed in `c49ea9b`: read-only dashboard engine, deterministic reports and
append-only event-derived history (see `docs/review/PHASE4-DASHBOARD-SPEC.md`).
No schema changes unless ADR-0004 is approved.

Step 3 done - dashboard is implemented, 216/216 tests pass, Phase 4 released
and closed (closure accepted 2026-08-17, baseline `c49ea9b`).

---

# Next Recommended Agent

Backend-focused implementation agent for Phase 6 (Ecosystem Intelligence),
**trend analysis** - gated on a separate owner authorization. Phase 6 planning
baseline (D-P1..D-P9, commit `8f01b10`), Milestone 1 documentation, Milestone
2 (discovery + candidate workflow), Milestone 3 (benchmark ingestion +
persistent storage, committed 2026-08-19) and approval materialization +
model registry (canonical M3, committed 2026-08-19) are complete (v1.2
Section 20; proposal spec; ADR-0005/0006; `discovery/` module; `benchmark/`
module; `core/models.py`; 420/420 Python green). Do not begin the next
milestone without explicit authorization.

Recommended input:

* START-HERE.md
* CONSTITUTION.md
* AI-Hub Specification v1.2 (Sections 5, 9, 15, 19, 20)
* docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md
* docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md
* decisions/0005-provider-model-discovery-candidates.md
* decisions/0006-benchmark-result-storage.md
* discovery/engine.py, discovery/sources.py, benchmark/ingest.py,
  core/models.py, app/main.py, database/schema.sql
* handover/CURRENT-STATE.md
* handover/NEXT-STEPS.md
