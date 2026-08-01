# ADR-0002: Project-Aware Agent Logging Architecture

**Status:** ACCEPTED

**Date:** 2026-07-31

**Author:** Phase 1 Release Engineer

**Amendments:** applied from `ARCHITECTURE-REVIEW-REPORT.md` findings
R-02, R-03, R-05, R-07, R-08 (see `docs/review/amendment-summary-R01-R08.md`)

**Acceptance date:** 2026-07-31

**Acceptance note:** Accepted following the final constitutional architecture
review (`ARCHITECTURE-FINAL-REVIEW.md` - verdict PASS, no BLOCKERs).

**Supersedes:** the generic `handover/AGENT-LOG.md` template (not part of the
original specifications)

**Related documents:**

* `spec/agent-logging.md` (PROPOSED)
* `decisions/0003-project-registry-and-discovery.md` (ACCEPTED) - project
  identity source

---

## Context

AI-Hub manages work across multiple independent projects: AI-Hub itself,
MediCab, CMMS, and future projects. The repository contains
`handover/AGENT-LOG.md`, a generic chronological template:

```
Date:
Agent:
Task:
Result:
Problems:
```

This template is not project-aware. AI-Hub requires a logging system that:

* supports an unlimited number of projects
* never mixes sessions from different projects
* identifies every entry's project unambiguously
* scales to years of development
* is machine-analyzable by future AI-Hub modules (agent performance, project
  history, recurring problems, task completion statistics)
* preserves repository independence (Constitution Article 3)
* preserves history and supports archival, never silent deletion
  (Constitution Article 5)

Project identity must be authoritative. It comes from the Project Registry
(ADR-0003), never inferred at write time.

## Problem

A single chronological Markdown log mixes unrelated projects and is
difficult to analyze at scale. Analysis requirements demand structure.
The existing template provides none.

## Options Considered

### Option A - One global Markdown log

Pro: trivial to write.

Con: mixes projects; free-form text is not analyzable; one file grows
without bound; conflicts under concurrent agents. Rejected.

### Option B - One Markdown log per project

Pro: separates projects.

Con: a single rolling file does not scale to years; does not separate
sessions; Markdown is not machine-analyzable without fragile parsing.
Rejected.

### Option C - One log per session (Markdown files)

Pro: matches the existing `SESSION-SUMMARY.md` mental model.

Con: no project separation without additional structure; Markdown remains
hard to analyze. Partial.

### Option D - Hybrid: registry-backed namespaces + JSONL per session + derived Markdown (recommended)

Pro:

* project separation by namespace **and** by explicit field on every entry
  (defense in depth)
* project identity is authoritative via the Project Registry (ADR-0003)
* append-only JSON Lines scale to years, support incremental writes, are
  language-agnostic and greppable
* structured fields enable statistical analysis without redesign
  (Constitution Article 9)
* Markdown summaries are derived views - regenerable, never the source of
  truth
* configurable `log_root` preserves repository independence
* schema-versioned entries allow evolution without breaking history
* immutable per-session `session_uuid` enables stable cross-referencing
  (parent/child sessions, analysis)

Con: requires a small tooling layer in a future phase; more ceremony than a
single log file.

## Decision

Adopt **Option D** as specified in `spec/agent-logging.md`:

* logical namespaces per registered project (physical layout is an
  implementation detail; default is a directory tree under `log_root`)
* one `<session_id>.jsonl` file per session (append-only, schema-versioned)
* every session carries a human-readable `session_id` **and** an immutable
  `session_uuid`
* agent metadata is a structured object (`name`, `provider`, `model`,
  `version`, `role`)
* outcomes include `SUCCESS`, `PARTIAL`, `FAILED`, `BLOCKED`,
  `INTERRUPTED`, `HANDOFF`, `WAITING_USER`
* optional `parent_session_id`/`parent_session_uuid`, `git_branch`,
  `git_commit_start`, `git_commit_end` on session entries
* traceability chain `Project -> Milestone -> Task -> Session -> Event`
  documented in the spec
* one derived `<session_id>.summary.md` per session
* project identity is registry-backed (ADR-0003)
* unregistered sessions are REJECTED (R-08) - logging fails until the
  project is registered
* `project_id` is immutable (R-07) - renames create a new id, never rename
  history
* UUID v4 randomness is a documented exception (R-02): it is limited to
  unique session identity generation and has no influence on decisions,
  recommendations, ranking, or automation (Constitution Article 7)

Granularity recommendation: **hybrid - one logical namespace per project,
one file per session.** This is the only option that satisfies project
separation, unbounded growth, and analyzability simultaneously.

## Consequences

* Positive: multi-project work is never mixed; every entry self-identifies
  its project and session.
* Positive: future analysis modules consume the `.jsonl` store directly.
* Positive: repository independence preserved via configurable `log_root`.
* Positive: immutable `session_uuid` makes logs robust to renames and
  supports task trees.
* Positive: history is preserved indefinitely; archival is explicit.
* Positive: architecture review amendments (R-02, R-03, R-05, R-07, R-08)
  resolved the identified contradictions and safety gaps without changing
  the core decision.
* Negative: `handover/AGENT-LOG.md` (superseded) is removed once accepted.
* Negative: a small tooling layer is required (Phase 2 tooling).
* Follow-up: add `log_root`, `[workspace] root`, and `[registry] path` to
  the configuration specification (v1.2 Section 10); reflect `logs/` and
  `projects/` in `START-HERE.md`.

## Acceptance Criteria

This ADR is accepted when:

* the owner approves the hybrid JSONL + derived Markdown design
* ADR-0003 (Project Registry and Discovery) is accepted as its identity
  source
* configuration values are added to the configuration specification
* the superseded `handover/AGENT-LOG.md` is removed
* `spec/agent-logging.md` is referenced from `START-HERE.md`
