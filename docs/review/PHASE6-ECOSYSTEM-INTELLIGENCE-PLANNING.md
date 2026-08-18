# PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md

# AI-Hub Phase 6 - Ecosystem Intelligence Planning Package

**Date:** 2026-08-18

**Status:** PLANNING BASELINE - APPROVED (owner, 2026-08-18; D-P1..D-P9
approved). Planning only. This document authorizes NO implementation.

**Baselines (immutable):**

* Phase 1: `7ceac80c9b0b1718ec090307b2220e1350ca85dd`
* Phase 2: `ae0a6c2a917586e597df5dd51ff9c51522dd9afe` (manifest `2c6e3eb`)
* Phase 3: `d6dd3c9` (implementation), `ff4b8a7` (manifest), `c6327f4`
  (closure), `8370ba0` (approval)
* Phase 4: `c49ea9b37bebf07b34a5acef8046b483614dee69` (manifest `3c47c61`)
* Phase 5: `8231dcecf1f5968fee007967e40452bbe7fe63eb` (implementation),
  `c113d2c1018d881c7f41ff443639f6a9bc30173f` (release package / current HEAD)
* `main` == `origin/main` (0 ahead / 0 behind), working tree clean - verified.
* Test baseline: 264/264 Python, 48/48 adapter/MCP, 28/28 VS Code offline
  unit, 2/2 VS Code real integration.

**Governance sources inspected (evidence, not assumptions):**

* `CONSTITUTION.md` (Articles 1-12)
* `AI-Hub Project Specification v1.2.md` (Sections 1, 5, 6, 8, 9, 14, 15, 17,
  18, 19)
* `decisions/0001-*` (ACCEPTED), `decisions/0002-*` (ACCEPTED),
  `decisions/0003-*` (ACCEPTED), `decisions/README.md`
* `spec/project-registry.md` (PROPOSED; ADR-0003), `spec/agent-logging.md`
* `docs/review/amendment-summary-R01-R08.md`
* `docs/review/PHASE5-CONNECTORS-SPEC.md`, `docs/review/PHASE4-DASHBOARD-SPEC.md`,
  `docs/review/PHASE4-IMPLEMENTATION-PLAN.md`
* `docs/release/PHASE5-RELEASE-MANIFEST.md`,
  `handover/PHASE-5-CLOSURE.md` (deferred-item register)
* `handover/CURRENT-STATE.md`, `handover/NEXT-STEPS.md`, `PROJECT-STATUS.md`
* `database/schema.sql`, `database/database.py`, `app/config.py`,
  `app/main.py`, `core/providers.py`, `core/events.py`, `monitoring/*`,
  `scoring/*`, `recommendation/*`, `fallback/*`, `dashboard/*`,
  `connectors/*`, `projects/registry.json`, `scripts/seed_providers.py`

---

## 1. Executive summary

Phase 6 - **AI Ecosystem Intelligence** is the final roadmap phase listed in
v1.2 Section 15 ("AI Ecosystem Intelligence / Automatic Discovery / Benchmark
Integration / Trend Analysis") and the phase to which Phases 2-5 explicitly
deferred their ecosystem-facing gaps (v1.2 Section 9 automatic discovery;
`handover/PHASE-5-CLOSURE.md` Section 7).

Phase 6 establishes three capability pillars, all consistent with the
existing architecture and with Constitution Articles 1, 2, 4, 5, 7, 8, 9, 10:

1. **Automatic Discovery** - propose new AI providers/models into AI-Hub as
   review-gated candidates that may only become registered providers/models
   through explicit human approval (v1.2 Section 9's PENDING_REVIEW pattern).
2. **Benchmark Integration** - ingest published benchmark results as
   `BENCHMARK`-sourced scores with full provenance (run name, version, date,
   source), exploiting the ADR-0001 normalized `scores` design that already
   makes any dimension "a row, never a migration" (Article 9).
3. **Trend Analysis** - deterministic, read-only analysis over the
   append-only event-derived history already delivered in `dashboard/history.py`
   (Articles 4, 7, 8, 10), keeping point-in-time snapshots (ADR-0004)
   optional and deferred.

Phase 6 does **not** include: the project-registry *workspace* discovery
domain (ADR-0003 describes that as a separate future capability); MCP modern
era (`2026-07-28`, D-1); credentials/cost tracking; credential-based features;
auto-approval of anything; or a redesign of Phases 1-5. The default delivery
is offline-capable (stdlib + sqlite3 + pytest only), additive in schema, and
explicitly gated at every milestone.

Phase 6 is the last planned phase; its Definition of Done is tied to the
v1.2 Section 17 readiness criteria (reproducible decisions, explainable
recommendations, deterministic lifecycle, non-destructive monitoring,
deterministic fallback chains, preserved history, documented decisions).

**Discovery representation ambiguity (RESOLVED, D-P1):** v1.2 Section 9 says
automatic discoveries "enter PENDING_REVIEW", but the Section 5 provider
lifecycle begins at `NEW` and the `providers.status` CHECK constraint in
`database/schema.sql:29` does not list `PENDING_REVIEW`. Two readings were
documented in Section 6 below. Approved resolution (2026-08-18): discovery
candidates are represented in a dedicated candidate table; the provider
lifecycle and its database constraints are preserved untouched.

---

## 2. Baseline and inspected evidence

Repository state (verified 2026-08-18, planning session):

* HEAD: `c113d2c1018d881c7f41ff443639f6a9bc30173f` (Phase 5 release package).
* Branch: `main`; `main` == `origin/main` (0 ahead / 0 behind); clean tree.
* Phase 5 release manifest: `docs/release/PHASE5-RELEASE-MANIFEST.md`
  (baseline `8231dce`, status APPROVED, closure accepted 2026-08-18).
* Phase 5 closure: `handover/PHASE-5-CLOSURE.md`; deferred item #1:
  "Automatic provider discovery (PENDING_REVIEW workflow) - v1.2 Section 9;
  out of Phase 5 scope - Phase 6".

Implemented capabilities Phase 6 builds on (file:line evidence):

| Capability | Evidence in repo | Phase 6 relationship |
|------------|------------------|----------------------|
| Provider registry (manual) | `core/providers.py` (`add_provider`, `update_provider`, `archive_provider`, `LEGAL_TRANSITIONS`, `VALID_STATUSES`) | Approval target for discovery candidates |
| Provider lifecycle | v1.2 Section 5; `database/schema.sql:28-29` CHECK | Candidates must NOT bypass it |
| Monitoring (Section 9 pattern) | `monitoring/*`, `monitoring/availability.apply_lifecycle` | Defines the PENDING_REVIEW intent; never auto-activates (Article 2) |
| Normalized scores + `BENCHMARK` source | `database/schema.sql:73-85`; `scoring/ingest.py` (`ALLOWED_SOURCES` includes `BENCHMARK`) | Benchmark ingestion anchor |
| Score aging | `scoring/engine.py` (fresh/aging/old/stale) | Applied unchanged to ingested scores |
| Event-reconstructed history | `dashboard/history.py` (`score_history`, `availability_history` from `SCORE_*` / `MONITOR_STATUS_CHANGED` / `HEALTH_CHECK_*`) | Trend analysis data source |
| Dashboard reports | `dashboard/reports.py` `REPORT_BUILDERS` | Trend/candidate reporting mirror |
| Read-only adapter + connectors | `connectors/adapter.py`; `connectors/mcp/`; `connectors/vscode/` | Optional read-only surface for trends/candidates |
| Event vocabulary | `core/events.py` `EVENT_TYPES` (whitelist); `MODEL_ADDED`/`MODEL_UPDATED`/`MODEL_ARCHIVED` defined but never emitted | New discovery/benchmark/model event types required |
| Models table, no management API | `database/schema.sql:43-64`; models inserted only via raw SQL in tests | Minimal model materialization API required |
| Config conventions | `app/config.py` (`DEFAULT_CONFIG`, `Config`, `validate`), `config.toml` | Extension of the same pattern |
| Schema application, no migrations | `database/database.py` (`initialize` uses `executescript`; `EXPECTED_TABLES`; no `user_version`, no ALTER/migration facility) | Limits schema evolution to additive or requires a migration ADR |

Inspected gaps that are explicitly **adjacent but out of Phase 6 scope**
(flagged, not folded in):

* Project-registry *workspace* discovery (ADR-0003, `spec/project-registry.md`
  Section 6 "NOT IMPLEMENTED; future capability"). That is the *managed
  projects* domain (Git repos under `workspace.root`), a different domain from
  the AI provider/model ecosystem. ADR-0003 acceptance requires "a future
  phase" - Phase 6 is the ecosystem phase; including workspace discovery would
  need explicit owner authorization as a separate workstream.
* Config keys `[workspace] root`, `[registry] path`, `logging.log_root` exist
  in `config.toml:53-61` but are consumed by no code (ADR-0002/0003 follow-up).
  Phase 6 does not consume them unless the workspace-discovery workstream is
  authorized.
* `projects/registry.json` conformance fields (`renamed_to`,
  `has_credentials_remote`) - non-blocking, unrelated to Phase 6; carried from
  Phase 3/4 closure as a low-severity item.
* MCP modern era `2026-07-28` (D-1) - stays out of scope.
* ADR-0004 point-in-time score snapshots - optional, stays deferred.

---

## 3. Problem statement

Today AI-Hub's ecosystem knowledge is **manual and static**: providers and
scores can only enter through a human author (or the fixed seed), benchmark
results have no ingestion or provenance path, and "intelligence" about how the
ecosystem evolves is limited to reconstructed history with no analysis layer.
Consequences, evidenced by the repository:

1. **No automatic discovery.** v1.2 Section 9 promises that automatic
   discoveries enter a review state (PENDING_REVIEW) and only approved
   discoveries become ACTIVE; Phases 2-5 implemented everything *except* the
   discovery path (`core/providers.py:9` documents "no automatic discovery";
   `handover/PHASE-2..5-CLOSURE.md` defer it).
2. **No model registry operation.** `models` is writable only by raw SQL;
   `MODEL_*` event types exist (`core/events.py`) but are never emitted. A
   discovered/approved provider cannot bring its models in through a governed
   path.
3. **No benchmark integration.** `BENCHMARK` exists only as a permitted
   `source` string for a single manual `set_score` call
   (`scoring/ingest.py`). There is no batch import, no run metadata, no
   audit trail of "which benchmark, when, from where".
4. **No trend analysis.** `dashboard/history.py` returns raw series; nothing
   computes direction, magnitude or stability, so recommendations cannot
   reflect "this model is improving/declining" without a new analysis layer.
5. **Unknown ecosystem knowledge stays unknown, but cannot even be
   *acquired*.** Article 10 is honored by construction, yet the acquisition
   pipeline that would populate the knowledge is missing.

Phase 6 closes gaps 1-4 through the three pillars, preserving all closed-phase
baselines and immutability rules.

---

## 4. Phase 6 objectives

O1. Implement **automatic provider/model discovery** that produces
    review-gated candidates only; approved candidates are materialized as
    registered providers/models through the existing governance rules
    (v1.2 Sections 5 and 9; Articles 1, 2, 10).
O2. Implement **benchmark integration** that ingests published benchmark
    results as `BENCHMARK`-sourced scores with recorded provenance (Article 8).
O3. Implement **trend analysis** that produces deterministic, read-only,
    explainable trend views over existing event-derived history, with
    "insufficient data" instead of fabricated conclusions (Articles 4, 7, 10).
O4. Provide governed CLI surfaces for discovery review, benchmark import, and
    trend inspection; optionally expose read-only Phase 6 views through the
    existing adapter/MCP/VS Code connectors (decision D-P6).
O5. Preserve every closed-phase baseline: no Phase 1-5 redesign, no event
    rewrite, no schema migration without an ADR, `requirements.txt` unchanged
    (except none), npm graph untouched, deterministic behaviour maintained.
O6. Advance the project to the v1.2 Section 17 Definition of Done as the
    final roadmap phase.

---

## 5. Scope boundaries

### 5.1 In scope

* Provider/model discovery *candidate* generation (identifiers, metadata,
  source URL/file, fetched/imported timestamp, content hash, submitter).
* The discovery review workflow: list candidates; explicit human
  `approve` / `reject`; approved candidates materialize providers (+ their
  models) through governed registry operations; rejected candidates are
  closed without deletion (Article 5).
* A minimal, governed model-registry operation (metadata for models of
  approved providers; emit the reserved `MODEL_*` event types) so discovery
  and benchmarks can attach models deterministically.
* Benchmark result ingestion with provenance (benchmark name/version, run
  date, origin, raw values, mapping to canonical dimensions) stored through
  the `scores` table (source `BENCHMARK`) and/or a benchmark audit table -
  see decision D-P3.
* Trend analysis over score history and availability history (direction,
  magnitude, windowed stability) computed on read from append-only events.
* New config keys, new event types, new CLI subcommands, new tests, and the
  v1.2 Phase 6 documentation section (Article 11; v1.2 Section 14).
* A release package (manifest + closure) at phase end, mirroring Phases 4-5.

### 5.2 Out of scope

* **Workspace / project-registry discovery** (Git repos under
  `workspace.root`; ADR-0003 Section 6) - a separate domain. **DEFERRED by
  owner decision D-P5 (2026-08-18): not implemented during Phase 6** unless a
  future explicit owner decision changes the scope.
* Auto-approval of any candidate; any change to the v1.2 Section 5 lifecycle
  (D-P1 resolution is the dedicated candidate table; the lifecycle is
  unchanged).
* Finding or storing credentials, API keys, tokens, secret configuration; any
  feature that *requires* credentials (e.g. spend/cost tracking) (Article 6).
* Unrestricted network behaviour. Network use in Phase 6 is approved (D-P2,
  2026-08-18) **only** for discovery and benchmark ingestion, subject to
  explicit allowlisting, provenance snapshotting, failure handling, no
  credential/API-key storage, and existing security/governance constraints.
  Core AI-Hub stays offline-capable.
* MCP modern era (`2026-07-28`), HTTP/SSE MCP transports (D-1).
* Point-in-time `score_snapshots` (ADR-0004) - **DEFERRED by owner decision
  D-P8 (2026-08-18): not implemented during Phase 6** unless separately
  authorized.
* Model *seeding* as a broad manual-data program; the governed materialization
  of approved-discovery models (objective O1) is the boundary (D-P4).
* Any UI beyond the existing CLI text reports. MCP/VS Code connector surfaces
  are **not** authorized (D-P6, 2026-08-18): Phase 6 intelligence surfaces are
  CLI-only; the Phase 5 connector boundary is preserved.
* Scheduled/periodic execution. Phase 6 delivers **on-demand operations only**
  (D-P7, 2026-08-18); no scheduler, daemon, cron integration or autonomous
  recurring execution.

### 5.3 Relationship to the existing provider registry

* The `providers`, `models`, `scores`, `availability`, `events` and
  `recommendations` tables are unchanged in semantics.
* Discovery candidates receive their **own** storage so the `providers.status`
  lifecycle and its CHECK constraint remain exactly as released (D-P1,
  approved 2026-08-18).
* Approval of a candidate invokes the existing registry operations/state
  rules (starting at `NEW`/`EVALUATING` and proceeding per Section 5);
  `PROVIDER_ADDED`, `PROVIDER_STATUS_CHANGED`, `PROVIDER_ARCHIVED` event
  emission semantics are reused.

### 5.4 Relationship to monitoring / history / reporting

* Monitoring never modifies provider information directly (v1.2 Section 9)
  and Phase 6 discovery/review never bypasses that rule.
* History stays append-only and event-derived (`dashboard/history.py`);
  trend analysis consumes it read-only.
* Reporting gains optional deterministic candidate/trend reports following
  the `REPORT_BUILDERS` pattern (self-describing headers, explicit ordering).
* `monitoring.interval_minutes` / `dashboard.refresh_seconds` remain inert
  (no scheduler; decision D-P7).

### 5.5 Relationship to MCP / connectors

* Connectors and the shared adapter remain strictly read-only and free of
  decision logic (v1.2 Section 19; `connectors/adapter.py`).
* **D-P6 approved (2026-08-18): no MCP/VS Code connector surfaces are added in
  Phase 6.** Phase 6 intelligence surfaces are CLI-only; the Phase 5
  connector boundary (read-only, decision-free, no new commands/tools/features)
  is preserved. No Phase 6 write path exists through any connector, and no
  connector ever approves or imports.

---

## 6. Architecture impact

### 6.1 Proposed module layout (mirrors Phase 3/4 package convention)

| Proposed module/file | Purpose |
|----------------------|---------|
| `discovery/__init__.py`, `discovery/engine.py` | Candidate lifecycle: discover/import, list, approve, reject; candidate source classification |
| `discovery/sources.py` | Curated-import reader (+ optional gated network fetch, D-P2) producing snapshot payloads |
| `benchmark/__init__.py`, `benchmark/import.py` | Benchmark result ingestion + mapping to dimensions (+ audit records, D-P3) |
| `trend/__init__.py`, `trend/analysis.py` | Read-only trend computation over `dashboard.history` series |
| `core/models.py` (new) | Minimal model registry operations (approval materialization + metadata; emits `MODEL_*`) |
| `tests/test_discovery.py`, `tests/test_benchmark.py`, `tests/test_trend.py`, `tests/test_models.py` | New unit suites |
| `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md` | Proposal spec (doc-before-code, Milestone 1) |

No changes to `core/providers.py` core contracts (add/update/archive/list)
unless D-P1 selects the lifecycle extension. Decision logic never enters
connectors.

### 6.2 PENDING_REVIEW representation - decision D-P1

Governing texts conflict on one point and it **must** be an owner decision:

* v1.2 Section 9: "Automatic discoveries enter PENDING_REVIEW. Only approved
  discoveries become ACTIVE records."
* v1.2 Section 5 lifecycle: begins at `NEW`; `PENDING_REVIEW` is not a
  lifecycle state.
* `database/schema.sql:29` CHECK does not include `PENDING_REVIEW`;
  `core/providers.VALID_STATUSES` (7 states) matches.
* `spec/project-registry.md` Section 4 carries a terminology note treating
  `PENDING_REVIEW` as a "provider lifecycle state name" shared with the
  project registry domain.

**Option A (recommended) - dedicated candidate table, lifecycle intact.**
New table `discovery_candidates` (or `provider_candidates`) holds candidate
rows with their own state set (`DISCOVERED`, `PENDING_REVIEW`, `APPROVED`,
`REJECTED`) and full provenance payload. Approval creates a real provider row
via the existing `add_provider`/state rules (NEW -> EVALUATING -> ACTIVE).
Pros: no schema CHECK migration; Section 5 lifecycle, `VALID_STATUSES`,
monitoring and recommendation eligibility untouched; clean separation.
Cons: the word "PENDING_REVIEW" lives on the candidate, not the provider.

**Option B - extend the provider lifecycle with `PENDING_REVIEW`.**
Requires schema CHECK migration (`providers.status`), `VALID_STATUSES`
extension, `LEGAL_TRANSITIONS` additions, availability-state exclusions,
monitoring/filter updates, and a new migration facility (none exists;
`database/database.py` has no `user_version`/ALTER path) - a significantly
larger blast radius and a new ADR.

Recommendation: **Option A**.

**RESOLVED (D-P1, owner approval 2026-08-18): Option A - dedicated
discovery-candidate table.** The provider lifecycle and its current database
constraints are preserved; no migration or lifecycle change is introduced to
accommodate `PENDING_REVIEW`. Approval materializes candidates as providers
only through explicit human action. An ADR records this resolution in
Milestone 1 (Article 8).

### 6.3 Data sources and ingestion boundaries (decision D-P2)

* **Default: offline curated import.** Candidate metadata and benchmark
  results arrive as owner-provided structured files (e.g. JSON/CSV patches,
  `scripts/` seed convention), imported on demand. Deterministic, audit-able,
  offline-capable, matches the seed pattern (`scripts/seed_providers.py`).
* **Approved (D-P2, 2026-08-18) - controlled network pull.** Fetch public
  metadata (e.g. official model-list/benchmark endpoints) subject to explicit
  allowlisting, capture the raw response as an immutable snapshot record
  (fetch timestamp, URL, content hash, size) before any analysis, then run
  **all downstream analysis over the snapshot** so determinism (Article 7)
  holds. Fetches are user-gated (Article 2), time/rate-bounded, never store
  credentials or API keys and never target private endpoints, and use
  injectable transports for offline tests (same test pattern as
  `monitoring/health.py`). Unrestricted network behaviour is prohibited
  (Article 6).
* Network is **never required** for Phase 6 to function; offline curated
  import remains the primary path.

### 6.4 Scheduling (decision D-P7)

No scheduler exists in the repository (verified: no cron/scheduler/loop in
production code; `monitoring.interval_minutes` inert). **D-P7 approved
(2026-08-18): Phase 6 executes on demand only** (`discover run`,
`benchmark import`, `trend ...`). No scheduler, daemon, cron integration or
autonomous recurring execution is introduced in Phase 6; automated scheduling
remains an ADR-0003 open question (`spec/project-registry.md` Section 9).

---

## 7. Data / model impact

### 7.1 Schema (additive only, by default)

* `discovery_candidates` table (new; D-P1 Option A): candidate id, provider
  name (unique across candidates), source type, source ref, payload JSON,
  state (`DISCOVERED`/`PENDING_REVIEW`/`APPROVED`/`REJECTED`), provenance
  (imported/fetched at, content hash, submitter), created/updated, reason on
  reject/approve. Additive `CREATE TABLE IF NOT EXISTS` + `EXPECTED_TABLES`
  update (matches ADR-0001 precedent and `database/database.py`).
* Benchmark audit table(s) (new; D-P3 approved 2026-08-18 - persistent,
  provenance-aware benchmark storage): `benchmark_runs` (id, name, version,
  origin, imported_at, source hash) and `benchmark_results` (run_id, model_id,
  dimension/metric, value, norm_value) preserving raw values independently of
  score mapping. The required schema/design decision is documented through an
  ADR before implementation (source attribution and retrieval metadata
  preserved; benchmark data never fabricated; ingestion auditable and
  reproducible within documented limitations).
* No alteration of existing tables in the base scope. No lifecycle change
  (D-P1 resolved to candidate table) and no snapshot adoption (D-P8 deferred)
  in Phase 6.
* `scores` rows created by benchmark mapping use `source = 'BENCHMARK'` and
  the canonical dimension set of v1.2 Section 1.2 (value kept normalized
  0-100 with documented mapping); the existing UNIQUE (model_id, dimension)
  constrains one current score per dimension. Raw benchmark metrics live in
  `benchmark_results` (or, under no-schema option D-P3.alt, in the run/score
  provenance) - never lost.

### 7.2 Models

Approved discovery materialization creates provider + model rows via the
governed model operation (`core/models.py`), emitting `MODEL_ADDED` /
`MODEL_UPDATED` (reserved but currently un-emitted, `core/events.py`).
`MODEL_ARCHIVED` is used only for archival semantics (Article 5), never
deleting.

### 7.3 Events (extension, documented per v1.2 Section 14)

New whitelist additions proposed (names exact, to be finalized in the
proposal spec): `DISCOVERY_CANDIDATE_ADDED`, `DISCOVERY_IMPORT_COMPLETE`
(+ `DISCOVERY_IMPORT_ERROR`), `DISCOVERY_CANDIDATE_APPROVED`,
`DISCOVERY_CANDIDATE_REJECTED`, `BENCHMARK_IMPORTED`,
`TREND_*` events are **not** needed (trend is read-only; none recorded),
`MODEL_ADDED`/`MODEL_UPDATED`/`MODEL_ARCHIVED` become emitted.

### 7.4 Backward compatibility and migration

* Existing 7 tables, indexes, FKs, and SQL semantics unchanged.
* Existing CLI subcommands and flags unchanged; new subcommands are additive.
* Existing tests (264/264 base) must remain green during every milestone.
* No data migration in the additive scheme; the existing `initialize()`
  (idempotent `executescript`) is extended only by new additive statements and
  `EXPECTED_TABLES`.
* `requirements.txt` unchanged; stdlib + sqlite3 + pytest only (mirrors D-1).
  Optional network fetch uses stdlib `urllib` (as `monitoring/health.py`).

---

## 8. Connector / integration impact

* Connectors stay read-only, decision-free, offline (v1.2 Section 19; Phase 5
  manifest guarantees). Phase 6 adds no write path through any connector and
  never invokes approval/import from connectors.
* **D-P6 approved (2026-08-18): no connector surfaces are added in Phase 6.**
  The Phase 5 connector boundary is preserved: `package.json`
  `contributes.commands`/`activationEvents` and the MCP tool set do not change
  in Phase 6.
* Adapter delegation-identity tests (connector output == engine output) remain
  as-is; no new Phase 6 adapter functions are introduced until a future
  separate authorization.

---

## 9. CLI / UI / API impact

Proposed additive CLI (existing argparse pattern in `app/main.py`):

```
python -m app.main discovery run --source <file>            # import candidates
python -m app.main discovery list [--state PENDING_REVIEW]  # queue for review
python -m app.main discovery approve <candidate_id> [--reason]
python -m app.main discovery reject  <candidate_id> --reason
python -m app.main benchmark import --file <path> [--name <benchmark>]
python -m app.main benchmark list
python -m app.main model list [--provider <id>]             # new read-only registry
python -m app.main trend scores --model <id> [--dimension <d>]
python -m app.main trend availability --provider <id>
```

Surface rules: review/approve/reject/import are explicit, human-gated
operations (Articles 1, 2); trend/model-list are read-only; every mutating
operation records an event (Article 8). No GUI in Phase 6 (v1.2 Section 18.2
reporting philosophy). UI = text reports; optional connector views under D-P6.

---

## 10. Security and governance considerations

* **Consent and sovereignty (Articles 1, 2):** no candidate becomes an ACTIVE
  provider, and no benchmark row is ingested, without an explicit human
  command; nothing is automatic or scheduled silently (D-P7).
* **Secrets (Article 6):** discovery/benchmark payloads must never contain
  credentials; imported files are scanned/rejected on secret-like keys
  (reuse `app/config.py._reject_secrets` pattern); stored URLs are sanitized
  with `has_secret_remote`-style flags (R-01 discipline); raw credentials
  never stored.
* **Determinism (Article 7):** all analysis runs over stored snapshots;
  identical DB + snapshot inputs produce identical outputs; explicit ordering;
  no hidden weighting (Article 4).
* **Truthfulness (Article 10):** empty queues, format errors, insufficient
  history and unknown values are reported as such, never fabricated.
* **History (Article 5):** candidates and benchmark data are never silently
  deleted; reject/archive semantics only.
* **Traceability (Article 8):** every discovery import, approval, rejection,
  model materialization, and benchmark import emits an append-only event with
  a deterministic identifier; the acting command/operator is captured.
* **Governance:** ADR(s) for D-P1 (required) and D-P3 (if benchmark tables
  adopted); v1.2 specification update in Milestone 1 (Article 11; v1.2 Section
  14); no closed-baseline edits.

---

## 11. Testing strategy

* Offline-first: in-memory SQLite fixtures (existing `tests/conftest.py`
  pattern); injected transports for any optional network path
  (`monitoring/health.py` pattern).
* Unit suites: `test_discovery.py` (candidate states, no auto-approval,
  dedupe, provenance, empty queue, read-only of unrelated state),
  `test_benchmark.py` (import valid/invalid, mapping to dimensions, source =
  BENCHMARK, provenance, no partial writes on error),
  `test_trend.py` (direction/magnitude/stability, insufficient-data flag,
  determinism, read-only), `test_models.py` (add/list/update archival
  semantics, MODEL_* events, no model deletion).
* Review-gate acceptance tests (Gherkin style, v1.2 Section 13): candidate
  approval path; discovery never writes to `providers` before approval;
  rejection never deletes.
* Determinism and no-fabrication cases for every new surface (empty DB, empty
  queues, stale/unknown history).
* Regression gate every milestone: base 264 + new suites green;
  connectors/adapter 48/48; VS Code 28/28 + 2/2 (14 if D-P6 touches
  connector tests) unchanged semantics.
* Security tests: secret-key rejection on imported payloads; sanitized URLs.
* `git diff --check` clean; no network during tests.

---

## 12. Milestone decomposition

| # | Milestone | Deliverable | Gate |
|---|-----------|-------------|------|
| 1 | Doc-before-code (Article 11) | v1.2 Phase 6 section, `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md` (proposal spec), ADR(s) for D-P1 (+ D-P3 if needed), CHANGELOG/PROJECT-STATUS/handover refresh | Owner approval |
| 2 | Discovery + candidate workflow | `discovery/` module, candidate storage, curated import + controlled network (D-P2 approved), review CLI (list/approve/reject), new event types, config additions | Tests pass |
| 3 | Approval materialization + model registry | Approve -> provider (+models) via governed ops; `core/models.py`; `MODEL_*` events; `model list` | Tests pass |
| 4 | Benchmark integration | `benchmark/` ingest, provenance audit (D-P3), BENCHMARK-source score mapping, import/list CLI | Tests pass |
| 5 | Trend analysis | `trend/` read-only analysis over `dashboard.history`; trend CLI (CLI-only; D-P6 - no connector surfaces) | Tests pass |
| 6 | Full regression + release package | Complete suite green (264 base + new), PHASE6 manifest + closure, owner approval, immutable baseline | Owner approval |

Every milestone is independently verifiable; planning (this document) must
not be mixed with any implementation milestone.

---

## 13. Acceptance criteria

1. Discovery can produce candidates only; **no path** converts a candidate to
   a registered provider without an explicit `discovery approve`.
2. Every candidate carries provenance (source, imported/fetched at, content
   hash, submitter) and an `ADDED`/`APPROVED`/`REJECTED` event trace.
3. Approval materializes provider + model rows through the governed registry
   operations only (no raw SQL write path in the new modules).
4. Imported benchmark results become `scores` with `source = 'BENCHMARK'`
   (value 0-100 mapped deterministically) and their raw form + run metadata
   remain audit-able; failed imports write nothing (atomicity) and report the
   format error (never fabricated).
5. Trend outputs are deterministic for identical inputs, read-only, and mark
   "insufficient data" (with the window criteria) rather than inventing
   direction (Articles 7, 10).
6. No secret-like keys are stored; URLs are sanitized; `requirements.txt`,
   npm graph and all closed baselines are unchanged.
7. Regression: 264 base + all new suites green; adapter/MCP 48/48; VS Code
   28/28 + 2/2; `git diff --check` clean at the release baseline.
8. Connectors remain read-only, decision-free, offline; no Phase 6 connector
   surface is added (D-P6 approved CLI-only, 2026-08-18).
9. All new behaviour is documented in the v1.2 Phase 6 section and living
   docs before it ships (Article 11; v1.2 Section 14).

---

## 14. Risks and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| D-P1 ambiguity: PENDING_REVIEW vs Section 5 lifecycle | High | Owner decision in this package; ADR records the resolution; single representation |
| Discovery data quality/drift (stale, unstructured official metadata) | Medium | Provenance + snapshot hashes; curated import default; review gate; flagged confidence (vs 10) |
| Network non-determinism (if D-P2 granted) | Medium | Snapshot-before-analysis; injectable transports; offline-capable core |
| Schema expansion regrets (candidate/benchmark tables) | Medium | Additive-only; ADR-0001-style normalized design; ADR for table adoption |
| Benchmark normalization bias | Medium | Documented mapping; raw values preserved; EXPLAINABLE mapping in provenance |
| Review backlog (candidate queue) | Low | `discovery list --state` tooling; explicit reject; no auto-approval |
| Decision logic leaking into connectors | Medium | Delegation identity tests; module boundary; no connector write path |
| Architecture drift by multiple agents | Medium | ADRs + specifications + this package |
| Accidental dependency introduction | Medium | `requirements.txt` unchanged; isolated npm graph |

---

## 15. Dependencies

* **Decided (planning baseline approval 2026-08-18):** D-P1 (dedicated
  candidate table; lifecycle unchanged) - required for Milestone 2;
  D-P2 (controlled network for discovery/benchmark ingestion, allowlisted +
  provenance + failure handling); D-P3 (persistent provenance-aware benchmark
  storage, ADR before implementation); D-P4 (provider/model registry scope
  only); D-P5 (ADR-0003 workspace discovery - DEFERRED); D-P6 (CLI-only, no
  connector surfaces); D-P7 (on-demand execution only); D-P8 (ADR-0004
  snapshots - DEFERRED); D-P9 (sequential milestone gates).
* **Required at M1:** v1.2 Phase 6 specification section per Article 11 and
  v1.2 Section 14; ADR for D-P1 and ADR for D-P3 (benchmark storage) before
  implementation.
* **Technical:** Python 3.11+ (tomllib) / verified 3.14.2; stdlib only; no new
  Python or npm dependencies (D-1/D-4 discipline).
* **Non-blocking follow-ups carried from earlier phases (not Phase 6 work):**
  `projects/registry.json` conformance fields; ADR-0004 snapshots; MCP modern
  era.

---

## 16. Owner decisions required

The planning baseline decisions D-P1..D-P9 (options and recommendations
below) were **approved by the owner on 2026-08-18**.

| # | Decision | Options | Approved resolution |
|---|----------|---------|---------------------|
| D-P1 | Discovery representation (Section 6.2) | A. Candidate table; B. Extend provider lifecycle with PENDING_REVIEW (+ schema migration + ADR) | **A** - dedicated candidate table; lifecycle and constraints preserved; no migration for PENDING_REVIEW |
| D-P2 | Discovery / benchmark data acquisition | Offline curated import only; optionally + user-gated network pull with snapshots | Controlled network approved for discovery/benchmark ingestion subject to allowlisting, provenance, failure handling, no credentials/API keys, no unrestricted network |
| D-P3 | Benchmark storage | Dedicated `benchmark_runs`/`benchmark_results` (+ ADR); or schema-free mapping into `scores`/provenance only | Persistent, provenance-aware benchmark storage; schema/design ADR required before implementation; provenance + retrieval metadata preserved; no fabrication |
| D-P4 | Model registry scope | Minimal governed materialization of approved-discovery models; vs also a broad model-seeding program | Provider/model registry scope only; no credential-management features; no silent scope expansion |
| D-P5 | ADR-0003 project-registry workspace discovery | Defer (separate domain); or include as parallel workstream | **DEFERRED** - not implemented during Phase 6 |
| D-P6 | Read-only connector exposure of trends/candidates | CLI-only; or also adapter + MCP tools + VS Code features | **CLI-only** - no MCP/VS Code surfaces; Phase 5 connector boundary preserved |
| D-P7 | Scheduling | On-demand CLI only; or scheduling workstream | **On-demand only** - no scheduler/daemon/cron/autonomous recurring execution |
| D-P8 | ADR-0004 score snapshots | Remain deferred; or prioritize in Phase 6 for trend performance | **DEFERRED** - not implemented during Phase 6 |
| D-P9 | Phase 6 milestone gating | Milestones 1-6 each gate on owner approval (Phase 5 pattern) | Sequential gates; each milestone independently inspected, implemented, tested and verified before the next; no silent milestone combination |

D-P1 resolution (dedicated candidate table) is the binding representation for
Milestone 2; D-P2/D-P3 govern the ingestion scope; D-P5/D-P8 are deferred;
D-P6 keeps surfaces CLI-only; D-P7 keeps execution on-demand. This approval
**does not authorize implementation or M1 execution** (Section 17).

---

## 17. Explicit implementation authorization gate

This document is a **planning baseline** (approved 2026-08-18, D-P1..D-P9).

* The planning baseline **does not** start, implement, release, or close
  Phase 6.
* No Phase 1-5 file, baseline, or immutability rule is affected by this
  document or its commit.
* Phase 6 implementation (including **M1** documentation execution) may begin
  **only** after the owner provides a SEPARATE, explicit **Phase 6 M1
  implementation authorization** (the same pattern as Phases 4-5).
* Milestone 1 (documentation / doc-before-code) is the first implementation
  milestone and must itself be approved before any code (Article 11).
* No implementation commit, schema change, migration, discovery, benchmark
  ingestion, trend-analysis code, release manifest or closure report is
  produced from this planning baseline; `main` is not pushed by planning
  work.

---

*End of Phase 6 planning baseline. Approved 2026-08-18 (D-P1..D-P9). No
implementation authorized.*