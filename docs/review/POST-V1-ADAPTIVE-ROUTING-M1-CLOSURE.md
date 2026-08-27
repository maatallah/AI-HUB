# POST-V1 ADAPTIVE ROUTING — M1 CLOSURE RECORD

Status: **M1 ACCEPTED / CLOSED WITH DEFERRED FINDINGS**
Milestone Commit: `5689d8f573b6730a41a88179166bb9015f602f06` ("Implement M1 post-v1 routing decision plane (DECIDE/RECORD)")
Parent Baseline: `359d1e173acce7ae827825bb900d10516d08bcc4` ("Define post-v1 routing decision contract")
Date: 2026-08-27
Audit Verdict: **PASS WITH FINDINGS** (unanimous across acceptance criteria; findings recorded below)

Governing documents:
* `docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md` (R1)
* `docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md` (R1)
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M1-SCOPE.md` (scope authority, rulings recorded)

---

## 1. M1 Objective & Summary

Deliver the post-v1 routing decision contract end-to-end behind one reviewable gate:
a pure, read-only decision-envelope builder (DECIDE), one read-only CLI exposure (`route decide`),
and the minimal append-only persistence path (`route record`) reusing existing provenance.

### Authorized Files

* `recommendation/decision.py` (new) — envelope builder + request validation + RECORD helper
* `app/main.py` (modified, additive) — `route decide` / `route record` subparser group
* `tests/test_decision.py` (new) — builder unit tests, status matrix, determinism, zero-write proof
* `tests/test_decision_cli.py` (new) — CLI behavior and round-trip tests

### Implementation Summary

* Pure, zero-write decision envelope computation (`build_decision_envelope`) implementing contract §§3–11.
* All four statuses implemented: `OK`, `NO_CANDIDATE`, `CONSTRAINT_UNSATISFIABLE`, `INSUFFICIENT_DATA`.
* Injectable clock parameter (`now`) for determinism (Constitution Article 7).
* Ephemeral provenance block in DECIDE (`recorded=false`, `decision_id=null`).
* Append-only RECORD operation (`record_decision`) persisting ranked candidates via `record_recommendation`.
* CLI `route decide` (text + `--json`) and `route record` (reads stdin JSON).

---

## 2. Milestone Invariants & Boundary Compliance

* **Q1 RULING HONORED:** `Q1 = DEFER` — `recommendation/engine.py::_sort_key` was not modified;
  `app/config.py` and `decision_version` (3.0.0) untouched; zero closed-phase files modified.
* **CLOSED-PHASE IMMUTABILITY:** `git diff 5689d8f^ 5689d8f` over all closed-phase directories
  (`core/`, `database/`, `fallback/`, `scoring/`, `monitoring/`, `connectors/`, etc.) is empty.
  The change to `app/main.py` is purely additive.
* **ZERO WRITE INVARIANT:** DECIDE contains no write paths; zero writes/events/monitoring calls.
* **STOPPING RULE RESPECTED:** §14 milestone stopping rule was strictly respected.
* **NO M2 WORK:** No adapter/MCP wiring, no HTTP surface, no execution-plane features, and no
  post-M1 work was started.

---

## 3. Verification & Test Suite Result

* **Full Test Suite:** **508 passed** (0 failures, 0 errors, 0 warnings).
* **Pre-existing Tests:** 467 tests passed unmodified (zero modifications to existing test files).
* **New M1 Tests:** 41 tests (29 in `test_decision.py`, 12 in `test_decision_cli.py`).

---

## 4. Deferred Findings (Backlog for Future Authorized Milestone)

The following findings were identified during the post-commit audit and are formally recorded
as backlog items. They are **not** authorized for implementation during this closure:

* **F1 — §10(3) Zero-Write Fingerprint Coverage:**
  The mechanical zero-write fingerprint test covers `NO_CANDIDATE` and `OK`, but does not directly
  fingerprint the `CONSTRAINT_UNSATISFIABLE` and `INSUFFICIENT_DATA` paths.
  *(Disposition: Backlog item for test hardening in next milestone).*

* **F2 — Envelope Validation Typing:**
  `validate_envelope` does not cross-check `resolved_weights` against candidate `breakdown`
  dimensions or per-dimension fields (`aged`). A malformed envelope may therefore reach an untyped
  `KeyError` in explanation reconstruction rather than being rejected by the typed `DecisionError` path.
  *(Disposition: Backlog item for validation hardening in next milestone).*

* **F3 — CLI Exception Handling:**
  `cmd_route` does not currently include `ProvenanceError` in its handled exception tuple, so a
  provenance/database failure during RECORD could escape as a traceback instead of the standard
  CLI error/exit-1 path.
  *(Disposition: Backlog item for CLI error hardening in next milestone).*

### Documented Interpretations (F4 — Non-Defect)

* **Whole-Envelope Re-recording:** Re-recording a previously recorded envelope remains allowed and is
  strictly append-only (creates new distinct recommendation IDs and events).
* **Intra-Envelope Duplicates:** Duplicate `(provider_id, model_id)` candidates within the same
  envelope are rejected by validation.
* **Zero-Evidence Freshness Exemption:** Candidates with zero stored evidence are exempt from
  `max_stale_days` exclusion because the contract is silent on that case (they surface via
  `INSUFFICIENT_DATA` or insufficient-data flags).

---

## 5. Formal Closure Declaration

**Milestone M1 is ACCEPTED and CLOSED WITH DEFERRED FINDINGS.**

No further code, test, or configuration changes are authorized under M1.
