# PHASE2-IMPLEMENTATION-PLAN.md

# AI-Hub Phase 2 - Monitoring Engine Implementation Plan

**Date:** 2026-08-01

**Baseline:** `7ceac80c9b0b1718ec090307b2220e1350ca85dd` (main, pushed)

**Status:** PENDING OWNER APPROVAL - no implementation before approval.

---

## 1. Scope (from the start authorization)

1. Provider health monitoring foundation: availability checks, provider status
   tracking, lifecycle state preparation.
2. Provider seed validation: verify existing provider metadata, identify
   invalid or outdated endpoints, record results through the event system.
3. Prepare quota and usage monitoring architecture.
4. Maintain existing principles: append-only events, explicit registry, no
   automatic discovery, no secret storage, configuration-driven behaviour.

Hard constraints (Constitution Articles 1, 2, 5, 6, 10, 11):

* Monitoring never modifies provider information directly (v1.2 Section 9).
* Automatic discoveries enter PENDING_REVIEW; only approved become ACTIVE
  (v1.2 Section 9). Phase 2 does NOT implement automatic discovery - this rule
  is preserved and deferred.
* No secrets are stored or logged (Article 6, v1.2 Section 11).
* Unknown values stay unknown - never fabricated (Article 10).
* Behaviour changes require specification updates (Article 11).
* No Phase 1 architecture redesign.

---

## 2. Repository state confirmation

* Phase 1 closure commits present on `main` and pushed:
  * `7ceac80` Phase 1: repository foundation
  * `db43f53` Finalize MIT license
  * `ef3a5c0` Approve Phase 1 closure
  * `03975d3` Remove superseded agent log
* Working tree: contains my uncommitted release-documentation updates from the
  finalization session (`PROJECT-STATUS.md`, `START-HERE.md`,
  `docs/release/*`, `handover/*`, `CHANGELOG.md`, and new
  `docs/release/PHASE1-CLOSURE-SUMMARY.md`). These are doc-only, consistent
  with the release, and should be committed as part of Phase 2 step 0 so the
  Phase 2 work tree starts clean.

---

## 3. Files to create

| File | Purpose |
|------|---------|
| `monitoring/__init__.py` | Module marker + public API re-exports |
| `monitoring/health.py` | Health check executor (HTTP checks, no auth, no secrets, timeout-driven) |
| `monitoring/availability.py` | Availability state tracking + lifecycle transition application |
| `monitoring/quota.py` | Quota and usage monitoring architecture (quota snapshot, reset detection, quota_type tracking) |
| `monitoring/validation.py` | Provider seed validation (base URL reachability + metadata checks, results via events) |
| `tests/test_health.py` | Unit tests for health check logic (mocked transport) |
| `tests/test_availability.py` | Unit tests for availability tracking + lifecycle transitions |
| `tests/test_quota.py` | Unit tests for quota monitoring architecture |
| `tests/test_validation.py` | Unit tests for seed validation |
| `docs/review/PHASE2-MONITORING-SPEC.md` | Proposal spec for the monitoring engine (Section 14 / Article 11 documentation) |

## 4. Files to modify

| File | Change |
|------|--------|
| `core/events.py` | Extend `EVENT_TYPES` with monitoring event types (HEALTH_CHECK_*, QUOTA_*, VALIDATION_*, MONITOR_STATUS_CHANGED) |
| `app/config.py` | Add `monitoring.timeout_seconds`, `monitoring.failure_threshold`, `monitoring.latency_threshold_ms` keys + validation + defaults |
| `config.toml` + `templates/config.toml` | Document the new monitoring keys |
| `app/main.py` | Add `monitor` CLI subcommand (run health checks, show availability status, run seed validation) |
| `AI-Hub Project Specification v1.2.md` | Update Section 10 config table and add monitoring detail per Section 14 (documentation rules) |
| `CHANGELOG.md` | Record Phase 2 additions |
| `PROJECT-STATUS.md` | Advance phase status |
| `docs/release/PHASE1-RELEASE-MANIFEST.md` | NOT modified (immutable). New Phase 2 manifest in step 8. |
| `requirements.txt` | Add `requests` only if stdlib proves insufficient (prefer `urllib`; see decision D-4) |

## 5. Database changes

* **No schema changes required.** The existing `availability` table already
  carries `state`, `reason`, `quota_type`, `reset_at`, `last_success`,
  `last_failure`, `consecutive_failures` - exactly the fields Phase 2 needs.
  The `providers` table already carries lifecycle `status` and `status_reason`.
  Events table is append-only and already present.
* **Migration policy:** If any schema change becomes necessary mid-phase, a
  migration must be documented in a new ADR and implemented idempotently
  (matching the existing `CREATE TABLE IF NOT EXISTS` pattern). Not planned.

---

## 6. Design outline

### 6.1 Health checks (`monitoring/health.py`)

* `check_provider(conn, provider_id, transport=None)` -> HealthResult.
* Uses `urllib.request` with a configurable timeout
  (`monitoring.timeout_seconds`, default 10).
* **No authentication headers, no secrets, no payloads** - verifies the
  documented `base_url` is reachable and responds (HTTP status).
* Provider without a `base_url` -> result `UNKNOWN` (Article 10: never
  fabricate). Blackbox AI and MiniMax currently have `base_url = NULL`.
* Every check emits an event: `HEALTH_CHECK_OK` / `HEALTH_CHECK_FAILED` /
  `HEALTH_CHECK_UNKNOWN` (extended vocabulary).
* No retry logic in the check itself; consecutive-failure counting is the
  caller's concern (6.2).

### 6.2 Availability + lifecycle tracking (`monitoring/availability.py`)

* `update_availability(conn, provider_id, health_result)`:
  * On success: set `state=ACTIVE`, clear `consecutive_failures`, set
    `last_success`, clear `last_failure`.
  * On failure: increment `consecutive_failures`, set `last_failure`; do NOT
    change state directly.
* `apply_lifecycle(conn, provider_id, reason)` decides transitions using the
  v1.2 Section 5 rules and the existing `LEGAL_TRANSITIONS` table (exact
  rules in section 6.3 below).
* Uses `core.providers.update_provider` for the status change so events,
  reason validation, and updated_at stay consistent with Phase 1 behaviour.
* **No automatic archival** (requires explicit confirmation - Article 1).
* Status changes emit existing `PROVIDER_STATUS_CHANGED` events plus new
  `MONITOR_STATUS_CHANGED` events.

### 6.3 Lifecycle transition rules and thresholds

**Threshold scope decision (D-5/D-6):** All thresholds are **global
configuration values** (single set in `config.toml`). Provider-specific
overrides are NOT implemented in Phase 2 (out of scope; would require a
per-provider override mechanism). This is documented in the proposal spec.

#### Configuration defaults

| Key | Default | Meaning |
|-----|---------|---------|
| `monitoring.interval_minutes` | `60` | (existing) monitoring frequency |
| `monitoring.timeout_seconds` | `10` | per-check HTTP timeout |
| `monitoring.failure_threshold` | `3` | consecutive failures that mark DEGRADED; a second consecutive run of failures while DEGRADED marks OFFLINE |
| `monitoring.latency_threshold_ms` | `10000` | response time above this is "high latency" and counts as a failure signal |

#### Consecutive-failure model

A single running counter (`availability.consecutive_failures`) drives the
transition rules. It is incremented on each failed check and reset to `0` on
each successful check.

#### Exact transition rules

**ACTIVE → DEGRADED**
Trigger: `consecutive_failures >= failure_threshold` (default 3 repeated
failures) **OR** observed latency `> latency_threshold_ms` (default 10000 ms).
Reason (mandatory): "Repeated failures." or "High latency." (recorded in
`status_reason`).

**DEGRADED → OFFLINE**
Trigger: already DEGRADED **and** `consecutive_failures >= failure_threshold`
while in DEGRADED (i.e. a further full run of failures while already
degraded). Reason (mandatory): "Repeated monitoring failures beyond
configured threshold."

**OFFLINE → ACTIVE**
Trigger: a successful health check (HTTP 2xx/3xx, latency within threshold)
while OFFLINE. Reason: "Successful recovery."

**ACTIVE → LIMITED**
Trigger: quota signal (HTTP 429 Too Many Requests, or 401/403 with a
rate-limit/quota header), or an explicit quota event recorded by the quota
module (section 6.4). Reason (mandatory): "Quota exhausted." / "Rate limit
exceeded." / "Temporary restrictions."

**DEGRADED (no transition from quota alone)**
Per v1.2 Section 5, only ACTIVE → LIMITED is legal. A quota signal observed
on a DEGRADED provider is recorded as a `QUOTA_SIGNAL` event only; the
provider is NOT moved by quota alone.

**LIMITED → ACTIVE**
Trigger: quota reset detected (`reset_at` reached/passed and a subsequent
successful check). Reason: "Quota reset detected."

**No automatic ARCHIVED** transitions in Phase 2 (requires explicit owner
confirmation, Article 1).

### 6.4 Quota architecture (`monitoring/quota.py`)

* No external spend API available in Phase 2 (no credentials). Quota
  monitoring is *architecture preparation*:
  * `quota_type` recorded on availability rows (daily, monthly, rate).
  * `reset_at` timestamp for reset detection (LIMITED -> ACTIVE).
  * Health-check 429 / 403 responses are classified as quota signals and
    recorded (event `QUOTA_SIGNAL`); they apply ACTIVE -> LIMITED only.
    DEGRADED providers record the signal but are not moved (v1.2 Section 5).
  * Data model deliberately matches the existing `availability` columns - no
    new tables.

### 6.5 Seed validation (`monitoring/validation.py`)

* Validate the 9 seeded providers' metadata:
  * `base_url` present, parseable, http/https scheme.
  * `documentation_url` parseable when present.
  * Endpoint reachability check (optional, config-gated; skipped if
    `monitoring.enabled = false`).
* Results recorded as events: `VALIDATION_PASSED` / `VALIDATION_FAILED` /
  `VALIDATION_UNKNOWN` with payload (provider, url, error).
* Does NOT modify provider records; it reports and records only.
* Blackbox AI / MiniMax (`base_url = NULL`) -> `VALIDATION_UNKNOWN` with note
  to be confirmed (Article 10).

### 6.6 Event vocabulary extension (`core/events.py`)

Add to `EVENT_TYPES`:

```
HEALTH_CHECK_OK
HEALTH_CHECK_FAILED
HEALTH_CHECK_UNKNOWN
MONITOR_STATUS_CHANGED
QUOTA_SIGNAL
VALIDATION_PASSED
VALIDATION_FAILED
VALIDATION_UNKNOWN
```

Phase 1 events remain unchanged.

### 6.7 CLI (`app/main.py`)

```
python -m app.main monitor run [--provider N]        # run health checks
python -m app.main monitor status                    # show availability
python -m app.main monitor validate                  # validate seed data
```

---

## 7. Tests to add

| Test file | Coverage |
|-----------|----------|
| `tests/test_health.py` | OK / FAILED / UNKNOWN classification; timeout; no-secret guarantee (no auth header present); base_url missing |
| `tests/test_availability.py` | success resets failures; failure increments counter; lifecycle transitions (ACTIVE->DEGRADED->OFFLINE, OFFLINE->ACTIVE); illegal transitions rejected; reason mandatory for non-ACTIVE; no automatic archival |
| `tests/test_quota.py` | 429 -> LIMITED; reset -> ACTIVE; quota_type recorded; no new tables needed |
| `tests/test_validation.py` | valid/invalid/missing base_url classification; events recorded; no provider mutation |
| `tests/test_events.py` | new event types accepted; unknown still rejected |

All tests use an injected fake transport - **no real network access in tests**.

---

## 8. Phase 2 deliverable packaging

On completion:

* `docs/release/PHASE2-RELEASE-MANIFEST.md` - Phase 2 baseline (git SHA,
  checksums, test summary).
* Update `handover/NEXT-STEPS.md` (Phase 2 complete -> Phase 3) and
  `handover/CURRENT-STATE.md`.
* Re-run full suite (expect 49 + new tests, all passing).
* Phase 2 release requires owner approval.

---

## 9. Risks and open decisions

| # | Decision | Recommendation | Needs ADR? |
|---|----------|----------------|------------|
| D-1 | Monitoring writes to `providers.status` | Allowed only via legal transitions through existing `update_provider` (keeps Phase 1 invariants). Direct writes forbidden. | No (uses existing contract) |
| D-2 | Automatic discovery / PENDING_REVIEW | Explicitly OUT of Phase 2 scope; documented and deferred. No schema change. | Deferred |
| D-3 | Automatic archival | Forbidden (explicit confirmation required, Article 1). Not implemented. | No |
| D-4 | HTTP client dependency | Prefer stdlib `urllib`; add `requests` only if needed. Keeps requirements minimal (pytest only today). | No |
| D-5 | New config keys (`timeout_seconds`=10, `failure_threshold`=3, `latency_threshold_ms`=10000) | Add with defaults + validation; update v1.2 Section 10 and both config.toml files. Thresholds are **global** config values; provider-specific overrides deferred. | Spec update (not ADR) |
| D-6 | Quota monitoring depth | Architecture prep only; no spend tracking (no credentials). Matches v1.2 which defines quota only as a lifecycle trigger. | No |

---

## 10. Suggested implementation order

1. Commit outstanding Phase 1 release docs (**done**: commit `96cbe35`).
2. Extend `core/events.py` vocabulary (small, low risk).
3. Add config keys + validation + docs (D-5): `timeout_seconds=10`,
   `failure_threshold=3`, `latency_threshold_ms=10000`.
4. `monitoring/health.py` + tests.
5. `monitoring/availability.py` + lifecycle + tests.
6. `monitoring/quota.py` + tests.
7. `monitoring/validation.py` + tests.
8. CLI wiring + integration tests.
9. Documentation (spec Section 10, PHASE2-MONITORING-SPEC.md, CHANGELOG,
   PROJECT-STATUS).
10. Phase 2 manifest + release review.

---

*End of Phase 2 implementation plan. Awaiting owner approval.*
