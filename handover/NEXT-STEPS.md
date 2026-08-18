# handover/NEXT-STEPS.md

# AI-Hub Next Steps

## Immediate Goal

Phase 5 (Connectors - VS Code / MCP) is RELEASED and CLOSED (baseline
`8231dce`, closure accepted 2026-08-18). Phase 6 (Ecosystem Intelligence) is
authorized: planning baseline approved (D-P1..D-P9, commit `8f01b10`) and
Milestone 1 (doc-before-code) complete (v1.2 Section 20, proposal spec,
ADR-0005/0006). The next defined step is Phase 6 **Milestone 2 (discovery +
candidate workflow)**, gated on a separate owner authorization (D-P9).
Prior released phases: Phase 4 (`c49ea9b`, 216/216 tests, closure accepted
2026-08-17).

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

Phase 4 is released (`c49ea9b`, 216/216 tests, closure accepted 2026-08-17) -
see `docs/review/PHASE4-IMPLEMENTATION-PLAN.md`,
`docs/review/PHASE4-DASHBOARD-SPEC.md`,
`docs/release/PHASE4-RELEASE-MANIFEST.md` (baseline `c49ea9b`) and
`handover/PHASE-4-CLOSURE.md`.

Phase 5 is RELEASED and CLOSED (2026-08-18, baseline `8231dce`, closure
accepted) - see `docs/review/PHASE5-CONNECTORS-SPEC.md`, v1.2 Section 19,
`connectors/adapter.py`, `connectors/mcp/`, `connectors/vscode/`,
`docs/release/PHASE5-RELEASE-MANIFEST.md` and `handover/PHASE-5-CLOSURE.md`.

Phase 6 (Ecosystem Intelligence) is authorized (2026-08-18). Planning
baseline `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md` approved
(D-P1..D-P9, commit `8f01b10`). Milestone 1 (doc-before-code) complete -
`docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md`, v1.2 Section 20,
`decisions/0005-*` and `decisions/0006-*`. Implementation milestones 2-6
require separate owner authorizations (D-P9).

---

# Pre-Phase 5 Actions (owner)

- [x] Approve Phase 4 release (`docs/release/PHASE4-RELEASE-MANIFEST.md`,
  approved 2026-08-17)
- [x] Sign off Phase 4 closure (`handover/PHASE-4-CLOSURE.md`, accepted
  2026-08-17)
- [x] Authorize Phase 5 (Connectors - VS Code / MCP) planning (approved
  2026-08-17)

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

# Phase 4 Entry Authorization

Phase 4 authorized by owner 2026-08-17 (plan baseline `f9316e4`). Plan and
proposal spec:

* `docs/review/PHASE4-IMPLEMENTATION-PLAN.md` (approved)
* `docs/review/PHASE4-DASHBOARD-SPEC.md` (proposal spec)

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

- [x] `docs/review/PHASE4-DASHBOARD-SPEC.md` + v1.2 Section 18
- [x] `dashboard/engine.py` aggregation views
- [x] `dashboard/reports.py` report builders
- [x] `dashboard/history.py` event-derived history
- [x] CLI `dashboard status/report/history`
- [x] Tests: dashboard engine, reports, history (54 new; 216/216 total)
- [x] Phase 4 release review + approval (owner, 2026-08-17) - released and
  closed (baseline `c49ea9b`)

---

# Phase 6 Entry Authorization

Phase 6 authorized by owner 2026-08-18 (planning baseline + M1). Planning and
proposal documents:

* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md` (planning baseline,
  approved D-P1..D-P9)
* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md` (proposal spec)
* `AI-Hub Project Specification v1.2.md` Section 20 (Ecosystem Intelligence)
* `decisions/0005-provider-model-discovery-candidates.md` (D-P1, ACCEPTED)
* `decisions/0006-benchmark-result-storage.md` (D-P3, ACCEPTED)

Milestone 1 (documentation / doc-before-code) is complete. Milestone 2
(discovery + candidate workflow) must NOT start until a separate owner
authorization prompt is provided (D-P9 sequential gates).

---

# Phase 6 Completion Status

- [x] Planning baseline approved (D-P1..D-P9, commit `8f01b10`)
- [x] Milestone 1: v1.2 Section 20 + `docs/review/PHASE6-ECOSYSTEM-
      INTELLIGENCE-SPEC.md` + ADR-0005/0006 + living-doc refresh
- [ ] Milestone 2: discovery + candidate workflow (requires owner
      authorization)
- [ ] Milestone 3: approval materialization + model registry
- [ ] Milestone 4: benchmark integration
- [ ] Milestone 5: trend analysis
- [ ] Milestone 6: full regression + release package

---

# Pre-Phase 6 Actions (owner)

- [x] Authorize Phase 6 planning (2026-08-18)
- [x] Approve planning decisions D-P1..D-P9 (2026-08-18)
- [x] Authorize Milestone 1 documentation (2026-08-18)

---

# Step 1 — Phase 6 Documentation (doc-before-code, Milestone 1)

Completed (2026-08-18): `AI-Hub Project Specification v1.2.md` Section 20,
`docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md`, `decisions/0005-*`,
`decisions/0006-*`, CHANGELOG.md, PROJECT-STATUS.md,
handover/CURRENT-STATE.md, handover/NEXT-STEPS.md.

Milestone 2 (discovery + candidate workflow) and every later implementation
milestone must each be authorized separately by the owner before it starts
(D-P9).

---

# Phase 5 Completion Status (historical)

- [x] Spec v1.2 Section 19 (Connectors) (Milestone 1)
- [x] `docs/review/PHASE5-CONNECTORS-SPEC.md` (Milestone 1)
- [x] `connectors/adapter.py` shared read-only adapter (Milestone 2)
- [x] `connectors/mcp/` MCP server (stdio, bounded subset) (Milestone 2)
- [x] `connectors/vscode/` VS Code extension (Milestone 3)
- [x] Tests: connectors adapter / MCP / vscode (46 Python + 27 TS unit +
      2 integration)
- [x] Milestone 4: full connector regression VERIFIED (2026-08-18) -
      262/262 Python, 46/46 MCP/adapter, 27/27 TS unit, 2/2 integration
- [x] Milestone 5: hardening / release readiness (3 new tests + living-doc
      refresh) - complete
- [x] Milestone 5: release package (manifest + closure) + owner approval -
      approved and closed 2026-08-18 (baseline `8231dce`)

# Step 2 — Phase 4 Documentation (doc-before-code)

Completed in `36d4aef`: `docs/review/PHASE4-DASHBOARD-SPEC.md`, v1.2 Section
18, CHANGELOG.md, PROJECT-STATUS.md, handover/CURRENT-STATE.md,
handover/NEXT-STEPS.md.

# Step 3 — Phase 4 Implementation

Completed in `c49ea9b`: read-only dashboard engine, deterministic reports and
append-only event-derived history (see `docs/review/PHASE4-DASHBOARD-SPEC.md`).
No schema changes unless ADR-0004 is approved.

Step 3 done - dashboard is implemented, 216/216 tests pass, Phase 4 released
and closed (closure accepted 2026-08-17, baseline `c49ea9b`).

---

# Next Recommended Agent

Backend-focused implementation agent for Phase 6 (Ecosystem Intelligence),
**Milestone 2 (discovery + candidate workflow)** - gated on separate owner
authorization. Phase 6 planning baseline (D-P1..D-P9) and Milestone 1
documentation are complete (commit `8f01b10`; v1.2 Section 20; proposal spec;
ADR-0005/0006). Do not begin M2 without explicit authorization.

Recommended input:

* START-HERE.md
* CONSTITUTION.md
* AI-Hub Specification v1.2 (Sections 5, 9, 15, 19, 20)
* docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md
* docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md
* decisions/0005-provider-model-discovery-candidates.md
* decisions/0006-benchmark-result-storage.md
* handover/CURRENT-STATE.md
* handover/NEXT-STEPS.md
