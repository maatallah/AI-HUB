# PHASE4-IMPLEMENTATION-PLAN.md

# AI-Hub Phase 4 - Dashboard / Reporting / History Implementation Plan

**Date:** 2026-08-01

**Baselines:**
* Phase 1 (immutable): `7ceac80c9b0b1718ec090307b2220e1350ca85dd`
* Phase 2 (immutable): `ae0a6c2a917586e597df5dd51ff9c51522dd9afe` (manifest `2c6e3eb`)
* Phase 3 (immutable): `d6dd3c9` (implementation), `ff4b8a7` (manifest),
  `c6327f4` (closure report), `8370ba0` (approval)
* ADR-0001 accepted: `74d23b5`

**Status:** PENDING OWNER APPROVAL - no implementation before approval.

---

## 1. Scope (from the start authorization)

1. **Dashboard** - read-only, aggregated visibility over providers, models,
   scores, availability, recommendations and events (v1.2 Phase 4;
   `handover/AGENT-HANDOVER.md` "Dashboard: visibility, reporting, human
   interaction").
2. **Reporting** - deterministic summary reports (provider status, score
   coverage, recommendation history, monitoring state) consumable by humans
   and future connectors.
3. **History** - score/availability history for trend analysis. Phase 3
   stored score changes as append-only events (`SCORE_RECORDED` /
   `SCORE_UPDATED`) and explicitly deferred point-in-time snapshots to Phase
   4 (`docs/review/PHASE3-SCORING-SPEC.md` Section 1.5; D-6).

Constraints (Constitution Articles 1, 4, 5, 7, 8, 10, 11):

* **Read-only engine** - dashboard/reporting/history never mutate providers,
  models, scores, availability or preferences. Visibility only (Article 1).
* Append-only events only - history reads events, never rewrites them
  (Article 5, v1.2 Section 8).
* Deterministic, explainable output (Articles 4, 7) - no random ordering, no
  hidden transformations.
* Unknown values stay unknown - no fabricated history or estimates
  (Article 10).
* Behaviour changes require specification updates (Article 11) - v1.2 Phase 4
  sections updated in step 9.
* No Phase 1-3 architecture redesign; existing engines are consumed, not
  rewritten.
* No new secrets, no network access required (offline-capable reporting).
* No new dependencies unless approved (stdlib + sqlite3 + pytest only).

---

## 2. Repository state confirmation

* Phase 3 release baseline present: `d6dd3c9` (implementation),
  `ff4b8a7` (manifest), `c6327f4` (closure), `8370ba0` (approval),
  `dc295d3` (Phase 4 entry conditions).
* `main` == `origin/main` (`dc295d3`), working tree clean. Confirmed.
* Tests: 162/162 passing (Phase 4 baseline).
* Data available to Phase 4 (read-only):
  * `providers.status` lifecycle (NEW/EVALUATING/ACTIVE/LIMITED/DEGRADED/
    OFFLINE/ARCHIVED).
  * `scores` (ADR-0001) - current value per (model, dimension) with value,
    confidence, source, scored_at.
  * `availability` - state, reason, quota_type, last_success, last_failure,
    consecutive_failures.
  * `events` - append-only history incl. `HEALTH_CHECK_*` (latency_ms),
    `MONITOR_STATUS_CHANGED`, `QUOTA_SIGNAL`, `SCORE_RECORDED` /
    `SCORE_UPDATED`, `RECOMMENDATION_CREATED`, `FALLBACK_*`.
  * `recommendations` - decision provenance (task, profile, decision_version,
    score_breakdown JSON, explanation, confidence, requested_at).
  * `preferences` - custom profiles (`profile.<name>`).
* `dashboard/` directory exists and is empty (Phase 1 skeleton placeholder).
* Config already exposes `[dashboard] refresh_seconds = 60` (v1.2 Section 10)
  with validation in `app/config.py`.

---

## 3. Files to create

| File | Purpose |
|------|---------|
| `dashboard/__init__.py` | Module marker + public API re-exports |
| `dashboard/engine.py` | Read-only aggregation queries (provider/model/score/availability/recommendation overviews) |
| `dashboard/reports.py` | Deterministic report builders (text/table output, no GUI) |
| `dashboard/history.py` | Score/availability history reconstruction from append-only events + optional snapshots |
| `tests/test_dashboard_engine.py` | Unit tests for aggregation queries (empty DB, filtered, joined rows) |
| `tests/test_dashboard_reports.py` | Unit tests for report formatting + determinism |
| `tests/test_dashboard_history.py` | Unit tests for history reconstruction from seeded events + snapshots |
| `docs/review/PHASE4-DASHBOARD-SPEC.md` | Proposal spec for dashboard/reporting/history (Article 11 documentation) |

## 4. Files to modify

| File | Change |
|------|--------|
| `app/main.py` | Add `dashboard` CLI subcommands: `dashboard status`, `dashboard report <name>`, `dashboard history --model N [--dimension D]`. Follows the existing argparse subcommand architecture (verified present in Phases 1-3). |
| `core/events.py` | Extend `EVENT_TYPES` with `SNAPSHOT_RECORDED` if point-in-time snapshots are stored (see D-2) |
| `database/schema.sql` | NOT changed unless a snapshot table is approved via ADR-0004 (see section 5). |
| `database/database.py` | `EXPECTED_TABLES` updated ONLY if a snapshot table is added. |
| `app/config.py` | No new keys planned (`dashboard.refresh_seconds` exists). Only if D-3 adds keys. |
| `config.toml` + `templates/config.toml` | Only if D-3 adds config keys. |
| `AI-Hub Project Specification v1.2.md` | Add Phase 4 detail sections (dashboard/reporting/history) per Section 14 doc rules |
| `CHANGELOG.md` | Record Phase 4 additions |
| `PROJECT-STATUS.md` | Advance phase status |
| `handover/CURRENT-STATE.md`, `handover/NEXT-STEPS.md` | Mark dashboard/reporting/history implemented |
| `docs/release/PHASE3-RELEASE-MANIFEST.md` | NOT modified (immutable). New Phase 4 manifest at phase end. |
| `requirements.txt` | No new dependencies expected (stdlib + sqlite3 + pytest only) |

---

## 5. Database changes

* **No schema changes planned.** Existing tables fully cover dashboard and
  reporting. Score history is reconstructed from append-only events
  (`SCORE_RECORDED` / `SCORE_UPDATED` payloads already carry dimension, value,
  confidence, source, and event timestamp) - no new table required.
* **Optional snapshot table** (`score_snapshots`): only if trend queries over
  large histories become too slow to reconstruct from events. If adopted, it
  requires **ADR-0004** first (idempotent `CREATE TABLE IF NOT EXISTS`,
  matching existing pattern), plus `EXPECTED_TABLES` and v1.2 Section 8
  updates. See decision D-2.
* **Indexes:** existing `idx_events_occurred`, `idx_events_type`,
  `idx_scores_model` support the planned queries. No additional indexes
  planned.
* **Relationships:** all reads join through existing FKs
  (`scores.model_id -> models -> providers`, `availability.provider_id`,
  `recommendations.provider_id/model_id`).

---

## 6. Design outline

### 6.1 Dashboard aggregation (`dashboard/engine.py`)

Read-only queries producing stable dict/row views:

* `overview(conn)` - total providers, models, scored models, ACTIVE/LIMITED/
  DEGRADED/OFFLINE counts, available providers (score coverage).
* `provider_view(conn)` - per provider: status, availability state,
  consecutive_failures, model count, stored score count.
* `score_view(conn, model_id=None)` - current scores joined with model and
  provider names (reuses `scoring.list_scores` semantics without mutation).
* `recommendation_view(conn, limit=N)` - provenance records ordered by
  `requested_at` desc.
* `event_view(conn, event_type=None, limit=N)` - append-only event log
  (reuses `core.events.list_events`).

All output is deterministic (fixed ordering, explicit columns). Empty inputs
produce empty (not fabricated) results (Article 10).

### 6.2 Reporting (`dashboard/reports.py`)

Deterministic text/table report builders, one function per report:

* `report_providers` - provider status table.
* `report_scores` - score coverage + per-dimension tables.
* `report_recommendations` - provenance summary.
* `report_monitoring` - availability/health summary.
* `report_overview` - headline dashboard summary.

Reports are plain-text/tab-separated so they are grep-able and connector-safe
(no GUI in Phase 4; VS Code/MCP are Phase 5). No hidden sorting - ordering is
explicit and documented (Article 7).

### 6.3 History (`dashboard/history.py`)

* **Event-derived history (primary):** reconstruct per-model score history
  from `SCORE_RECORDED` / `SCORE_UPDATED` events, yielding a deterministic
  series `[(occurred_at, dimension, value, confidence, source)]`. No new data
  written (Article 5, v1.2 Section 8).
* **Availability history:** derive series from `MONITOR_STATUS_CHANGED` and
  `HEALTH_CHECK_*` events (state transitions + latency samples).
* **Optional snapshots (D-2):** if approved via ADR-0004, a `SNAPSHOT_RECORDED`
  event + `score_snapshots` table captures point-in-time state for trend
  analysis. Snapshots are never fabricated - they copy current stored values
  only.
* History is read-only: it never rewrites or deletes events (Article 5).

### 6.4 CLI (`app/main.py`)

```
python -m app.main dashboard status                     # headline overview
python -m app.main dashboard report <providers|scores|recommendations|monitoring|overview>
python -m app.main dashboard history --model N [--dimension D]   # score series
python -m app.main dashboard history --availability --provider P  # availability series
```

### 6.5 Determinism and explainability

* Every query/report has an explicit ordering; no reliance on rowid order
  (Article 7).
* Every report is self-describing (column headers). A generated-at timestamp is
  optional and injected by the caller so tests pass a fixed value, preserving
  deterministic output.
* No hidden aggregation weights; totals are simple counts/sums (Article 4).

---

## 7. Tests to add

| Test file | Coverage |
|-----------|----------|
| `tests/test_dashboard_engine.py` | overview/provider_view/score_view/recommendation_view/event_view on empty + seeded in-memory DB; determinism |
| `tests/test_dashboard_reports.py` | report formatting, empty inputs, deterministic ordering, no mutation |
| `tests/test_dashboard_history.py` | score series from SCORE_RECORDED/SCORE_UPDATED events, availability series, optional snapshot path, no fabrication |
| `tests/test_config.py` (extend) | `dashboard` section validation (already exists; extend only if D-3 adds keys) |

All tests use in-memory SQLite fixtures and injected data - no real network
access.

---

## 8. Documentation updates required

* `AI-Hub Project Specification v1.2.md` - add Phase 4 detail (dashboard /
  reporting / history) per Section 14 doc rules (Article 11 doc-before-code).
* `docs/review/PHASE4-DASHBOARD-SPEC.md` - new proposal spec.
* `CHANGELOG.md` - Phase 4 additions.
* `PROJECT-STATUS.md` - phase status advance.
* `handover/CURRENT-STATE.md`, `handover/NEXT-STEPS.md` - implementation state.
* `docs/release/PHASE4-RELEASE-MANIFEST.md` - release baseline at phase end
  (git SHA, checksums, test summary).
* ADRs: no new ADR planned. ADR-0004 only if a snapshot table is approved
  (D-2).

---

## 9. Risks and open decisions

| # | Decision | Recommendation | Needs ADR? |
|---|----------|----------------|------------|
| D-1 | Dashboard output format | Plain-text/tab-separated tables (no GUI in Phase 4); connectors (Phase 5) consume the same data via CLI. | No |
| D-2 | Score history storage | Primary: reconstruct from append-only events (no schema change). Optional `score_snapshots` table only if trend performance requires it. | Yes (ADR-0004) if snapshots table adopted |
| D-3 | New dashboard config keys | None planned; reuse existing `dashboard.refresh_seconds`. Add keys only if a refresh/snapshot interval is needed. | No (spec update) |
| D-4 | No new dependencies | stdlib + sqlite3 + pytest only. Reports are plain text - no plotting libs in Phase 4. | No |
| D-5 | Dashboard never mutates state | All Phase 4 modules are read-only; enforce via no-write function design + tests. | No |
| D-6 | Events pagination | Reuse `core.events.list_events(limit=...)`; large histories use limit + filters (non-blocking). | No |

---

## 10. Suggested implementation order

1. Confirm push state + owner approval.
2. `docs/review/PHASE4-DASHBOARD-SPEC.md` proposal spec + v1.2 Phase 4
   sections + CHANGELOG + PROJECT-STATUS + handover updates (Article 11
   doc-before-code: specification and documentation are finalized and
   reviewed before any implementation begins).
3. `dashboard/engine.py` aggregation queries + `tests/test_dashboard_engine.py`.
4. `dashboard/reports.py` report builders + `tests/test_dashboard_reports.py`.
5. `dashboard/history.py` event-derived history + `tests/test_dashboard_history.py`.
6. CLI wiring (`dashboard status / report / history`) + integration tests.
   (`app/main.py` already provides the argparse subcommand architecture used
   by Phases 1-3 - `build_parser`, `subparsers`, `set_defaults(func=...)` -
   so the new `dashboard` subcommands follow the existing pattern; no
   redesign required.)
7. Phase 4 manifest + release review (owner approval).
8. Re-evaluate D-2 (snapshot table + ADR-0004) only if trend performance
   demands it.

---

*End of Phase 4 implementation plan. Awaiting owner approval.*
