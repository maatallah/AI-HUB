# PHASE2-RELEASE-MANIFEST.md

# AI-Hub Phase 2 Release Manifest (Draft for Review)

**Project name:** AI-Hub

**Release name:** Phase 2 - Monitoring Engine

**Phase number:** Phase 2 (of 6)

**Release date:** 2026-08-01

**Phase 1 baseline:** `7ceac80c9b0b1718ec090307b2220e1350ca85dd` (immutable)

**Current branch:** `main`

**Status:** PENDING OWNER REVIEW - implementation complete, awaiting approval.

> This manifest becomes the immutable Phase 3 baseline once approved.

---

## Phase 2 deliverables

| Module | Purpose |
|--------|---------|
| `monitoring/health.py` | HTTP health checks (urllib, no auth, no secrets, timeout/latency driven) |
| `monitoring/availability.py` | Availability tracking + lifecycle transitions (v1.2 Section 5) |
| `monitoring/quota.py` | Quota architecture (quota_type, reset detection, ACTIVE->LIMITED) |
| `monitoring/validation.py` | Seed metadata validation (results via events only) |
| CLI `monitor run/status/validate` | `app/main.py` extension |

## Config additions (v1.2 Section 10)

| Key | Default |
|-----|---------|
| `monitoring.timeout_seconds` | 10 |
| `monitoring.failure_threshold` | 3 |
| `monitoring.latency_threshold_ms` | 10000 |

Thresholds are global (no per-provider overrides in Phase 2).

## Event vocabulary additions

`HEALTH_CHECK_OK`, `HEALTH_CHECK_FAILED`, `HEALTH_CHECK_UNKNOWN`,
`MONITOR_STATUS_CHANGED`, `QUOTA_SIGNAL`, `VALIDATION_PASSED`,
`VALIDATION_FAILED`, `VALIDATION_UNKNOWN`.

## Test summary

Command: `python -m pytest -q` (run 2026-08-01)

| Metric | Value |
|--------|-------|
| Tests collected | 99 |
| Passed | 99 |
| Failed | 0 |
| New in Phase 2 | 50 (health, availability, quota, validation, config) |

All network behaviour is injected via fake transports; no real network in
tests.

## Environment

* Python 3.14.2, pytest 9.1.1, Windows (win32)

---

## Scope boundaries (confirmed)

* No automatic provider discovery (PENDING_REVIEW deferred - v1.2 Section 9).
* No automatic archival (Article 1 - explicit confirmation required).
* No spend/cost tracking (requires credentials; Phase 3+).
* No schema changes - existing `availability` and `providers` tables reused.
* No Phase 1 architecture redesign.

## Lifecycle transitions implemented

| Transition | Trigger |
|------------|---------|
| ACTIVE -> DEGRADED | failures >= threshold OR latency > threshold |
| DEGRADED -> OFFLINE | further full run of failures while DEGRADED |
| OFFLINE -> ACTIVE | successful check |
| ACTIVE -> LIMITED | quota signal |
| LIMITED -> ACTIVE | quota reset detected |
| -> ARCHIVED | never automatic |

---

## Checksums (SHA-256, prefix 16)

| File | SHA-256 (prefix 16) |
|------|---------------------|
| `monitoring/health.py` | `36180B00BBB3C365` |
| `monitoring/availability.py` | `008CFF6B97E469E1` |
| `monitoring/quota.py` | `73B016C8B51F3E86` |
| `monitoring/validation.py` | `62DA7BAC45F573A7` |
| `app/config.py` | `B797D84C35B57A1E` |
| `core/events.py` | `310ECC9412BB3E64` |

---

*End of Phase 2 release manifest draft. Awaiting owner review.*
