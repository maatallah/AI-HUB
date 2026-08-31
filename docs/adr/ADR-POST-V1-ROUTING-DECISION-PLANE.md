# ADR: Post-V1 Routing Decision Plane — Decision Contract & Read-Only Decision API

**Status:** ACCEPTED

**Date:** 2026-08-21

**Author:** Post-V1 Routing Decision Contract effort (documentation-first; no implementation performed)

**Review note:** Owner review (2026-08-21) approved the design direction and required exactly one
revision before these documents may be committed: strict separation of the unconditionally
read-only DECIDE operation from an explicit RECORD DECISION operation. Revision R1 (this
revision) applies that separation. Per Constitution Article 11 this decision record precedes any
code; nothing here authorizes implementation. Committing the documents, and any subsequent
implementation, are separately governed steps.

**Related documents:**

* `docs/review/POST-V1-ADAPTIVE-AI-ROUTING-FEASIBILITY.md` — feasibility/design spike whose
  CONDITIONAL GO verdict and five conditions this ADR resolves (committed as `5150804`)
* `docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md` — companion specification; **normative for
  all contract detail** (envelope fields, inputs, statuses, ordering, error semantics)
* `AI-Hub Project Specification v1.2` — Section 7 (recommendation engine), Section 8 (fallback),
  Section 4 (Constitution), Section 15 (closed v1 roadmap)
* `decisions/0001-model-score-representation.md` (normalized `scores` table read by every
  candidate computation), `decisions/0005-provider-model-discovery-candidates.md`
  (human-review-gate precedent reused by the feedback boundary),
  `decisions/0006-benchmark-result-storage.md` (governed evidence-import precedent)
* Code relied upon (read, not modified): `recommendation/engine.py`, `recommendation/profiles.py`,
  `recommendation/explain.py`, `recommendation/provenance.py`, `fallback/engine.py`,
  `scoring/engine.py`, `scoring/derive.py`, `core/events.py`, `app/config.py`

---

## Context

The v1 roadmap is complete and closed (Phase 6 released). The post-v1 feasibility spike verified,
in code, that AI-Hub already computes the full object an "adaptive routing" consumer needs: a
deterministically ranked primary plus fallback chain with per-dimension scores, confidence, flags,
explanations, and optional provenance. What it lacks is a stable, versioned, machine-consumable
**routing decision contract** with a sanctioned read-only surface.

The feasibility study issued a CONDITIONAL GO with exactly five conditions to resolve:

1. **Decision-plane-only boundary** — AI-Hub must never execute requests.
2. **Cost semantics** — `_sort_key` sorts raw `cost` ascending while the weighted formula treats
   every dimension as higher-is-better; the dimension has no canonical definition.
3. **Feedback governance** — whether runtime outcomes may flow back into scores, and by what gate.
4. **Freshness rule** — how stale evidence participates and how staleness is expressed.
5. **Write-path discipline** — how the design mechanically guarantees that a decide operation
   performs zero writes, and where persistence may live instead.

## Problem

How should an external consumer (application, IDE integration, MCP client, future gateway) ask
AI-Hub *"given this task and these constraints, what AI should I use?"* and receive a
deterministic, explainable, provenance-bearing answer — without expanding AI-Hub's write surface,
without executing anything, and while resolving the five feasibility conditions?

## Options Considered

### Option A — Decision-plane-only contract + read-only Decision API (adopted)

Define a versioned JSON envelope produced as a pure function of `(request inputs, database state)`
by the existing Phase 3 engines, exposed through a read-only surface (CLI first). The DECIDE
operation is unconditionally read-only — zero writes, zero events, no monitoring trigger, under
every input combination. Persistence exists only as a separate, explicitly invoked RECORD DECISION
operation reusing the existing append-only provenance mechanism. Execution stays entirely with
the caller.

Pro: reuses every computation verbatim (no second source of truth); smallest blast radius;
constitutionally clean (Articles 2, 6, 7); resolves all five conditions inside one document pair;
transport-independent (CLI/MCP/HTTP/VS Code can share identical bytes).

Con: consumers must implement execution, retries, and outcome handling themselves; every decision
is ephemeral until the caller explicitly invokes RECORD, so unrecorded decisions leave no ledger
trace (documented trade).

### Option B — Execution adapter inside AI-Hub (feasibility Option B) — rejected

AI-Hub would send prompts, hold credentials, retry, and stream on the caller's behalf.

Con: requires credential custody (violates Article 6); collapses the decision/execution plane
split that keeps AI-Hub a local, auditable advisor; large new attack and failure surface; no
existing code supports it.

### Option C — Gateway/router service (feasibility Option C) — rejected

A standing service that routes live traffic through AI-Hub.

Con: constitutionally incompatible per the feasibility study (Articles 2, 6, 7): automated
execution of provider calls, credential handling, and non-deterministic live behavior; introduces
an always-on infrastructure component foreign to the repository's local-first posture.

## Decision

Adopt **Option A**. The companion specification
(`docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md`) is normative; the essential commitments are:

* **The envelope.** `contract_version` `"1"`, status ∈ {`OK`, `NO_CANDIDATE`,
  `CONSTRAINT_UNSATISFIABLE`, `INSUFFICIENT_DATA`}, request echo, full `policy` echo
  (decision_version, resolved weights, aging days, thresholds, max_chain_length),
  `total_eligible`, ranked candidates with per-dimension breakdown/confidence/source/aged and
  truthful flags, `selected`, `fallback_chain`, `rationale`, `provenance`, `warnings`.
  Identical inputs over identical database state produce identical envelopes.
* **DECIDE vs RECORD.** Two strictly separated operations: DECIDE is the pure/read-only
  computation returning the envelope — every envelope it produces is ephemeral/unrecorded
  (`provenance.recorded=false`, `decision_id=null`); RECORD DECISION is an explicit,
  caller-initiated append-only persistence of a previously produced decision, reusing the
  existing provenance mechanism. DECIDE never writes; RECORD never decides.
* **Inputs.** Existing: task, profile, min_context_window, required_capabilities, limit. New
  pure filters only: allowed/denied providers and models and `freshness.max_stale_days`. No
  persistence input exists: no argument to DECIDE can cause a write.
* **Condition 1 — boundary.** The contract answers *what should be used*, never *use it now*. It
  never sends prompts, holds credentials, retries, streams, or proxies (spec §14).
* **Condition 2 — cost.** Canonical definition adopted: `cost` is an affordability score on the
  existing 0–100 scale, higher = cheaper, participating in the weighted sum like any other
  dimension. When implemented, `_sort_key` must treat cost descending (one-line normative change
  recorded in spec §7; not applied now). Unknown cost is NULL + flag, never silent zero. Actual
  provider billing is permanently out of scope.
* **Condition 3 — feedback.** Runtime observations may inform future decisions only after a
  human-reviewed aggregation step producing explicitly sourced score updates; they never
  auto-mutate authoritative scores or derived metrics (spec §12).
* **Condition 4 — freshness.** Reuse the existing aging multipliers verbatim; stale data
  participates with visibly decayed confidence, never silently discarded; optional caller-side
  `max_stale_days` filter reports its exclusions; no TTL/expiry field; monitoring is never
  triggered by a decision (spec §6).
* **Condition 5 — write path.** DECIDE is unconditionally read-only: zero writes, zero events,
  zero monitoring, zero mutation — mechanically guaranteed by the absence of any write path in
  the operation. Persistence lives in the separate **RECORD DECISION** operation, the single
  sanctioned append-only write of the post-v1 design, reusing the existing `record_recommendation`
  path. Lifecycle, registry, discovery, benchmark, event-history, and configuration mutation
  paths are untouched and unexposed; `select_fallback`/`check_recovery` remain internal
  (spec §11).
* **Versioning.** Additive-only within contract v1 (new optional fields; no new status values);
  `policy.decision_version` continues to govern decision logic (spec §15).
* **Exposure.** One read-only surface to start (CLI recommended); MCP tool, VS Code command, or
  HTTP wrapper may follow under separate authorization. All surfaces serve identical bytes.
* **Non-goals.** No execution, proxying, credentials, scheduling, telemetry ingestion, schema
  changes, new dependencies, cost-billing integration, region/residency constraints.

### Location and numbering note

Existing ADRs live in `decisions/` with sequential numbers; ADR-0004 remains reserved for the
deferred point-in-time snapshots decision. This record uses the owner-specified path
`docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md` with a descriptive filename and consumes no
sequence number; if the owner prefers, it may later be renumbered/copied into `decisions/`
without content change.

## Consequences

* Positive: the feasibility study's CONDITIONAL GO becomes actionable — all five conditions are
  resolved in writing before any code exists (Article 11).
* Positive: DECIDE adds zero write surface — the invariant "decide never writes" is mechanical,
  not conventional; the separate RECORD DECISION operation reuses the released, append-only
  provenance path already exercised by the CLI.
* Positive: determinism and explainability are preserved and made *auditable off-box* via the
  policy echo and breakdown in every envelope (Articles 4, 7).
* Positive: the cost-semantics inconsistency is resolved canonically without touching shipped
  behavior; the normative sort fix is recorded and version-visible when applied.
* Negative: callers own execution-plane concerns entirely (retries, fallback advancement,
  outcome observation); AI-Hub cannot detect runtime unavailability.
* Negative: every decision is ephemeral until RECORD is invoked; auditability requires the
  explicit RECORD DECISION operation or caller-side retention.
* Follow-up (separately authorized, none performed here): implement the envelope + CLI exposure
  behind a milestone gate, including the normative `_sort_key` cost-direction change and tests;
  deliver RECORD DECISION (REQUIRED classification, spec §17) as a distinct, separately invokable
  capability; then optionally MCP/VS Code wiring.

## Acceptance Criteria

This ADR is accepted when:

* the owner confirms Revision R1 (DECIDE/RECORD separation) satisfies the sole revision
  requirement of the 2026-08-21 review - YES (confirmed by owner 2026-08-31)
* any implementation effort is subsequently authorized by its own explicit mandate (spec + tests +
  milestone gate), never implied by this document - YES (M1-M4 implemented and closed; M4 closure
  `8b309eb`, 548/548 tests passing, `decision_version` 3.1.0 active)

---

*Proposed only. No source, schema, configuration, test, MCP, or VS Code artifact was created or
modified for this decision; the only artifacts of this effort are this file and the companion
specification.*
