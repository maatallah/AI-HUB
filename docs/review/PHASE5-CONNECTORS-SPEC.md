# PHASE5-CONNECTORS-SPEC.md

# AI-Hub Phase 5 - Connectors (VS Code / MCP) Proposal Spec

**Date:** 2026-08-17

**Status:** PROPOSED (Phase 5 revised planning proposal approved 2026-08-17
by owner; Milestone 1 - documentation only, no implementation)

This document records the approved Phase 5 architecture and decisions for the
AI-Hub connectors (MCP server and VS Code extension). It mirrors the Phase 4
proposal spec pattern and delegates to the existing Phase 1-4 modules using
their real names. It is read-only by design: connectors never mutate AI-Hub
data and never contain decision logic (Constitution Articles 1, 2, 4, 5, 6).

---

## 1. Objectives

1. Provide read-only, decision-free access to AI-Hub intelligence from
   external tools.
2. Deliver an MCP server (`connectors/mcp/`) exposing AI-Hub data and
   decision output to MCP clients over stdio.
3. Deliver a VS Code extension (`connectors/vscode/`) rendering dashboard
   reports as presentation/integration only.
4. Route all reads through a single shared adapter
   (`connectors/adapter.py`) that delegates to existing engines - no
   duplicated SQL, no reaching into database internals.
5. Preserve the "no new Python dependencies" rule (stdlib + sqlite3 + pytest
   only) and isolate the VS Code npm dependency graph from core AI-Hub
   policy.

---

## 2. MCP architecture

### 2.1 Bounded MCP subset (decision D-1)

The MCP connector is a **deliberately bounded MCP subset**. It is NOT
declared as "full MCP conformance". It targets the **legacy protocol era**
(handshake-based `initialize`, revisions `2024-10-07` .. `2025-11-25`).

**Supported protocol versions** (negotiated via `initialize`):

* `2025-11-25` (primary target)
* `2025-06-18`
* `2025-03-26`
* `2024-11-05`

**Transport:** stdio only. Newline-delimited JSON-RPC 2.0 messages on
stdin/stdout, UTF-8, one message per line. No HTTP, no SSE, no streamable
transport, no `Mcp-Session-Id`, no TLS. Offline-capable by design.

**Supported primitives (Tools capability only):**

* `initialize` / `notifications/initialized` (handshake)
* `ping`
* `tools/list`
* `tools/call`

**NOT supported:** resources, prompts, sampling, roots, logging, completions,
`server/discover`, JSON-RPC batches, progress notifications, HTTP transports.

### 2.2 Tool discovery and semantics

* `tools/list` returns the fixed tool set with `name`, `description`,
  `inputSchema` (JSON Schema `type: "object"`). Deterministic ordering
  (alphabetical by tool name). `listChanged` is not advertised and no
  `notifications/tools/list_changed` is emitted.
* `tools/call` returns a single `{type: "text", text: ...}` content item.
  Tool-level failures (missing data, engine error) return
  `isError: true` on the result; unknown tools and invalid params return
  JSON-RPC errors.
* Error codes: `-32700` parse error, `-32600` invalid request,
  `-32601` method not found, `-32602` invalid params / unknown tool,
  `-32603` internal error.
* `recommend_top` calls `recommendation.recommend` ONLY (read-only ranking).
  It does NOT call `recommendation.record_recommendation` and does NOT write
  provenance: connectors write nothing (Constitution Article 5).

### 2.3 Modern era (2026-07-28) is out of scope

The stateless modern era `2026-07-28` (per-request `_meta` versioning,
`server/discover`) is explicitly not implemented. Over stdio the connector
behaves as a legacy server; MCP clients in auto/legacy mode fall back to the
`initialize` handshake. A client pinned exclusively to `2026-07-28` receives
the equivalent of `UnsupportedProtocolVersionError`. Revisit only if a
concrete client requires it.

---

## 3. Dependency decisions

### 3.1 D-1 - MCP Python dependency: NONE

Resolved: **no new Python dependency**. The bounded stdio MCP subset is
implemented with the Python standard library only (`json`, `sys`,
`argparse`, `sqlite3`, `typing`). A concrete reason to add an MCP SDK would
be: a requirement for the modern era, an HTTP transport, or full resource/
prompt/sampling semantics - none are in scope. `requirements.txt` is not
changed by Phase 5.

### 3.2 D-4 - VS Code dependency: isolated npm graph

The VS Code extension lives under `connectors/vscode/` as a self-contained
Node.js / TypeScript workspace:

* Own `package.json` (`devDependencies`: `typescript`, `@types/vscode`,
  `@vscode/test-cli`), `tsconfig.json`, `src/`.
* The `vscode` API module is provided at runtime by the VS Code host; it is
  never bundled into the Python project.
* **No Python module imports any npm package; no Python code depends on it.**
  The Python dependency model (`requirements.txt`) is unaffected.
* The no-new-dependencies rule governs the Python runtime only; the
  extension's npm graph is contained within `connectors/vscode/` and is
  isolated from core AI-Hub policy.
* `connectors/vscode/node_modules/` is git-ignored; `npm install` and any
  build are owner-run local steps, not part of Python tooling or tests.
* No package is installed automatically by AI-Hub.

---

## 4. Shared read-only adapter

`connectors/adapter.py` (Phase 5 implementation milestone) is the single,
stable read-only application interface used by both connectors. It receives
an already-open SQLite connection and returns plain dict/list structures. It
executes no SQL of its own and never mutates state.

### 4.1 Delegation map (existing modules only)

| Adapter function | Delegates to |
|------------------|--------------|
| `provider_status(conn)` | `dashboard.engine.provider_view` + `monitoring.availability.list_availability` |
| `model_scores(conn, model_id=None)` | `dashboard.engine.score_view` (reuses `scoring.list_scores`) |
| `recommend_top(conn, task, profile=..., limit=...)` | `recommendation.recommend` |
| `fallback_chain(conn, task, profile=..., max_chain_length=...)` | `fallback.build_chain` |
| `dashboard_report(conn, name, ...)` | `dashboard.reports.REPORT_BUILDERS` |
| `score_history(conn, model_id, dimension=None)` | `dashboard.history.score_history` |
| `availability_history(conn, provider_id=None)` | `dashboard.history.availability_history` |
| `provider_list(conn, status=None)` | `core.providers.list_providers` |

All delegations target public functions verified present in the live
repository (Phase 1-4). The adapter performs no writes, records no events and
writes no provenance.

---

## 5. Decision-logic boundary

Explicit guarantee - connectors and the adapter contain NO decision logic:

* `provider_status` - delegates to `dashboard.engine.provider_view` and
  `monitoring.availability.list_availability` (status/intelligence already
  maintained by Phases 2/4).
* `model_scores` - delegates to `dashboard.engine.score_view`
  (`scoring.list_scores` semantics).
* `recommend_top` - delegates to `recommendation.recommend`.
* `fallback_chain` - delegates to `fallback.build_chain`.
* history/report tools - delegate to `dashboard.history` and
  `dashboard.reports.REPORT_BUILDERS`.

No scoring formula, recommendation ranking, fallback policy, or provider
lifecycle logic is implemented inside connectors. Enforced by module
boundary (connectors only import the adapter + CLI) and by tests asserting no
write and identical output to direct engine calls.

---

## 6. Security / mutation boundaries

Phase 5 acceptance criteria guarantee (mirroring Phase 4 D-5, plus
Constitution Articles 1, 5, 6):

1. Performs no writes to AI-Hub data (no INSERT/UPDATE/DELETE).
2. Does not modify VS Code settings.
3. Does not modify config files (`config.toml`, `templates/config.toml`).
4. Does not create or store API keys or credentials.
5. Does not modify environment variables.
6. Makes no real network calls (stdio transport; local CLI invocation).
7. Does not install extensions or packages automatically.

---

## 7. VS Code connector scope

* **Commands** (from `package.json` `contributes.commands`):
  `ai-hub.status`, `ai-hub.dashboardReport`, `ai-hub.scoreHistory`,
  `ai-hub.availabilityHistory`.
* **Views:** Tree data provider listing available reports; `WebviewPanel`
  rendering a selected report in monospace (tab-separated CLI output).
* **Data source:** invokes the AI-Hub CLI
  (`python -m app.main ...`) via the shared adapter entry point or CLI - it
  does not open SQLite directly.
* **Error handling:** non-zero CLI exit codes / empty output surface as
  error notifications; empty results show a "no data" notice (never
  fabricated, Article 10).
* Strictly presentation/integration logic; no AI-Hub decision logic.

---

## 8. Milestones

| # | Milestone | Deliverable | Gate |
|---|-----------|-------------|------|
| 1 | Doc-before-code | v1.2 Section 19, this spec, CHANGELOG, PROJECT-STATUS, handover | Owner approval |
| 2 | Shared adapter + MCP server | `connectors/adapter.py`, `connectors/mcp/` tools, stdio transport | Tests pass |
| 3 | VS Code extension | commands, Tree/Webview views of dashboard reports | Tests pass |
| 4 | Full regression | 216 + new connector tests green | Release baseline |
| 5 | Release package | PHASE5 manifest + closure + owner approval | Owner approval |

---

## 9. Test acceptance criteria

Concrete, replacing vague "tests pass":

1. Valid tool call returns structured text result for every tool.
2. `tools/list` returns the exact tool set with deterministic ordering.
3. Malformed JSON request -> `-32700`.
4. Unknown tool in `tools/call` -> `-32602`.
5. Missing/type-invalid parameters -> `-32602` with message.
6. Identical DB input -> identical tool output across calls (deterministic,
   Article 7).
7. Empty/no-data cases return empty (never fabricated, Article 10).
8. Underlying engine/database failure -> `isError: true` or `-32603`, never a
   crash.
9. Read-only: DB rows unchanged after every tool call.
10. No-network: tests run offline; no socket/urllib/http calls issued.
11. Adapter output identical to direct engine calls (no re-implementation).
12. Regression: full existing 216 tests still pass.

---

## 10. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| MCP spec drift / client era confusion | Medium | Pin legacy era set; document modern era as out of scope; conformance tests |
| VS Code API churn | Medium | Stable long-supported APIs only (commands, Webview, TreeDataProvider) |
| Duplicated SQL in connectors | High | Single adapter; tests assert connector output == engine output |
| Decision logic leaking into connectors | High | Module boundary + no-write tests + delegation map |
| No-network constraint | Low | stdio transport is offline by design |
| Accidental dependency introduction | Medium | requirements.txt unchanged; isolated npm graph (D-4) |

---

## 11. Owner/manual actions

1. Approve this Phase 5 specification milestone (Milestone 1).
2. Approve Milestone 2 (adapter + MCP server) before implementation.
3. Approve Milestone 3 (VS Code extension) before implementation.
4. Owner-run `npm install` inside `connectors/vscode/` for local builds.
5. Approve Phase 5 release + closure at the end.

---

*End of Phase 5 connectors/architecture spec.*