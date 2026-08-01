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

[fallback]
max_chain_length = 5

[recommendation]
default_profile = "coding"

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
