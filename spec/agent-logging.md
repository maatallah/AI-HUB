# spec/agent-logging.md

# AI-Hub Agent Logging System Specification

**Status:** PROPOSED (revision 3 - amended per architecture review,
findings R-02, R-03, R-05, R-07, R-08)

**Date:** 2026-07-31

**Author:** Phase 1 Release Engineer

**Amendments:** applied from `ARCHITECTURE-REVIEW-REPORT.md` (see
`docs/review/amendment-summary-R01-R08.md`)

**Related ADRs:**

* `decisions/0002-agent-logging-architecture.md` (ACCEPTED)
* `decisions/0003-project-registry-and-discovery.md` (ACCEPTED)

**Dependencies:** `spec/project-registry.md` - project identity comes from
the Project Registry, never inferred at write time.

**Scope:** This is an implementation contract for project-aware, analyzable
logging of agent work across all projects AI-Hub manages. It supersedes the
generic `handover/AGENT-LOG.md` template, which was not part of the original
specifications.

---

# 1. Problem

AI-Hub manages work across multiple independent projects (AI-Hub itself,
MediCab, CMMS, future projects). A single chronological log mixes unrelated
work and prevents historical analysis. The existing `handover/AGENT-LOG.md`
template is a flat per-session form with no project identity.

This specification defines a logging system that:

* supports an unlimited number of projects
* never mixes sessions from different projects
* identifies every entry's project unambiguously
* scales to years of development
* is machine-analyzable (agent performance, project history, recurring
  problems, task completion statistics)
* preserves repository independence (Constitution Article 3)
* preserves history (Constitution Article 5)
* remains deterministic and truthful (Constitution Articles 7 and 10)

---

# 2. Design Decision Summary

The logging system is a **hybrid** of a structured store and derived
human-readable views:

| Layer | Format | Role |
|-------|--------|------|
| Store (source of truth) | JSON Lines (`.jsonl`), one object per entry | Machine-analyzable, append-only, scalable |
| Human view (derived) | Markdown (`.summary.md`) per session | Readable; regenerable from the store |
| Project identity | `project_id` from the Project Registry (`projects/registry.json`) | Authoritative project identity |

Granularity recommendation: **hybrid - one logical namespace per project,
one file per session.** Justification in ADR-0002.

---

# 3. Project Identity and the Project Registry

Project identity is **authoritative and external** to the log.

* Every log entry's `project_id` MUST be a project registered in
  `projects/registry.json` (see `spec/project-registry.md`).
* A log entry MUST never invent a `project_id` at write time. Unregistered
  sessions are **REJECTED** (R-08): logging fails until the project is
  registered. Work is never silently assigned to a project.
* `project_id` is **immutable** (R-07): renaming a project does not rename
  history; a rename creates a new `project_id` and archives the old one.
* The registry stores the canonical `name` and `path`; entries copy them as
  of-when-written metadata for immutable history. Paths are metadata only;
  `project_id` is the only portable identity key.

This removes all ambiguity (requirement 3): the registry defines the set of
valid project namespaces.

---

# 4. Logical Storage Model

This specification defines a **logical storage model**, not a fixed physical
layout.

Logical model:

```
namespace = project namespace, keyed by project_id
  one session stream per session
  one project manifest per namespace
```

The default physical mapping is a directory tree under a configurable
`log_root` (Section 5). Implementations MAY map namespaces to different
roots, volumes, or a database backend, provided that:

* namespaces are never mixed
* sessions within a namespace are never interleaved across files
* the schema (Section 7) is preserved

The registry (`projects/registry.json`) is likewise logical; its default
location is `projects/registry.json`, and it may be relocated via
configuration.

---

# 5. Default Directory Structure

```
<log_root>/                      # default "logs/"
  <project_id>/                  # one namespace per registered project
    <YYYY>/
      <session_id>.jsonl         # structured entries for one session
      <session_id>.summary.md    # derived human-readable summary
  archive/
    <project_id>/                # completed / inactive namespaces
```

Example:

```
logs/
  ai-hub/
    2026/
      20260731-152000Z-ai-hub-release-01.jsonl
      20260731-152000Z-ai-hub-release-01.summary.md
  medicab/
    ...
```

Notes:

* The year subdirectory bounds file count as a namespace ages.
* `archive/` holds completed or long-inactive namespaces (Section 11).
* Logs for another project are never written inside that project's
  repository - repository independence is preserved.

---

# 6. Identifiers and Naming Conventions

## project_id

* comes from the Project Registry (Section 3)
* lowercase ASCII, hyphens only (`ai-hub`, `medicab`, `cmms`)
* immutable; a rename creates a new id and archives the old (R-07)

## session_id (human-readable, sortable)

```
<YYYYMMDD-HHMMSSZ>-<project_id>-<agent_name_slug>-<sequence>
```

Example: `20260731-152000Z-ai-hub-release-01`

* `YYYYMMDD-HHMMSSZ` is the UTC session start time.
* `agent_name_slug` is the agent name lowercased, non-alphanumerics replaced
  by `-`.
* `<sequence>` disambiguates same-second starts by the same agent in the
  same project.

## session_uuid (globally unique, immutable)

Every session also carries a UUID v4:

* stored as `session_uuid` on every entry of the session
* immutable once created; never reused
* the stable key for analysis and cross-referencing (e.g. parent/child)
* `session_id` is for human reading and sorting; `session_uuid` is the
  machine identity

**Documented randomness exception (R-02, Constitution Article 7):** the
randomness of UUID v4 is limited to unique session identity generation. It
has no influence on decisions, recommendations, ranking, or automation.
Therefore it does not violate deterministic behaviour.

## File naming

* `<session_id>.jsonl` - structured entries (append-only)
* `<session_id>.summary.md` - derived Markdown summary
* `project.json` - namespace manifest (derived counts; optional)

---

# 7. Log Entry Format

Format: **JSON Lines** (`.jsonl`) - one JSON object per line, UTF-8, `\n`
terminated. Append-only. `schema_version`: `1` (this document). Future
changes add fields (backward compatible) or bump the version with a
documented migration.

## 7.1 Common fields (every entry)

| Field | Type | Description |
|-------|------|-------------|
| `schema_version` | int | `1` |
| `entry_type` | string | `session_start`, `event`, `session_end` |
| `session_uuid` | string | immutable UUID (Section 6) |
| `session_id` | string | human-readable id (Section 6) |
| `timestamp` | string | UTC ISO 8601 with `Z` |
| `project_id` | string | registry project id |
| `project_name` | string | registry name, as-of-write |
| `repo_path` | string | canonical repository path, as-of-write |

## 7.2 session_start (first entry of a file)

| Field | Type | Description |
|-------|------|-------------|
| `agent` | object | see Section 8 |
| `phase` | int \| null | project phase (see Section 9) |
| `milestone` | string \| null | named milestone (see Section 9) |
| `task_id` | string \| null | task identifier (see Section 9) |
| `parent_session_uuid` | string \| null | parent session (sub-session/delegation) |
| `parent_session_id` | string \| null | parent human-readable id |
| `git_branch` | string \| null | branch at session start |
| `git_commit_start` | string \| null | commit hash at session start |
| `objective` | string | one-sentence session objective |

## 7.3 event (zero or more, appended during a session)

| Field | Type | Description |
|-------|------|-------------|
| `event` | string | `file_created`, `file_modified`, `file_removed`, `test_executed`, `spec_updated`, `adr_updated`, `commit`, `note` |
| `detail` | object | path(s), command, commit hash, etc. |
| `result` | string \| null | `ok`, `failed`, or `null` |

Events inherit their session's context; they need not repeat `task_id`,
`milestone`, or `phase`, but MAY for stream-level analysis.

## 7.4 session_end (final entry of a file)

| Field | Type | Description |
|-------|------|-------------|
| `agent` | object | as of session end |
| `git_branch` | string \| null | branch at session end |
| `git_commit_end` | string \| null | commit hash at session end |
| `files_created` | array | relative paths |
| `files_modified` | array | relative paths |
| `files_removed` | array | relative paths |
| `specifications_updated` | array | spec documents touched |
| `adrs_created` | array | ADR paths |
| `adrs_modified` | array | ADR paths |
| `tests_executed` | array | commands run |
| `test_results` | object | `{command, total, passed, failed, skipped}` |
| `outcome` | string | Section 10 |
| `known_issues` | array | unresolved problems observed |
| `tech_debt_introduced` | array | items |
| `tech_debt_resolved` | array | items |
| `recommendations` | array | suggestions |
| `next_suggested_task` | string | feeds `NEXT-STEPS.md` |

Unknown values are stored as `null`, never fabricated (Constitution
Article 10).

**Log security (R-05, Constitution Article 6):** logs must never contain
credentials, tokens, API keys, passwords, private keys, or secrets. Free-form
fields (`event.detail`, `known_issues`, `recommendations`, `notes`, and any
other text) are subject to Article 6. Agents MUST NOT write secrets into any
log field. Future redaction mechanisms MAY be added; they must not be relied
upon as the primary control.

---

# 8. Agent Metadata

`agent` is a structured object:

```json
"agent": {
  "name": "opencode",
  "provider": "deepseek",
  "model": "deepseek-v4-flash-free",
  "version": "2026-07-31",
  "role": "release-engineer"
}
```

| Field | Description |
|-------|-------------|
| `name` | agent tool name (`opencode`) |
| `provider` | model provider (`deepseek`, `openai`, `anthropic`) |
| `model` | model identifier |
| `version` | tool/model version |
| `role` | `implementation`, `release-engineer`, `reviewer`, `researcher` |

---

# 9. Task Traceability

Traceability chain, coarse to fine:

```
Project -> Milestone -> Task -> Session -> Event
```

| Concept | Definition | Where recorded |
|---------|-----------|----------------|
| Project | registry project (Section 3) | every entry (`project_id`) |
| Milestone | named deliverable (`phase-1`, `v1.0`, `release-2`) | `session_start.milestone` |
| Phase | coarse stage (AI-Hub roadmap 0-6, or the project's own phase) | `session_start.phase` |
| Task | discrete work item; stable `task_id` (external tracker id allowed, e.g. `TRK-123`) | `session_start.task_id` |
| Session | one agent working session; at most one `task_id` (null if exploratory) | one `.jsonl` file |
| Event | an action within a session; belongs to exactly one session | `entry_type=event` |

Rules:

* A session belongs to at most one `task_id`. Long work spanning tasks is
  split into separate sessions.
* A task may span multiple sessions; link them by task_id.
* A sub-session (delegated sub-agent) sets `parent_session_uuid` /
  `parent_session_id`, enabling full task trees to be reconstructed.
* Analysis modules aggregate by `project_id`, then `milestone`, then
  `task_id`, then `session_uuid`.

---

# 10. Session Outcomes

`outcome` is one of:

| Outcome | Meaning |
|---------|---------|
| `SUCCESS` | objective fully met |
| `PARTIAL` | some goals met, some not |
| `FAILED` | objective not met / errors |
| `BLOCKED` | cannot proceed due to external dependency |
| `INTERRUPTED` | session ended prematurely (crash, timeout, user) |
| `HANDOFF` | work transferred to another agent/human; `next_suggested_task` expected |
| `WAITING_USER` | paused pending user decision/input |

`INTERRUPTED`, `HANDOFF`, and `WAITING_USER` are not failures; they must not
be counted as failures in analysis.

---

# 11. Retention Policy

* **Active namespaces: permanent.** Nothing is deleted automatically
  (Constitution Article 5).
* **Archival:** a namespace moves to `<log_root>/archive/` when its project
  is completed or inactive for 12+ months (configurable), or on explicit
  user action.
* **Derived views:** `.summary.md` files are derived and regenerable.
* **Deletion:** only explicit user action, never automatic (v1.2 Section 12).
* **Compaction:** none for active namespaces; archived directories may be
  compressed at the user's discretion.

---

# 12. Update Workflow

1. **Session start** - write a `session_start` entry creating
   `<session_id>.jsonl` in the project's namespace. `session_uuid` is
   generated. `project_id` MUST be registry-registered.
2. **During the session** - append `event` entries (file changes, tests,
   spec/ADR updates, commits). Appends are `a+` single-writer; each agent
   writes only its own session file, so concurrent agents never interleave.
3. **Session end** - append a `session_end` entry with aggregate fields,
   `outcome`, and `next_suggested_task`. For `HANDOFF`, state the recipient.
4. **Derive views** - an idempotent helper (Phase 2 tooling) regenerates
   `<session_id>.summary.md` from the `.jsonl` and refreshes the namespace
   manifest.
5. **Handover sync** - `next_suggested_task` is mirrored into
   `handover/NEXT-STEPS.md`; significant outcomes refresh
   `handover/CURRENT-STATE.md`. The log remains authoritative history.

Every AI agent contributing to AI-Hub MUST append a `session_end` entry
before ending work (mirrors v1.1 Section 21).

---

# 13. Relationships With Existing Documents

| Document | Relationship |
|----------|--------------|
| `START-HERE.md` | Repository index. Add `logs/` and `projects/` to the structure listing and pointers to these specs. Logs are history, not onboarding reading. |
| `AGENT-HANDOVER.md` | Orientation: "how to continue this project now." The log is durable cross-project history. |
| `CURRENT-STATE.md` | Live snapshot. The log is the audit trail behind it. |
| `NEXT-STEPS.md` | Actionable plan; consumes each session's `next_suggested_task`. |
| `SESSION-SUMMARY.md` | Per-session continuity doc. The log's `.summary.md` is its structured twin; keep `SESSION-SUMMARY.md` and generate it from `session_end`. |
| `AGENT-LOG.md` | Superseded. Not part of original specs. Remove after ADR-0002 is accepted. |
| `projects/registry.json` | Authoritative project identity for all logs. |

**Terminology note:** the project registry states `ACTIVE`, `ARCHIVED` and
`PENDING_REVIEW` share names with the provider lifecycle states (v1.2
Sections 5 and 9) but belong to a different domain (managed projects vs. AI
providers). They are separate state models and MUST NOT be confused.

---

# 14. Future Analysis Modules

The structured store enables:

* **agent performance** - group `session_end` by `agent`; aggregate
  `outcome` and `test_results`
* **project history** - chronological scan per `project_id`
* **implementation history** - files created/modified per project and phase
* **architectural decisions** - `adrs_created` / `adrs_modified` per project
* **recurring problems** - cluster `known_issues` and `tech_debt_*`
* **task completion statistics** - `outcome` distribution and
  `next_suggested_task` closure rate

Because every entry is self-identifying, analysis works even when streams
are merged.

---

# 15. Config Integration

```toml
[logging]
level = "INFO"
log_root = "logs"

[workspace]
root = "M:\\dev"

[registry]
path = "projects/registry.json"
```

`log_root`, `workspace.root`, and `registry.path` are relative to the
repository root by default and may point anywhere, preserving repository
independence. These values are documented in the configuration specification
(v1.2 Section 10) and present in `config.toml`.

**Portability (R-03):** these values are always configuration driven.
`M:\dev` is a machine-specific default example only; implementation MUST
NOT hardcode workspace paths. Absolute paths are metadata only; `project_id`
is the only portable identity key.

---

# 16. Open Questions for Approval

1. ~~Should sessions against unregistered projects be rejected outright, or
   queued to a `_pending/` namespace for later registration?~~ **RESOLVED
   (R-08):** unregistered sessions are REJECTED. Logging fails until the
   project is registered; no `_pending/` namespace exists.
2. Retention default: 12 months inactivity threshold for archival - confirm.
3. ~~Auto-generate `handover/SESSION-SUMMARY.md` from `session_end` (recommended)
   or keep manual?~~ **RESOLVED:** auto-generate from `session_end`, consistent
   with Section 13.

---

# 17. Definition of Done for This Design

* ADR-0002 and ADR-0003 accepted.
* Registry values added to the configuration specification.
* A `scripts/` helper exists to create sessions, append entries, derive
  summaries, and update manifests (Phase 2 tooling).
* `handover/AGENT-LOG.md` removed.
* Structure reflected in `START-HERE.md`.
