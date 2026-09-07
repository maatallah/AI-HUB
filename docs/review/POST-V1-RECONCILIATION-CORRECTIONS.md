# Post-v1 Reconciliation Corrections Log

Status: **OPEN — reconciliation corrections pending**
Date: 2026-09-07
Baseline: `1b769f8` (post-v1 routing experiment closure)

---

## Purpose

This document tracks corrective actions arising from the post-v1/M1–M4 current-state
reconciliation performed after closure of the real-world routing experiment.

It is a **tracking/audit document**, not a source of runtime configuration. Its purpose
is to ensure that future OpenCode sessions can determine:

* what discrepancy was identified,
* why it required correction,
* what evidence established the expected state,
* whether it has been corrected,
* when it was corrected,
* how it was corrected,
* how it was verified,
* and which commit eventually contains the correction.

**Historical documents must not be rewritten merely to match current values.** A
historical record that was correct at the time of authorship retains its original
content regardless of subsequent version changes.

**No entry in this document authorizes M5 or any new implementation work.**
Corrections require owner authorization through the ongoing workflow.

---

## Status Legend

| Status | Meaning |
|--------|---------|
| **OPEN** | Discrepancy identified, not yet corrected |
| **CORRECTED** | Correction performed |
| **VERIFIED** | Correction independently checked |
| **COMMITTED** | Correction is contained in a Git commit |

A correction may have multiple status milestones (e.g., OPEN → CORRECTED → VERIFIED → COMMITTED).

---

## Baseline

| Field | Value |
|-------|-------|
| Repository | `M:\dev\AI-Hub` |
| Baseline HEAD | `1b769f8dc6d44c9d0eff0de65f647d9a1e7b2f0d` |
| origin/main | `7ff3971cba5df45eb9e84dc7f2a80491b404dd37` |
| Current reconciliation date | 2026-09-07 |
| Post-v1 M1–M4 status | complete |
| Real-world experiment status | closed (Tasks 1–7 PASS, Task 8 BLOCKED) |
| Task 8 disposition | blocked by insufficient approved scope — process lesson, not defect |
| M5 | not authorized |

---

## Correction Register

| ID | Area | Issue | Expected State | Evidence / Reason | Status | Correction Date | Verification | Commit |
|----|------|-------|----------------|-------------------|--------|-----------------|--------------|--------|
| CORR-001 | Configuration | Working-tree `config.toml` has `discovery.enabled = true` | `discovery.enabled = false` | `app/config.py:68` DEFAULT_CONFIG = `False`; `templates/config.toml:43` = `false`; committed `config.toml` at `1b769f8` = `false`; Phase 6 spec line 297 = `false`; Phase 6 release manifest line 58 = `false`; `CURRENT-STATE.md:173` = "default false" | VERIFIED | 2026-09-07 | `config.toml:51` restored to `enabled = false`. Verified: working tree now matches committed state at `1b769f8` (`git diff --stat -- config.toml` returns empty); confirmed agreement with `templates/config.toml:43`, `app/config.py:68`, Phase 6 spec, Phase 6 release manifest, and `CURRENT-STATE.md`. | — |
| CORR-002 | Handover documentation | `handover/AGENT-HANDOVER.md` remains frozen in Phase 1 status framing | Accurately reflect the current Phase 1–6 + M1–M4 state | Current-state reconstruction: lines 39–42 state "Phase 1 released. Ready for Phase 2"; lines 197–203 list implemented features as "Known Future Areas"; lines 207–217 describe Phase 1 as current goal | VERIFIED | 2026-09-07 | Replaced Phase 1 status (lines 39–42) with current Phases 1–6 + M1–M4 status including experiment closure and M5-not-authorized statement. Replaced "Known Future Areas" (lines 196–203) with "Implemented Capabilities" listing all released phases plus a "Known Future Areas" section noting M5 is not authorized. Replaced "First Implementation Goal" (lines 207–217) with historical framing. Verified: grep confirms no remaining statement presents Phase 1 as current; grep confirms M5-not-authorized present; grep confirms experiment closure referenced. | — |
| CORR-003 | Handover documentation | `handover/CURRENT-STATE.md` contains obsolete M1/M2 source paths | `recommendation/decision.py` instead of nonexistent `app/routing/decide.py` and `app/routing/record.py` | `app/routing/` directory does not exist; glob `**/routing/**/*.py` returns no results; actual implementation is in `recommendation/decision.py:169` (`build_decision_envelope`) and `recommendation/decision.py:548` (`record_decision`) | VERIFIED | 2026-09-07 | Lines 297,299: `app/routing/decide.py` → `recommendation/decision.py` and `app/routing/record.py` → `recommendation/decision.py`. Confirmed `recommendation/decision.py` exists; confirmed `app/routing/` does not exist. No other lines in file reference `app/routing`. | — |
| CORR-004 | Handover documentation | `handover/NEXT-STEPS.md` contains obsolete M1/M2 source paths | `recommendation/decision.py` instead of nonexistent `app/routing/decide.py` and `app/routing/record.py` | Same evidence as CORR-003; lines 425–426 reference `app/routing/decide.py` and `app/routing/record.py` | VERIFIED | 2026-09-07 | Lines 425,426: `app/routing/decide.py` → `recommendation/decision.py` and `app/routing/record.py` → `recommendation/decision.py`. Confirmed `recommendation/decision.py` exists; confirmed `app/routing/` does not exist. No other lines in file reference `app/routing`. | — |
| CORR-005 | Handover documentation | `CURRENT-STATE.md` does not reference the completed real-world experiment closure | Current-state document should identify the experiment and its closure | 635-line document contains zero mentions of "experiment", "real-world", or "routing experiment"; experiment was conducted, closed, and documented in `docs/review/POST-V1-ROUTING-REAL-WORLD-EXPERIMENT-CLOSURE.md` (committed at `1b769f8`) | VERIFIED | 2026-09-07 | Added experiment closure block after the "Pending" section in the Post-v1 Adaptive Routing (M1-M4) section. Includes scope/closure doc references, Tasks 1–7 PASS, Task 8 BLOCKED (target function not specified), classification, and explicit statements that no M5 was authorized by the experiment. Verified: grep confirms "experiment" now present in CURRENT-STATE.md; Task 8 BLOCKED reason confirmed correct. | — |
| CORR-006 | Handover documentation | `NEXT-STEPS.md` does not reference the completed real-world experiment closure | Post-v1 section should reference the closure | 448-line document contains zero mentions of "experiment", "real-world", or "routing experiment"; experiment closure is documented but not reflected in handover | VERIFIED | 2026-09-07 | Added experiment closure block after the M5-not-authorized line in the Post-v1 Adaptive Routing section. Records Tasks 1–7 PASS, Task 8 BLOCKED (target function not specified by approved scope), closure doc reference, no M5 authorization derived from experiment, and pointer to reconciliation corrections log. Verified: grep confirms "experiment" now present in NEXT-STEPS.md; describes experiment as closed, not pending. | — |
| CORR-007 | Handover documentation | `CURRENT-STATE.md` "Last Updated" information predates the experiment closure | Reflect the September 2026 experiment closure state | Line 7: "2026-08-31 (Post-v1 Adaptive Routing M1-M4 complete...)"; experiment closure completed 2026-09-03+ | VERIFIED | 2026-09-07 | Updated "Last Updated" line from `2026-08-31` to `2026-09-07`. Rewrote summary to reflect current state: experiment closed, documentation reconciliation in progress, no M5 authorized. Verified: CURRENT-STATE.md line 7 now reads `2026-09-07`. | — |
| CORR-008 | Handover documentation | `CURRENT-STATE.md` phrase "M4/M5 status" can ambiguously suggest adaptive-routing M5 | Explicitly distinguish Phase 5 Milestone 5 from any future adaptive-routing M5 | Line 620: "M4/M5 status and release recorded" — in context refers to Phase 5 Milestone 5 (connectors hardening), but could be misread as adaptive routing M5 | VERIFIED | 2026-09-07 | Replaced ambiguous "M4/M5 status and release recorded" with explicit "Phase 5 Milestone 4 and Milestone 5 (hardening/release) status and release recorded". Verified: grep confirms no remaining "M4/M5" in the document; Phase 5 Milestone 5 context is now unambiguous. | — |
| CORR-009 | Project documentation | `README.md` is materially stale/minimal | Provide a useful current project overview and entry point | 7 lines for a 548-test, 10-table, 6-phase project with CLI, connectors, VS Code extension, MCP server; no project status, no feature overview, no entry point beyond a bare pointer to START-HERE.md | VERIFIED | 2026-09-07 | Rewrote README.md with: project purpose, implemented phases (1–6), post-v1 M1–M4 summary, experiment closure (Tasks 1–7 PASS, Task 8 BLOCKED), governance boundary (M5 NOT AUTHORIZED), key documents table. Verified: grep confirms no M5-authorized claim; `decision_version` 3.1.0 stated; experiment described as closed with Task 8 BLOCKED for correct reason; no claim that discovery is enabled by default. | — |

---

## Historical References — NOT Corrections

The following occurrences of `decision_version` `3.0.0` are **intentionally NOT corrective
actions**. They are historical records that were correct at the time of authorship.
Changing them would falsify historical state.

| Document | Line | Content | Reason to preserve |
|----------|------|---------|-------------------|
| `AI-Hub Project Specification v1.2.md` | 565 | `decision_version = "3.0.0"` | Design-time specification authored during Phase 3. The spec records the version that existed when it was written. The runtime value was bumped to `3.1.0` in M3; the spec is not a live configuration reference. |
| `docs/release/PHASE3-RELEASE-MANIFEST.md` | 48 | `recommendation.decision_version` `3.0.0` | Release manifest recording what was true at Phase 3 release time. Altering a release manifest would falsify the release record. |
| `docs/review/PHASE3-SCORING-SPEC.md` | 163 | `recommendation.decision_version` `3.0.0` | Phase 3 scoring specification. Historical document from the Phase 3 era. |
| `docs/review/POST-V1-ADAPTIVE-ROUTING-M3-SCOPE.md` | 57 | `decision_version` `3.0.0 → 3.1.0` | Correctly documents the M3 bump as a delta — the old value is mentioned as the "from" state. |
| `CHANGELOG.md` | various | Documents `3.0.0 → 3.1.0` transition | Changelog correctly records the historical bump. |

**Principle:** Historical documents are preserved per Constitution Article 5 (Preservation
of History) and Article 10 (Truthfulness). A value that was true at time of authorship
remains true in the historical record.

---

## Non-Actionable / Owner Decision Items

The following items are recorded for awareness but are **not corrective actions**. They
require explicit owner decision and must not be represented as already-corrected issues.

| Item | Current State | Owner Decision Required |
|------|---------------|------------------------|
| CRLF-only working-tree changes (`.gitignore`, `CONSTITUTION.md`, `README.md`, `handover/AGENT-HANDOVER.md`) | Line-ending warnings only; no content diff | Whether to commit as-is or normalize line endings |
| Four untracked synthetic/validation files | `docs/review/POST-V1-ADAPTIVE-ROUTING-M1-SCOPE.md`, `docs/review/SYNTHETIC-BENCHMARK-SCORES.json`, `docs/review/SYNTHETIC-DISCOVERY-CANDIDATES.json`, `docs/review/SYNTHETIC-VALIDATION-DATA.md` | Whether to track, gitignore, or delete |
| Future decision to enable `discovery.enabled` permanently | Currently `false` in all committed and template sources | Whether to authorize `true` as the committed default |
| Phase 6 release approval/closure | Release package created and verified; approval + closure acceptance pending | Owner approval gate (M6) |
| Phase 6 push to origin/main | 3 experiment commits + any reconciliation corrections unpushed | Owner-authorized push (separate from release approval) |
| Pre-existing uncommitted working-tree changes | 5 modified files: `.gitignore`, `CONSTITUTION.md`, `README.md`, `config.toml`, `handover/AGENT-HANDOVER.md` | Whether to commit, and whether to include in the same commit as reconciliation corrections |

---

## M5 Boundary

**This correction log does not authorize M5, adaptive learning, feedback ingestion,
telemetry collection, scoring changes, routing changes, or other implementation work.**

The following governing documents maintain the M5 boundary:

* `START-HERE.md:11` — "no M5 authorized"
* `handover/CURRENT-STATE.md:316` — "No M5 is authorized"
* `handover/NEXT-STEPS.md:433` — "No M5 is authorized"
* `docs/review/POST-V1-ROUTING-REAL-WORLD-EXPERIMENT-CLOSURE.md:9` — "does not authorize M5, adaptive learning, feedback ingestion, telemetry collection, scoring changes, routing changes, or any other implementation work"
* `docs/review/POST-V1-ROUTING-REAL-WORLD-EXPERIMENT-CLOSURE.md:282` — same

Any future M5 authorization requires a separate owner-approved scope.

---

## Update Rules

Whenever a correction is performed:

1. **Source change:** The relevant source/document is changed.
2. **CORR entry updated:** The corresponding CORR entry in this log is updated.
3. **Correction date recorded:** The date of correction is entered.
4. **Change described:** The exact change is described in the entry.
5. **Verification evidence:** Verification evidence is recorded (who/what confirmed the fix).
6. **Commit SHA:** The Git commit SHA is added only **after** the correction is committed.
7. **Historical preservation:** Documents classified as LEAVE UNCHANGED must **not** be modified merely to eliminate version differences.

**Document status:** OPEN — reconciliation corrections pending.
