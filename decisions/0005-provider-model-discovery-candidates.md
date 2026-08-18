# ADR-0005: Provider/Model Discovery Candidate Representation

**Status:** ACCEPTED

**Date:** 2026-08-18

**Author:** Phase 6 M1 Release Engineer

**Acceptance date:** 2026-08-18

**Acceptance note:** Accepted with the owner's approval of Phase 6 planning
decision **D-P1** and the Phase 6 Milestone 1 (doc-before-code) milestone
(2026-08-18).

**Related documents:**

* `AI-Hub Project Specification v1.2` - Section 20 (Ecosystem Intelligence,
  Phase 6); Sections 5 (provider lifecycle) and 9 (monitoring rules /
  PENDING_REVIEW pattern)
* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md` (planning baseline,
  D-P1)
* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md` (proposal spec,
  Section 2)
* `core/providers.py` (provider lifecycle statuses), `database/schema.sql`
  (providers CHECK constraint)

---

## Context

v1.2 Section 9 states that automatic discoveries "enter PENDING_REVIEW" and
only approved discoveries become ACTIVE records. However, the provider
lifecycle in v1.2 Section 5 begins at `NEW`, and the `providers.status` CHECK
constraint in `database/schema.sql:29` enumerates exactly seven states
(`NEW, EVALUATING, ACTIVE, LIMITED, DEGRADED, OFFLINE, ARCHIVED`) with no
`PENDING_REVIEW`. `core/providers.VALID_STATUSES` (`core/providers.py:24`)
matches that CHECK. Additionally, the repository ships **no database
migration facility** (`database/database.py` applies `schema.sql` idempotently
via `executescript`; no `PRAGMA user_version`, no ALTER path).

## Problem

How should automatic provider/model discovery represent candidates that have
not yet been approved, without breaking the released provider lifecycle, the
schema CHECK constraint, or the no-migration runtime?

## Options Considered

### Option A - Dedicated discovery-candidate table (recommended)

A new `discovery_candidates` table holds candidate rows with their own state
set (`DISCOVERED`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`) and full
provenance. Approval creates real provider rows via the existing registry
operations (`core.providers.add_provider` and state rules NEW -> EVALUATING ->
ACTIVE).

Pro: no schema CHECK migration; Section 5 lifecycle, `VALID_STATUSES`,
monitoring and recommendation eligibility untouched; clean domain separation
between "candidate" and "provider".

Con: the word `PENDING_REVIEW` lives on the candidate, not the provider; a
small terminology note is required in v1.2 Section 20 (mirroring the existing
project-registry/providers terminology note at `spec/project-registry.md`
Section 4).

### Option B - Extend provider lifecycle with PENDING_REVIEW

Add `PENDING_REVIEW` to the `providers.status` CHECK, to
`core/providers.VALID_STATUSES`/`LEGAL_TRANSITIONS`, to availability-state
exclusions and to monitoring/filter logic, plus a new migration facility.

Pro: literal reading of v1.2 Section 9.

Con: requires a migration mechanism that does not exist (larger blast radius),
amends the released Section 5 lifecycle, and risks confusion between
runtime/provider states in `availability`.

## Decision

Adopt **Option A - dedicated discovery-candidate table**.

* Candidates are never `providers` rows; the provider lifecycle and its
  current database constraints are preserved verbatim.
* No migration or lifecycle change is introduced to accommodate
  `PENDING_REVIEW`.
* Only explicit human approval (`discovery approve`) materializes a candidate
  as a provider (and its models); nothing auto-approves (Article 2).
* Additive `CREATE TABLE IF NOT EXISTS` for `discovery_candidates`; update
  `database/database.py EXPECTED_TABLES`.
* Full provenance per candidate: source type/ref, content hash, imported at,
  submitter, reviewed at, reason.
* `PENDING_REVIEW` remains a **candidate** state; the provider lifecycle is
  unchanged. v1.2 Section 20 carries a terminology note.

## Consequences

* Positive: released Phase 1-5 baselines and immutability rules untouched;
  lifecycle-determinism preserved (Article 7).
* Positive: candidate review cannot disrupt monitoring, availability or
  recommendation eligibility.
* Positive: provenance history per candidate, rejections never deleted
  (Article 5).
* Positive: additive schema pattern matches the ADR-0001 precedent.
* Negative: the term `PENDING_REVIEW` is shared between the (approved)
  project-registry domain and the new candidate domain - mitigated by the
  terminology note in v1.2 Section 20.
* Follow-up: implement the `discovery_candidates` table and the discovery
  workflow in Phase 6 Milestone 2; extend `core/events.py` with
  `DISCOVERY_CANDIDATE_*` / `DISCOVERY_IMPORT_*` event types.

**Numbering note:** ADR-0004 is reserved for the deferred point-in-time score
snapshots decision (referenced as such across the specification and phase
closures; deferred by D-P8). This decision therefore occupies the next
sequential number, ADR-0005.

## Acceptance Criteria

This ADR is accepted when:

* the owner approves D-P1 (Option A) and Milestone 1 (2026-08-18) - DONE
* v1.2 Section 20 and the Phase 6 proposal spec document the candidate-table
  representation - DONE (Milestone 1)
* `discovery_candidates` and the review workflow are implemented behind the
  M2 milestone gate with tests