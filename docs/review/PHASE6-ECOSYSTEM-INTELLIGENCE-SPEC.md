# PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md

# AI-Hub Phase 6 - Ecosystem Intelligence Proposal Spec

**Date:** 2026-08-18

**Status:** PROPOSED (Phase 6 planning baseline approved 2026-08-18 by owner;
Milestone 1 - documentation only, no implementation).

**Authoritative inputs:**

* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md` (planning baseline,
  commit `8f01b10`; D-P1..D-P9 approved)
* ADR-0005 (D-P1: provider/model discovery candidate representation, ACCEPTED)
* ADR-0006 (D-P3: benchmark result storage and ingestion, ACCEPTED)
* `AI-Hub Project Specification v1.2.md` Section 20 - Ecosystem Intelligence
  (Phase 6)

This document records the approved Phase 6 architecture and decisions for the
AI-Hub ecosystem intelligence capability (automatic provider/model discovery,
benchmark integration, trend analysis). It mirrors the Phase 4/5 proposal
spec pattern, delegates to the existing Phase 1-5 modules using their real
names, and is governed by the Constitution (Articles 1, 2, 4, 5, 6, 7, 8, 9,
10, 11, 12).

---

## 1. Objectives

1. Provide **automatic provider/model discovery** that produces review-gated
   candidates only; candidates may become registered providers/models through
   explicit human approval (v1.2 Sections 5 and 9; D-P1; ADR-0005).
2. Provide **benchmark integration** that ingests published benchmark results
   as persistence-provenance-backed, `BENCHMARK`-sourced scores (D-P3;
   ADR-0006).
3. Provide **trend analysis** that is deterministic, read-only and
   explainable over the existing append-only event-derived history
   ("insufficient data" instead of fabricated conclusions; Articles 4, 7, 10).
4. Deliver Phase 6 intelligence through **CLI surfaces only** (D-P6); no
   MCP/VS Code connector surface changes.
5. Preserve every closed-phase baseline: no Phase 1-5 redesign, no event
   rewrites, additive schema only with ADRs in place, `requirements.txt`
   unchanged (stdlib + sqlite3 + pytest only), isolated npm graph untouched,
   deterministic behaviour maintained.

---

## 2. Discovery architecture (ADR-0005)

### 2.1 Candidate model (D-P1, approved)

Discovery operates on a dedicated `discovery_candidates` table. Candidates
are **never** `providers` rows; the provider lifecycle (v1.2 Section 5) and
its `providers.status` CHECK constraint (`database/schema.sql:29`) are
unchanged. No migration or lifecycle change is introduced for
`PENDING_REVIEW`.

Candidate state set (table-column, not provider status):

```
DISCOVERED -> PENDING_REVIEW -> APPROVED | REJECTED
```

| State | Meaning |
|-------|---------|
| `DISCOVERED` | imported/fetched; not yet queued |
| `PENDING_REVIEW` | queued for human review |
| `APPROVED` | human-approved; provider (+models) materialized |
| `REJECTED` | human-dismissed; retained, never deleted (Article 5) |

Only explicit human action (`discovery approve`) moves a candidate to
`APPROVED` and materializes provider/model rows. Nothing auto-approves.
Candidates are never deleted; `REJECTED` retains full provenance.

### 2.2 Candidate table (additive)

```
discovery_candidates(
  id INTEGER PK AUTOINCREMENT,
  provider_name TEXT NOT NULL UNIQUE,
  source_type TEXT NOT NULL,          -- curated | network
  source_ref TEXT,                     -- file path or allowlisted URL
  payload TEXT NOT NULL,               -- JSON metadata (models, company,
                                       -- api_type, base_url, documentation_url)
  state TEXT NOT NULL DEFAULT 'DISCOVERED'
    CHECK (state IN ('DISCOVERED','PENDING_REVIEW','APPROVED','REJECTED')),
  content_hash TEXT NOT NULL,
  imported_at TEXT NOT NULL DEFAULT (datetime('now')),
  reviewed_at TEXT,
  reason TEXT,                         -- mandatory on reject; recorded on approve
  submitter TEXT NOT NULL,             -- e.g. "cli:discovery run"
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
)
```

Additive `CREATE TABLE IF NOT EXISTS` + `EXPECTED_TABLES` update
(`database/database.py`), matching the ADR-0001 precedent.

### 2.3 Workflow and materialization

```
curated import / allowlisted network fetch
        |
        v
DISCOVERED -> PENDING_REVIEW         (discovery run/import: candidates only)
        |
        v
human `discovery approve <id>`      (explicit action; Article 2)
        |
        v
provider + models created via governed ops   (core.providers + core.models,
                                               state NEW -> EVALUATING -> ACTIVE)
```

Approval invokes existing registry operations only (no raw SQL write path in
new modules). `PROVIDER_ADDED`, `PROVIDER_STATUS_CHANGED`, `MODEL_ADDED`
events are reused/emitted; materialized models belong to the approved
provider only.

### 2.4 Sources and ingestion boundaries (D-P2, approved)

* **Curated import (primary):** owner-provided structured files (JSON
  patches) imported on demand. Deterministic, audit-able, offline.
* **Network fetch (approved, controlled):** only allowlisted public metadata
  endpoints (config-gated `discovery.allowlisted_urls`, default empty =
  network disabled). Fetch is user-gated (Article 2), time/rate-bounded,
  requires an explicit `--allow-network`-style flag and a non-empty
  allowlist, never stores credentials/API keys, never targets private
  endpoints, and records an immutable snapshot (URL, fetched_at, content
  hash, size) before analysis so determinism holds (Article 7). Transports
  are injectable for offline tests (`monitoring/health.py` pattern).
* Network is **never required**; core AI-Hub stays offline-capable.

### 2.5 Events (extension of the whitelist)

New event types (proposal spec names; finalized in M2):
`DISCOVERY_CANDIDATE_ADDED`, `DISCOVERY_IMPORT_COMPLETE`,
`DISCOVERY_IMPORT_ERROR`, `DISCOVERY_CANDIDATE_APPROVED`,
`DISCOVERY_CANDIDATE_REJECTED`. Every import/approval/rejection records an
event (Article 8). No TREND events (trend is read-only).

---

## 3. Benchmark architecture (ADR-0006)

### 3.1 Rationale

`BENCHMARK` is an allowed `scores.source` (`scoring/ingest.py`,
`ALLOWED_SOURCES`; CHECK at `database/schema.sql:80`), but no ingestion
pipeline or benchmark provenance exists today. ADR-0006 establishes
persistent, provenance-aware benchmark storage (D-P3).

### 3.2 Storage (additive, ADR-0006)

```
benchmark_runs(
  id INTEGER PK AUTOINCREMENT,
  name TEXT NOT NULL,                 -- benchmark identity (e.g. "mmlu")
  version TEXT NOT NULL,
  origin TEXT NOT NULL,               -- file/URL; sources attribution
  fetched_at TEXT,
  content_hash TEXT NOT NULL,
  imported_at TEXT NOT NULL DEFAULT (datetime('now')),
  submitter TEXT NOT NULL,
  mapping TEXT NOT NULL               -- JSON: metric -> (dimension, formula)
)

benchmark_results(
  id INTEGER PK AUTOINCREMENT,
  run_id INTEGER NOT NULL REFERENCES benchmark_runs(id),
  model_id INTEGER NOT NULL REFERENCES models(id),
  metric TEXT NOT NULL,               -- raw benchmark metric name
  raw_value REAL NOT NULL,
  norm_value REAL NOT NULL,           -- 0-100 deterministic normalization
  UNIQUE (run_id, model_id, metric)
)
```

Raw values and retrieval metadata are preserved (source attribution) and are
never fabricated (Article 10). The mapping to canonical v1.2 dimensions is
recorded on the run; only mapped, validated rows produce `scores` rows with
`source = 'BENCHMARK'`.

### 3.3 Score mapping

Mapped benchmark rows update the normalized `scores` table via the existing
`scoring.ingest.set_score` upsert semantics (`UNIQUE (model_id, dimension)`);
value normalized 0-100 with a documented, deterministic formula recorded in
the run `mapping`. Confidence reflects documented benchmark properties;
`scored_at = run` date. Ageing (v1.2 Section 4) applies unchanged. Raw
benchmark values always remain queryable via `benchmark_results` - never lost,
never guessed.

### 3.4 Ingestion rules

* Batch import is **atomic per file**: any invalid row fails the whole
  import with the format/validation error recorded; no partial `scores` or
  `benchmark_results` writes (failure/degradation behaviour).
* Imports are auditable (`BENCHMARK_IMPORTED` event + run provenance),
  reproducible within the documented limitations (Article 8).
* Dry-run mode (`--dry-run`) validates without mutation.

---

## 4. Model registry integration (D-P4, approved)

Scope limited to the provider/model registry domain:

* `core/models.py` (new, M3): `add_model`, `list_models`, `update_model`,
  `archive_model` for models of approved (or existing) providers; emits the
  reserved `MODEL_ADDED` / `MODEL_UPDATED` / `MODEL_ARCHIVED` events
  (`core/events.py` - defined, currently never emitted). No deletion
  (Article 5).
* Discovery approval materializes provider + models via these governed
  operations only.
* No credential-management features; no silent expansion into unrelated
  model-management functionality.

---

## 5. Trend analysis

### 5.1 Scope

Deterministic, read-only analysis over the series produced by
`dashboard/history.py` (`score_history`, `availability_history`). No new
events, no tables, no writing. Point-in-time clusters/ snapshots (ADR-0004)
remain **deferred** (D-P8).

### 5.2 Outputs

For a request window:

* Direction (`up` / `down` / `stable` / `insufficient_data`) with the window
  criteria and minimum point count (configurable, documented).
* Magnitude (normalized delta over the window; explicit formula).
* Stability/variance measure (explicit, documented).
* Full regression series passed through unchanged.

Insufficient history yields `insufficient_data` with the thresholds used -
**never** a fabricated direction (Article 10). Identical DB + parameters ->
identical trend output (Article 7).

---

## 6. CLI / UI scope (D-P6, approved)

Additive CLI subcommands (`app/main.py` argparse pattern; existing commands
unchanged):

```
python -m app.main discovery run     [--allow-network] [--timeout N]  # allowlisted fetch (requires non-empty allowlist + flag)
python -m app.main discovery import  <file>                          # curated import
python -m app.main discovery list    [--state PENDING_REVIEW]
python -m app.main discovery approve <candidate_id> [--reason]
python -m app.main discovery reject  <candidate_id> --reason
python -m app.main benchmark import  --file <path> [--name <benchmark>] [--dry-run]
python -m app.main benchmark list    [--run <id>]
python -m app.main model list        [--provider <provider_id>]
python -m app.main trend scores      --model <model_id> [--dimension <d>]
python -m app.main trend availability --provider <provider_id>
```

Surface rules: approve/reject/import are explicit, human-gated; trend/model
list are read-only; every mutating operation records an event. No GUI in
Phase 6 (v1.2 Section 18.2 reporting philosophy). **No MCP/VS Code changes**
(D-P6): the adapter, MCP tool set, and VS Code `package.json`
`contributes.commands`/`activationEvents`/`FEATURES` are untouched.

---

## 7. Security / mutation boundaries (mirrors Phase 5, D-5 + Articles 1, 5, 6)

1. No write to AI-Hub data outside the documented governed operations
   (discovery candidate rows; materialized providers/models; benchmark
   runs/results + mapped scores; events).
2. No auto-approval; no scheduler/daemon/cron/autonomous recurring execution
   (D-P7). All operations are on-demand CLI.
3. No storing of credentials, API keys, tokens or secret configuration.
   Imported payloads are scanned for secret-like keys
   (`app/config.py._reject_secrets` pattern); stored URLs are sanitized
   (R-01 discipline) - never credentials.
4. No modification of config files/environment/VS Code settings.
5. Network used only per Section 2.4 (allowlist + snapshot + user gate).
6. No installation of packages/extensions; `requirements.txt` and the npm
   graph unchanged.

---

## 8. Config additions (documented, validated in M2)

Proposed keys (extend `DEFAULT_CONFIG`/`Config`/`validate()` in
`app/config.py`; mirrored in `config.toml` + `templates/config.toml`):

```
[discovery]
enabled = false                 # master switch for discovery workflows (default false)
allowlisted_urls = []           # explicit allowlist; empty = network disabled
timeout_seconds = 10
import_dir = "data/discovery"   # curated import location (documented example)

[benchmark]
import_dir = "data/benchmarks"  # curated import location (documented example)

[trend]
window_days = 90                # default analysis window
min_points = 3                  # minimum points for a directional conclusion
```

Decisions deferred to M2 planning detail: master-switch semantics for
`discovery.enabled` (import vs fetch gating), import-dir defaults and
location. These are configuration/validation details only and do not change
the approved architecture.

---

## 9. Milestones (with gates)

| # | Milestone | Deliverable | Gate |
|---|-----------|-------------|------|
| 1 | Doc-before-code (Article 11) | v1.2 Section 20; this spec; ADR-0005; ADR-0006; CHANGELOG/PROJECT-STATUS/handover refresh | Owner approval |
| 2 | Discovery + candidate workflow | `discovery/` module, `discovery_candidates`, curated import + controlled network (D-P2), review CLI, new event types, config additions | Tests pass |
| 3 | Approval materialization + model registry | approve -> provider (+models); `core/models.py`; `MODEL_*` events; `model list` | Tests pass |
| 4 | Benchmark integration | `benchmark/` ingest, ADR-0006 storage, BENCHMARK-source mapping, import/list CLI | Tests pass |
| 5 | Trend analysis | `trend/` read-only analysis over `dashboard.history`; trend CLI (CLI-only, D-P6) | Tests pass |
| 6 | Full regression + release package | 264 base + new suites green; PHASE6 manifest + closure; owner approval; immutable baseline | Owner approval |

Milestones are sequential gates (D-P9): each is independently inspected,
implemented, tested and verified before the next begins; milestones are never
silently combined. No milestone starts without explicit owner authorization.

---

## 10. Test acceptance criteria

1. Discovery produces candidates only; **no path** converts a candidate to a
   provider without `discovery approve`.
2. Every candidate has provenance (source, imported/fetched at, content
   hash, submitter) and `DISCOVERY_CANDIDATE_*` event trace.
3. Approval materializes provider + model rows through governed operations
   only; `MODEL_*` / `PROVIDER_*` events recorded.
4. Network fetch (when allowlisted) requires an explicit flag + non-empty
   allowlist; snapshot stored before analysis; tests run offline with
   injected transports (determinism, Article 7).
5. Benchmark import: valid rows produce `BENCHMARK`-sourced scores + raw
   `benchmark_results` rows with run provenance; invalid files fail atomically
   with a reported error; `--dry-run` mutates nothing (Article 10).
6. Trend outputs deterministic for identical inputs; insufficient data ->
    `insufficient_data` flag with thresholds (never fabricated).
7. No secret-like keys stored; URLs sanitized; `requirements.txt` and npm
   graph unchanged; VS Code `package.json`/MCP tool set unchanged (D-P6).
8. Regression: 264 base + new suites green at every milestone; adapter/MCP
   48/48; VS Code 28/28 + 2/2; `git diff --check` clean at the release
   baseline.
9. All new behaviour documented in v1.2 Section 20 + this spec + living docs
   before it ships (Article 11; v1.2 Section 14).
10. Concurrency/discipline: review-gated approval is single-operation;
    `discovery approve/reject` on a non-`PENDING_REVIEW` candidate fails with
    a clear error (no silent state rewrites).

---

## 11. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| D-P1 dual-state confusion (candidate vs provider status) | Medium | Candidate table + distinct event names + terminology notes in v1.2 §20 (mirrors §18.3 style notes) |
| Discovery data quality/drift | Medium | Provenance + content hashes; curated-import primary; review gate; flagged confidence |
| Network non-determinism (allowlisted) | Medium | Snapshot-before-analysis; injectable transports; offline-capable core |
| Benchmark normalization bias | Medium | Documented mapping per run; raw values preserved in `benchmark_results`; dry-run |
| Schema expansion regret | Medium | Additive-only; ADR-0005/0006 already accepted |
| Decision logic leaking into M2+ modules | Medium | Module boundary (discovery/benchmark/trend never import connectors; connectors never import them) |
| Accidental dependency introduction | Medium | `requirements.txt` unchanged; stdlib only |

---

## 12. Owner/manual actions

1. Approve this Milestone 1 proposal spec (gate M1 -> M2).
2. Authorize Milestone 2 separately (discovery + candidate workflow).
3. Authorize milestones 3-6 separately at each gate (D-P9).
4. Approve Phase 6 release + closure at the end (M6).
5. (Optional) populate `discovery.allowlisted_urls` for network fetch; supply
   curated import files.

---

*End of Phase 6 ecosystem intelligence spec. Milestone 1 - documentation
only; no implementation authorized beyond this document.*