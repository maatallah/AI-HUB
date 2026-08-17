# handover/NEXT-STEPS.md

# AI-Hub Next Steps

## Immediate Goal

Execute Phase 4 (Dashboard / Reporting / History): finalize the documentation
set (doc-before-code), then implement the read-only dashboard, reports and
history engine, then release review.

Phase 1 has been formally closed - see `handover/PHASE-1-CLOSURE.md` and
`docs/release/PHASE1-CLOSURE-SUMMARY.md`.

Phase 2 is released - see `handover/PHASE-2-CLOSURE.md`, plus
`docs/review/PHASE2-IMPLEMENTATION-PLAN.md`,
`docs/review/PHASE2-MONITORING-SPEC.md` and
`docs/release/PHASE2-RELEASE-MANIFEST.md`.

Phase 3 is released (162/162 tests) - see
`docs/review/PHASE3-IMPLEMENTATION-PLAN.md`,
`docs/review/PHASE3-SCORING-SPEC.md`,
`handover/PHASE-3-CLOSURE.md` and
`docs/release/PHASE3-RELEASE-MANIFEST.md` (status APPROVED).

Phase 4 is authorized (2026-08-17, owner approval, plan baseline `f9316e4`) -
see `docs/review/PHASE4-IMPLEMENTATION-PLAN.md` and
`docs/review/PHASE4-DASHBOARD-SPEC.md`. Documentation step in progress;
implementation not yet begun.

---

# Pre-Phase 4 Actions (owner)

- [x] Review and approve Phase 3 release (approved 2026-08-01,
  `docs/release/PHASE3-RELEASE-MANIFEST.md` status = APPROVED)
- [x] Sign off Phase 3 closure (handover/PHASE-3-CLOSURE.md, accepted
  2026-08-01)
- [x] Approve finalized Phase 4 plan (approved 2026-08-17, baseline
  `f9316e4`)

---

# Step 3 — Phase 4 Entry Conditions

Phase 4 (Dashboard / Reporting / History) must NOT start until a separate
owner authorization prompt is provided. Before coding, the Phase 4 plan must
be produced and approved (same pattern as Phase 2/3).

Entry conditions (all met as of 2026-08-01):

- [x] Phase 3 release approved (immutable baseline `d6dd3c9`, manifest
  APPROVED)
- [x] Phase 3 closure signed off (`handover/PHASE-3-CLOSURE.md`)
- [x] `main` synchronized with `origin/main`
- [x] 162/162 tests passing
- [x] ADR-0001 accepted (`scores` table) - scoring data model available

---

# Phase 1 Completion Status

- [x] Create repository skeleton
- [x] Initialize SQLite database with documented schema
- [x] Implement configuration system
- [x] Implement manual provider registry
- [x] Create test framework
- [x] Create initial provider seed dataset (`scripts/seed_providers.py`)
- [x] Select a `LICENSE` (MIT)
- [x] Review ADR-0001 (PROPOSED, assessed ready for ACCEPTED)
- [x] Create `handover/PHASE-1-CLOSURE.md` and `PROJECT-STATUS.md`
- [x] Re-verify tests on a clean checkout (49/49 passed, 2026-08-01)

# Phase 2 Completion Status

- [x] Health check module (`monitoring/health.py`)
- [x] Availability + lifecycle tracking (`monitoring/availability.py`)
- [x] Quota architecture (`monitoring/quota.py`)
- [x] Seed validation (`monitoring/validation.py`)
- [x] Event vocabulary extension (`core/events.py`)
- [x] Monitoring config keys + docs (v1.2 Section 10)
- [x] CLI `monitor run/status/validate`
- [x] Tests: 99/99 passing (50 new)
- [x] Phase 2 release review + approval (owner)

# Phase 3 Completion Status

- [x] Scoring engine (`scoring/`) - scores, aging, derived operational dims
- [x] Recommendation engine (`recommendation/`) - profiles, ranking, explain
- [x] Fallback engine (`fallback/`) - chain, eligibility, recovery
- [x] Provenance records (`recommendations` table + events)
- [x] Event vocabulary extension (`core/events.py`)
- [x] Scoring config keys + docs (v1.2 Section 10)
- [x] CLI `score`, `recommend`, `fallback`
- [x] Tests: 162/162 passing (59 new)
- [x] Phase 3 release review + approval (owner, 2026-08-01)

# Phase 4 Completion Status

- [ ] `docs/review/PHASE4-DASHBOARD-SPEC.md` + v1.2 Section 18 (in progress)
- [ ] `dashboard/engine.py` aggregation views
- [ ] `dashboard/reports.py` report builders
- [ ] `dashboard/history.py` event-derived history
- [ ] CLI `dashboard status/report/history`
- [ ] Tests: dashboard engine, reports, history
- [ ] Phase 4 release review + approval (owner)

---

# Step 1 — Phase 4 Documentation (doc-before-code)

```
# Article 11: finalize spec + docs first (in progress)
docs/review/PHASE4-DASHBOARD-SPEC.md
v1.2 Section 18
CHANGELOG.md
PROJECT-STATUS.md
handover/CURRENT-STATE.md
handover/NEXT-STEPS.md
```

# Step 2 — Phase 4 Implementation

Phase 3 (scoring, recommendation, fallback) is released. Phase 4 adds the
read-only dashboard, reporting and event-derived history (see
`docs/review/PHASE4-DASHBOARD-SPEC.md`). Fallback Step 2 filters on
availability (v1.2 Section 7), which Phase 2 maintains; scoring feeds the
dashboard. No schema changes unless ADR-0004 is approved.

---

# Next Recommended Agent

Backend-focused implementation agent for Phase 4 (Dashboard).

Recommended input:

* START-HERE.md
* CONSTITUTION.md
* AI-Hub Specification v1.2
* docs/review/PHASE4-IMPLEMENTATION-PLAN.md
* docs/review/PHASE4-DASHBOARD-SPEC.md
* docs/review/PHASE3-SCORING-SPEC.md
* handover/CURRENT-STATE.md
* handover/NEXT-STEPS.md
* this document
