# PHASE5-RELEASE-MANIFEST.md

# AI-Hub Phase 5 Release Manifest

**Project name:** AI-Hub

**Release name:** Phase 5 - Connectors (VS Code / MCP)

**Phase number:** Phase 5 (of 6)

**Release date:** 2026-08-18

**Git commit SHA:** `8231dcecf1f5968fee007967e40452bbe7fe63eb`

**Phase 4 baseline:** `c49ea9b37bebf07b34a5acef8046b483614dee69` (immutable)

**Current branch:** `main`

**Status:** APPROVED (owner review complete; closure accepted 2026-08-18)

> This document is the immutable reference baseline for subsequent phases. It
> records the state at release. Later project evolution must not rewrite it.

---

## Phase 5 deliverables

| Module | Purpose |
|--------|---------|
| `connectors/adapter.py` | Single, stable read-only application interface. Delegates to existing Phase 1-4 engines only; executes no SQL, performs no writes, contains no decision logic. |
| `connectors/mcp/` | Bounded stdio MCP subset: legacy protocol era (`2024-10-07`..`2025-11-25`), Tools capability only, stdlib only (D-1). `server.py` (protocol/error dispatch) + `tools.py` (7 fixed tools, deterministic ordering). No HTTP/SSE, no modern era. |
| `connectors/vscode/` | Read-only VS Code extension: 7 commands, activity-bar reports tree + webview panels rendering CLI stdout verbatim. Isolated npm graph (D-4); never opens SQLite; never mutates settings/config/environment; no network; no API-key handling. |
| Tests | 48 Phase 5 Python tests (adapter 19, MCP 29), 28 offline TS unit tests, 2 real VS Code integration tests |

## Config additions

None. `app/config.py`, `config.toml` and `templates/config.toml` unchanged.
The extension reads two local VS Code settings (`ai-hub.pythonPath`,
`ai-hub.workingDirectory`) and never writes them.

## Event vocabulary additions

None. Connectors never record events and never write provenance.
`recommend_top` calls `recommendation.recommend` only (read-only ranking).

## Test summary

Command: `python -m pytest -q` (run 2026-08-18)

| Metric | Value |
|--------|-------|
| Tests collected | 264 |
| Passed | 264 |
| Failed | 0 |
| New in Phase 5 | 48 (adapter 19, MCP 29; incl. 2 M5 hardening tests) |

Additional runs (2026-08-18):

* Phase 5 subset `test_connectors_adapter.py test_connectors_mcp.py`: 48/48
  passed (37.27s).
* VS Code offline unit (`npm run test:unit`): 28/28 passed.
* VS Code real integration (`npm test`, @vscode/test-cli): 2/2 passed
  (837ms), exit 0.

All tests run offline with in-memory/injected SQLite fixtures and data.

## Environment

* Python 3.14.2, pytest 9.1.1, Windows (win32)
* Node v24.13.0 / npm 11.6.2 (isolated `connectors/vscode/` workspace only;
  owner-run `npm install`, git-ignored `node_modules/`, `out/`, `out-test/`,
  `.vscode-test/`)

---

## Scope boundaries (confirmed)

* Read-only - connectors and the adapter never mutate AI-Hub data: no
  INSERT/UPDATE/DELETE anywhere (Constitution Article 1); MCP CLI enforces
  `PRAGMA query_only = ON` on the served connection.
* Deterministic - identical DB input -> identical tool/report output
  (Article 7); explicit ordering; no hidden weighting.
* No fabricated data - empty/no-data cases return empty results or header-only
  reports; the extension shows a "(no data)" notice (Article 10).
* No decision logic - no scoring, recommendation ranking, fallback policy or
  provider lifecycle logic inside connectors (spec sections 4-5); enforced by
  the module boundary (adapter + CLI only) and no-write / delegation-identity
  tests.
* No network - stdio transport + local CLI invocation; no socket/urllib/http
  in connectors (no-network guard tested).
* No API keys / credentials / environment / VS Code settings / config file
  mutation (Article 6).
* No new Python dependencies - stdlib + sqlite3 + pytest only (D-1);
  `requirements.txt` unchanged. Isolated npm graph (D-4).
* MCP modern era `2026-07-28` explicitly out of scope (D-1 bounded subset).

## Determinism and provenance

* Fixed seven-tool set with deterministic alphabetical `tools/list` ordering;
  `recommend_top` never records provenance and never writes events.
* Tool-level failures return `isError: true`; protocol/validation failures map
  to JSON-RPC `-32700` / `-32600` / `-32601` / `-32602`; internal dispatch
  exceptions map to `-32603` (all tested).
* Empty query results produce empty (not fabricated) structures.

---

## Checksums (SHA-256, prefix 16)

| File | SHA-256 (prefix 16) |
|------|---------------------|
| `connectors/__init__.py` | `909606698401994E` |
| `connectors/adapter.py` | `4C30002B57B549D8` |
| `connectors/mcp/__init__.py` | `F64CC80189E6FB23` |
| `connectors/mcp/server.py` | `E246B6F6CDD20B97` |
| `connectors/mcp/tools.py` | `FB9EE5B0B244BC94` |
| `connectors/vscode/package.json` | `CEF27CBF9041A0C7` |
| `connectors/vscode/.vscode-test.mjs` | `E1B28F4198063202` |
| `connectors/vscode/src/cli.ts` | `2476FD38EF41F2AB` |
| `connectors/vscode/src/extension.ts` | `A062B94054A6F9C9` |
| `connectors/vscode/src/extensionCore.ts` | `1D456F921D6FE907` |
| `connectors/vscode/src/features.ts` | `DF6D8C6803FB9D7C` |
| `connectors/vscode/src/present.ts` | `2C3E6E368254AC83` |

---

*End of Phase 5 Release Manifest. Approved 2026-08-18.*