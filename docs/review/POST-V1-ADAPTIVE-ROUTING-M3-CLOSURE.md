# POST-V1 ADAPTIVE ROUTING — M3 CLOSURE RECORD

Status: **M3 ACCEPTED / CLOSED**
Milestone Scope: `c54a585d321a9c505cb81c0fbfb5988e925260eb` ("Define post-v1 adaptive routing M3 scope")
Milestone Commit: `a6846def729200cda9a195b8d2417763dbc5d49f` ("Implement post-v1 adaptive routing M3")
Parent of Implementation: `c54a585…` (M3 scope commit)
Date: 2026-08-28
Audit Verdict: **M3 ACCEPTED** (R1–R4 PASS; hard invariants PASS; boundary/governance audit PASS)
Owner Ruling: **Q1 = APPLY-NOW for M3**

Governing documents:
* `docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md` — approved decision record; Condition 2 (canonical cost
  semantics) and its "separate governed change" requirement are binding
* `docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md` — normative contract; §7 (cost semantics),
  §15 (versioning; `_sort_key` change bumps `decision_version`)
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M3-SCOPE.md` (M3 scope authority)
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M2-CLOSURE.md` (M2 closure; Q1 deferred to M3)
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M1-CLOSURE.md` (M1 closure; Q1 deferred)

---

## 1. M3 Objective & Summary

Complete the last remaining feasibility condition of the approved post-v1 routing decision plane: the
**canonical cost-semantics correction (Condition 2 / Q1)**. M1 and M2 delivered the decision contract
end-to-end but deferred Q1 twice; M3 applies it as a separate governed change with its own
`decision_version` bump.

### Owner Ruling

**Q1 = APPLY-NOW for M3** (recorded 2026-08-28).

### Implementation Summary

* **R1 — Canonical cost ordering (`recommendation/engine.py::_sort_key`):** cost key changed from
  `(cost if cost is not None else 1e9)` (ascending, price-like) to `-(cost if cost is not None else -1.0)`
  (descending, higher-is-better). Matches the availability/reliability semantics and the weighted-sum
  formula. Missing cost still sorts last (never fabricated, Article 10). All other sort dimensions
  (`final_score`, `availability`, `reliability`, `latency`, `model_identifier`) unchanged.
* **R2 — Decision version bump (`app/config.py`):** `recommendation.decision_version` `3.0.0 → 3.1.0`.
  Propagates via the existing DECIDE envelope `policy` echo and RECORD provenance persistence
  (contract §15). `contract_version` remains `"1"`.
* **R3 — Cost-zero profile invariance (`tests/test_decision.py`):** `coding` profile weights `cost`
  0.00; added `test_cost_zero_weight_profile_ranking_invariant` proving cost does not influence a
  0.00-cost-weight profile's ranking/selection. The cost tie-break test now asserts descending order
  where legitimately visible.
* **R4 — Governance record (`CHANGELOG.md`):** `### Changed (Post-v1 Adaptive Routing - M3 -
  Q1 cost semantics)` section under `[Unreleased]` records the cost-direction fix, the
  `decision_version` bump, and the R3 invariance guarantee.

### Authorized Files

M3 implementation diff is the five authorized files:
`recommendation/engine.py` (R1 only), `app/config.py` (R2 only), `tests/test_decision.py` (R1–R3
coverage), `CHANGELOG.md` (R4 record), and the **owner-authorized one-line whitelist expansion**
`tests/test_config.py` — a single stale default `decision_version` expectation (`"3.0.0"` → `"3.1.0"`)
in `test_defaults_used_when_file_missing`, necessary because R2 legitimately changes the default.

---

## 2. Milestone Invariants & Boundary Compliance

* **DECIDE ZERO-WRITE:** DECIDE calls no write path; zero-write fingerprint green across `empty`,
  `evidence`, `no_scores`, `constraint_unsatisfiable`, `insufficient_data`.
* **RECORD EXPLICIT:** `record_decision` remains the single explicit append-only persistence path.
* **CONTRACT VERSION PRESERVED:** `contract_version` stays `"1"` (additive-only evolution within v1).
* **`max_cost` EXCLUDED:** `max_cost` remains unimplemented (referenced only in governance/contract docs).
* **NO SCHEMA / NO EVENT-LOG / NO DEPENDENCY / NO CREDENTIAL / NO EXECUTION CHANGES:** commit diff
  introduces no DDL, no `EVENT_TYPES` change, no new package, no secret material, no execution/proxying.
* **NO ADAPTIVE-INTENT BEYOND Q1:** no new adaptive-routing behavior beyond the canonical cost ordering.
* **M1/M2 IMMUTABLE:** no M1 or M2 artifact changed; M1 and M2 remain closed and backward-compatible.

---

## 3. Verification & Test Suite Result

* **Python (full suite):** **548 passed** (0 failures, 0 errors). Independently reproduced at review
  (`pytest tests/ -q`) and re-verified at closure.
* **Targeted/regression:** R2 version test, R3 invariance test, R1 cost tie-break, zero-write fingerprint
  (all four+ statuses), determinism, and `test_decision_cli.py` — all green.
* **Baseline:** M2 closure 546 → M3 closure 548 (+2 net: added R2 version + R3 invariance tests;
  the R1 tie-break test was updated, not added).
* **`max_cost` negative/absence tests:** pass (feature unimplemented).

---

## 4. Milestone Review Verdict

* **M3 ACCEPTED** via formal milestone review of `a6846de`.
* R1–R4: **PASS** (requirement table and independent evidence recorded in review).
* Hard invariants (DECIDE zero-write; RECORD explicit; `contract_version` `"1"`; `max_cost`
  unimplemented; no schema/event/dependency/credential/execution/adaptive changes; M1/M2 untouched): **PASS**.
* Whitelist-expansion audit: `tests/test_config.py` is exactly the owner-authorized one-line
  version-expectation correction; no other file changed.
* Boundary/governance audit: `a6846de^ = c54a585`; single implementation commit; working tree clean except
  the pre-existing untouched untracked `docs/review/POST-V1-ADAPTIVE-ROUTING-M1-SCOPE.md`; nothing pushed.

---

## 5. Formal Closure Declaration

**Milestone M3 is ACCEPTED and CLOSED.**

This closure record is a governance artifact distinct from the implementation commit `a6846de`, which
remains unchanged. No further code, test, or configuration changes are authorized under M3.
The next step is a separate **AI-Hub functional test / acceptance drive**, not another development
milestone. `max_cost` and other deferred scope remain explicitly excluded, pending future owner ruling.
