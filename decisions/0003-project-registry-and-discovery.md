# ADR-0003: Project Registry and Workspace Discovery

**Status:** ACCEPTED

**Date:** 2026-07-31

**Author:** Phase 1 Release Engineer

**Amendments:** applied from `ARCHITECTURE-REVIEW-REPORT.md` findings
R-01, R-03, R-04, R-06, R-07, R-08 (see `docs/review/amendment-summary-R01-R08.md`)

**Acceptance date:** 2026-07-31

**Acceptance note:** Accepted following the final constitutional architecture
review (`ARCHITECTURE-FINAL-REVIEW.md` - verdict PASS, no BLOCKERs).

**Related documents:**

* `spec/project-registry.md` (PROPOSED)
* `decisions/0002-agent-logging-architecture.md` (ACCEPTED) - consumer of
  project identity
* `AI-Hub Project Specification v1.2` - monitoring's PENDING_REVIEW pattern
  (Section 9)

---

## Context

AI-Hub needs an authoritative list of the projects it manages. The agent
logging system (ADR-0002) requires a stable, unambiguous `project_id` for
every entry. Project identity must not be invented at write time.

The development workspace (`M:\dev`) contains multiple repositories
(AI-Hub, MediCab, CMMS, future projects). AI-Hub should be able to discover
potential projects from the workspace, but must never assume that every Git
repository is a managed project, and must never modify discovered
repositories.

## Problem

Without a registry, project identity is ad hoc (invented at write time),
which risks mixed or ambiguous logs and prevents cross-project analysis.
Without discovery, the user must manually register every project - error
prone and incomplete. Discovery without a review gate would silently activate
projects, violating user sovereignty (Constitution Article 2) and repository
independence (Article 3).

## Options Considered

### Option A - No registry; invent project ids in logs

Pro: nothing to build.

Con: ambiguous identity, mixed logs, no authoritative source. Rejected.

### Option B - Registry, manual registration only

Pro: fully user-controlled; simple.

Con: misses unregistered repositories; manual overhead. Acceptable baseline,
insufficient long-term.

### Option C - Registry + automatic discovery that auto-activates

Pro: low user effort.

Con: silently manages repositories the user never chose; violates Articles 2
and 3. Rejected.

### Option D - Registry + discovery that produces candidates behind a review gate (recommended)

Pro:

* registry is the authoritative source of managed projects
* discovery reduces manual effort but can only create `DISCOVERED` /
  `PENDING_REVIEW` candidates
* human review is the only path to `ACTIVE` - user sovereignty preserved
* safety constraints (never modify discovered repos, never create files
  inside them, never store credentials) are explicit
* repository metadata (branch, remote, HEAD, status) is collected without
  coupling AI-Hub to any application repository

Con: requires a review workflow and scheduled or on-demand scanning; more
moving parts than manual-only.

## Decision

Adopt **Option D** as specified in `spec/project-registry.md`:

* authoritative store: `projects/registry.json` (schema-versioned)
* registry states: `DISCOVERED`, `PENDING_REVIEW`, `ACTIVE`, `PAUSED`,
  `ARCHIVED`, `IGNORED`
* origin tracked per project: `git_discovery` or `manual`
* workspace discovery (future capability): scan `M:\dev` for `.git/`
  directories, collect metadata, create candidates only
* workflow: Git repositories -> discovery candidates -> registry review ->
  registered AI-Hub projects
* safety: never modify discovered repos, never write into them without
  explicit configuration, never store secrets, never auto-activate
* remote URLs are sanitized before storage (credentials removed,
  `has_credentials_remote` records their presence) (R-01, Article 6)
* `workspace.root` is configuration driven and MUST NOT be hardcoded;
  `M:\dev` is only a default example; paths are metadata, `project_id` is
  the only portable key (R-03)
* discovery must not follow symbolic links or NTFS junctions, must never
  traverse outside the configured workspace root, and is strictly read-only
  (R-04)
* discovery only creates candidates; `ACTIVE` repository metadata is updated
  from `session_end` git metadata or explicit user action (R-06)
* `project_id` is immutable; renames create a new id and archive the old
  with `renamed_to` (R-07)

The AI-Hub repository itself is registered manually (`source: manual`,
`status: ACTIVE`).

## Consequences

* Positive: project identity is authoritative and unambiguous (ADR-0002).
* Positive: user sovereignty preserved via the review gate.
* Positive: discovery scales to many repositories without manual cataloguing.
* Positive: repository independence - discovery reads metadata only, writes
  only to AI-Hub-owned storage.
* Positive: architecture review amendments (R-01, R-03, R-04, R-06, R-07)
  closed the security and ownership gaps without changing the core decision.
* Negative: discovery is a future capability; it is NOT implemented in the
  current phase.
* Negative: candidates require human review; a review backlog may form.
* Follow-up: configuration values `[workspace] root` and `[registry] path`;
  registry file seeded with the `ai-hub` project.

## Acceptance Criteria

This ADR is accepted when:

* the owner approves the registry + review-gated discovery design
* `projects/registry.json` exists with the `ai-hub` project registered
* configuration values are documented in the configuration specification
* a future phase implements discovery behind the candidate gate
