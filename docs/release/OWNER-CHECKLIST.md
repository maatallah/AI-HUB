# OWNER-CHECKLIST.md

# AI-Hub Phase 1 - Owner Action Checklist

**Date:** 2026-08-01

Actions are grouped by timing. Items marked **MANUAL** require the owner's
direct intervention and cannot be completed by an agent.

---

## 1. Required Before Release

| # | Action | Manual? | Notes |
|---|--------|---------|-------|
| 1 | Initialize git repository and commit the Phase 1 baseline | **MANUAL** | `git init`, `git add -A`, `git commit -m "Phase 1: repository foundation"` |
| 2 | Select and apply a `LICENSE` | **MANUAL** | Placeholder currently in place |
| 3 | Sign off Phase 1 closure (`handover/PHASE-1-CLOSURE.md`) | **MANUAL** | Signature line provided |
| 4 | Approve the Phase 1 release package | **MANUAL** | See `docs/release/` |

## 2. Required Before Phase 2

| # | Action | Manual? | Notes |
|---|--------|---------|-------|
| 1 | Accept ADR-0001 (normalized `scores` table) | Decision | Not required for Phase 2, but recommended before Phase 3 |
| 2 | Approve removal of superseded `handover/AGENT-LOG.md` | **MANUAL** | Irreversible without git; ADR-0002 is accepted |
| 3 | Confirm git remote creation (GitHub) if publishing | **MANUAL** | External account action |
| 4 | Decide on repository publication (private/public) | **MANUAL** | External account action |
| 5 | Authorize Phase 2 (Monitoring Engine) planning | Decision | After closure sign-off |

## 3. Optional Improvements

| # | Action | Notes |
|---|--------|-------|
| 1 | Update `START-HERE.md` to reference `logs/` and `projects/` | ADR-0002 follow-up |
| 2 | Refresh `handover/CURRENT-STATE.md` / `SESSION-SUMMARY.md` for ADR-0002/0003 | Stale living docs |
| 3 | Align `projects/registry.json` seed with amended schema (`renamed_to`, `has_credentials_remote`) | Non-blocking conformance |
| 4 | Run tests on a clean checkout after git init | Verify release integrity |
| 5 | Validate seed dataset base URLs | Planned in Phase 2 |

## 4. Future Work

| # | Action | Phase |
|---|--------|-------|
| 1 | Monitoring Engine (health, quota, availability, lifecycle) | Phase 2 |
| 2 | Scoring / Recommendation / Fallback Engines + ADR-0001 migration | Phase 3 |
| 3 | Dashboard and reporting | Phase 4 |
| 4 | Connectors (VS Code, MCP) | Phase 5 |
| 5 | AI Ecosystem Intelligence | Phase 6 |
| 6 | Model seeding | Phase 2/3 |

---

## Actions Requiring Manual Intervention (explicit)

The following CANNOT be automated by an agent and stop the release until the
owner acts:

1. `git init` + first commit (irreversible once history exists; requires
   owner intent and identity).
2. `LICENSE` selection (legal decision).
3. Git remote creation / repository publication (external account).
4. Signing/approving the release (owner authority).
5. Removal of `handover/AGENT-LOG.md` (irreversible without git baseline).

See `docs/release/WAITING-FOR-OWNER.md` for the detailed wait list.
