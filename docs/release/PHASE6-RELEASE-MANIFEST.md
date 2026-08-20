# PHASE6-RELEASE-MANIFEST.md

# AI-Hub Phase 6 Release Manifest

**Project name:** AI-Hub

**Release name:** Phase 6 - Ecosystem Intelligence (Discovery / Benchmark /
Model Registry / Trend Analysis)

**Phase number:** Phase 6 (of 6) - the final roadmap phase (v1.2 Section 15)

**Release date:** 2026-08-19

**Phase 5 baseline:** `c113d2c1018d881c7f41ff443639f6a9bc30173f` (immutable)

**Phase 6 implementation baseline:** `6655def` (trend analysis - the last
implementation commit before the release package)

**Current branch:** `main`

**Status:** PENDING OWNER APPROVAL (release package created 2026-08-19 per owner
authorization; closure acceptance and release approval pending)

> This document is the immutable reference baseline for any subsequent work. It
> records the state at release. Later project evolution must not rewrite it.

---

## Phase 6 milestone commits

No milestone number is invented for the release commit itself. Phase 6
implementation commits, in canonical order (approval materialization and
benchmark swap labels - see the release reconciliation below):

| Commit | Phase 6 milestone | Content |
|--------|-------------------|---------|
| `8f01b10` | Planning baseline | Planning baseline; decisions D-P1..D-P9 approved 2026-08-18 |
| `d32324a` | Milestone 1 | Doc-before-code: v1.2 Section 20, proposal spec, ADR-0005/0006, living docs |
| `a037dfd` | Milestone 2 | Discovery + candidate workflow (`discovery/`, `discovery_candidates`, 5 event types, `[discovery]` config, review CLI) |
| `eca910f` | canonical M4 (historical label "M3") | Benchmark ingestion + persistent storage (`benchmark/`, `benchmark_runs`/`benchmark_results`, `BENCHMARK_IMPORTED`, `[benchmark]` config, `benchmark import\|list` CLI) |
| `98696d1` | canonical M3 | Approval materialization + model registry (`core/models.py`, governed `approve_candidate`, `MODEL_*` events, `model list` CLI) |
| `6655def` | Milestone 5 | Trend analysis (`trend/` read-only analysis, `[trend]` config, `trend scores\|availability` CLI) |

## Phase 6 deliverables

| Module | Purpose |
|--------|---------|
| `discovery/` | Review-gated candidate workflow (D-P1: dedicated candidate table; provider lifecycle untouched). Curated import + controlled allowlisted network (D-P2), provenance + content hashes, `discovery import\|run\|list\|approve\|reject`. Approval materializes provider + models through governed registry operations only. |
| `benchmark/` | Provenance-aware benchmark ingestion (D-P3/ADR-0006): atomic per-file import, deterministic normalization (`identity` / `fraction_to_percent`), raw values preserved in `benchmark_results`, replay reports `duplicate_of` (never silent), scores mapped via `scoring.ingest.set_score` (source `BENCHMARK`). |
| `trend/` | Read-only, deterministic trend analysis over the append-only event-derived history (`dashboard/history.py`): direction (`up`/`down`/`stable`/`insufficient_data`), magnitude, windowed stability; CLI-only (D-P6); no DB writes, no tables, no `TREND_*` events. |
| `core/models.py` | Governed model registry operations (add/get/list/update/archive) emitting the previously-reserved `MODEL_*` events; owner Option A archival (event-only, required reason). |
| Schema additions | `discovery_candidates` (ADR-0005), `benchmark_runs` + `benchmark_results` (ADR-0006), 3 indexes - all additive; provider lifecycle CHECK and all Phase 1-5 tables unchanged. |
| Tests | 203 new Python tests (discovery 70, benchmark 39, models 29, trend 45, plus config/schema/CLI fixtures) |

## Config additions

| Section | Keys | Defaults |
|---------|------|----------|
| `[discovery]` | `enabled` (master switch), `allowlisted_urls`, `timeout_seconds`, `import_dir` | `false`, empty, 10, `data/discovery` |
| `[benchmark]` | `import_dir` | `data/benchmarks` |
| `[trend]` | `window_days`, `min_points` | 90, 3 |

All keys validated through `app.config` (`DEFAULT_CONFIG`, `Config`, `validate`,
`effective_config_text`) and mirrored identically in `config.toml` +
`templates/config.toml`.

## Event vocabulary additions

Added to the whitelist (`core/events.py` `EVENT_TYPES`):

* `DISCOVERY_CANDIDATE_ADDED`
* `DISCOVERY_IMPORT_COMPLETE`
* `DISCOVERY_IMPORT_ERROR`
* `DISCOVERY_CANDIDATE_APPROVED`
* `DISCOVERY_CANDIDATE_REJECTED`
* `BENCHMARK_IMPORTED`

`MODEL_ADDED` / `MODEL_UPDATED` / `MODEL_ARCHIVED` were reserved (whitelisted)
in Phase 1 and are now emitted for the first time by `core/models.py` - the
whitelist entry is unchanged.

## Test summary

Command: `python -m pytest -q` (run 2026-08-19)

| Metric | Value |
|--------|-------|
| Tests collected | 467 |
| Passed | 467 |
| Failed | 0 |
| Skipped | 0 |
| New in Phase 6 | 203 (467 total - 264 Phase 5 base) |

Additional runs (2026-08-19):

* Phase 5 subset `test_connectors_adapter.py test_connectors_mcp.py`: 48/48
  passed (39.41s).
* VS Code offline unit (`npm run test:unit`): 28/28 passed (377ms).
* VS Code real integration (`npm test`, @vscode/test-cli): 2/2 passed
  (923ms), exit 0.
* `git diff --check` clean at the release baseline.

All tests run offline with in-memory/injected SQLite fixtures and data.

## Environment

* Python 3.14.2, pytest 9.1.1, Windows (win32)
* Node v24.13.0 / npm 11.6.2 (isolated `connectors/vscode/` workspace only;
  owner-run `npm install`, git-ignored `node_modules/`, `out/`, `out-test/`,
  `.vscode-test/`)

---

## Scope boundaries (confirmed)

* Additive schema only - 3 new tables (`discovery_candidates`,
  `benchmark_runs`, `benchmark_results`) + 3 indexes; no Phase 1-5 table,
  column or CHECK constraint changed; the `providers.status` lifecycle is
  preserved untouched (D-P1).
* Discovery produces candidates only; **no path** converts a candidate to a
  provider without explicit `discovery approve` (governed registry operations
  only, no raw SQL write path in new modules).
* Trend analysis is strictly derived/read-only: no DB writes, no tables, no
  `TREND_*` events; no ADR-0004 snapshots (D-P8 stays deferred).
* CLI-only intelligence surfaces (D-P6); connectors and the shared adapter
  are untouched - read-only, decision-free, offline; no new connector
  commands/tools/features.
* On-demand execution only (D-P7); no scheduler, daemon, cron or autonomous
  recurring execution.
* Controlled network only (D-P2): allowlisted, provenance-snapshotted, failure
  handled; no credentials/API keys stored; no unrestricted network; core stays
  offline-capable.
* No new Python dependencies (stdlib + sqlite3 + pytest only; D-1);
  `requirements.txt` unchanged; isolated npm graph unchanged (D-4).
* ADR-0003 workspace discovery stays deferred (D-P5); MCP modern era
  `2026-07-28` stays out of scope (D-1).
* No secret-like keys stored; URLs sanitized; no implemented secrets or
  credentials introduced.

## Determinism and provenance

* Deterministic - identical DB input -> identical CLI/report output
  (Article 7); explicit ordering; documented formulas.
* No fabricated data - insufficient trend data -> `insufficient_data` with the
  threshold exposed (Article 10); benchmark raw values preserved and
  queryable; failed imports write nothing and report the error.
* Every discovery candidate carries provenance (source, imported/fetched at,
  content hash, submitter) and an `ADDED`/`APPROVED`/`REJECTED` event trace.
* Every benchmark run carries provenance (name, version, origin, fetched_at,
  content_hash, imported_at, submitter, mapping); replay appends a NEW run and
  reports `duplicate_of`.
* Review-gated approval is single-operation; approve/reject on a
  non-`PENDING_REVIEW` candidate fails deterministically (no silent state
  rewrites).

---

## Release reconciliation - historical milestone-label discrepancy

* `eca910f` historically carries the owner label **"M3"** for the benchmark
  work (owner authorized benchmark integration as "M3").
* The approved planning baseline (Section 12) and proposal spec (Section 9)
  number benchmark as **M4** and approval materialization + model registry as
  **M3**.
* Canonical Phase 6 sequence: **canonical M3 = `98696d1`** (approval
  materialization + model registry); **canonical M4 = `eca910f`** (benchmark).
* The historical commit `eca910f` is **not amended, rewritten, renamed or
  otherwise altered**. This section is a documented historical-label
  reconciliation only, mirroring the note already present in
  `handover/NEXT-STEPS.md` and `PROJECT-STATUS.md`.

---

## Checksums (SHA-256, prefix 16)

| File | SHA-256 (prefix 16) |
|------|---------------------|
| `discovery/__init__.py` | `4B6442EA7240A33B` |
| `discovery/engine.py` | `181C67835EA2717C` |
| `discovery/sources.py` | `48EB58A2C960C6E6` |
| `benchmark/__init__.py` | `CE009D95B97B205A` |
| `benchmark/ingest.py` | `02A1D0D8669C2328` |
| `trend/__init__.py` | `AC80F7721CEE41BB` |
| `trend/analysis.py` | `B923ADC72ABE388B` |
| `core/models.py` | `6F945A0295E4B893` |
| `database/schema.sql` | `98CD6F761A6308B1` |
| `app/config.py` | `C67B942F95CA0641` |
| `app/main.py` | `0E81D7D8D6CA869B` |
| `core/events.py` | `4C9D4604B1685482` |

---

## Approval

Status: PENDING OWNER APPROVAL (release package created 2026-08-19 per owner
authorization; approval and closure acceptance pending).

Approval covers the following commits:

* `8f01b10` - Phase 6 planning baseline (D-P1..D-P9, approved 2026-08-18)
* `d32324a` - Phase 6 Milestone 1 (doc-before-code)
* `a037dfd` - Phase 6 Milestone 2 (discovery + candidate workflow)
* `eca910f` - Phase 6 canonical M4 (historical label "M3") - benchmark
* `98696d1` - Phase 6 canonical M3 - approval materialization + model registry
* `6655def` - Phase 6 trend analysis
* (release manifest / closure commit - the Phase 6 release commit; its SHA is
  recorded in living docs and the release-package report)

Signed by: (pending)

Date: (pending)

Action:  [ ] Approve Phase 6 release   [ ] Request changes

---

*End of Phase 6 Release Manifest. Release date 2026-08-19. Approval pending.*