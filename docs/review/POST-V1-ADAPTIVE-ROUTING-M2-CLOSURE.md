# POST-V1 ADAPTIVE ROUTING — M2 CLOSURE RECORD

Status: **M2 ACCEPTED / CLOSED**
Milestone Scope: `2999a630e2655c12ddf508be4b32cbfdbb00f1ad` ("Define post-v1 adaptive routing M2 scope")
Milestone Commit: `0fb771c6c1ca3b504e980f8d4252425db821d9d5` ("Implement post-v1 adaptive routing M2")
Parent of Implementation: `2999a63…` (M2 scope commit)
Date: 2026-08-28
Audit Verdict: **M2 ACCEPTED** (R1–R8 PASS; hard invariants PASS; boundary/governance audit PASS)

Governing documents:
* `docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md` (normative contract; §17(5) wiring authority)
* `docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md` (Option A exposure pattern, binding)
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M1-CLOSURE.md` (M1 closure; findings F1–F3 = M2 backlog)
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M2-SCOPE.md` (M2 scope authority)

---

## 1. M2 Objective & Summary

Deliver the post-v1 consumer surface by wiring the M1 decision envelope (`build_decision_envelope`,
`record_decision`) through the three existing read-only connector channels (shared adapter, MCP tool
registry, VS Code command set) and resolve the three M1 deferred findings (F1–F3).

### Implementation Summary

* **R1** — Adapter `route_decide(conn, task, *, …)`: keyword-only contract inputs; wraps
  `build_decision_envelope` (zero-write); added to `__all__`.
* **R2** — Adapter `route_record(conn, envelope)`: wraps `record_decision`; returns
  `{"decision_id", "recorded_ids", "count"}`; added to `__all__`.
* **R3** — MCP tool `route.decide`: thin handler over `adapter.route_decide`; full contract §3 input
  vocabulary; `additionalProperties: false`; alphabetical `_TOOL_DEFS` insertion; auto-derived `TOOLS`.
* **R4** — MCP tool `route.record`: thin handler over `adapter.route_record`; accepts envelope JSON object.
* **R5** — VS Code feature `ai-hub.routeDecide`: `Feature` entry invoking
  `python -m app.main route decide --task <T> --json`; registered in `package.json` command + activation event.
* **R6** — F1 resolved: zero-write fingerprint test extended across all four statuses
  (`empty`, `evidence`, `no_scores`, `constraint_unsatisfiable`, `insufficient_data`).
* **R7** — F2 resolved: `validate_envelope` typed per-dimension checks (value/weight/contribution/confidence,
  source/aged presence, dimension object) and `resolved_weights` ↔ breakdown dimension cross-check,
  all raising `DecisionError`.
* **R8** — F3 resolved: `cmd_route` includes `ProvenanceError` in the handled exception tuple
  (exit 1 + stderr error text, no traceback).

### Authorized Files

Unmodified scope §10(11) whitelist files plus four owner-authorized whitelist expansions
(required to keep existing tests green and follow conventions for R3/R4/R5/R7):
`tests/test_connectors_mcp.py` (tool-set assertion), `connectors/vscode/package.json` and
`connectors/vscode/test/features.test.ts` (R5 feature registration/count), and
`recommendation/decision.py` (R7 validation host module).

---

## 2. Milestone Invariants & Boundary Compliance

* **DECIDE ZERO-WRITE:** `route_decide`/`_route_decide` call only `build_decision_envelope`; no write/event/monitoring call.
* **RECORD EXPLICIT:** `route_record`/`_route_record` call only `record_decision` (append-only); it is the only persistence path.
* **NO SCHEMA / NO EVENT-LOG / NO DEPENDENCY / NO CREDENTIAL CHANGES:** commit diff introduces no DDL,
  no `EVENT_TYPES` change, no new package, and no secret material.
* **NO EXECUTION / NO ADAPTIVE-INTENT BEYOND M2:** no execution-plane code; Q1 cost-direction flip remains deferred;
  `decision_version` (3.0.0) and `recommendation/engine.py`, `app/config.py` untouched.
* **COLLECTOR/EXISTING SURFACES ADDITIVE ONLY:** existing adapter functions, MCP tools, and VS Code features unchanged (additive only).
* **M1 IMMUTABLE:** no M1 file (`M1-CLOSURE`, `M1-SCOPE`, `DECISION-CONTRACT`) changed; M1 remains closed.

---

## 3. Verification & Test Suite Result

* **Python:** **546 passed** (0 failures, 0 errors). Independently reproduced at closure (`pytest tests/ -q`).
* **Baseline:** 508 (M1) → 546 (M2): +38 new M2 tests (`test_adapter_decision.py`, `test_mcp_route.py`,
  `test_vscode_route_feature.py`, extended `test_decision.py`, `test_decision_cli.py`).
* **VS Code unit tests:** **28 passed** / 0 failed (`npm run test:unit`), TypeScript compile clean.
* **F1–F3:** each deferred finding verified resolved by dedicated tests.

---

## 4. Milestone Review Verdict

* **M2 ACCEPTED** via formal milestone review of `0fb771c`.
* R1–R8: **PASS** (requirement table and independent evidence recorded in review).
* Hard invariants (DECIDE zero-write; RECORD explicit; no schema/event/dependency/credential/execution/adaptive
  changes; M1 untouched): **PASS**.
* Whitelist-expansion audit: the four owner-authorized expansions are limited to what R3/R4/R5/R7 require.
* Boundary/governance audit: `0fb771c^ = 2999a63`; single implementation commit; working tree clean except the
  pre-existing untouched untracked `docs/review/POST-V1-ADAPTIVE-ROUTING-M1-SCOPE.md`; nothing pushed.

---

## 5. Formal Closure Declaration

**Milestone M2 is ACCEPTED and CLOSED.**

This closure record is a governance artifact distinct from the implementation commit `0fb771c`, which remains
unchanged. No further code, test, or configuration changes are authorized under M2. M3 (or any subsequent
milestone) requires a new explicit owner authorization.
