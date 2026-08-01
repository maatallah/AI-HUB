# ARCHITECTURE-REVIEW-REPORT.md

# AI-Hub Architecture Review — Agent Logging & Project Registry

**Reviewer:** Phase 1 Release Engineer (independent review)

**Date:** 2026-07-31

**Status:** Final — conditional recommendation

**Scope reviewed:**

* `spec/agent-logging.md`
* `spec/project-registry.md`
* `decisions/0002-agent-logging-architecture.md`
* `decisions/0003-project-registry-and-discovery.md`
* `CONSTITUTION.md`
* `AI-Hub Project Specification v1.2`

**Method:** document review only. No code was written or executed.

---

# 1. Executive Summary

The designs in ADR-0002 and ADR-0003 are architecturally sound, well
documented, and consistent with the Constitution in the large. The hybrid
JSONL + derived Markdown logging model and the review-gated discovery
workflow are appropriate and future-proof.

**However, the review found one BLOCKER and seven SHOULD FIX items.**
Acceptance of ADR-0002 and ADR-0003 is recommended **conditional on** the
BLOCKER being addressed first and the SHOULD FIX items being accepted as
spec amendments. All findings are documentation-level; none require code
changes because the system is not yet implemented.

Verdict: **ACCEPT AFTER AMENDMENTS** (apply R-01; then adopt R-02–R-08).

---

# 2. Review Checklist

| # | Criteria | Outcome |
|---|----------|---------|
| 1 | Contradictions between specifications | 2 minor (R-02, R-08) |
| 2 | Missing safety constraints | 3 (R-01, R-04, R-05) |
| 3 | Missing lifecycle states | acceptable (R-10 future) |
| 4 | Ambiguous ownership of data | 2 (R-06, R-07) |
| 5 | Future scalability problems | 3 (R-09, R-13, R-14) |
| 6 | Security/privacy concerns | 3 (R-01, R-05, R-11) |
| 7 | Conflicts with repository independence | none blocking (R-09 note) |
| 8 | Migration problems later | addressed by design (R-07, R-12) |

---

# 3. Findings

## BLOCKER

### R-01 — Remote URL may leak credentials into the registry

*Category: security / safety constraints*
*Location: `spec/project-registry.md` §3 (`repository.remote`), §6.3 ("remote
URL, if available"), and the §3 example `"remote": "https://..."`*

Git remote URLs frequently embed credentials, e.g.
`https://user:token@host/repo.git`. The registry stores `repository.remote`
verbatim and §6.3 collects "remote URL" without qualification. Storing such a
URL would violate Constitution Article 6 ("Raw credentials must never be
stored").

**Recommendation (mandatory):** add an explicit constraint that any remote
URL MUST be sanitized before storage (strip userinfo/credentials,
i.e. store scheme + host + path only), and record `has_credentials_remote:
true|false` instead of the credential itself.

## SHOULD FIX BEFORE ACCEPTANCE

### R-02 — `session_uuid` uses random UUID v4; conflicts with Constitution Article 7

*Category: contradiction / determinism*
*Location: `spec/agent-logging.md` §6; ADR-0002 §Decision*

Article 7 requires deterministic behaviour: "Random behaviour is prohibited
unless explicitly documented." UUID v4 is randomly generated. The specs
currently do not acknowledge or justify this exception.

**Recommendation:** either (a) document the exception explicitly in
ADR-0002 and the spec (randomness is confined to identity generation and has
no effect on recommendations, satisfying Article 7's intent), or (b) use a
deterministic UUID v5 derived from `session_id`. Option (a) is simpler and
recommended.

### R-03 — Workspace root must be config-driven, not hardcoded (portability)

*Category: scalability / portability*
*Location: `spec/project-registry.md` §6.1 ("configured workspace root
(default `M:\dev`)"), §8; `spec/agent-logging.md` §15; example paths in
`projects/registry.json`*

The user-identified concern is valid and **largely addressed** — the specs
already frame `M:\dev` as a default under `[workspace] root`. However, the
specs do not yet state explicitly that:

1. the value MUST come from configuration and MUST NOT be hardcoded in code;
2. machine-specific paths (`M:\dev\AI-Hub`) are never identity — only
   `project_id` is portable;
3. `registry.path` and `repo_path` are platform-native and will differ across
   machines.

**Recommendation:** add an explicit statement (e.g. in
`spec/project-registry.md` §6.1 and §8): "`M:\dev` is a default value only.
Implementation MUST read `workspace.root` from configuration and MUST NOT
hardcode a workspace root. Paths are machine-specific and MUST never be used
as project identity; `project_id` is the only portable key."

### R-04 — Discovery must not escape the configured root (symlinks/junctions)

*Category: safety constraints*
*Location: `spec/project-registry.md` §6.1–6.2*

On Windows, symlinks and NTFS junctions can point outside the workspace root.
A recursive scan that follows them could traverse and read arbitrary
directories, violating the intended containment and the "never modify /
never create files" guarantees.

**Recommendation:** add a safety constraint: "Discovery MUST NOT follow
symlinks or junctions and MUST NOT traverse outside the configured
`workspace.root`."

### R-05 — Free-form log fields could capture secrets

*Category: security / safety constraints*
*Location: `spec/agent-logging.md` §7.3 (`event.detail`), §7.4
(`known_issues`, `recommendations`)*

These are free-form. An agent could inadvertently log a command containing a
token, or paste a secret into notes. The logging spec has no no-secrets rule
for log content (only the registry does, in project-registry §3).

**Recommendation:** add to `spec/agent-logging.md`: log content is subject
to Constitution Article 6; agents MUST NOT write secrets into any log field;
document a future redaction mechanism for `event.detail` and free-text
fields.

### R-06 — Refresh path for ACTIVE project repository metadata is undefined

*Category: ownership of data*
*Location: `spec/project-registry.md` §4 ("Discovery can create or refresh
`DISCOVERED` / `PENDING_REVIEW` only"), §3 (`repository` object)*

Discovery is correctly constrained to candidates. But that leaves an
ambiguity: who refreshes `branch`, `last_commit`, `status` for `ACTIVE`
projects? Without a defined source, ACTIVE metadata goes stale or is
updated ad hoc.

**Recommendation:** define that `ACTIVE` repository metadata is refreshed
from session-end log data (`git_branch`, `git_commit_end`) by the logging
helper, or by explicit user action — never by candidate discovery.

### R-07 — No policy for `project_id` immutability/renames

*Category: ownership / migration*
*Location: `spec/project-registry.md` §3; `spec/agent-logging.md` §3, §6*

If a `project_id` ever changes, every historical log namespace and entry
loses its stable key. The specs do not define whether `project_id` is
immutable.

**Recommendation (low effort):** state that `project_id` is immutable;
renames create a new id and the old id is archived in the registry with a
`renamed_to` pointer. This avoids a future migration trap.

### R-08 — Internal inconsistency on unregistered sessions

*Category: contradiction (internal)*
*Location: `spec/agent-logging.md` §3 ("MUST be rejected ... or logged to a
designated review bucket") vs §16 question 1 (reject vs. `_pending/` bucket)*

Section 3 states the policy as a MUST while Section 16 presents it as
undecided. The two readings conflict.

**Recommendation:** resolve by choosing **reject** (as recommended in §16)
and make §3 consistent, or formalize the `_pending/` bucket as the decided
policy.

## FUTURE IMPROVEMENT

### R-09 — Logs/registry inside the AI-Hub git repository

*Category: scalability / repository independence (note)*

Append-heavy logs for **all** projects live inside the AI-Hub repository by
default. Over years this bloats the AI-Hub git tree and embeds other
projects' history in it. Not a constitutional violation (independence means
no dependency on app repos), but a hygiene concern.

**Recommendation (future):** gitignore `logs/`, or default `log_root` to a
location outside the git tree; consider storing `projects/registry.json`
metadata (not log bodies) only.

### R-10 — Transition completeness for registry states

*Location: `spec/project-registry.md` §4*

`ARCHIVED` is terminal with no un-archive path; `IGNORED` re-offer and
`PAUSED`↔`ACTIVE` are not formally specified (question 2 in §9 touches
IGNORED). Define these explicitly when discovery is implemented.

### R-11 — Privacy of paths when sharing logs

*Location: `spec/agent-logging.md` §7 (`repo_path`), §14 (analysis)*

Absolute paths expose local usernames/layout (e.g. `C:\Users\<user>\...`).
If logs are ever shared or published, a redaction option is needed.

### R-12 — `phase` semantics for external projects

*Location: `spec/agent-logging.md` §9*

"AI-Hub roadmap 0-6, or the project's own phase" leaves the meaning of
`phase` for non-AI-Hub projects open. Define it as a free-form project stage
string or require each project to declare its phase vocabulary.

### R-13 — Registry write concurrency

*Location: `spec/project-registry.md` §9 question 4*

Multiple agents updating `registry.json` concurrently need an atomic,
single-writer protocol. Elevate from open question to a stated constraint
(atomic replace + advisory lock) when tooling is built.

### R-14 — Discovery scan cost

*Location: `spec/project-registry.md` §6*

Recursive scans of a large workspace can be slow. Define exclusion rules
(`node_modules`, `.venv`, build dirs) and a cap on recursion depth in the
implementation.

## ACCEPTABLE

### R-15 — Retention policy
12-month archival default, no automatic deletion — consistent with v1.2
§12 and Constitution Article 5. Acceptable.

### R-16 — Registry state model
`DISCOVERED / PENDING_REVIEW / ACTIVE / PAUSED / ARCHIVED / IGNORED` covers
the workflow; no required state is missing.

### R-17 — Logical storage model
Namespaces decoupled from physical layout is the right call; a future DB
backend is unblocked. Acceptable.

### R-18 — Versioning
`schema_version` on entries and `registry_version` on the registry enable
controlled migration. Good practice.

### R-19 — No authentication on local logs
Appropriate for a personal, single-user, local tool. Acceptable for scope.

### R-20 — Hybrid granularity decision
Namespace-per-project + file-per-session satisfies separation, growth, and
analyzability. Confirmed sound.

### R-21 — Terminology collision (accepted with note)
Provider lifecycle (v1.2 §5: `ACTIVE`, `ARCHIVED`) and project registry
states share names, and monitoring's `PENDING_REVIEW` (v1.2 §9) collides
with the registry's `PENDING_REVIEW`. Different domains; not a
contradiction, but add a one-line disambiguation to the docs/glossary to
prevent future confusion.

---

# 4. Constitution Compliance Check

| Article | Compliance | Notes |
|---------|-----------|-------|
| 1 User Sovereignty | Pass | review gate; user decides |
| 2 Recommendation over Automation | Pass | discovery never auto-activates |
| 3 Repository Independence | Pass | logs/registry are AI-Hub-owned; discovery reads only |
| 4 Explainability | Pass (n/a) | no recommendations produced by these systems |
| 5 Preservation of History | Pass | permanent logs; archival, not deletion |
| 6 Security First | **Fail (R-01)** | remote URL may carry credentials |
| 7 Deterministic Behaviour | **Fail (R-02)** | UUID v4 randomness undocumented |
| 8 Traceability | Pass | ADRs + versioned schema |
| 9 Extensibility | Pass | namespaces, versioned schema, states extensible |
| 10 Truthfulness | Pass | `null` for unknown; machine-specific paths honest |
| 11 Documentation Before Code | Pass | specs + ADRs precede implementation |
| 12 Long-Term Maintainability | Pass (R-09/R-12 notes) | logical model; path hygiene to confirm |

---

# 5. Final Recommendation

**ACCEPT AFTER AMENDMENTS**

* **Required before acceptance:** apply R-01 (BLOCKER — Article 6).
* **Recommended before acceptance:** adopt R-02–R-08 as spec amendments.
  All are documentation changes; none affect the existing Phase 1
  implementation.
* **Deferred:** R-09–R-14 to be addressed when tooling/discovery is
  implemented (Phase 2+).
* **Confirmed acceptable:** R-15–R-21.

Once R-01–R-08 are incorporated, ADR-0002 and ADR-0003 are fit for ACCEPTED
status and the two specifications are fit to enter the configuration
specification (v1.2 §10) update.
