# Amendment Summary - R-01 through R-08

**Source:** `ARCHITECTURE-REVIEW-REPORT.md` (2026-07-31)

**Scope:** documentation only. No code, no scripts, no Phase 1 files.

**Result:** all eight amendments applied. ADR-0002 and ADR-0003 are now fit
for owner review toward ACCEPTED.

---

## R-01 — Remote URL may leak credentials into the registry (BLOCKER)

- **Affected documents:** `spec/project-registry.md`; `decisions/0003`.
- **Old problem:** `repository.remote` was stored verbatim; a URL like
  `https://user:token@host/repo.git` could persist credentials, violating
  Constitution Article 6.
- **Resolution:** remote URLs are sanitized before storage (userinfo removed);
  a boolean `has_credentials_remote` records that credentials were present
  and stripped; Safety and repository sections cite Article 6.

## R-02 — `session_uuid` UUID v4 randomness conflicts with Article 7

- **Affected documents:** `spec/agent-logging.md`; `decisions/0002`.
- **Old problem:** UUID v4 randomness was undocumented and appeared to
  violate deterministic behaviour (Article 7).
- **Resolution:** UUID v4 is retained with a documented exception - the
  randomness is limited to unique session identity generation and has no
  influence on decisions, recommendations, ranking, or automation.

## R-03 — Workspace root must be config-driven, not hardcoded

- **Affected documents:** `spec/project-registry.md`; `spec/agent-logging.md`;
  `decisions/0002`; `decisions/0003`.
- **Old problem:** `M:\dev` appeared to be a hardcoded constant.
- **Resolution:** `workspace.root`, `log_root`, and `[registry] path` are
  configuration values; `M:\dev` is only a machine-specific default example;
  absolute paths are metadata only and `project_id` is the only portable key.

## R-04 — Discovery must not escape the configured root

- **Affected documents:** `spec/project-registry.md`; `decisions/0003`.
- **Old problem:** no constraint on symbolic links, NTFS junctions, or
  traversal outside the workspace root.
- **Resolution:** discovery MUST NOT follow symlinks or NTFS junctions, MUST
  NEVER traverse outside the configured root, and is strictly read-only.

## R-05 — Free-form log fields could capture secrets

- **Affected documents:** `spec/agent-logging.md`; `decisions/0002`.
- **Old problem:** no log-security constraint on free-form fields.
- **Resolution:** logs must never contain credentials, tokens, API keys,
  passwords, private keys, or secrets; free-form fields are subject to
  Article 6; future redaction must not be the primary control.

## R-06 — Refresh path for ACTIVE repository metadata is undefined

- **Affected documents:** `spec/project-registry.md`; `decisions/0003`.
- **Old problem:** how/when ACTIVE projects refresh repository metadata was
  ambiguous; discovery risked silently mutating ACTIVE state.
- **Resolution:** discovery only creates candidates; ACTIVE metadata is
  updated from `session_end` git metadata or explicit user action; discovery
  never silently modifies ACTIVE projects.

## R-07 — No policy for `project_id` immutability/renames

- **Affected documents:** `spec/project-registry.md`; `spec/agent-logging.md`;
  `decisions/0002`; `decisions/0003`.
- **Old problem:** renames would have rewritten history.
- **Resolution:** `project_id` is immutable; a rename creates a new id, the
  old entry becomes ARCHIVED with `renamed_to: <new_project_id>`, and history
  is never renamed.

## R-08 — Internal inconsistency on unregistered sessions

- **Affected documents:** `spec/agent-logging.md`; `spec/project-registry.md`;
  `decisions/0002`.
- **Old problem:** Section 3 said "reject or review bucket" while Section 16
  asked reject vs. `_pending/`; ADR text contradicted both.
- **Resolution:** policy is **REJECT** - logging fails until the project is
  registered; no `_pending/` namespace exists; Section 3, Section 16, ADR-0002,
  and the registry Section 7 are aligned.

---

## Additional clarifications applied

- **Terminology:** project registry states (`ACTIVE`, `ARCHIVED`,
  `PENDING_REVIEW`) share names with provider lifecycle states (v1.2 Sections
  5 and 9) but belong to different domains; both specs carry an explicit note.

## Consistency review result

Cross-checked Constitution Articles 3, 5, 6, 7, 10; the v1.2 configuration
proposals (Section 10); ADR-0002; ADR-0003; and both specs.

- All R-01..R-08 references in the amended documents match their source
  findings.
- No residual "review bucket" / `_pending/` ambiguity outside the
  (unchanged) review report and the resolved Section 16 note.
- `ARCHITECTURE-REVIEW-REPORT.md` preserved verbatim as the audit record.
- ADR-0002 and ADR-0003 remain **PROPOSED** pending owner review.
