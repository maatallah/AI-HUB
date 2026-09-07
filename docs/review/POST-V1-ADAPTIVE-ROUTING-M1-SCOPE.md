# POST-V1 ADAPTIVE ROUTING — M1 MINIMUM IMPLEMENTATION SCOPE

Status: **PLANNING DOCUMENT** (scope/architecture only — no implementation performed or authorized)
Baseline inspected: `359d1e173acce7ae827825bb900d10516d08bcc4` ("Define post-v1 routing decision contract")
Parent: `515080495a34e106f46d90d151f451c2e94cfca0` ("Post-v1 adaptive routing feasibility baseline")
Date: 2026-08-21
Nature: Milestone scope definition for the already-approved post-v1 Routing Decision Contract.
**Not** an implementation authorization. No source, schema, configuration, or test artifact was
created or modified. This file is the only artifact created.

Governing documents:

* `docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md` (R1) — normative contract; §17 defines the
  minimum viable contract this milestone implements
* `docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md` (R1) — approved decision record; DECIDE vs
  RECORD separation is binding
* `docs/review/POST-V1-ADAPTIVE-AI-ROUTING-FEASIBILITY.md` — CONDITIONAL GO basis (`5150804`)

---

## 1. Purpose

Define the smallest coherent implementation slice (M1) that demonstrates the committed routing
decision contract end-to-end: a caller asks *"given this task and these constraints, what AI
should I use?"* and receives the versioned envelope; a caller who wants persistence invokes the
separate RECORD operation. M1 makes the owner-mandated invariant mechanically real:

> **DECIDE never writes. RECORD never decides.**

Everything here is scope definition. Section 14 fixes the authorization boundary.

## 2. Current Baseline

* Branch `main`, HEAD `359d1e1…`, working tree clean, `main` ahead of `origin/main` by 2 commits
  (`5150804`, `359d1e1`) — nothing pushed.
* v1 / Phase 6 released and closed; closed-phase artifacts are immutable baselines.
* The decision contract and ADR are committed documentation; **no routing-decision code exists**.
* Verified integration surfaces (read during planning): `recommendation/engine.py`
  (`recommend(...)` signature and `_sort_key` order), `fallback/engine.py::build_chain`,
  `recommendation/provenance.py::record_recommendation`, `recommendation/explain.py::
  build_explanation`, `connectors/adapter.py` read-only functions, `app/main.py` argparse command
  scaffolding, `tests/` flat pytest layout.

## 3. M1 Objective

Deliver, behind one reviewable gate:

1. A pure **decision-envelope builder** implementing contract §§3–11 (inputs, statuses,
   ordering, freshness, cost semantics definition, error semantics, zero-write discipline).
2. One read-only CLI exposure (`route decide`) rendering text by default, envelope as JSON.
3. The minimal **RECORD DECISION** operation (`route record`) persisting an explicitly supplied
   decision through the existing append-only provenance path — including the normative
   `_sort_key` cost-direction change **only if** Open Question Q1 is resolved as "apply now".

M1 is complete when every acceptance criterion in Section 10 passes on a clean tree.

## 4. M1 Required Scope

| # | Item | Contract ref | Notes |
|---|------|--------------|-------|
| R1 | Envelope builder: pure function `(conn, request) -> envelope dict` | §§4–5 | Reuses `recommend()` internally; adds no decision logic of its own |
| R2 | All four statuses: `OK`, `NO_CANDIDATE`, `CONSTRAINT_UNSATISFIABLE`, `INSUFFICIENT_DATA` | §10 | Including exclusion counts/reasons in `warnings` |
| R3 | New input filters: allowed/denied providers+models, `freshness.max_stale_days` | §3, §6 | Pure post-filters over the eligible set; exclusions reported |
| R4 | Full `policy` echo from effective config (decision_version, resolved weights, aging days, latency threshold, derive flag, max chain length) | §5 | Reproducibility without config access |
| R5 | Candidate fields: rank, identity, final_score, confidence, breakdown, flags | §5.1 | Breakdown exactly as persisted today by provenance |
| R6 | Ordering per §5.2 (shipped `_sort_key` order unless Q1 = apply-now) | §5.2 | Deterministic tie-breaks preserved |
| R7 | Fallback chain via existing `build_chain`; DEGRADED last-resort placement | §8 | Chain length ≤ `max_chain_length` |
| R8 | Ephemeral provenance block: `recorded=false`, `decision_id=null` — always, in M1's DECIDE | §9 | Mechanical zero-write invariant (tested) |
| R9 | CLI `route decide` (text default, `--json`) | §13, §17(5) | Single read-only exposure; stdout only |
| R10 | CLI `route record`: reads a previously produced envelope (stdin JSON), validates it, persists its ranked candidates via existing `record_recommendation`, prints persisted ids | §9, §11, §17(6) | REQUIRED per spec §17(6); thin wrapper over existing mechanism; no decision calculation |

## 5. Deferred Scope (explicitly sequenced after M1)

* Adapter function exposing the envelope to MCP/VS Code (`connectors/adapter.py`) — spec §17(5)
  permits same-or-next milestone; deferred to keep M1's surface one exposure.
* MCP tool and VS Code command wiring (D-1 bounded-tools posture unchanged).
* HTTP/server surface (rejected for now; separately governed if ever).
* `max_cost` constraint knob enforcement (semantics defined, §7).
* Dedicated cost-normalization tooling (generic `score set` / benchmark mapping suffice).
* Runtime feedback events, review queueing (§12 boundary only).
* Contradictory-evidence detection; region/residency and deadline constraints; per-model
  availability overrides; ADR-0004 point-in-time snapshots.

## 6. Explicit Non-Goals

No execution/proxying/retries/streaming; no credential handling; no schema changes; no new event
types; no new dependencies; no monitoring triggers from DECIDE; no mutation of lifecycle,
registry, discovery, benchmark, history, or configuration state; no Phase 7 plan; no changes to
closed-phase public contracts (subject solely to Q1, see §12); no telemetry ingestion.

## 7. Integration Points (existing modules/interfaces — all verified)

| Existing interface | Used by M1 for |
|---|---|
| `recommendation.engine.recommend` (engine.py:96) | candidate scoring/ranking core |
| `recommendation.engine._eligible_models`, `ELIGIBLE_STATUSES` | eligibility set; allow/deny/freshness post-filters wrap it |
| `recommendation.engine._sort_key` | candidate ordering (Q1 may alter cost direction) |
| `Recommendation` dataclass | breakdown/flags/confidence source |
| `recommendation.profiles.get_profile` (+ `ProfileError`) | weight resolution; invalid-profile error path |
| `recommendation.explain.build_explanation` (explain.py:11) | `rationale` text |
| `fallback.engine.build_chain` / `Chain` (engine.py:77) | `selected` + `fallback_chain` |
| `scoring.engine.effective_score` / age computation | freshness filter evidence ages |
| `recommendation.provenance.record_recommendation` (provenance.py:23) | sole write path (RECORD only) |
| `core.events.RECOMMENDATION_CREATED` | emitted only inside record_recommendation |
| `app.config.DEFAULT_CONFIG` | policy echo values |
| `app.main` argparse scaffolding | new `route` command group (additive) |
| `tests/conftest.py` fixtures | seeded-database test harness conventions |

## 8. Proposed Files/Modules (none created yet)

**New**

* `recommendation/decision.py` — envelope builder + request validation + status resolution +
  RECORD helper (envelope validation + persistence loop). Alternative location: new top-level
  `routing/` package (Open Question Q3). Chosen proposal keeps engine/profiles/explain/provenance
  imports intra-package.
* `tests/test_decision.py` — builder unit tests (statuses, determinism, filters, zero-write proof).
* `tests/test_decision_cli.py` — CLI behavior tests (mirrors `test_models_cli.py` style).

**Modified (additive only)**

* `app/main.py` — add `route` subparser group (`decide`, `record`) + `cmd_route_*` handlers;
  no existing command touched.

**Conditionally modified (only on Q1 = apply-now)**

* `recommendation/engine.py::_sort_key` — one-line cost-direction change (ascending → descending),
  paired with `decision_version` bump `3.0.0 → 3.1.0` in `app/config.py`.

## 9. Test Strategy

1. **Status matrix** (unit): seed DBs driving each of the four statuses; assert envelope status,
   `warnings` content, and candidate presence rules per contract §10.
2. **Determinism**: identical DB snapshot + identical args ⇒ identical JSON, comparing with
   `created_at` normalized (same-instant determinism per Art. 7; wall-clock field excluded).
3. **Zero-write proof** (mechanical invariant): before/after every DECIDE call assert logical DB
   fingerprint — table row counts (`providers`, `models`, `scores`, `availability`, `events`,
   `recommendations`) and max `events.rowid` — unchanged; run across all status paths.
4. **Filters**: allow/deny provider/model lists and `freshness.max_stale_days` each demonstrably
   exclude seeded candidates and report counts in `warnings`; combined-filter precedence fixed.
5. **Ordering/tie-breaks**: crafted score ties exercise every `_sort_key` level; expected order
   asserted against §5.2 (or Q1-modified) sequence.
6. **Chain**: length bounds, primary selection, DEGRADED-as-last-resort placement.
7. **RECORD**: stdin envelope persists one `recommendations` row per ranked candidate with
   `RECOMMENDATION_CREATED` events; returned UUIDs match table contents; malformed/duplicate/
   foreign envelopes rejected with typed errors; append-only semantics (re-record creates new
   ids, never updates). DECIDE-after-RECORD still proves zero writes.
8. **CLI**: exit codes, `--json` parseability, text rendering, unknown args rejected; stdout-only.
9. **Regression**: entire existing suite passes unmodified (`pytest`), proving closed-phase
   behavior stability.

## 10. Acceptance Criteria (objectively verifiable)

1. `ai-hub route decide "<task>" --json` emits an envelope containing every contract §5 field;
   a schema-conformance test enumerates them.
2. Byte-identical JSON (modulo `created_at`) across repeated runs on an immutable DB copy.
3. Zero-write fingerprint test green for every DECIDE invocation path.
4. All four statuses demonstrated by named seeded scenarios in the test suite.
5. `ai-hub route record` persists exactly the envelope's ranked candidates; ids verifiable via
   existing `recommendations` queries; events present.
6. Full pre-existing test suite passes with zero modifications to existing test files.
7. `git diff --name-only` for the implementation commit ⊆ {`recommendation/decision.py`,
   `app/main.py`, `tests/test_decision.py`, `tests/test_decision_cli.py`} (+ `engine.py`/
   `config.py` only under Q1=apply-now).
8. If Q1 = apply-now: ordering change visible in envelopes via `policy.decision_version = "3.1.0"`;
   changelog entry exists; profiles weighting cost 0.00 demonstrably unaffected.

## 11. Compatibility / Invariants

* Closed v1 public contracts unchanged: no signature changes to any existing function; new CLI
  group is additive; existing command outputs byte-stable (regression suite enforces).
* Schema untouched; `EVENT_TYPES` set untouched; dependencies untouched.
* MCP server remains `PRAGMA query_only`, legacy-era stdio; VS Code untouched.
* Constitution mapping per contract §18 carries over; Art. 7 determinism documented as
  same-instant (wall-clock `created_at` is declared input-time dependence).
* Append-only ledger discipline: RECORD inserts only; no updates/deletes anywhere in M1.

## 12. Risks

| Risk | Mitigation |
|---|---|
| Q1 cost-direction fix alters visible ordering of closed CLI outputs (`recommend top`, `fallback chain`) | Owner ruling required first; pair with `decision_version` bump + CHANGELOG note; verify cost-0.00-weight profiles unaffected |
| `created_at` nondeterminism misread as Art. 7 violation | Declared input-time dependence in contract §18; tests normalize the field |
| Envelope drift vs future consumers | Schema-conformance test enumerates §5 fields exactly |
| Zero-write proof fragile under SQLite journaling/WAL | Logical fingerprint assertions, not file hashing |
| Scope creep toward execution features | §6 non-goals + §14 boundary; reviewer rejects any execution-plane code |
| `route record` misuse as hidden decide-and-write | Validation requires a well-formed prior envelope; help text and errors restate DECIDE/RECORD separation |

## 13. Open Questions — RESOLVED by owner ruling (2026-08-21)

* **Q1 — Cost sort direction:** **DEFER.** M1 ships the current `_sort_key` order; the normative
  flip is scheduled as a separate governed change (with its own `decision_version` bump). No
  `engine.py`/`config.py` modification occurs in M1.
* **Q2 — RECORD input form:** **stdin-JSON envelope** (as proposed).
* **Q3 — Module location:** **`recommendation/decision.py`** (as proposed).
* **Q4 — Clock injection:** **NOW** — builder takes an optional `now` parameter from the start;
  defaults to wall clock.
* **Q5 — RECORD sequencing:** **KEEP IN M1** (R10 stays inside this milestone).

Consequence of Q1=defer: §8's "conditionally modified" entries are void; the authorized file
list is exactly {`recommendation/decision.py`, `app/main.py`, `tests/test_decision.py`,
`tests/test_decision_cli.py`} and §10(7)/(8) reduce to the purely-additive case per §13a.

## 13a. Closed-Phase Public Contract Impact (Objective 10)

If Q1 is resolved as **defer**, M1 requires **zero changes** to any closed-phase module: it is
purely additive (one new module, one additive CLI group, two new test files) and therefore leaves
every existing public contract byte-stable. If Q1 is resolved as **apply-now**, exactly one
behavior-visible change occurs (cost tie-break direction in `_sort_key`), API-compatible (same
signatures) but observable in two closed CLI outputs, and is governed by the recorded
`decision_version` bump. No other deviation exists.

## 14. Implementation Authorization Boundary

This document authorizes **nothing**. Implementation requires an explicit owner mandate that (a)
answers Q1–Q5, (b) approves this scope, and (c) states the authorized file list. Absent that:
no code, no tests, no CLI edits, no commits beyond this planning artifact if the owner later
authorizes committing it. Any implementation commit must satisfy §10(7)'s file whitelist and stop
for review at the milestone gate before any further milestone (adapter/MCP wiring) begins.

---

*End of scope document. Planning only — no implementation was started, and no production file was
touched.*
