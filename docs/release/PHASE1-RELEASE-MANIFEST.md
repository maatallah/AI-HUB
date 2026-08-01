# PHASE1-RELEASE-MANIFEST.md

**Project name:** AI-Hub

**Release name:** Phase 1 - Repository Foundation

**Release date:** 2026-08-01

**Specification version:** v1.2 (Architecture v1.1 + Implementation Spec v1.2)

**Constitution version:** v1.0 (`CONSTITUTION.md`)

**Phase:** Phase 1 (of 6)

---

## ADR Status Summary

| ADR | Title | Status | Acceptance date |
|-----|-------|--------|-----------------|
| ADR-0001 | Model Score Representation | PROPOSED | - (recommended before Phase 3) |
| ADR-0002 | Project-Aware Agent Logging Architecture | **ACCEPTED** | 2026-07-31 |
| ADR-0003 | Project Registry and Workspace Discovery | **ACCEPTED** | 2026-07-31 |

ADR-0002 and ADR-0003 were accepted following the final constitutional
architecture review (`ARCHITECTURE-FINAL-REVIEW.md`, verdict PASS - no
BLOCKERs).

---

## Completed Milestones

* Phase 0 - Documentation and Architecture (specifications approved)
* Phase 1 - Repository Foundation (this release)
  * Repository skeleton
  * SQLite database + documented schema (6 tables)
  * Configuration system (TOML, validated, no secrets)
  * Manual provider registry (add / update / list / archive)
  * Append-only event log
  * Minimal CLI (`python -m app.main`)
  * Test framework (49 tests)
  * Provider seed dataset (9 providers)
  * Project registry seed (`projects/registry.json`)
  * ADR-0002 / ADR-0003 accepted

## Deferred Milestones

* Phase 2 - Monitoring Engine
* Phase 3 - Scoring, Recommendation, Fallback Engines (ADR-0001 `scores` table)
* Phase 4 - Dashboard
* Phase 5 - Connectors (VS Code, MCP)
* Phase 6 - AI Ecosystem Intelligence

---

## Directory Structure

```
AI-Hub/
  app/            __init__.py, config.py, main.py
  core/           __init__.py, providers.py, events.py
  database/       __init__.py, database.py, schema.sql
  monitoring/     (empty - Phase 2)
  connectors/     vscode/, mcp/ (empty - Phase 5)
  dashboard/      (empty - Phase 4)
  tests/          conftest.py, test_database.py, test_schema.py,
                  test_config.py, test_providers.py
  scripts/        seed_providers.py
  backup/         (empty)
  docs/           release/, review/ (review + release records)
  spec/           agent-logging.md, project-registry.md
  projects/       registry.json
  decisions/      README.md, 0001, 0002, 0003
  templates/      config.toml
  handover/       AGENT-HANDOVER.md, CURRENT-STATE.md, NEXT-STEPS.md,
                  SESSION-SUMMARY.md, AGENT-LOG.md (superseded),
                  PHASE-1-CLOSURE.md
  config.toml     documented defaults
  requirements.txt
  CHANGELOG.md
  LICENSE         placeholder (owner decision pending)
  PROJECT-STATUS.md
  START-HERE.md
  CONSTITUTION.md
```

## Implemented Modules

| Module | Responsibility |
|--------|----------------|
| `app/config.py` | Configuration load, merge, validation, secret-key rejection |
| `app/main.py` | CLI: `init-db`, `config show/validate`, `provider add/list/update/archive` |
| `core/providers.py` | Manual provider registry (archive, never delete) |
| `core/events.py` | Append-only event log |
| `database/database.py` | SQLite connection, schema init, validation |
| `database/schema.sql` | 6 tables: providers, models, availability, events, preferences, recommendations |
| `scripts/seed_providers.py` | Idempotent seed dataset (9 providers, metadata only) |

## Configuration Files

* `config.toml` - effective documented defaults
* `templates/config.toml` - template to copy to `config.toml`
* Keys: `database.path`, `monitoring.enabled`, `monitoring.interval_minutes`,
  `fallback.max_chain_length`, `recommendation.default_profile`,
  `dashboard.refresh_seconds`, `logging.level`, `logging.log_root`,
  `workspace.root`, `registry.path`

---

## Tests Executed

Command: `python -m pytest -q`

| Metric | Value |
|--------|-------|
| Tests collected | 49 |
| Passed | 49 |
| Failed | 0 |
| Skipped | 0 |
| Runtime | Python 3.14.2, pytest 9.1.1 |

Coverage areas: database creation/idempotency, schema validation (tables,
columns, FKs, CHECKs), configuration load/override/defaults/secret rejection,
provider CRUD + event logging.

---

## Review Documents

| Document | Result |
|----------|--------|
| `ARCHITECTURE-REVIEW-REPORT.md` | R-01..R-21 findings; R-01 BLOCKER resolved |
| `docs/review/amendment-summary-R01-R08.md` | All 8 amendments applied |
| `ARCHITECTURE-FINAL-REVIEW.md` | PASS; 3 minor SHOULD FIX (S-01..S-03, now resolved) |
| `docs/review/PHASE1-IMPLEMENTATION-READINESS.md` | Ready for Phase 2 |
| `docs/review/PHASE1-CLOSURE-CHECKLIST.md` | Closure package |

## Accepted ADRs

* ADR-0002 - Agent Logging Architecture (ACCEPTED, 2026-07-31)
* ADR-0003 - Project Registry and Discovery (ACCEPTED, 2026-07-31)

---

## Known Limitations

* Git repository not yet initialized; no version control baseline.
* `LICENSE` is a placeholder - owner must select a license.
* ADR-0001 (normalized `scores` table) is PROPOSED; schema migration required
  before Phase 3.
* `handover/AGENT-LOG.md` is superseded by ADR-0002; removal pending (requires
  owner confirmation - irreversible without git).
* `START-HERE.md` does not yet reference `logs/` and `projects/` (ADR-0002
  follow-up).
* `projects/registry.json` seed entry predates the R-01/R-07 schema fields
  (`renamed_to`, `repository.has_credentials_remote`); conformance update
  recommended (non-blocking).
* `handover/CURRENT-STATE.md` and `SESSION-SUMMARY.md` do not yet reflect
  ADR-0002/0003 acceptance (stale living docs).
* Discovery is a future capability - NOT implemented.

---

## Future Roadmap

* Phase 2 - Monitoring Engine (provider health, quota, availability,
  lifecycle enforcement)
* Phase 3 - Scoring / Recommendation / Fallback Engines; ADR-0001 migration
* Phase 4 - Dashboard and reporting
* Phase 5 - Connectors (VS Code, MCP)
* Phase 6 - AI Ecosystem Intelligence, benchmark integration, trend analysis
* Model seeding

## Owner Actions Still Required

See `docs/release/OWNER-CHECKLIST.md` and
`docs/release/WAITING-FOR-OWNER.md`.

* Initialize git + first commit (mandatory, manual)
* Select a `LICENSE` (mandatory, manual)
* Decide on repository publication (mandatory, manual)
* Accept ADR-0001 (before Phase 3)
* Sign off Phase 1 closure

## Phase 2 Entry Criteria

1. Git initialized and Phase 1 baseline committed.
2. Owner sign-off of Phase 1 closure.
3. `LICENSE` selected (owner decision).
4. Config alignment confirmed (log_root, workspace.root, registry.path).
5. ADR-0002 / ADR-0003 accepted (done).
6. S-01 / S-02 / S-03 resolved (done).

---

## Checksum Table (SHA-256)

Computed 2026-08-01 for release integrity (pre-git baseline).

| File | SHA-256 (prefix 16) |
|------|---------------------|
| `database/schema.sql` | `33DA68C2F2C0E266` |
| `database/database.py` | `DAD111BBD89AB960` |
| `app/config.py` | `BDF93EAF8FEF67C4` |
| `app/main.py` | `03F119228BA8FC43` |
| `core/providers.py` | `C1847480790BDD1E` |
| `core/events.py` | `630F4E13BF9E3F36` |
| `scripts/seed_providers.py` | `5D53C3FAA550E2EC` |
| `config.toml` | `2B58524F525961F8` |
| `templates/config.toml` | `9F4E65EFEC042312` |
| `projects/registry.json` | `EDA9BB72628507BF` |
| `CONSTITUTION.md` | `71A3E9D5DCBC57A2` |
| `AI-Hub Project Specification v1.2.md` | `617D00297930A6F1` |
| `spec/agent-logging.md` | `91BF7CAA970A7545` |
| `spec/project-registry.md` | `66897CAD3F5340CF` |
