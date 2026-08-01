# PHASE1-RELEASE-NOTES.md

# AI-Hub Phase 1 Release Notes

**Release:** Phase 1 - Repository Foundation

**Date:** 2026-08-01

**Specification:** v1.2

---

## What Phase 1 Accomplished

Phase 1 delivered the repository foundation that all future phases build
upon. It established the implementation baseline, a validated SQLite schema,
a safe configuration system, and a manual provider registry - without any
online monitoring, automation, or editor integration (deferred to later
phases).

### Repository Structure

A complete skeleton was created matching the phase roadmap: `app/`, `core/`,
`database/`, `monitoring/`, `connectors/`, `dashboard/`, `tests/`,
`scripts/`, `backup/`, `docs/`, `spec/`, `decisions/`, `templates/`,
`handover/`, and `projects/`. Empty directories mark future-phase work.

### Database

A SQLite database module (`database/database.py`) and documented schema
(`database/schema.sql`) implement the six core tables required by the
architecture: `providers`, `models`, `availability`, `events`,
`preferences`, and `recommendations`. The schema enforces the lifecycle
state set, append-only events, and NULL for unknown values.

### Configuration

A TOML-based configuration system (`app/config.py`) provides documented
defaults, validation of every known value, and rejection of any key that
looks like a secret (Constitution Article 6). Configuration alignment now
covers `logging.log_root`, `workspace.root`, and `registry.path`, matching
v1.2 Section 10.

### Provider Registry

A manual provider registry (`core/providers.py`) supports add, update, list,
and archive operations. Providers are archived, never deleted
(Constitution Article 5). A status reason is required whenever state is not
ACTIVE. An append-only event log (`core/events.py`) records activity.

### Seed Data

An idempotent seed script (`scripts/seed_providers.py`) registers nine
providers as metadata only (no secrets, no live calls): OpenAI, Google
Gemini, Anthropic, OpenRouter, Blackbox AI, DeepSeek, MiniMax, Qwen, and
GitHub Models.

### Test Framework

A pytest suite of 49 tests covers database creation and idempotency, schema
validation, configuration loading and safety, and provider registry
operations. All 49 tests pass.

### Architectural Governance

Two architecture decisions were accepted:

* **ADR-0002** - Project-Aware Agent Logging Architecture
* **ADR-0003** - Project Registry and Workspace Discovery

Two supporting specifications were documented:

* `spec/agent-logging.md`
* `spec/project-registry.md`

Architecture reviews (R-01..R-08 amendments, final constitutional review)
all passed with no remaining BLOCKERs.

---

## Not Included in This Release

* Monitoring engine (Phase 2)
* Scoring / recommendation / fallback engines (Phase 3)
* Dashboard (Phase 4)
* VS Code / MCP connectors (Phase 5)
* AI ecosystem intelligence (Phase 6)
* Model seeding

---

## Known Limitations

See `docs/release/PHASE1-RELEASE-MANIFEST.md` and
`docs/release/OWNER-CHECKLIST.md`. Key points: `LICENSE` is set to MIT but the
copyright line is still a placeholder and the change is not yet committed;
ADR-0001 remains PROPOSED for Phase 3; the registry seed does not yet carry
the R-01/R-07 schema fields.

---

## Next

Phase 2 (Monitoring Engine) planning is the intended follow-up once the
owner completes the mandatory manual actions.
