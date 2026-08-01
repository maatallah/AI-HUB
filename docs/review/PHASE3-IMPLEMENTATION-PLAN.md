# PHASE3-IMPLEMENTATION-PLAN.md

# AI-Hub Phase 3 - Scoring / Recommendation / Fallback Implementation Plan

**Date:** 2026-08-01

**Baselines:**
* Phase 1 (immutable): `7ceac80c9b0b1718ec090307b2220e1350ca85dd`
* Phase 2 (immutable): `ae0a6c2a917586e597df5dd51ff9c51522dd9afe` (manifest `2c6e3eb`)
* ADR-0001 accepted: `74d23b5`

**Status:** PENDING OWNER APPROVAL - no implementation before approval.

---

## 1. Scope (from the start authorization)

1. Scoring Engine - normalized per-dimension scores in the `scores` table
   (ADR-0001), derived where possible from Phase 2 monitoring outputs.
2. Recommendation Engine - deterministic, explainable model/provider ranking
   using v1.2 Section 2 profiles and Section 3 formula.
3. Fallback Strategy - deterministic chain generation (v1.2 Section 7) driven
   by monitoring failure inputs.
4. Decision provenance - `recommendations` records for reproducibility
   (v1.2 Section 8).

Constraints (Constitution Articles 1, 2, 4, 5, 6, 7, 8, 10, 11):

* Append-only events only - no event UPDATE/DELETE.
* No secrets stored anywhere.
* No automatic provider discovery; no automatic provider approval.
* No hidden provider mutation - recommendations and scoring never change
  provider status directly.
* Configuration-driven behaviour (profiles, thresholds via `config.toml`).
* Every recommendation explainable (Article 4); deterministic (Article 7).
* Unknown scores stay unknown (Article 10) - no fabricated values.
* Behaviour changes require specification updates (Article 11).
* No Phase 1/2 architecture redesign; monitoring is reused, not rewritten.

---

## 2. Repository state confirmation

* Phase 2 release baseline present: `ae0a6c2` (implementation),
  `2c6e3eb` (manifest), `28f0b86` (closure report), `fe45752` (approval
  references).
* ADR-0001 status: **ACCEPTED** (2026-08-01) - `decisions/0001-model-score-representation.md`.
* Schema state: `scores` table present in `database/schema.sql` with
  `UNIQUE (model_id, dimension)`, source CHECK, FK to `models`.
  `EXPECTED_TABLES` includes `scores`. `recommendations` and `preferences`
  tables already exist (Phase 1), empty and unused.
* Tests: 103/103 passing (Phase 2 baseline 99 + 4 new score schema tests).
* Monitoring outputs available to Phase 3:
  * `availability` table: `state`, `reason`, `quota_type`, `reset_at`,
    `last_success`, `last_failure`, `consecutive_failures`.
  * `providers.status` lifecycle (ACTIVE/LIMITED/DEGRADED/OFFLINE/ARCHIVED).
  * Event history: `HEALTH_CHECK_*` (with `latency_ms`), `MONITOR_STATUS_CHANGED`,
    `QUOTA_SIGNAL`, `VALIDATION_*`.
* NOTE: `main` is currently **1 commit ahead of `origin/main`**
  (`74d23b5` Accept ADR-0001). The authorization stated the repository was
  pushed; confirm push status with the owner before Phase 3 work starts.

---

## 3. Files to create

| File | Purpose |
|------|---------|
| `scoring/__init__.py` | Module marker + public API re-exports |
| `scoring/engine.py` | Scoring engine: dimension computation, aging, normalization (v1.2 Sections 1, 4) |
| `scoring/ingest.py` | Manual / official score ingestion into `scores` (sources: MANUAL, OFFICIAL_INFORMATION) |
| `scoring/derive.py` | Derived operational scores from monitoring (availability, reliability, latency) |
| `recommendation/__init__.py` | Module marker + public API re-exports |
| `recommendation/profiles.py` | Built-in profiles (coding, reasoning, free, long_context) + custom profile loading |
| `recommendation/engine.py` | Recommendation computation: filter, score, sort, explain (v1.2 Sections 2, 3, 7) |
| `recommendation/explain.py` | Score breakdown + explanation text generation |
| `fallback/__init__.py` | Module marker + public API re-exports |
| `fallback/engine.py` | Fallback chain generation + failure-driven selection (v1.2 Section 7) |
| `tests/test_scoring_engine.py` | Unit tests for scoring engine (dimensions, aging, normalization, determinism) |
| `tests/test_scoring_ingest.py` | Unit tests for score ingestion + validation (source checks, no fabrication) |
| `tests/test_scoring_derive.py` | Unit tests for monitoring-derived operational scores |
| `tests/test_recommendation.py` | Unit tests for recommendation engine (profiles, formula, filtering, sorting, determinism) |
| `tests/test_fallback.py` | Unit tests for fallback chain (filtering, ordering, max chain length) |
| `tests/test_provenance.py` | Integration tests for `recommendations` records + event logging |
| `scripts/seed_scores.py` | Optional seed dataset of representative scores (idempotent, MANUAL/OFFICIAL source) |
| `docs/review/PHASE3-SCORING-SPEC.md` | Proposal spec for scoring/recommendation/fallback (Article 11 documentation) |

## 4. Files to modify

| File | Change |
|------|--------|
| `core/events.py` | Extend `EVENT_TYPES` with Phase 3 event types (SCORE_RECORDED, SCORE_UPDATED, RECOMMENDATION_CREATED, FALLBACK_TRIGGERED, FALLBACK_RECOVERED, PROFILE_UPDATED) |
| `app/config.py` | Add `scoring` config section (aging defaults, derived-score toggle) + validation + defaults |
| `config.toml` + `templates/config.toml` | Document the new `scoring` keys |
| `app/main.py` | Add `score` and `recommend` and `fallback` CLI subcommands |
| `database/schema.sql` | NOT changed for scores (ADR-0001 already applied). Only if a migration ADR is needed (see section 5). |
| `AI-Hub Project Specification v1.2.md` | Update Sections 3, 7, 8 detail + Section 10 config (per Section 14 doc rules) |
| `CHANGELOG.md` | Record Phase 3 additions |
| `PROJECT-STATUS.md` | Advance phase status |
| `handover/CURRENT-STATE.md` | Mark scoring/recommendation/fallback implemented |
| `docs/release/PHASE2-RELEASE-MANIFEST.md` | NOT modified (immutable). New Phase 3 manifest in step 9. |
| `requirements.txt` | No new dependencies expected (stdlib + sqlite3 + pytest only) |

## 5. Database changes

* **No schema changes planned.** The `scores` table (ADR-0001) and the
  `recommendations` + `preferences` tables (Phase 1) already provide the full
  data model Phase 3 needs.
* **Migration strategy:** Schema is applied idempotently by
  `database.initialize` (`CREATE TABLE IF NOT EXISTS`). Existing Phase 1/2
  databases gain the `scores` table on the next `init-db` run; no data
  migration required. If Phase 3 uncovers a genuine schema need, a migration
  ADR (ADR-0004) is required first (idempotent, matching existing pattern).
* **Indexes:** `idx_scores_model` (model_id) already exists. No additional
  indexes planned; the `scores` UNIQUE(model_id, dimension) index supports
  lookup. If recommendation queries show need, add composite index
  `(model_id, dimension, scored_at)` via ADR-0004.
* **Relationships:**
  * `scores.model_id` -> `models.id` -> `providers.id` (existing FK).
  * `recommendations.provider_id` / `recommendations.model_id` -> existing FK.
  * Monitoring data (`availability`, `events`) is read-only input, never
    written by scoring/recommendation/fallback.

---

## 6. Design outline

### 6.1 Scoring dimensions

Canonical dimension names stored in `scores.dimension` (match v1.2 Section
1.2 and profile names):

| Dimension | Kind | Source |
|-----------|------|--------|
| `coding` | Capability | MANUAL / BENCHMARK / AUTOMATED_TEST / OFFICIAL_INFORMATION |
| `reasoning` | Capability | MANUAL / BENCHMARK / AUTOMATED_TEST / OFFICIAL_INFORMATION |
| `mathematics` | Capability | MANUAL / BENCHMARK / AUTOMATED_TEST |
| `long_context` | Capability | MANUAL / BENCHMARK / AUTOMATED_TEST |
| `vision` | Capability | MANUAL / BENCHMARK / AUTOMATED_TEST |
| `tool_calling` | Capability | MANUAL / BENCHMARK / AUTOMATED_TEST |
| `availability` | Operational (derived) | computed from `availability`/`providers.status` |
| `reliability` | Operational (derived) | computed from `consecutive_failures` + events |
| `latency` | Operational (derived) | computed from `HEALTH_CHECK_*` latency |
| `cost` | Operational | MANUAL / OFFICIAL_INFORMATION (no spend APIs - no credentials) |
| `stability` | Operational | MANUAL / OFFICIAL_INFORMATION (deferred default) |
| `context_window` | Capability | derived from `models.context_window` |

### 6.2 Scoring engine (`scoring/engine.py`)

* Each dimension produces a normalized score between 0 and 100 (v1.2 Section
  3). Values are never fabricated (Article 10): missing dimension -> no row.
* **Derived operational scores** (computed on demand from monitoring data,
  deterministic):
  * `availability`: map `providers.status` + `availability.state`:
    ACTIVE=100, LIMITED=70, DEGRADED=40, OFFLINE=0, ARCHIVED excluded.
  * `reliability`: `max(0, 100 - consecutive_failures * 20)` with a floor;
    uses `availability.consecutive_failures`.
  * `latency`: latest `HEALTH_CHECK_OK` latency mapped into 0-100
    (0ms=100, >= latency_threshold_ms=0); UNKNOWN if no measurement.
* **Stored scores** (`scoring/ingest.py`): manual or official entries with
  explicit `source`, `confidence`, `scored_at`. Ingest validates the source
  against the allowed vocabulary and the value range (0-100 per v1.2 Section 3;
  table allows value >= 0).
* **Score aging** (v1.2 Section 4): confidence multiplier by age of
  `scored_at`:
  * 0-30 days: 1.00
  * 31-90 days: 0.90
  * 91-180 days: 0.75
  * >180 days: 0.50
* **Unknown handling:** a model without a score row for a profile dimension
  contributes 0 to that dimension but is flagged as "insufficient data" in the
  explanation; it is never assigned a fabricated value (Article 10).
* **Calculation frequency:** derived scores recomputed at recommendation time
  (always fresh from monitoring). Stored scores are recorded on ingest; aging
  is applied at computation time, not persisted.
* **Historical retention:** each ingest/update records a `SCORE_RECORDED` /
  `SCORE_UPDATED` event (append-only history). The `scores` table holds the
  current value per (model, dimension) per ADR-0001. Optional periodic snapshots
  deferred to Phase 4 (dashboard/history).

### 6.3 Recommendation engine (`recommendation/engine.py`)

* **Profiles** (`recommendation/profiles.py`): built-ins from v1.2 Section 2
  (coding, reasoning, free, long_context) with exact weights. Custom profiles
  load from the `preferences` table (key `profile.<name>` as JSON) - configurable,
  no code change needed (Article 9).
* **Formula** (v1.2 Section 3):
  `Final = Σ(profile_weight × dimension_score)` over dimensions in the profile,
  normalized to 0-100. No hidden weighting.
* **Filtering rules** (v1.2 Section 7 Step 2) applied before ranking:
  * exclude models whose provider status is not ACTIVE/LIMITED (never
    recommend OFFLINE/ARCHIVED; DEGRADED allowed but flagged),
  * exclude models with insufficient `context_window` for the task,
  * exclude models missing required capabilities (`supports_*` flags) when the
    task declares them.
* **Ranking** (v1.2 Section 7 Step 4): sort by Final Score desc, then
  Availability desc, Reliability desc, Lower Cost, Lower Latency, then
  alphabetical (model_identifier) - guarantees deterministic ordering
  (Article 7).
* **Explainability** (`recommendation/explain.py`): produce `score_breakdown`
  (per-dimension: value, confidence, source, age multiplier, weighted
  contribution) + human-readable `explanation` text answering Article 4
  (what/why/evidence/confidence).
* **Decision provenance** (v1.2 Section 8): every recommendation writes a
  `recommendations` row: id (uuid), task, profile, provider_id, model_id,
  decision_version, score_breakdown (JSON), explanation, confidence.
* **Confidence:** final recommendation confidence = weighted mean of dimension
  confidence (stored) × aging multiplier, clamped to 0-1.
* **Decision version:** `decision_version` string (e.g. `3.0.0`) in
  configuration so decisions are reproducible and comparable across versions.

### 6.4 Fallback strategy (`fallback/engine.py`)

* **Failure detection input:** monitoring outputs only - `availability.state`,
  `providers.status`, `consecutive_failures`, and `HEALTH_CHECK_*` /
  `QUOTA_SIGNAL` events. Fallback never performs its own probing (no redesign
  of monitoring).
* **Decision flow** (v1.2 Section 7):
  1. Generate recommendation chain: primary (top of ranking) + up to
     `fallback.max_chain_length` (default 5) next-best ACTIVE/LIMITED
     providers.
  2. On a failure signal for the currently-selected provider (state enters
     DEGRADED/OFFLINE/LIMITED), select the next provider in the chain whose
     state is eligible.
  3. Recovery: when the primary's state returns to ACTIVE (monitoring
     `OFFLINE -> ACTIVE` / `LIMITED -> ACTIVE`), future selections revert to
     full ranking; the chain is regenerated.
* **Provider selection rules:** eligibility = ACTIVE or LIMITED; DEGRADED is
  the last resort and is flagged in the explanation; OFFLINE/ARCHIVED are
  never selected.
* **Event logging:** `FALLBACK_TRIGGERED` (from provider A to B, reason) and
  `FALLBACK_RECOVERED` (return to primary). `RECOMMENDATION_CREATED` for each
  recommendation. All append-only.
* **Determinism:** chain order is derived from the same deterministic ranking;
  no randomness (Article 7).

### 6.5 CLI (`app/main.py`)

```
python -m app.main score list [--model N]              # show scores
python -m app.main score set --model N --dimension coding --value 85 --source MANUAL [--confidence 0.9]
python -m app.main recommend --task "python" [--profile coding]   # top recommendation
python -m app.main recommend chain --task "python" [--max 5]      # full chain (fallback)
python -m app.main fallback status                        # current fallback chain state
```

---

## 7. Tests to add

| Test file | Coverage |
|-----------|----------|
| `tests/test_scoring_engine.py` | dimension normalization, aging multipliers, derived operational scores, unknown handling, determinism |
| `tests/test_scoring_ingest.py` | source validation, value range, UNIQUE(model_id, dimension) upsert, events recorded, no fabrication |
| `tests/test_scoring_derive.py` | availability/latency/reliability mapping from seeded availability + events |
| `tests/test_recommendation.py` | profile weights, formula, filtering, sorting + tie-breaking, custom profile loading, explainability output |
| `tests/test_fallback.py` | chain generation, max_chain_length, failure-driven selection, recovery, DEGRADED last resort, determinism |
| `tests/test_provenance.py` | `recommendations` row written, decision_version, score_breakdown JSON, events appended, no provider mutation |
| `tests/test_config.py` (extend) | `scoring` section validation |

All tests use in-memory SQLite fixtures and injected monitoring data - no real
network access.

---

## 8. Documentation updates required

* `AI-Hub Project Specification v1.2.md` - Sections 3, 7, 8 detail, Section 10
  config keys (Article 11 doc-before-code).
* `docs/review/PHASE3-SCORING-SPEC.md` - new proposal spec.
* `CHANGELOG.md` - Phase 3 additions.
* `PROJECT-STATUS.md` - phase status advance.
* `handover/CURRENT-STATE.md`, `handover/NEXT-STEPS.md` - implementation state.
* `docs/release/PHASE3-RELEASE-MANIFEST.md` - release baseline at phase end
  (git SHA, checksums, test summary).
* ADRs: no new ADR planned (ADR-0001 covers the data model). ADR-0004 only if
  a schema change proves necessary.

---

## 9. Risks and open decisions

| # | Decision | Recommendation | Needs ADR? |
|---|----------|----------------|------------|
| D-1 | `recommendations.id` uses uuid | Deterministic content-based or UUID; uuid4 acceptable because recommendation *content* is deterministic (Article 7 concerns identical inputs -> identical output, not ID). | No |
| D-2 | Derived operational scores recomputed at read time | Compute on demand from monitoring; never persist (avoids stale/fabricated values). | No |
| D-3 | Custom profiles stored in `preferences` as JSON | Config-driven, no code change (Article 9). Validation at load. | No |
| D-4 | DEGRADED providers eligible as last resort | Allowed but flagged in explanation; never OFFLINE/ARCHIVED. | No |
| D-5 | New `scoring` config section + `decision_version` | Add with defaults + validation; update v1.2 Section 10 and both config.toml files. | Spec update (not ADR) |
| D-6 | Score history | Current value in `scores` + append-only events for history; snapshots deferred to Phase 4. | No (matches ADR-0001) |
| D-7 | No external spend/cost data (no credentials) | `cost` score only via MANUAL/OFFICIAL_INFORMATION; never estimated silently (Article 10). | No |
| D-8 | Push discrepancy | `main` is 1 commit ahead of `origin/main` (`74d23b5`); confirm push before starting. | Owner action |

---

## 10. Suggested implementation order

1. Confirm push state + owner approval.
2. Extend `core/events.py` vocabulary (SCORE_*, RECOMMENDATION_*, FALLBACK_*,
   PROFILE_UPDATED).
3. Add `scoring` config keys + validation + docs (D-5).
4. `scoring/derive.py` + `scoring/ingest.py` + `scoring/engine.py` + tests.
5. `recommendation/profiles.py` + `recommendation/engine.py` +
   `recommendation/explain.py` + tests.
6. `fallback/engine.py` + tests.
7. `recommendation` + `fallback` provenance integration (`recommendations`
   table) + `tests/test_provenance.py`.
8. CLI wiring + integration tests.
9. Documentation (spec Sections 3/7/8/10, PHASE3-SCORING-SPEC.md, CHANGELOG,
   PROJECT-STATUS, handover).
10. Phase 3 manifest + release review (owner approval).

---

*End of Phase 3 implementation plan. Awaiting owner approval.*
