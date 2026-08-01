# PHASE2-MONITORING-SPEC.md

# AI-Hub Monitoring Engine - Implementation Specification (Proposal)

**Reference:** AI-Hub Project Specification v1.2 Sections 5, 6, 9, 10

**Proposal date:** 2026-08-01

**Phase:** 2 - Monitoring Engine

**Status:** PROPOSED (pending review)

---

## 1. Scope

Phase 2 implements the Monitoring Engine:

* provider health checks
* availability tracking and lifecycle state preparation
* quota and usage monitoring architecture
* provider seed validation

It does NOT implement automatic provider discovery (v1.2 Section 9 keeps
discoveries in PENDING_REVIEW; that remains deferred) and does NOT perform
automatic archival (Constitution Article 1 requires explicit confirmation).

## 2. Governing principles

* Monitoring never modifies provider information directly (v1.2 Section 9).
* No secrets are stored or logged (Constitution Article 6, v1.2 Section 11).
* Unknown values remain unknown - never fabricated (Article 10).
* Events are append-only (Article 5).
* All thresholds are global configuration values.

## 3. Modules

| Module | Responsibility |
|--------|----------------|
| `monitoring/health.py` | HTTP reachability checks, no auth, no secrets |
| `monitoring/availability.py` | Availability rows + lifecycle transitions |
| `monitoring/quota.py` | Quota architecture (quota_type, reset detection) |
| `monitoring/validation.py` | Seed metadata validation, results via events |

## 4. Health checks

`check_provider(conn, provider_id, ...)` verifies the documented `base_url`
is reachable.

* Transport: `urllib.request`, HEAD request, no headers (no secrets).
* Timeout: `monitoring.timeout_seconds` (default 10).
* A provider without `base_url` returns `UNKNOWN` (never fabricated).
* Results: `OK` / `FAILED` / `UNKNOWN`, each recorded as a `HEALTH_CHECK_*`
  event.

Latency is measured and compared to `monitoring.latency_threshold_ms`
(default 10000). Responses above the threshold are classified FAILED.

## 5. Availability and lifecycle

The `availability` table stores runtime state per provider
(`state`, `reason`, `quota_type`, `reset_at`, `last_success`,
`last_failure`, `consecutive_failures`).

* Successful check: `state=ACTIVE`, failures reset to 0.
* Failed check: `consecutive_failures += 1`; state is not changed directly.

Transitions are applied only through `core.providers.update_provider`, which
enforces the legal transition table and reason requirements.

### Thresholds (global)

| Key | Default | Meaning |
|-----|---------|---------|
| `monitoring.interval_minutes` | 60 | monitoring frequency |
| `monitoring.timeout_seconds` | 10 | per-check HTTP timeout |
| `monitoring.failure_threshold` | 3 | consecutive failures marking DEGRADED; a further full run while DEGRADED marks OFFLINE |
| `monitoring.latency_threshold_ms` | 10000 | response time above this is high latency |

### Transition rules

| Transition | Trigger | Reason (mandatory unless ACTIVE) |
|------------|---------|----------------------------------|
| ACTIVE -> DEGRADED | `consecutive_failures >= failure_threshold` OR latency `> latency_threshold_ms` | "Repeated failures." / "High latency." |
| DEGRADED -> OFFLINE | already DEGRADED AND further run `>= failure_threshold` | "Repeated monitoring failures beyond configured threshold." |
| OFFLINE -> ACTIVE | successful check | "Successful recovery." (cleared on ACTIVE) |
| ACTIVE -> LIMITED | quota signal | "Quota exhausted." / "Rate limit exceeded." |
| LIMITED -> ACTIVE | quota reset detected | "Quota reset detected." |

Only transitions in the v1.2 Section 5 legal table are permitted. ARCHIVED is
never applied automatically.

## 6. Quota architecture

No external spend API is available (no credentials). Phase 2 establishes the
architecture:

* `quota_type` on availability rows (daily / monthly / rate).
* `reset_at` for LIMITED -> ACTIVE reset detection.
* HTTP 429 (and 401/403 with quota headers) are recorded as `QUOTA_SIGNAL`
  events and apply ACTIVE -> LIMITED.

Only ACTIVE -> LIMITED is legal (v1.2 Section 5); DEGRADED providers record
the signal but are not moved by quota alone.

## 7. Seed validation

`validate_provider` / `validate_seed` check seeded provider metadata:

* `base_url` / `documentation_url` parseable with http/https scheme.
* Missing URLs -> `VALIDATION_UNKNOWN` (never fabricated).
* Reachability check optional and config-gated.
* Results recorded as `VALIDATION_PASSED` / `VALIDATION_FAILED` /
  `VALIDATION_UNKNOWN` events.

Validation never modifies provider records.

## 8. Event vocabulary

Extended `core/events.py` `EVENT_TYPES` with:

```
HEALTH_CHECK_OK          HEALTH_CHECK_FAILED      HEALTH_CHECK_UNKNOWN
MONITOR_STATUS_CHANGED   QUOTA_SIGNAL             VALIDATION_PASSED
VALIDATION_FAILED        VALIDATION_UNKNOWN
```

## 9. CLI

```
python -m app.main monitor run [--provider N]
python -m app.main monitor status
python -m app.main monitor validate
```

## 10. Tests

`tests/test_health.py`, `test_availability.py`, `test_quota.py`,
`test_validation.py`. All network behaviour is injected via fake transports -
no real network access in tests.

## 11. Non-goals (explicit)

* Automatic provider discovery (PENDING_REVIEW workflow deferred).
* Automatic archival.
* Spend/cost tracking (requires credentials; Phase 3+).
* Per-provider threshold overrides (global only).

---

*End of proposal.*
