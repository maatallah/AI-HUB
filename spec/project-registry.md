# spec/project-registry.md

# AI-Hub Project Registry and Workspace Discovery

**Status:** PROPOSED (amended per architecture review, findings R-01, R-03,
R-04, R-06, R-07, R-08)

**Date:** 2026-07-31

**Author:** Phase 1 Release Engineer

**Amendments:** applied from `ARCHITECTURE-REVIEW-REPORT.md` (see
`docs/review/amendment-summary-R01-R08.md`)

**Related ADR:** `decisions/0003-project-registry-and-discovery.md` (ACCEPTED)

**Depends on:** Constitution Article 3 (repository independence)

**Consumed by:** `spec/agent-logging.md` (project identity for all logs)

---

# 1. Purpose

The Project Registry is the **authoritative source** for the set of projects
AI-Hub manages. It provides the stable `project_id` used by the agent logging
system, tracks each project's lifecycle state, and records its origin and
repository metadata.

This specification also defines **workspace discovery** - the future
capability that proposes registry candidates from Git repositories found in
the development workspace. Discovery generates **candidates only**; it never
activates projects.

---

# 2. Location and Format

Default location:

```
projects/
  registry.json
```

Format: JSON, UTF-8. A `registry_version` field enables future migration.

The path is logical and configurable (`[registry] path`), consistent with
the logging system's logical storage model.

---

# 3. Registry Schema

```json
{
  "registry_version": 1,
  "projects": [
    {
      "id": "medicab",
      "name": "MediCab",
      "path": "M:\\dev\\MediCab",
      "source": "git_discovery",
      "status": "ACTIVE",
      "first_detected": "2026-07-31T00:00:00Z",
      "last_seen": "2026-07-31T00:00:00Z",
      "notes": null,
      "repository": {
        "type": "git",
        "branch": "main",
        "remote": "https://example.com/repo.git",
        "has_credentials_remote": true,
        "last_commit": "abc123",
        "last_commit_date": "2026-07-30T10:00:00Z",
        "status": "clean"
      }
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | immutable `project_id` (lowercase, hyphens) |
| `name` | string | human-readable project name |
| `path` | string | canonical repository path (metadata only, platform-native) |
| `source` | string | `git_discovery` or `manual` (Section 5) |
| `status` | string | registry state (Section 4) |
| `first_detected` | string | UTC ISO 8601 |
| `last_seen` | string | UTC ISO 8601 |
| `notes` | string \| null | optional |
| `renamed_to` | string \| null | new `project_id` if this id was superseded (R-07) |
| `repository` | object \| null | metadata only; `null` if no repository |
| `repository.remote` | string \| null | remote URL with credentials removed (R-01) |
| `repository.has_credentials_remote` | boolean | `true` if the original remote URL contained credentials (never stored) |

**Safety (Constitution Article 6):** the registry stores metadata only. It
MUST never contain API keys, tokens, credentials, or secrets. Remote URLs
MUST be sanitized before persistence: any userinfo (e.g.
`https://user:token@example.com/repo.git`) is removed and only the
scheme/host/path is stored, with `has_credentials_remote=true` recording that
credentials were present but discarded.

**Project identity immutability (R-07):** `project_id` is immutable.
Renaming a project does NOT rename history. If a rename is required, a new
`project_id` is created; the old registry entry transitions to `ARCHIVED`
and records `renamed_to: <new_project_id>`. Existing logs keep their
original `project_id`.

---

# 4. Registry State Model

```
DISCOVERED -> PENDING_REVIEW -> ACTIVE -> PAUSED
                   |                |
                   v                v
                 IGNORED         ARCHIVED
```

| State | Meaning |
|-------|---------|
| `DISCOVERED` | found by discovery; not yet reviewed |
| `PENDING_REVIEW` | queued for human review |
| `ACTIVE` | an AI-Hub managed project (explicit approval) |
| `PAUSED` | temporarily inactive; logs retained |
| `ARCHIVED` | completed / retired; history retained, never deleted |
| `IGNORED` | explicitly dismissed; not managed |

Transition rules:

* Only a human (or explicit user action) moves a project to `ACTIVE`.
* Discovery can create or refresh `DISCOVERED` / `PENDING_REVIEW` only.
* `ARCHIVED` and `IGNORED` are never automatic.
* Projects are never deleted from the registry (Constitution Article 5);
  they are transitioned to `ARCHIVED` or `IGNORED`.

**Metadata ownership (R-06):** discovery only creates candidates. Repository
metadata for `ACTIVE` projects is updated exclusively from:

* `session_end` git metadata (`git_branch`, `git_commit_end`)
* explicit user action

Discovery never silently modifies `ACTIVE` projects.

**Terminology note:** the registry states `ACTIVE`, `ARCHIVED` and
`PENDING_REVIEW` share names with the provider lifecycle states
(v1.2 Sections 5 and 9) but belong to a different domain (managed projects
vs. AI providers). They are separate state models and MUST NOT be confused.

---

# 5. Source Origins

| Source | Meaning |
|--------|---------|
| `git_discovery` | proposed by workspace discovery (Section 6) |
| `manual` | registered directly by the user (e.g. AI-Hub itself, non-Git projects) |

The set is extensible; future sources (e.g. `ai_hub_self`, tracker imports)
must be documented before use.

---

# 6. Workspace Discovery (Future Capability)

**Status: NOT IMPLEMENTED.** This section documents the design. It will be
implemented in a future phase after ADR-0003 is accepted.

## 6.1 Workspace root (R-03)

`workspace.root` is always configuration driven. `M:\dev` is only the
current default example; it MUST NOT be hardcoded in code. Implementation
MUST read the workspace root from configuration on every run. Absolute paths
(including `path` in the registry and `repo_path` in log entries) are
metadata only and are never used as identity. `project_id` is the only
portable identity key.

## 6.2 Detection

Scan immediate and nested subdirectories under the configured workspace
root. A directory is a repository candidate if it contains a `.git/`
directory.

## 6.3 Metadata collected per detected repository

| Field | Description |
|-------|-------------|
| repository path | absolute path (metadata only) |
| repository name | directory name |
| current branch | from Git |
| remote URL | if available; sanitized - credentials removed, `has_credentials_remote` records their presence (R-01) |
| last commit hash | HEAD |
| last commit date | HEAD date |
| repository status | `clean` / `modified` |
| first detected date | recorded on first discovery |

## 6.4 Safety constraints

* Never modify discovered repositories.
* Never create files inside discovered repositories without explicit
  configuration.
* Never store API keys or credentials (Article 6). Remote URLs are
  sanitized before storage (R-01).
* Never assume every Git repository is an AI-Hub managed project.
* Discovery MUST NOT follow symbolic links (R-04).
* Discovery MUST NOT follow NTFS junctions (R-04).
* Discovery MUST NEVER traverse outside the configured `workspace.root`
  (R-04).
* Discovery is strictly read-only (R-04).

## 6.5 Workflow

```
Git repositories
        |
        v
Discovery candidates      (DISCOVERED / PENDING_REVIEW)
        |
        v
Project registry review   (human)
        |
        v
Registered AI-Hub projects (ACTIVE)
```

Discovery populates candidates; review activates them. No candidate becomes
`ACTIVE` without human approval.

---

# 7. Relationship to Agent Logging

* `project_id` in every log entry (spec/agent-logging.md Section 3) MUST
  exist in this registry.
* Each registered `ACTIVE` project maps to one logging namespace.
* `DISCOVERED` / `PENDING_REVIEW` / `IGNORED` projects produce no logging
  namespaces.
* `PAUSED` projects keep their logging namespace but accept no new sessions;
  existing history is retained and readable.
* `ARCHIVED` projects' namespaces move to the log archive; new sessions are
  rejected until the project is explicitly re-activated.
* Unregistered sessions are REJECTED (R-08): logging requires prior
  registration; no work is silently assigned to a project.
* Registry metadata (name, path) is copied into log entries as-of-write.

---

# 8. Config Integration

```toml
[workspace]
root = "M:\\dev"

[registry]
path = "projects/registry.json"
```

Documented in the configuration specification (v1.2 Section 10) and present
in `config.toml`.

**Portability (R-03):** `workspace.root` and `[registry] path` are
configuration values, not constants. `M:\dev` is a machine-specific default
example only; implementations MUST NOT hardcode it. Paths are never used as
project identity - `project_id` is the only portable key.

---

# 9. Open Questions for Approval

1. Should discovery run on a schedule (Windows Task Scheduler) or on-demand?
2. Should `IGNORED` repos be re-offered after a state change (e.g. new
   remote, new activity)?
3. Nesting policy: should a repository nested inside another repository be
   treated as a separate project?
4. Registry writes: single-writer lock or append-only journal + snapshot?

---

# 10. Definition of Done for This Design

* ADR-0003 accepted.
* Registry schema versioned and documented.
* Discovery implemented behind the candidate gate (future phase).
* Registry file present with at least the `ai-hub` project registered
  (`source: manual`).
* Configuration values documented in the configuration specification.
