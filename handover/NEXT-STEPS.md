# handover/NEXT-STEPS.md

# AI-Hub Next Steps

## Immediate Goal

Phase 4 (Dashboard / Reporting / History) released and closed (`c49ea9b`,
216/216 tests, closure accepted 2026-08-17). Phase 5 (Connectors - VS Code /
MCP) authorized 2026-08-17. Milestones 1-3 complete and closed (documentation,
shared adapter + MCP server, VS Code extension; 262/262 Python tests). Milestone
4 (full connector regression) is the current defined step; Milestone 5
(release package + closure) follows - both gated on owner approval.

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

Phase 5 is authorized (2026-08-17, revised planning proposal approved). Milestones
1-3 complete and closed (documentation, adapter + MCP server, VS Code extension) -
see `docs/review/PHASE5-CONNECTORS-SPEC.md`, v1.2 Section 19,
`connectors/adapter.py`, `connectors/mcp/` and `connectors/vscode/`. Owner
verification for Milestone 3 passed 2026-08-18. Milestones 4-5 (full
regression, release package) pending.

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

# Phase 5 Entry Authorization

Phase 5 authorized by owner 2026-08-17 (revised planning proposal approved).
Plan and proposal spec:

* `docs/review/PHASE5-CONNECTORS-SPEC.md` (proposal spec)
* Spec v1.2 Section 19 - Connectors (Phase 5)

Milestone 1 (documentation / doc-before-code) is in progress. Implementation
must NOT start until this documentation milestone is approved by the owner.

---

# Phase 5 Completion Status

- [x] Spec v1.2 Section 19 (Connectors) (Milestone 1)
- [x] `docs/review/PHASE5-CONNECTORS-SPEC.md` (Milestone 1)
- [x] `connectors/adapter.py` shared read-only adapter (Milestone 2)
- [x] `connectors/mcp/` MCP server (stdio, bounded subset) (Milestone 2)
- [x] `connectors/vscode/` VS Code extension (Milestone 3)
- [x] Tests: connectors adapter / MCP / vscode (46 Python + 27 TS unit +
      2 integration)
- [ ] Milestone 4: full connector regression - gated on owner approval
- [ ] Milestone 5: Phase 5 release package (manifest + closure) + owner
      approval

---

# Step 1 — Phase 5 Documentation (doc-before-code, Milestone 1)

Completed (2026-08-17): `AI-Hub Project Specification v1.2.md` Section 19,
`docs/review/PHASE5-CONNECTORS-SPEC.md`, CHANGELOG.md, PROJECT-STATUS.md,
handover/CURRENT-STATE.md, handover/NEXT-STEPS.md.

Milestone 2 (shared adapter + MCP server) and Milestone 3 (VS Code extension)
implemented and closed (owner approval 2026-08-18). Milestones 4-5 pending.

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

Backend-focused implementation agent for Phase 5 (Connectors - VS Code /
MCP). Milestones 2-3 (shared adapter + MCP server, VS Code extension) are
complete and closed. Milestone 4 (full connector regression) is the next
approved milestone after the owner approves the Milestone 3 completion record,
followed by Milestone 5 (Phase 5 release package + closure).

Recommended input:

* START-HERE.md
* CONSTITUTION.md
* AI-Hub Specification v1.2
* docs/review/PHASE5-CONNECTORS-SPEC.md
* docs/review/PHASE4-DASHBOARD-SPEC.md
* docs/release/PHASE4-RELEASE-MANIFEST.md
* handover/CURRENT-STATE.md
* handover/NEXT-STEPS.md
* this document
