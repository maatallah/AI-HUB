# POST-V1 ADAPTIVE ROUTING — M3 SCOPE SPECIFICATION

Status: **PLANNING DOCUMENT** (scope/architecture only — no implementation performed or authorized)
Baseline inspected: `2738757a7b5392bd20376da0a0dc4cd9362c0565` ("Close M2 post-v1 adaptive routing")
Parent (of this scope commit): `2738757a…` (M2 closure record)
Date: 2026-08-28
Nature: Milestone scope definition for the **Q1 cost-semantics completion** (Feasibility Condition 2).
**Not** an implementation authorization. No source, schema, configuration, or test artifact was
created or modified. This file is the only artifact produced by the M3 scoping effort.

Governing documents:

* `docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md` — approved decision record; Condition 2
  (canonical cost semantics) and its "separate governed change" requirement are binding
* `docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md` — normative contract; §7 (cost semantics),
  §15 (versioning; `_sort_key` change bumps `decision_version`)
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M2-CLOSURE.md` (`2738757a`) — M2 closure record
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M2-SCOPE.md` (`2999a63`) — M2 scope authority
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M1-CLOSURE.md` — M1 closure record (Q1 deferred)

---

## 1. Purpose

Define the implementation slice (M3) that completes the last remaining feasibility condition of the
approved post-v1 routing decision plane: the **canonical cost-semantics correction (Condition 2)**.

M1 and M2 delivered the decision contract end-to-end (envelope + RECORD + CLI + adapter/MCP/VS Code
exposure) but explicitly deferred **Q1** — the normative `_sort_key` cost-direction flip — twice
(M1 closure, M2 scope/closure). The ADR and contract record that this flip "is scheduled as a
separate governed change with its own `decision_version` bump." M3 is that separate, governed change.

Owner ruling for M3: **Q1 = APPLY-NOW.**

Everything here is scope definition. Implementation requires a separate explicit owner mandate
(Section 12).

## 2. Current Baseline

* Branch `main`, HEAD `2738757a…`, working tree clean except one untracked file
  (`docs/review/POST-V1-ADAPTIVE-ROUTING-M1-SCOPE.md`); `main` ahead of `origin/main` by 7 commits —
  nothing pushed.
* M1 complete and closed (`5689d8f` → `0df2126`); M2 complete and closed (`2999a63` → `0fb771c` →
  `2738757a`).
* Full test suite at M2 closure: **546 passed** (Python) + **28 passed** (VS Code unit).
* Remaining normative gap (verified at planning): `recommendation/engine.py::_sort_key` still sorts
  `cost` **ascending** (price-like); `app/config.py` `recommendation.decision_version` is still
  `"3.0.0"`. This is the sole unresolved feasibility Condition 2.

## 3. M3 Objective

Deliver, behind one reviewable gate, the deferred normative cost-semantics correction:

1. Correct `recommendation/engine.py::_sort_key` so canonical `cost` ordering follows the approved
   higher-is-better semantic: **cost sorts descending; missing cost remains last** (consistent with
   the other quality dimensions; never fabricated, Article 10).
2. Bump `recommendation.decision_version` `3.0.0 → 3.1.0` in `app/config.py` so the change is
   version-visible in every envelope/`policy` echo and persisted provenance row (contract §15).
3. Add the required regression/acceptance coverage (R3 cost-weight `0.00` profiles demonstrably
   unaffected; ordering change asserted where legitimately visible).
4. Record the normative change in the governance/changelog artifacts (R4).

M3 is complete when every acceptance criterion in Section 9 passes on a clean tree.

## 4. Owner Ruling

* **Q1 = APPLY-NOW for M3** (owner decision recorded 2026-08-28). The cost-direction flip is applied
  in M3, paired with the `decision_version` bump and tests, per ADR Condition 2 and contract §7/§15.

## 5. M3 Required Scope

| # | Item | Contract ref | Notes |
|---|------|--------------|-------|
| R1 | Canonical cost ordering in `_sort_key` | §7 | `cost` sorts descending; missing cost sorts last; consistent with availability/reliability and the weighted formula (higher-is-better) |
| R2 | `decision_version` bump | §15 | `recommendation.decision_version` `3.0.0 → 3.1.0` in `app/config.py`; visible in every envelope `policy` echo and RECORD provenance rows |
| R3 | Cost-weight `0.00` profile invariance | §7 (unaffected claim) | Profiles weighting cost `0.00` (e.g. `coding`) produce identical ranking/selection before vs after the change; assert via test |
| R4 | Normative changelog/governance record | ADR follow-up; §15 | CHANGELOG/governance note recording the cost-direction change and the `decision_version` bump |

## 6. Deferred Scope (explicitly sequenced after M3)

* `max_cost` constraint enforcement — **not in M3**; enforcement semantics must be ruled separately.
* Contradictory-evidence detection; region/residency and deadline constraints; per-model availability
  overrides; ADR-0004 point-in-time snapshots.
* Dedicated cost-normalization tooling.
* Runtime feedback events / telemetry ingestion / review queueing (contract §12 boundary only).
* HTTP/server/gateway surface.

## 7. Explicit Non-Goals

No execution/proxying/retries/streaming; no `max_cost`; no credential handling; no schema changes;
no new event types; no new dependencies; no monitoring triggers from DECIDE; no mutation of
lifecycle, registry, discovery, benchmark, history, or configuration state beyond the single
`review decision_version` bump; no changes to any closed-phase module other than the two files
authorized in Section 11 for their listed purposes only; no new adaptive-routing behavior beyond Q1
cost semantics; no MCP/VS Code/CLI behavior change.

## 8. Integration Points (existing, verified)

| Existing interface | Used by M3 |
|---|---|
| `recommendation.engine.recommend` / `_sort_key` (engine.py) | candidate ordering; R1 change target |
| `recommendation.engine._dimension_sort_value` | interprets missing dimensions (missing-cost-last) |
| `scoring.ingest` dimensions incl. `cost` | source of the canonical cost evidence R1 orders |
| `app/config.recommendation.decision_version` (config.py) | R2 bump target; echoed in policy/provenance |
| `recommendation/decision.py` (policy echo / provenance) | reads `decision_version` from config; no change expected unless verification proves otherwise |
| `tests/test_decision.py`, `tests/test_decision_cli.py` | R1–R3 regression/acceptance coverage targets |

## 9. Acceptance Criteria (objectively verifiable)

1. `recommendation.engine._sort_key` orders `cost` descending; missing cost sorts last (crafted
   score-tie test asserts the §7 order).
2. Every DECIDE envelope `policy.decision_version == "3.1.0"`; RECORD persists `3.1.0`.
3. Cost-weight `0.00` profile (e.g. `coding`) yields byte-identical ranking/selection before vs
   after the change.
4. Full pre-existing suite passes with the single documented ordering/version expectation changes;
   no other behavior regression.
5. Zero-write fingerprint across all four routing statuses remains green (DECIDE still never writes).
6. CHANGELOG/governance record present.
7. `git diff --name-only` for the implementation commit is restricted to the authorized file list
   (Section 10 + the two closed-phase files in Section 11) and the M3 closure record.

## 10. Compatibility / Invariants

* DECIDE remains zero-write; RECORD remains the single explicit append-only persistence path.
* `contract_version` stays `"1"`; evolution additive-only within v1 (§15).
* No schema/`EVENT_TYPES`/dependency/credential change.
* No execution/autonomous/adaptive behavior beyond the cost ordering.
* Backward compatibility of M1/M2 surfaces preserved; the only intended-visible change is `cost`
  ordering + `decision_version` echo.
* Determininistic/reproducible behavior preserved (same-instant determinism, Article 7).

## 11. Implementation Authorization Boundary & File List

This scope document authorizes **nothing** — no code, no tests, no configuration edit, no commit
beyond this planning artifact except the scope-definition commit itself. Implementation requires a
separate explicit owner mandate. The implementation commit must satisfy §10's file whitelist and the
following **explicit M3 file-boundary authorization**:

**Closed-phase files authorized for M3 — listed purpose only:**

* `recommendation/engine.py` — Q1 `_sort_key` cost-direction correction (R1) only.
* `app/config.py` — `recommendation.decision_version` `3.0.0 → 3.1.0` (R2) only.

This is not general permission to modify either file.

**Proposed whitelist (additive; subject to owner mandate confirm):**

* `recommendation/engine.py` (R1 only)
* `app/config.py` (R2 only)
* `tests/test_decision.py` (R1–R3 coverage)
* `tests/test_decision_cli.py` (R2 echo coverage)
* `CHANGELOG.md` (R4 record)
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M3-CLOSURE.md` (separate M3 closure commit, not the implementation commit)

Dependent test/manifest expansions beyond this list (if any) require the same owner-authorized
expansion process used in M2 — never silently.

## 12. Governance / Authorization Boundary

* M3 implementation is separated from this scope commit by a review gate and a separate explicit
  implementation authorization (the M1/M2 discipline).
* M1 and M2 artifacts are immutable; neither is altered by this scope.
* Nothing may be pushed without separate authorization.

---

*End of scope document. Planning only — no implementation was started, and no production file was
touched. `recommendation/engine.py` and `app/config.py` remain unmodified. `max_cost` is excluded.*
