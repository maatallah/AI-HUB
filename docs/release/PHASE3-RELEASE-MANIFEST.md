# PHASE3-RELEASE-MANIFEST.md

# AI-Hub Phase 3 Release Manifest

**Project name:** AI-Hub

**Release name:** Phase 3 - Scoring / Recommendation / Fallback

**Phase number:** Phase 3 (of 6)

**Release date:** 2026-08-01

**Git commit SHA:** `d6dd3c9449cd5de1488fc467ddca6c0f0a19d6c9`

**Phase 2 baseline:** `ae0a6c2a917586e597df5dd51ff9c51522dd9afe` (immutable)

**Current branch:** `main`

**Status:** APPROVED (owner review complete)

> This document is the immutable reference baseline for Phase 4. It records
> the state at release. Later project evolution must not rewrite it.

---

## Phase 3 deliverables

| Module | Purpose |
|--------|---------|
| `scoring/engine.py` | Effective aged per-dimension scores (v1.2 Section 4 aging) |
| `scoring/ingest.py` | Score ingestion into the ADR-0001 `scores` table (source/confidence validation, SCORE_* events) |
| `scoring/derive.py` | Operational dimensions derived from monitoring at read time (availability, reliability, latency, context_window) |
| `recommendation/profiles.py` | Built-in profiles (coding, reasoning, free, long_context) + custom profiles from `preferences` |
| `recommendation/engine.py` | Deterministic ranking (v1.2 Section 7 Step 4), filtering, no hidden weighting |
| `recommendation/explain.py` | Human-readable explanations (Article 4) |
| `recommendation/provenance.py` | `recommendations` records + RECOMMENDATION_CREATED events |
| `fallback/engine.py` | Deterministic fallback chain; eligibility from monitoring; recovery |
| CLI `score` / `recommend` / `fallback` | `app/main.py` extension |

## Config additions (v1.2 Section 10)

| Key | Default |
|-----|---------|
| `scoring.aging_fresh_days` | 30 |
| `scoring.aging_aging_days` | 90 |
| `scoring.aging_old_days` | 180 |
| `scoring.derive_operational` | true |
| `recommendation.decision_version` | `3.0.0` |

## Event vocabulary additions

`SCORE_RECORDED`, `SCORE_UPDATED`, `RECOMMENDATION_CREATED`,
`FALLBACK_TRIGGERED`, `FALLBACK_RECOVERED`, `PROFILE_UPDATED`.

## Test summary

Command: `python -m pytest -q` (run 2026-08-01)

| Metric | Value |
|--------|-------|
| Tests collected | 162 |
| Passed | 162 |
| Failed | 0 |
| New in Phase 3 | 59 (scoring 24, recommendation 16, fallback 10, provenance 6, config 3) |

All tests run offline with in-memory SQLite fixtures and injected monitoring
data.

## Environment

* Python 3.14.2, pytest 9.1.1, Windows (win32)

---

## Scope boundaries (confirmed)

* No schema changes - ADR-0001 `scores` table used as-is; no new tables.
* No automatic provider discovery / approval (deferred to Phase 6).
* No automatic archival (Article 1 - explicit confirmation required).
* No spend/cost tracking (requires credentials); `cost` only via
  MANUAL/OFFICIAL_INFORMATION sources - never estimated silently.
* No monitoring redesign - Phase 2 monitoring outputs are read-only inputs.
* No provider lifecycle modification by scoring/recommendation/fallback.
* No hidden scoring logic - all formulas documented in PHASE3-SCORING-SPEC.md.

## Determinism and provenance

* Identical inputs -> identical recommendations (Article 7). The only random
  value is the provenance record UUID, which is not part of decision content.
* Every top recommendation records: id (UUID), task, profile, provider_id,
  model_id, decision_version, score_breakdown (JSON), explanation, confidence.

---

## Checksums (SHA-256, prefix 16)

| File | SHA-256 (prefix 16) |
|------|---------------------|
| `scoring/engine.py` | `5376DD0A1E4EFB82` |
| `scoring/ingest.py` | `683E5668B34C0200` |
| `scoring/derive.py` | `500C8DABFA133AB5` |
| `scoring/__init__.py` | `67951BD2CFD7A0DA` |
| `recommendation/engine.py` | `787239B7557936FE` |
| `recommendation/profiles.py` | `C0C4007339D764B0` |
| `recommendation/explain.py` | `5131FF5627E59083` |
| `recommendation/provenance.py` | `64165018FB2CE5EC` |
| `recommendation/__init__.py` | `F9270ECBE5067507` |
| `fallback/engine.py` | `BD3657550EF1859A` |
| `fallback/__init__.py` | `FB1FCA06FE6A32F9` |
| `app/config.py` | `E1FCCFECF9C32D44` |
| `core/events.py` | `ADC555486B98BA44` |

---

*End of Phase 3 Release Manifest. Awaiting owner approval.*
