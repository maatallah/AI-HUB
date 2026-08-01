# PHASE3-SCORING-SPEC.md

# AI-Hub Phase 3 - Scoring / Recommendation / Fallback Proposal Spec

**Date:** 2026-08-01

**Status:** IMPLEMENTED (see PHASE3-RELEASE-MANIFEST.md)

This document records the design decisions behind the Phase 3 implementation
and how they satisfy the AI-Hub Constitution and Specification v1.2.

---

## 1. Scoring

### 1.1 Dimensions

Canonical dimension names (stored in `scores.dimension`):

| Dimension | Kind | Derived? | Source |
|-----------|------|----------|--------|
| `coding` | Capability | No | MANUAL / BENCHMARK / AUTOMATED_TEST / OFFICIAL_INFORMATION |
| `reasoning` | Capability | No | MANUAL / BENCHMARK / AUTOMATED_TEST / OFFICIAL_INFORMATION |
| `mathematics` | Capability | No | MANUAL / BENCHMARK / AUTOMATED_TEST |
| `long_context` | Capability | No | MANUAL / BENCHMARK / AUTOMATED_TEST |
| `vision` | Capability | No | MANUAL / BENCHMARK / AUTOMATED_TEST |
| `tool_calling` | Capability | No | MANUAL / BENCHMARK / AUTOMATED_TEST |
| `availability` | Operational | Yes (monitoring) | AUTOMATED_TEST |
| `reliability` | Operational | Yes (monitoring) | AUTOMATED_TEST |
| `latency` | Operational | Yes (monitoring) | AUTOMATED_TEST |
| `cost` | Operational | No | MANUAL / OFFICIAL_INFORMATION |
| `stability` | Operational | No | MANUAL / OFFICIAL_INFORMATION |
| `context_window` | Capability | Yes (models table) | OFFICIAL_INFORMATION |

### 1.2 Value range

All scores are normalized to 0-100 (v1.2 Section 3). The `scores` table CHECK
enforces `value >= 0`; the application enforces 0-100 at ingest.

### 1.3 Derived operational scores

Computed at read time from monitoring outputs - never stored, never
fabricated (Constitution Article 10):

* **availability**: `ACTIVE=100, LIMITED=70, DEGRADED=40, OFFLINE=0`.
  `ARCHIVED`, `NEW`, `EVALUATING` produce no derived availability (no runtime
  state).
* **reliability**: `max(0, 100 - consecutive_failures * 20)`.
* **latency**: latest `HEALTH_CHECK_OK` latency mapped linearly:
  `100 * (1 - latency_ms / latency_threshold_ms)` (0ms -> 100,
  threshold -> 0). No measurement -> None.
* **context_window**: `min(100, context_window / 131072 * 100)` from the
  `models` table.

Derived scores report `source = AUTOMATED_TEST` (availability/reliability/
latency) or `OFFICIAL_INFORMATION` (context_window), with confidence 0.8
(1.0 for context_window).

### 1.4 Aging

Confidence multipliers applied at computation time (v1.2 Section 4):

| Age | Multiplier |
|-----|------------|
| 0-30 days | 1.00 |
| 31-90 days | 0.90 |
| 91-180 days | 0.75 |
| >180 days | 0.50 |

Boundaries are configurable (`scoring.aging_*_days`), strictly increasing.

### 1.5 Historical retention

* Current value per (model, dimension) in the `scores` table (ADR-0001).
* Append-only `SCORE_RECORDED` / `SCORE_UPDATED` events preserve history.
* Periodic snapshots deferred to Phase 4 (dashboard/history).

---

## 2. Recommendation

### 2.1 Profiles

Built-ins (v1.2 Section 2): `coding`, `reasoning`, `free`, `long_context`.
Weights are fractions summing to 1.0 (validated). Custom profiles load from
the `preferences` table key `profile.<name>` as JSON; built-ins cannot be
overridden.

### 2.2 Formula

`Final = sum(profile_weight x dimension_score)` (v1.2 Section 3). Missing
dimensions contribute 0 and are flagged "insufficient data". No hidden
weighting.

### 2.3 Filtering

Before ranking (v1.2 Section 7 Step 2):

* provider status must be ACTIVE/LIMITED/DEGRADED (OFFLINE/ARCHIVED/
  NEW/EVALUATING excluded; DEGRADED flagged as last resort),
* `context_window` must meet `min_context_window` when requested,
* required capabilities (`tool_calling`, `vision`, `streaming`, `json`) must
  be supported when requested.

### 2.4 Ordering

Deterministic (v1.2 Section 7 Step 4): Final Score desc, Availability desc,
Reliability desc, Cost asc, Latency asc, model_identifier asc. Missing
dimensions sort last in each key.

### 2.5 Confidence

`sum(weight x dimension_confidence) / sum(weights)`, clamped to 0-1, where
missing dimensions contribute confidence 0.

### 2.6 Provenance

Every top recommendation is recorded in the `recommendations` table: id
(UUID), task, profile, provider_id, model_id, decision_version, score
breakdown (JSON), explanation, confidence; plus a `RECOMMENDATION_CREATED`
event (v1.2 Section 8, Articles 4 and 8).

---

## 3. Fallback

### 3.1 Chain

Primary + up to `fallback.max_chain_length` (default 5) fallbacks, in
recommendation order.

### 3.2 Eligibility

Preferred: ACTIVE/LIMITED. Last resort: DEGRADED. Excluded: OFFLINE, ARCHIVED,
NEW, EVALUATING.

### 3.3 Selection

On a failure signal for the current provider, select the first eligible
provider that follows it in the chain. If none remains, the chain is
exhausted. Emits `FALLBACK_TRIGGERED`.

### 3.4 Recovery

When the primary returns to ACTIVE/LIMITED, it is selected again
(`FALLBACK_RECOVERED`).

### 3.5 Non-interference

Fallback reads monitoring outputs only (v1.2 Section 9). It never probes
providers and never modifies the provider lifecycle.

---

## 4. Configuration additions

| Key | Default | Meaning |
|-----|---------|---------|
| `scoring.aging_fresh_days` | 30 | days before aging (multiplier 1.00) |
| `scoring.aging_aging_days` | 90 | days before old (multiplier 0.90) |
| `scoring.aging_old_days` | 180 | days before stale (multiplier 0.75) |
| `scoring.derive_operational` | true | compute operational scores from monitoring at read time |
| `recommendation.decision_version` | `3.0.0` | version of the decision logic (provenance) |

`fallback.max_chain_length` (5) and `recommendation.default_profile`
(`coding`) existed in Phase 1 config.

---

## 5. Event vocabulary additions

`SCORE_RECORDED`, `SCORE_UPDATED`, `RECOMMENDATION_CREATED`,
`FALLBACK_TRIGGERED`, `FALLBACK_RECOVERED`, `PROFILE_UPDATED`.

---

## 6. Determinism and constraints

* Identical inputs -> identical recommendations (Article 7). The only random
  value is the provenance record UUID, which is not part of decision content.
* No secrets involved (Article 6).
* No automatic discovery/approval; no provider mutation (Articles 1, 2, 9).
* All decisions are explainable (Article 4) via the explanation text and score
  breakdown.

*End of Phase 3 scoring spec.*
