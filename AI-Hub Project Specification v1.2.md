# AI-Hub Project Specification v1.2

## Implementation Specification Addendum

**Status:** Approved

**Supersedes:** v1.1 (Implementation Details Only)

**Purpose**

This document supplements the Architecture Specification v1.1.

It does **not** redefine the architecture.

It specifies implementation behavior required to ensure deterministic, reproducible and explainable operation.

---

# 1. Scoring Framework

## 1.1 Philosophy

AI-Hub never produces a single "magic score."

Recommendations are built from multiple independent dimensions.

Each score must remain visible and explainable.

---

## 1.2 Score Categories

Every model maintains independent scores.

Scores are stored in the normalized `scores` table (ADR-0001, accepted
2026-08-01): one row per (model, dimension). The v1.1 scalar score columns on
the `models` table are superseded and retained for backward compatibility
only.

### Capability

* Coding
* Reasoning
* Mathematics
* Long-context handling
* Vision
* Tool Calling

---

### Operational

* Availability
* Reliability
* Latency
* Cost
* Stability

---

### Confidence

Every score records:

* value
* confidence
* timestamp
* source

These map to the `scores` columns `value`, `confidence`, `scored_at` and
`source`.

---

## 1.3 Score Sources

Allowed sources:

MANUAL

BENCHMARK

AUTOMATED_TEST

USER_FEEDBACK

OFFICIAL_INFORMATION

Every score must indicate its origin.

---

# 2. Recommendation Profiles

Recommendations are generated using profiles.

## Default Coding Profile

Coding

40%

Reasoning

20%

Reliability

20%

Availability

15%

Latency

5%

Cost

0%

---

## Reasoning Profile

Reasoning

45%

Coding

20%

Reliability

15%

Availability

10%

Latency

5%

Cost

5%

---

## Free Tier Profile

Cost

40%

Availability

20%

Coding

20%

Reasoning

10%

Latency

10%

---

## Long Context Profile

Context Window

40%

Reasoning

20%

Coding

20%

Reliability

10%

Availability

10%

---

Users may define custom profiles.

---

# 3. Recommendation Formula

Each dimension produces a normalized score between 0 and 100.

The final recommendation score is:

Final Score

=

Σ

(Profile Weight × Dimension Score)

Only dimensions defined by the selected profile participate.

No hidden weighting is permitted.

---

### Implementation (Phase 3)

Scores are stored in the normalized `scores` table (ADR-0001). Operational
dimensions (availability, reliability, latency) are derived at read time from
monitoring outputs (`scoring/derive.py`); the `context_window` dimension is
derived from the `models` table. Aging multipliers from Section 4 apply to
stored-score confidence. Missing dimensions contribute 0 and are flagged
"insufficient data" - they are never fabricated (Constitution Article 10).

---

# 4. Score Aging

Scores become less trustworthy over time.

Fresh

0–30 days

Confidence

100%

---

Aging

31–90 days

Confidence

90%

---

Old

91–180 days

Confidence

75%

---

Stale

More than 180 days

Confidence

50%

Recommendation remains possible, but AI-Hub should request refreshed information whenever practical.

---

# 5. Provider Lifecycle

Provider states:

NEW

↓

EVALUATING

↓

ACTIVE

↓

LIMITED

↓

DEGRADED

↓

OFFLINE

↓

ARCHIVED

---

## Transition Rules

NEW → EVALUATING

Provider manually added.

---

EVALUATING → ACTIVE

Validation successful.

---

ACTIVE → LIMITED

Quota exhausted.

Rate limit exceeded.

Temporary restrictions.

---

LIMITED → ACTIVE

Quota reset detected.

---

ACTIVE → DEGRADED

Repeated failures.

High latency.

Partial functionality.

---

DEGRADED → OFFLINE

Repeated monitoring failures beyond configured threshold.

---

OFFLINE → ACTIVE

Successful recovery.

---

OFFLINE → ARCHIVED

Only when:

* provider officially retired
* administrator archives provider
* documented archival policy applies

Automatic archival requires explicit confirmation.

Providers are never deleted automatically.

---

# 6. Availability States

Each provider exposes one state.

ACTIVE

LIMITED

DEGRADED

OFFLINE

ARCHIVED

Reason field is mandatory whenever state is not ACTIVE.

---

# 7. Fallback Algorithm

## Step 1

Detect task category.

Examples:

* Flutter
* Python
* SQL
* Architecture
* Documentation

---

## Step 2

Remove incompatible models.

Examples:

* insufficient context
* unavailable
* missing required capabilities

---

## Step 3

Apply recommendation profile.

---

## Step 4

Sort by:

Final Recommendation Score

↓

Availability

↓

Reliability

↓

Lower Cost

↓

Lower Latency

↓

Alphabetical Order

This guarantees deterministic ordering.

---

## Step 5

Generate chain.

Maximum chain length:

Primary Recommendation

*

Five fallback providers

---

### Implementation (Phase 3)

Eligibility derives from monitoring outputs: ACTIVE/LIMITED preferred,
DEGRADED last resort (flagged), OFFLINE/ARCHIVED/NEW/EVALUATING excluded.
On a failure signal the next eligible provider in the chain is selected
(`FALLBACK_TRIGGERED`); recovery to the primary is detected when it returns
to ACTIVE/LIMITED (`FALLBACK_RECOVERED`). Fallback never probes providers and
never modifies the provider lifecycle (Section 9).

---

# 8. Decision Provenance

Every recommendation is reproducible.

Recommendation records include:

Recommendation ID

Timestamp

Task

Selected Profile

Selected Model

Score Breakdown

Decision Version

Explanation

Confidence

This enables auditing and comparison across AI-Hub versions.

---

### Implementation (Phase 3)

Every top recommendation is recorded in the `recommendations` table with a
UUID id, decision version (`recommendation.decision_version`, default
`3.0.0`), score breakdown (JSON), explanation and confidence, plus an
append-only `RECOMMENDATION_CREATED` event. The UUID identifies the record;
recommendation *content* remains deterministic (Constitution Article 7).

---

# 9. Monitoring Rules

Monitoring never modifies provider information directly.

Automatic discoveries enter:

PENDING_REVIEW

Only approved discoveries become ACTIVE records.

---

# 10. Configuration Specification

AI-Hub configuration is stored separately from project configuration.

Example:

```toml
[database]
path = "database/ai_hub.db"

[monitoring]
enabled = true
interval_minutes = 60
timeout_seconds = 10
failure_threshold = 3
latency_threshold_ms = 10000

[scoring]
aging_fresh_days = 30
aging_aging_days = 90
aging_old_days = 180
derive_operational = true

[fallback]
max_chain_length = 5

[recommendation]
default_profile = "coding"
decision_version = "3.0.0"

[dashboard]
refresh_seconds = 60

[logging]
level = "INFO"
log_root = "logs"

[workspace]
root = "M:\\dev"

[registry]
path = "projects/registry.json"
```

Monitoring keys (Phase 2):

* `monitoring.enabled` - enable/disable monitoring (boolean, default `true`).
* `monitoring.interval_minutes` - monitoring frequency (positive integer,
  default `60`).
* `monitoring.timeout_seconds` - per-check HTTP timeout (positive integer,
  default `10`).
* `monitoring.failure_threshold` - consecutive check failures that mark a
  provider DEGRADED; a further full run of failures while DEGRADED marks it
  OFFLINE (integer >= 1, default `3`).
* `monitoring.latency_threshold_ms` - response time above this is treated as
  high latency and counts as a failure signal (positive integer, default
  `10000`).

Thresholds are global configuration values; per-provider overrides are not
supported.

Scoring keys (Phase 3):

* `scoring.aging_fresh_days` - days before a score ages (confidence
  multiplier 1.00; positive integer, default `30`).
* `scoring.aging_aging_days` - days before a score becomes old (multiplier
  0.90; positive integer, default `90`).
* `scoring.aging_old_days` - days before a score becomes stale (multiplier
  0.75; positive integer, default `180`; stale scores use 0.50). Boundaries
  must be strictly increasing.
* `scoring.derive_operational` - derive operational dimensions from monitoring
  at read time (boolean, default `true`).
* `recommendation.decision_version` - version of the recommendation decision
  logic, recorded in provenance (non-empty string, default `3.0.0`).

Configuration belongs exclusively to AI-Hub.

Configuration paths (`database.path`, `log_root`, `workspace.root`,
`registry.path`) are machine-specific metadata: they are local examples only
and are never used as project identity. `project_id` from the Project
Registry is the only portable identity key.

---

# 11. Credential Policy

AI-Hub may detect credentials.

It never stores raw secrets.

Metadata only.

Example:

credential_available = true

credential_location = "environment"

Supported locations:

* Environment Variables
* Windows Credential Manager
* User-defined Secret Provider

---

# 12. Event Retention

Events are never silently discarded.

Lifecycle:

Active Database

↓

Archive

↓

Optional Manual Deletion

Default archival period:

12 months

Permanent deletion requires explicit user action.

---

# 13. Testing Strategy

## Unit Tests

* scoring engine
* lifecycle transitions
* fallback ordering
* configuration parser

---

## Integration Tests

* provider monitoring
* database operations
* dashboard data generation

---

## Acceptance Tests

Example:

Given

Gemini quota exhausted

When

Recommendation requested

Then

Gemini enters LIMITED state

And

Fallback begins with the highest-ranked ACTIVE provider

---

# 14. Documentation Rules

Every implementation change affecting behavior must update:

* Specifications
* ADRs
* Session Summary

Implementation must never become the authoritative source of project behavior.

---

# 15. Phase Roadmap Update

Phase 0

Documentation

Architecture

Specifications

---

Phase 1

Repository Skeleton

SQLite Schema

Provider Registry

Configuration System

---

Phase 2

Monitoring Engine

Provider Health

Availability

Quota Tracking

---

Phase 3

Scoring Engine

Recommendation Engine

Fallback Engine

Decision Provenance

---

Phase 4

Dashboard

Reporting

History

---

Phase 5

VS Code Connector

MCP Connector

Editor Integration

---

Phase 6

AI Ecosystem Intelligence

Automatic Discovery

Benchmark Integration

Trend Analysis

---

# 16. Definition of Ready

Implementation may begin only when:

* Architecture Specification (v1.1) is approved.
* Implementation Specification (v1.2) is approved.
* ADR structure exists.
* Configuration specification exists.
* Database schema is documented.
* Agent handover documents are present.

---

# 17. Definition of Done

AI-Hub v1.0 is complete when:

* All specifications are implemented.
* Recommendation decisions are reproducible.
* Every recommendation is explainable.
* Provider lifecycle is deterministic.
* Monitoring is non-destructive.
* Fallback chains are deterministic.
* Historical information is preserved.
* All architectural decisions are documented.
* Another contributor can continue development using only the repository documentation.

---

# 18. Dashboard / Reporting / History (Phase 4)

## 18.1 Dashboard

The dashboard is a read-only aggregation layer.

It provides visibility over:

* providers (status)
* models
* scores
* availability
* recommendations
* events

It never mutates providers, models, scores, availability, preferences or
events (Constitution Article 1).

Views are deterministic and self-describing. Empty inputs produce empty (not
fabricated) results (Constitution Article 10).

### Implementation (Phase 4)

`dashboard/engine.py` provides read-only views: overview, provider_view,
score_view, recommendation_view and event_view. Counts/sums are exact; no
hidden aggregation weights (Constitution Article 4). Ordering is explicit on
every query (Constitution Article 7).

## 18.2 Reporting

Reports are deterministic, plain-text/tab-separated summaries for humans and
future connectors. No GUI in Phase 4.

### Implementation (Phase 4)

`dashboard/reports.py` exposes one builder per report: report_providers,
report_scores, report_recommendations, report_monitoring and report_overview.
A generated-at timestamp is optional and injected by the caller so tests pass
a fixed value, preserving deterministic output.

## 18.3 History

History is read-only reconstruction from the append-only events table
(Constitution Article 5; Section 8). It never rewrites or deletes events and
never fabricates missing data (Constitution Article 10).

### Implementation (Phase 4)

Score history is reconstructed from `SCORE_RECORDED` / `SCORE_UPDATED` events;
availability history from `MONITOR_STATUS_CHANGED` and `HEALTH_CHECK_*`
events (`dashboard/history.py`). Point-in-time snapshots are deferred and
require ADR-0004 before any schema change.

---

# 19. Connectors (Phase 5)

## 19.1 Philosophy

Connectors are external-facing, read-only access points to AI-Hub
intelligence. They consume AI-Hub data and decision output through the CLI or
the shared adapter; they NEVER contain decision logic (Constitution Articles
1, 2, 4). No scoring, recommendation, fallback, ranking or policy logic is
implemented inside any connector.

Phase 5 delivers two connectors:

* `connectors/mcp/` - a Model Context Protocol (MCP) server.
* `connectors/vscode/` - a VS Code extension (presentation/integration only).

## 19.2 MCP Connector

### 19.2.1 Bounded MCP compatibility

The MCP connector implements a **deliberately bounded subset** of the Model
Context Protocol. It targets the **legacy protocol era** (handshake-based
`initialize`, revisions `2024-10-07` through `2025-11-25`). It is NOT a full
implementation of the modern-era revision `2026-07-28` (see 19.2.5).

Supported protocol versions (negotiated at initialization):

* `2025-11-25` (primary target)
* `2025-06-18`
* `2025-03-26`
* `2024-11-05`

Version negotiation follows the standard `initialize` handshake: the server
echoes a requested version it supports, otherwise it responds with the
highest version it supports. The server identifies itself with `serverInfo`
(`name = "ai-hub", version = "<release>"`) and declares `capabilities =
{"tools": {}}`. MCP clients in legacy mode or `auto` probe mode connect
without error: over stdio a server that does not answer `server/discover`
is treated as a legacy server and the client falls back to `initialize`.

### 19.2.2 Transport

stdio only. JSON-RPC 2.0 messages on stdin/stdout (newline-delimited),
one message per line, UTF-8. No HTTP, no SSE, no streamable transport, no
`Mcp-Session-Id`, no TLS. The server is offline-capable by design.

### 19.2.3 Supported primitives

Tools capability only:

* `initialize` / `notifications/initialized` (handshake)
* `ping`
* `tools/list` - static tool discovery (no `listChanged` notifications)
* `tools/call` - single tool invocation

NOT supported: resources, prompts, sampling, roots, logging notification
opt-in, `server/discover`, JSON-RPC batches, progress notifications.

### 19.2.4 Tool discovery and semantics

* Tool discovery: `tools/list` returns the full fixed tool set with
  `name`, `description` and `inputSchema` (JSON Schema `type: "object"`).
  Ordering is deterministic (alphabetical by tool name).
* Tools (read-only, delegating to existing engines):

| Tool | Delegates to | Returns |
|------|--------------|---------|
| `provider_status` | `dashboard.engine.provider_view` + `monitoring.availability.list_availability` | Per-provider status, availability, failures |
| `model_scores` | `dashboard.engine.score_view` (i.e. `scoring.list_scores`) | Current per-dimension scores |
| `recommend_top` | `recommendation.recommend` | Ranked recommendations (ranking, confidence, flags); does NOT record provenance |
| `fallback_chain` | `fallback.build_chain` | Deterministic fallback chain |
| `dashboard_report` | `dashboard.reports.REPORT_BUILDERS` | Selected plain-text report |
| `score_history` | `dashboard.history.score_history` | Event-derived score series |
| `availability_history` | `dashboard.history.availability_history` | Event-derived availability series |
| `provider_list` | `core.providers.list_providers` | Provider registry rows |

* Request/response: valid request to a known tool returns `result` with
  `content` as a single `{type: "text", text: ...}` item. `isError` on the
  result is used for tool-level failures (missing data, engine errors).
* Errors use JSON-RPC codes: `-32700` parse error, `-32600` invalid request,
  `-32601` method not found, `-32602` invalid params / unknown tool,
  `-32603` internal error.

### 19.2.5 Explicit non-goal

The MCP connector targets the handshake-based legacy generation
(`2025-11-25` and earlier), which is fully expressible on stdio with the
standard library. The stateless modern-era revision `2026-07-28` (which
retires the `initialize`/`initialized` handshake in favour of per-request
`_meta` versioning and `server/discover`) is explicitly out of scope. If a
client requires `2026-07-28` with handshake disabled, the connector responds
as a legacy server (clients in `auto` mode fall back to `initialize`); a
client pinned exclusively to `2026-07-28` receives the equivalent of
`UnsupportedProtocolVersionError`. This bounded subset is the approved D-1
decision: stdlib-only implementation, no MCP SDK dependency.

## 19.3 VS Code Connector

### 19.3.1 Scope

A VS Code extension providing read-only views of AI-Hub dashboard reports.
It is strictly presentation/integration logic: it contains no AI-Hub decision
logic and performs no writes to AI-Hub data or to the VS Code configuration.

### 19.3.2 Data source

The extension invokes the AI-Hub CLI (`python -m app.main ...`) with the
user-configured AI-Hub workspace/DB path, and renders the resulting plain-text
reports. It does not read SQL, does not open the database, and does not run
engine queries itself.

### 19.3.3 Commands and views

* Commands (`ai-hub.status`, `ai-hub.dashboardReport`, `ai-hub.scoreHistory`,
  `ai-hub.availabilityHistory`), registered via `package.json`
  `contributes.commands`.
* Views: a Tree Data Provider for the report list and a `WebviewPanel` for a
  selected report (monospace, tab-separated as produced by the CLI).
* Error handling: CLI failures and non-zero exit codes are surfaced as error
  notifications; empty reports are shown with a "no data" notice (never
  fabricated).

### 19.3.4 Isolation from core dependency policy

The extension lives under `connectors/vscode/` as an isolated Node.js /
TypeScript workspace with its OWN `package.json` (devDependencies:
`typescript`, `@types/vscode`, `@vscode/test-cli`), `tsconfig.json` and
`src/`. It is:

* NOT part of the Python runtime: `requirements.txt` is unchanged; no Python
  module imports it; the Python project does not depend on any npm package.
* Isolated from the core AI-Hub dependency policy: the "no new dependencies"
  rule governs the Python runtime (`requirements.txt`); the extension's npm
  graph is fully contained within `connectors/vscode/`.
* Never executed or activated by AI-Hub core code.

The extension is built locally by the owner (or a future CI) with `npm
install` inside `connectors/vscode/`; the built artifact is not committed, and
`connectors/vscode/node_modules/` is git-ignored.

## 19.4 Shared read-only adapter

A single adapter module (`connectors/adapter.py` - planned, Phase 5
implementation) is the ONLY channel through which both connectors read AI-Hub
data. It is a stable application interface that delegates to existing engines
and NEVER issues its own SQL or reaches into database internals.

Delegation map (all read-only):

| Adapter function | Delegates to |
|------------------|--------------|
| `provider_status(conn)` | `dashboard.engine.provider_view` |
| `model_scores(conn, model_id=None)` | `dashboard.engine.score_view` |
| `recommend_top(conn, task, profile=..., limit=...)` | `recommendation.recommend` |
| `fallback_chain(conn, task, profile=..., max_chain_length=...)` | `fallback.build_chain` |
| `dashboard_report(conn, name, ...)` | `dashboard.reports.REPORT_BUILDERS` |
| `score_history(conn, model_id, dimension=None)` | `dashboard.history.score_history` |
| `availability_history(conn, provider_id=None)` | `dashboard.history.availability_history` |
| `provider_list(conn, status=None)` | `core.providers.list_providers` |

The adapter receives an already-open read-only SQLite connection and returns
plain dict/list structures. It performs no writes (Constitution Article 1),
no events, no provenance recording, no config reads and no network access.

## 19.5 Security and mutation boundaries

Phase 5 guarantees (mirroring Phase 4 D-5, enforced by tests):

* No writes to AI-Hub data (no INSERT/UPDATE/DELETE anywhere in connectors).
* No modification of VS Code settings or config files.
* No creation or storage of API keys or credentials (Constitution Article 6).
* No modification of environment variables.
* No real network calls (stdio transport, local CLI invocation).
* No automatic installation of extensions or packages.

## 19.6 Configuration, events and dependencies

* No new configuration keys. The MCP server and VS Code extension reuse the
  existing AI-Hub DB path resolution (`app.config.load_config` + CLI) and do
  not introduce TOML keys.
* No new event types; connectors never record events.
* No new Python dependencies (stdlib + sqlite3 + pytest only). The VS Code
  extension's npm devDependencies are isolated to `connectors/vscode/`
  (19.3.4).

### Implementation (Phase 5)

The Phase 5 implementation lives in `connectors/mcp/` and `connectors/vscode/`
with the shared adapter at `connectors/adapter.py`. All Phase 5 modules are
read-only; connector behaviour is verified by `tests/test_connectors_*`.
See `docs/review/PHASE5-CONNECTORS-SPEC.md` and the approved Phase 5 plan.
