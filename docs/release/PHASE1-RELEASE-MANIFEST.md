# PHASE1-RELEASE-MANIFEST.md

# AI-Hub Phase 1 Release Manifest (Immutable Baseline)

**Project name:** AI-Hub

**Release name:** Phase 1 - Repository Foundation

**Phase number:** Phase 1 (of 6)

**Release date:** 2026-08-01

**Git commit SHA:** `7ceac80c9b0b1718ec090307b2220e1350ca85dd`

**Current branch:** `main`

**Git remote:** `origin` (https://github.com/maatallah/AI-HUB.git)

**Specification version:** v1.2 (Architecture v1.1 + Implementation Spec v1.2)

**Constitution version:** v1.0 (`CONSTITUTION.md`)

> This document is the immutable reference baseline for Phase 2. It records
> the state at release. Later project evolution must not rewrite it.

---

## ADR Status Summary

| ADR | Title | Status | Acceptance date |
|-----|-------|--------|-----------------|
| ADR-0001 | Model Score Representation | PROPOSED | - (recommended before Phase 3) |
| ADR-0002 | Project-Aware Agent Logging Architecture | **ACCEPTED** | 2026-07-31 |
| ADR-0003 | Project Registry and Workspace Discovery | **ACCEPTED** | 2026-07-31 |

### Accepted ADR list

* ADR-0002 - Agent Logging Architecture
* ADR-0003 - Project Registry and Discovery

### Deferred ADR list

* ADR-0001 - Model Score Representation (PROPOSED; normalized `scores` table
  planned for Phase 3)

---

## Version Summary

| Artifact | Version |
|----------|---------|
| SQLite schema | Generation 1 (`database/schema.sql`, 6 tables) - no explicit version field; candidates: providers, models, availability, events, preferences, recommendations |
| Configuration | v1.2 Section 10 key set (10 keys across database, monitoring, fallback, recommendation, dashboard, logging, workspace, registry) |
| Project registry | `registry_version: 1` (`projects/registry.json`) |
| Seed provider registry | `scripts/seed_providers.py` - 9 providers (OpenAI, Google Gemini, Anthropic, OpenRouter, Blackbox AI, DeepSeek, MiniMax, Qwen, GitHub Models) |

---

## Test Summary

Command: `python -m pytest -q` (run 2026-08-01 during release verification)

| Metric | Value |
|--------|-------|
| Tests collected | 49 |
| Passed | 49 |
| Failed | 0 |
| Skipped | 0 |

Coverage: database creation/idempotency, schema validation (tables, columns,
FKs, CHECKs), configuration load/override/defaults/secret rejection, provider
CRUD + event logging.

## Environment

* Python version: 3.14.2
* pytest: 9.1.1
* Platform used for verification: Windows (win32)

---

## Review Documents Included

| Document | Result |
|----------|--------|
| `ARCHITECTURE-REVIEW-REPORT.md` | R-01..R-21 findings; R-01 BLOCKER resolved |
| `docs/review/amendment-summary-R01-R08.md` | All 8 amendments applied |
| `ARCHITECTURE-FINAL-REVIEW.md` | PASS; S-01..S-03 minor (now resolved) |
| `docs/review/PHASE1-IMPLEMENTATION-READINESS.md` | Ready for Phase 2 |
| `docs/review/PHASE1-CLOSURE-CHECKLIST.md` | Closure package |
| `docs/release/PHASE1-CLOSURE-SUMMARY.md` | This release's closure summary |

## Deliverables Completed

* Repository skeleton (all specified folders)
* SQLite database module + documented schema (6 tables)
* Configuration system (TOML, validated, no secrets)
* Manual provider registry (add / update / list / archive)
* Append-only event log
* Minimal CLI (`python -m app.main`)
* Test framework (49 tests, all passing)
* Provider seed dataset (9 providers)
* Project registry seed (`projects/registry.json`)
* ADR-0002 / ADR-0003 accepted
* Configuration alignment (log_root, workspace.root, registry.path)
* Documentation consistency cleanup (S-01/S-02/S-03)
* Release package (`docs/release/`)

## Deferred Work

* Phase 2 - Monitoring Engine
* Phase 3 - Scoring, Recommendation, Fallback Engines (ADR-0001 migration)
* Phase 4 - Dashboard
* Phase 5 - Connectors (VS Code, MCP)
* Phase 6 - AI Ecosystem Intelligence
* Model seeding

## Known Limitations

* `LICENSE` changed to MIT but the copyright line still contains template
  placeholders (`[year] [fullname]`) and the change is NOT yet committed
  (see Owner decisions).
* `projects/registry.json` seed entry does not yet carry the R-01/R-07 schema
  fields (`renamed_to`, `repository.has_credentials_remote`) - non-blocking.
* `handover/AGENT-LOG.md` is superseded by ADR-0002; removal pending owner
  confirmation.
* Workspace discovery is a future capability - NOT implemented.

## Remaining Owner Decisions

* Fill the MIT copyright line (`[year] [fullname]`), then commit and push the
  `LICENSE` change.
* Accept ADR-0001 (before Phase 3).
* Sign off Phase 1 closure (signature line in
  `handover/PHASE-1-CLOSURE.md`).
* Authorize Phase 2 planning.

---

## Release Readiness Statement

Phase 1 is **functionally ready for Phase 2**: 49/49 tests pass, the git
baseline is committed (`7ceac80`), ADR-0002/ADR-0003 are accepted, and all
documentation is internally consistent. The release is **READY WITH OWNER
ACTION REQUIRED** only because the MIT license is not yet committed and its
copyright line is incomplete.

---

## Checksums (SHA-256, prefix 16)

Computed 2026-08-01 for the major specification and implementation files.

| File | SHA-256 (prefix 16) |
|------|---------------------|
| `CONSTITUTION.md` | `71A3E9D5DCBC57A2` |
| `AI-Hub Project Specification v1.2.md` | `617D00297930A6F1` |
| `spec/agent-logging.md` | `91BF7CAA970A7545` |
| `spec/project-registry.md` | `66897CAD3F5340CF` |
| `database/schema.sql` | `33DA68C2F2C0E266` |
| `app/config.py` | `BDF93EAF8FEF67C4` |
| `core/providers.py` | `C1847480790BDD1E` |
| `config.toml` | `2B58524F525961F8` |
| `projects/registry.json` | `EDA9BB72628507BF` |

---

*End of Phase 1 Release Manifest. Immutable from 2026-08-01.*
