# POST-V1 ADAPTIVE ROUTING — M2 SCOPE SPECIFICATION

Status: **PLANNING DOCUMENT** (scope/architecture only — no implementation performed or authorized)
Baseline inspected: `0df21262d9fb82d64a02422fb7ba711fb4d79c65` ("Close M1 post-v1 routing decision plane")
Parent: `5689d8f573b6730a41a88179166bb9015f602f06` ("Implement M1 post-v1 routing decision plane (DECIDE/RECORD)")
Date: 2026-08-28
Nature: Milestone scope definition for consumer and connector exposure of the M1 decision envelope.
**Not** an implementation authorization. No source, schema, configuration, or test artifact was
created or modified. This file is the only artifact produced by the M2 scoping effort; one
additional untracked planning artifact exists from M1
(`docs/review/POST-V1-ADAPTIVE-ROUTING-M1-SCOPE.md`).

Governing documents:

* `docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md` (R1) — normative contract; §17(5) permits
  adapter/MCP/VS Code wiring in the same or next milestone after M1
* `docs/adr/ADR-POST-V1-ROUTING-DECISION-PLANE.md` (R1) — approved decision record; Option A
  exposure pattern is binding
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M1-SCOPE.md` — M1 scope authority (closed)
* `docs/review/POST-V1-ADAPTIVE-ROUTING-M1-CLOSURE.md` — M1 closure record; deferred findings
  F1–F3 are M2 backlog

---

## 1. Purpose

Define the implementation slice (M2) that completes the post-v1 consumer surface by wiring the
M1 decision envelope (`build_decision_envelope`, `record_decision`) through the three existing
read-only connector channels: the shared adapter, the MCP server tool registry, and the VS Code
extension command set. M2 also resolves the three deferred findings (F1–F3) carried forward from
the M1 closure record.

M2 delivers the contract §17(5) deferred item: *"adapter/MCP wiring may follow in the same
milestone or the next."* The decision envelope bytes are identical across every transport — the
contract, not the wiring, defines the decision.

Everything here is scope definition. Section 14 fixes the authorization boundary.

## 2. Current Baseline

* Branch `main`, HEAD `0df2126…`, working tree clean (one untracked file:
  `docs/review/POST-V1-ADAPTIVE-ROUTING-M1-SCOPE.md`); `main` ahead of `origin/main` by 4
  commits — nothing pushed.
* M1 complete and closed (`5689d8f` → `0df2126`): DECIDE envelope builder, RECORD operation,
  CLI `route decide` / `route record` all operational.
* Full test suite: **508 passed** (467 pre-existing + 41 new M1 tests).
* M1 deferred findings: F1 (zero-write fingerprint coverage for all four statuses),
  F2 (envelope validation typing), F3 (CLI `ProvenanceError` handling) — all backlog for M2.
* Connector surfaces verified (read during planning): `connectors/adapter.py` (8 public
  functions, all read-only, delegate to existing engines), `connectors/mcp/tools.py` (7 tools,
  thin handler pattern over adapter), `connectors/vscode/src/features.ts` (7 features, CLI
  invocation via `python -m app.main`, stdout rendering).
* Q1 (cost-direction `_sort_key` flip) remains **defer** — not in M2 scope.

## 3. M2 Objective

Deliver, behind one reviewable gate:

1. **Adapter function** `route_decide` in `connectors/adapter.py` — wraps `build_decision_envelope`,
   returns the envelope dict via the existing adapter convention (conn + plain args → dict).
2. **Adapter function** `route_record` in `connectors/adapter.py` — wraps `record_decision`,
   accepts an envelope dict, returns the persistence result dict.
3. **MCP tool** `route.decide` in `connectors/mcp/tools.py` — thin handler delegating to
   `adapter.route_decide`, with the full contract input vocabulary (task, profile,
   min_context_window, required_capabilities, allowed/denied providers/models, max_stale_days,
   limit). Returns the envelope as the MCP tool result.
4. **MCP tool** `route.record` in `connectors/mcp/tools.py` — thin handler delegating to
   `adapter.route_record`, accepting the envelope JSON as input.
5. **VS Code feature** `ai-hub.routeDecide` in `connectors/vscode/src/features.ts` — invokes
   `python -m app.main route decide --json` and renders the envelope. One new feature entry
   following the existing `Feature` interface.
6. **M1 backlog resolution**: F1 (extended zero-write fingerprint test coverage),
   F2 (validation typing hardening), F3 (CLI exception handling).

M2 is complete when every acceptance criterion in Section 10 passes on a clean tree.

## 4. M2 Required Scope

| # | Item | Contract ref | Notes |
|---|------|--------------|-------|
| R1 | Adapter `route_decide(conn, task, ...)` → envelope dict | §§3–5, §13 | Wraps `build_decision_envelope`; passes through all contract inputs; returns raw dict |
| R2 | Adapter `route_record(conn, envelope)` → persistence dict | §§9, §11 | Wraps `record_decision`; validates + persists; returns `{"decision_id", "recorded_ids", "count"}` |
| R3 | MCP tool `route.decide` (full input vocabulary) | §13, §17(5) | Handler pattern identical to `_recommend_top` / `_fallback_chain`; schema mirrors contract §3 |
| R4 | MCP tool `route.record` (envelope input) | §9, §11, §17(5) | Accepts envelope JSON object; delegates validation to adapter |
| R5 | VS Code `ai-hub.routeDecide` feature | §13, §17(5) | One `Feature` entry invoking `route decide --task T --json`; stdout rendering unchanged |
| R6 | F1: zero-write fingerprint test for `CONSTRAINT_UNSATISFIABLE` and `INSUFFICIENT_DATA` | M1 closure §4 | Extends existing fingerprint test to cover all four status paths |
| R7 | F2: validation typing hardening in `validate_envelope` | M1 closure §4 | Cross-check `resolved_weights` keys against candidate `breakdown` dimensions; typed `DecisionError` for `aged`/`breakdown` field presence |
| R8 | F3: CLI `ProvenanceError` handling in `cmd_route` | M1 closure §4 | Add `ProvenanceError` to the handled exception tuple in `cmd_route` |

## 5. Deferred Scope (explicitly sequenced after M2)

* HTTP/server surface (separately governed if ever adopted).
* `max_cost` constraint knob enforcement (semantics defined, §7 of contract).
* Dedicated cost-normalization tooling.
* Runtime feedback events and review queueing (contract §12 boundary only).
* Contradictory-evidence detection; region/residency and deadline constraints; per-model
  availability overrides; ADR-0004 point-in-time snapshots.
* Q1 cost-direction `_sort_key` flip (deferred; not in M2).
* Execution/proxying/retries/streaming/credentials/scheduling/telemetry ingestion.

## 6. Explicit Non-Goals

No execution/proxying/retries/streaming; no credential handling; no schema changes; no new event
types; no new dependencies; no monitoring triggers from DECIDE; no mutation of lifecycle,
registry, discovery, benchmark, history, or configuration state; no Phase 7 plan; no changes to
closed-phase public contracts; no telemetry ingestion; no HTTP server; no new CLI commands
(M2 wires existing CLI via adapter/VS Code; no new `app/main.py` commands).

## 7. Integration Points (existing modules/interfaces — all verified)

| Existing interface | Used by M2 for |
|---|---|
| `recommendation.decision.build_decision_envelope` (decision.py:169) | Core DECIDE computation, wrapped by adapter `route_decide` |
| `recommendation.decision.record_decision` (decision.py:510) | Core RECORD computation, wrapped by adapter `route_record` |
| `recommendation.decision.validate_envelope` (decision.py:429) | Envelope validation (F2 hardening applies here) |
| `recommendation.decision.DecisionError` (decision.py:54) | Typed errors for adapter/MCP surface |
| `connectors.adapter` existing pattern (adapter.py:42–134) | Adapter function convention: `conn` + args → plain dict/list |
| `connectors.mcp.tools` existing handler pattern (tools.py:47–88) | MCP tool handler convention: `(conn, arguments) -> result` |
| `connectors.mcp.tools._TOOL_DEFS` (tools.py:91) | Tool definition registry; alphabetical insertion |
| `connectors.mcp.tools.TOOLS` (tools.py:203) | Public tool-name set (auto-derived from `_TOOL_DEFS`) |
| `connectors.vscode.src.features.ts` Feature interface (features.ts:16–22) | VS Code feature convention: `commandId`, `title`, `requiresInput`, `buildArgs` |
| `app.main.cmd_route` (main.py:728) | CLI exception handling (F3 applies here) |
| `app.main` argparse `route` group (main.py:1000) | CLI `route decide --json` invoked by VS Code |
| `recommendation.provenance.ProvenanceError` (provenance.py:19) | Exception class for F3 handling |
| `tests/conftest.py` fixtures | Seeded-database test harness conventions |
| `tests/test_decision.py` existing fingerprint tests | F1 extension target |

## 8. Proposed Files/Modules

**Modified (additive only)**

* `connectors/adapter.py` — add `route_decide` and `route_record` functions following existing
  convention (args → dict). Two new imports: `from recommendation import decision`. Added to
  `__all__`.
* `connectors/mcp/tools.py` — add `_route_decide` and `_route_record` handlers, two entries in
  `_TOOL_DEFS` (alphabetical insertion). One new helper `_optional_list` for list-type inputs.
* `connectors/vscode/src/features.ts` — add one `Feature` entry for `ai-hub.routeDecide`.

**Modified (M1 backlog fixes)**

* `tests/test_decision.py` — extend zero-write fingerprint test (F1); add validation typing
  tests (F2).
* `tests/test_decision_cli.py` — add `ProvenanceError` handling test (F3).
* `app/main.py` — add `ProvenanceError` to exception tuple in `cmd_route` (F3).

**New (M2 tests)**

* `tests/test_adapter_decision.py` — adapter function tests for `route_decide` and
  `route_record`: contract input passthrough, error propagation, envelope dict shape.
* `tests/test_mcp_route.py` — MCP tool handler tests: argument validation, schema conformance,
  delegation to adapter, error mapping.
* `tests/test_vscode_route_feature.py` — VS Code feature tests: `buildArgs` correctness for
  `ai-hub.routeDecide`.

## 9. Test Strategy

1. **Adapter delegation** (unit): `route_decide` returns an envelope dict identical to
   `build_decision_envelope` for the same inputs; `route_record` returns the same result as
   `record_decision`. Verify via seeded DBs across all four statuses.
2. **Adapter input passthrough**: every contract input (task, profile, min_context_window,
   required_capabilities, allowed/denied providers/models, max_stale_days, limit) reaches the
   underlying function. Missing/invalid inputs produce `DecisionError` (not adapter-specific errors).
3. **MCP tool schema conformance**: `route.decide` tool definition matches the contract §3 input
   vocabulary; `additionalProperties: false` enforced; required fields present.
4. **MCP handler delegation**: `call_tool("route.decide", ...)` produces identical envelope to
   direct adapter call; `call_tool("route.record", ...)` persists identically.
5. **MCP error propagation**: unknown tool name, missing required args, invalid types all produce
   `ValueError` per existing `call_tool` contract.
6. **VS Code `buildArgs`**: `ai-hub.routeDecide` produces `["route", "decide", "--task", "<input>", "--json"]`
   for all task values; feature is found by `featureByCommand`.
7. **F1 — Full zero-write fingerprint**: extend existing test to exercise `CONSTRAINT_UNSATISFIABLE`
   and `INSUFFICIENT_DATA` paths with before/after table-row-count + max-event-rowid assertions.
8. **F2 — Validation typing**: malformed envelopes (missing `breakdown` keys, `aged` absent,
   `resolved_weights` dimension mismatch) raise `DecisionError` rather than `KeyError`/`TypeError`.
9. **F3 — CLI ProvenanceError**: `cmd_route` with a RECORD that triggers a provenance failure
   produces exit code 1 and stderr error text (no traceback).
10. **Regression**: entire existing suite passes unmodified (508 tests), proving no connector
    changes break existing behavior.

## 10. Acceptance Criteria (objectively verifiable)

1. `connectors.adapter.route_decide(conn, task)` returns an envelope dict containing every
   contract §5 field; a schema-conformance test enumerates them.
2. `connectors.adapter.route_record(conn, envelope)` persists exactly the envelope's ranked
   candidates; returned `decision_id` matches a `recommendations` table row.
3. MCP tool `route.decide` is present in `TOOLS` and `tool_definitions()` output; schema matches
   contract §3.
4. MCP tool `route.record` is present in `TOOLS` and `tool_definitions()` output.
5. `call_tool("route.decide", {"task": "test"})` returns an envelope dict identical to
   `adapter.route_decide(conn, "test")`.
6. `ai-hub.routeDecide` feature exists in `FEATURES`; `featureByCommand("ai-hub.routeDecide")`
   returns it; `buildArgs("python web service")` produces
   `["route", "decide", "--task", "python web service", "--json"]`.
7. Zero-write fingerprint test covers all four statuses (F1 resolved).
8. Malformed envelopes rejected by `validate_envelope` with `DecisionError` for all identified
   gap cases (F2 resolved).
9. CLI `route record` with provenance failure produces exit 1 and error text (F3 resolved).
10. Full pre-existing test suite passes with zero modifications to existing non-M2 test files.
11. `git diff --name-only` for the implementation commit ⊆ {
    `connectors/adapter.py`, `connectors/mcp/tools.py`, `connectors/vscode/src/features.ts`,
    `tests/test_adapter_decision.py`, `tests/test_mcp_route.py`, `tests/test_vscode_route_feature.py`,
    `tests/test_decision.py`, `tests/test_decision_cli.py`, `app/main.py` (F3 only)
    }.

## 11. Compatibility / Invariants

* Closed v1 public contracts unchanged: no signature changes to any existing function; new adapter
  functions are additive; existing adapter functions byte-stable; existing MCP tool set unchanged
  (additive only); existing VS Code features unchanged (additive only).
* Schema untouched; `EVENT_TYPES` set untouched; dependencies untouched.
* MCP server remains `PRAGMA query_only`, legacy-era stdio; no new write paths.
* DECIDE/RECORD separation invariant preserved: adapter `route_decide` calls only
  `build_decision_envelope` (zero writes); adapter `route_record` calls only `record_decision`
  (explicit, append-only).
* All existing connector conventions preserved: adapter returns plain dicts, MCP handlers delegate
  to adapter, VS Code invokes CLI and renders stdout.

## 12. Risks

| Risk | Mitigation |
|---|---|
| MCP tool schema drift from contract §3 | Schema-conformance test enumerates contract §3 inputs; `additionalProperties: false` |
| VS Code `buildArgs` divergence from CLI argparser | Test asserts exact args; feature follows existing pattern verbatim |
| F2 validation hardening introduces false rejections | New validation cases derived from contract §5 field definitions; regression suite catches regressions |
| F3 `ProvenanceError` handling masks underlying data issues | Error text preserved in stderr; exit code 1 is existing convention |
| Adapter function growth complicates `adapter.py` surface | Only two new functions added; existing convention scales linearly; no architectural change |
| Scope creep toward execution features | §6 non-goals + §14 boundary; reviewer rejects any execution-plane code |

## 13. Open Questions

* **Q1 — Cost sort direction:** **DEFER** (unchanged from M1). M2 ships without the `_sort_key`
  flip; `decision_version` stays `3.0.0`; no `engine.py`/`config.py` modification in M2.
* **Q2 — MCP tool naming:** `route.decide` / `route.record` (dot-separated namespace, consistent
  with MCP convention and existing tool names). No ambiguity with existing tools.
* **Q3 — VS Code feature name:** `ai-hub.routeDecide` (camelCase command ID, consistent with
  existing features). No `route-record` feature — RECORD is a persistence operation best
  invoked via CLI; VS Code reads and renders decisions only.
* **Q4 — Adapter `route_decide` parameter style:** keyword-only arguments matching
  `build_decision_envelope` signature exactly (no positional args except `conn` and `task`).
  Maintains 1:1 mapping for testability.
* **Q5 — MCP `route.record` input form:** envelope JSON object (same as CLI `route record` stdin
  format). Consistency across transports.

All questions resolved. No blockers.

## 13a. Closed-Phase Public Contract Impact (Objective 10)

M2 requires **zero changes** to any closed-phase module. All modifications are additive:
two new adapter functions, two new MCP tools, one new VS Code feature, new test files, and
three M1-backlog fixes confined to `app/main.py` (one exception tuple addition), `tests/test_decision.py`
(test additions), and `tests/test_decision_cli.py` (test additions). Every existing public
contract remains byte-stable.

## 14. Implementation Authorization Boundary

This document authorizes **nothing**. Implementation requires an explicit owner mandate that (a)
confirms Q1–Q5 rulings, (b) approves this scope, and (c) states the authorized file list. Absent
that: no code, no tests, no CLI edits, no commits beyond this planning artifact if the owner later
authorizes committing it. Any implementation commit must satisfy §10(11)'s file whitelist and stop
for review at the milestone gate before any further milestone begins.

---

*End of scope document. Planning only — no implementation was started, and no production file was
touched.*
