# PHASE4-RELEASE-MANIFEST.md

# AI-Hub Phase 4 Release Manifest

**Project name:** AI-Hub

**Release name:** Phase 4 - Dashboard / Reporting / History

**Phase number:** Phase 4 (of 6)

**Release date:** 2026-08-17

**Git commit SHA:** `c49ea9b37bebf07b34a5acef8046b483614dee69`

**Phase 3 baseline:** `d6dd3c9449cd5de1488fc467ddca6c0f0a19d6c9` (immutable)

**Current branch:** `main`

**Status:** PENDING OWNER APPROVAL (release review complete, 216/216 tests)

> This document is the immutable reference baseline for Phase 5. It records
> the state at release. Later project evolution must not rewrite it.

---

## Phase 4 deliverables

| Module | Purpose |
|--------|---------|
| `dashboard/engine.py` | Read-only aggregation views (overview, provider, score, recommendation, event) |
| `dashboard/reports.py` | Deterministic plain-text report builders (providers, scores, recommendations, monitoring, overview) |
| `dashboard/history.py` | Append-only event-derived score/availability history reconstruction |
| `dashboard/__init__.py` | Public API re-exports |
| CLI `dashboard status/report/history` | `app/main.py` extension (no schema/dependency changes) |

## Config additions

None. Reuses existing `dashboard.refresh_seconds = 60` (v1.2 Section 10).
`app/config.py`, `config.toml` and `templates/config.toml` unchanged.

## Event vocabulary additions

None. History reconstructs from existing append-only events
(`SCORE_RECORDED`, `SCORE_UPDATED`, `MONITOR_STATUS_CHANGED`,
`HEALTH_CHECK_*`). No `SNAPSHOT_RECORDED` - point-in-time snapshots are
deferred pending ADR-0004.

## Test summary

Command: `python -m pytest -q` (run 2026-08-17)

| Metric | Value |
|--------|-------|
| Tests collected | 216 |
| Passed | 216 |
| Failed | 0 |
| New in Phase 4 | 54 (engine 17, reports 14, history 12, CLI 11) |

All tests run offline with in-memory SQLite fixtures and injected data.

## Environment

* Python 3.14.2, pytest 9.1.1, Windows (win32)

---

## Scope boundaries (confirmed)

* No schema changes - ADR-0001 tables used as-is; no new tables.
* Read-only engine - dashboard/reports/history never mutate providers,
  models, scores, availability or preferences (Article 1).
* No snapshots - `score_snapshots` table and `SNAPSHOT_RECORDED` deferred
  until ADR-0004 is approved (D-2).
* No new dependencies - stdlib + sqlite3 + pytest only (D-4).
* No network access, no secrets.
* No Phase 1-3 architecture redesign - existing engines consumed, never
  rewritten.
* No GUI - plain-text/tab-separated output, connector-safe for Phase 5.
* No new config keys (D-3).

## Determinism and provenance

* Identical inputs -> identical reports/history (Article 7). Every query has
  an explicit ordering; no reliance on rowid order.
* Reports are self-describing (column headers). The generated-at timestamp is
  optional and caller-injected so tests pass fixed values.
* Empty inputs produce empty (not fabricated) results (Article 10); no hidden
  aggregation weights - totals are simple counts/sums (Article 4).
* History reads `events` only and never rewrites or deletes them (Article 5).

---

## Checksums (SHA-256, prefix 16)

| File | SHA-256 (prefix 16) |
|------|---------------------|
| `dashboard/__init__.py` | `2B99FAFF2FED293B` |
| `dashboard/engine.py` | `D4699ECCD9A941FF` |
| `dashboard/reports.py` | `AB0EEE4BBD6935A5` |
| `dashboard/history.py` | `0197FBEE280616AD` |
| `app/main.py` | `C1AAF205AB006BB4` |

---

*End of Phase 4 Release Manifest. Awaiting owner approval.*