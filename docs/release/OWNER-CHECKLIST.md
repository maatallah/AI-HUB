# OWNER-CHECKLIST.md

# AI-Hub Phase 1 - Owner Action Checklist

**Date:** 2026-08-01

Actions are grouped by timing. Items marked **MANUAL** require the owner's
direct intervention and cannot be completed by an agent.

---

## 1. Required Before Release

| # | Action | Manual? | Notes |
|---|--------|---------|-------|
| 1 | Initialize git repository and commit the Phase 1 baseline | DONE | Commit `7ceac80`, branch `main` |
| 2 | Select and apply a `LICENSE` | **IN PROGRESS** | MIT selected; copyright line (`[year] [fullname]`) still needs owner name/year; change uncommitted |
| 3 | Sign off Phase 1 closure (`handover/PHASE-1-CLOSURE.md`) | **MANUAL** | Signature line provided |
| 4 | Approve the Phase 1 release package | **MANUAL** | See `docs/release/` |

## 2. Required Before Phase 2

| # | Action | Manual? | Notes |
|---|--------|---------|-------|
| 1 | Accept ADR-0001 (normalized `scores` table) | Decision | Not required for Phase 2, but recommended before Phase 3 |
| 2 | Approve removal of superseded `handover/AGENT-LOG.md` | **MANUAL** | Irreversible without git; ADR-0002 is accepted |
| 3 | Confirm git remote creation (GitHub) | DONE | Remote `origin` = `https://github.com/maatallah/AI-HUB.git` |
| 4 | Commit and push the `LICENSE` change | **MANUAL** | `git add LICENSE && git commit -m "Add MIT license with owner attribution" && git push -u origin main` |
| 5 | Authorize Phase 2 (Monitoring Engine) planning | Decision | After closure sign-off |

## 3. Optional Improvements

| # | Action | Notes |
|---|--------|-------|
| 1 | Update `START-HERE.md` to reference `logs/` and `projects/` | Done (2026-08-01) |
| 2 | Refresh `handover/CURRENT-STATE.md` / `SESSION-SUMMARY.md` for ADR-0002/0003 | CURRENT-STATE refreshed; SESSION-SUMMARY is a historical session record - left unchanged |
| 3 | Align `projects/registry.json` seed with amended schema (`renamed_to`, `has_credentials_remote`) | Non-blocking conformance |
| 4 | Run tests on a clean checkout | Done (49/49 passed, 2026-08-01) |
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

The following CANNOT be automated by an agent:

1. Completing and committing the MIT `LICENSE` (owner name/year + git commit).
2. Signing/approving the release (owner authority).
3. Removal of `handover/AGENT-LOG.md` (irreversible without git baseline).

Already completed by the owner: `git init` + baseline commit (`7ceac80`),
remote creation (`origin` = `https://github.com/maatallah/AI-HUB.git`).

See `docs/release/WAITING-FOR-OWNER.md` for the detailed action list.
