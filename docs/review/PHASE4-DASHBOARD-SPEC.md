# PHASE4-DASHBOARD-SPEC.md

# AI-Hub Phase 4 - Dashboard / Reporting / History Proposal Spec

**Date:** 2026-08-17

**Status:** PROPOSED (Phase 4 implementation authorized 2026-08-17 by owner;
plan baseline `f9316e4`)

This document records the design decisions behind the Phase 4 dashboard,
reporting and history implementation and how they satisfy the AI-Hub
Constitution and Specification v1.2.

It is read-only: dashboard/reporting/history never mutate providers, models,
scores, availability, preferences or events (Constitution Articles 1, 5).

---

## 1. Dashboard

### 1.1 Scope

The dashboard is a **read-only aggregation layer** over the existing Phase
1-3 tables: providers, models, scores, availability, recommendations and
events. It provides stable, deterministic views consumed by the CLI reports
(Section 2) and by future connectors (Phase 5). It never writes to the
database (Constitution Article 1; approved PHASE4-IMPLEMENTATION-PLAN.md D-5).

### 1.2 Views (`dashboard/engine.py`)

Read-only queries producing stable row/dict views with explicit ordering
(Constitution Article 7 - no reliance on rowid order):

| View | Description |
|------|-------------|
| `overview(conn)` | Total providers, models, scored models; ACTIVE/LIMITED/ DEGRADED/OFFLINE counts; available providers (score coverage). |
| `provider_view(conn)` | Per provider: status, availability state, consecutive_failures, model count, stored score count. |
| `score_view(conn, model_id=None)` | Current scores joined with model and provider names (reuses `scoring.list_scores` semantics without mutation). |
| `recommendation_view(conn, limit=N)` | Provenance records ordered by `requested_at` desc (reuses `recommendation.list_recommendations`). |
| `event_view(conn, event_type=None, limit=N)` | Append-only event log (reuses `core.events.list_events`). |

All output is deterministic and self-describing. Empty inputs produce empty
(not fabricated) results (Constitution Article 10).

### 1.3 Aggregation rules

* Only exact counts/sums are used; no hidden aggregation weights
  (Constitution Article 4).
* Provider status/counts come from `providers.status`; runtime state from the
  `availability` table; scores from the `scores` table (ADR-0001).
* Derived operational dimensions (availability/reliability/latency) are read
  from monitoring at recommendation time; the dashboard reports the stored
  `scores` rows and the `availability` state directly - it never invents a
  value.

---

## 2. Reporting

### 2.1 Scope

Deterministic, plain-text/tab-separated summary reports consumable by humans
and future connectors. No GUI in Phase 4 (approved PHASE4-IMPLEMENTATION-PLAN
D-1); connectors (Phase 5) consume the same data via the CLI.

### 2.2 Report builders (`dashboard/reports.py`)

One function per report:

| Report | Description |
|--------|-------------|
| `report_providers` | Provider status table. |
| `report_scores` | Score coverage + per-dimension tables. |
| `report_recommendations` | Provenance summary (task, profile, model, decision_version, confidence). |
| `report_monitoring` | Availability/health summary. |
| `report_overview` | Headline dashboard summary. |

### 2.3 Determinism

* Every report has an explicit ordering; no hidden sorting (Constitution
  Article 7).
* Reports are self-describing (column headers).
* A generated-at timestamp is optional and injected by the caller so tests
  pass a fixed value, preserving deterministic output.
* No hidden aggregation weights; totals are simple counts/sums.

---

## 3. History

### 3.1 Scope

History is **read-only reconstruction** from the append-only `events` table
(Constitution Article 5; v1.2 Section 8). It never rewrites or deletes
events, and never fabricates missing data (Constitution Article 10).

### 3.2 Event-derived score history (`dashboard/history.py`)

* Per-model score series are reconstructed from `SCORE_RECORDED` /
  `SCORE_UPDATED` events, yielding a deterministic series
  `[(occurred_at, dimension, value, confidence, source)]`.
* No new database table is introduced for score history: the event payload
  already carries dimension, value, confidence, source and timestamp.

### 3.3 Event-derived availability history

* Availability series are derived from `MONITOR_STATUS_CHANGED` and
  `HEALTH_CHECK_*` events (state transitions + latency samples).

### 3.4 Snapshots

* Point-in-time snapshots (`score_snapshots` table + `SNAPSHOT_RECORDED`
  event) are **deferred**: they require ADR-0004 and explicit owner approval
  (approved PHASE4-IMPLEMENTATION-PLAN D-2). Snapshots, if ever adopted, copy
  current stored values only - they are never fabricated.
* `schema.sql` / `EXPECTED_TABLES` are NOT changed in Phase 4 unless ADR-0004
  is approved.

---

## 4. CLI

### 4.1 Commands (`app/main.py`)

```
python -m app.main dashboard status                     # headline overview
python -m app.main dashboard report <providers|scores|recommendations|monitoring|overview>
python -m app.main dashboard history --model N [--dimension D]   # score series
python -m app.main dashboard history --availability --provider P  # availability series
```

### 4.2 Architecture

The `dashboard` subcommand follows the existing argparse subcommand
architecture confirmed in Phases 1-3 (`build_parser`, `subparsers`,
`set_defaults(func=...)`). No redesign (Constitution Article 9; approved
PHASE4-IMPLEMENTATION-PLAN).

---

## 5. Configuration

* No new configuration keys are planned.
* Reuses the existing `[dashboard] refresh_seconds = 60` key (present since
  Phase 1, validated in `app/config.py`, documented in v1.2 Section 10 and
  `config.toml`).
* `config.toml` and `templates/config.toml` are unchanged unless D-3 adds a
  key (none planned).

---

## 6. Event vocabulary

* No new event types are introduced in Phase 4.
* `core/events.py` `EVENT_TYPES` is extended with `SNAPSHOT_RECORDED` only if
  ADR-0004 is approved (deferred - Section 3.4). This is an approved-plan
  exception, not an implementation decision.

---

## 7. Determinism and constraints

* Identical inputs and configuration produce identical dashboard views,
  reports and history (Constitution Article 7).
* Dashboard/reporting/history perform no writes (Constitution Article 1;
  D-5). Read-only enforcement via no-write function design + tests.
* No fabricated values: unknown history stays unknown (Article 10).
* No secrets are involved (Article 6); no network access is required; reports
  are offline-capable.
* No new dependencies: stdlib + sqlite3 + pytest only (D-4).
* Behavior changes require specification updates (Article 11); this spec and
  v1.2 Phase 4 sections are updated before code.

*End of Phase 4 dashboard/reporting/history spec.*