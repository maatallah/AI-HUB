# PROJECT-STATUS.md

# AI-Hub — Project Dashboard

> Open in 30 seconds and know where the project stands.

---

**Current version:** v1.2 (Architecture v1.1 + Implementation Spec v1.2)

**Current phase:** Phase 6 — Ecosystem Intelligence (planning baseline
approved 2026-08-18; Milestone 1 documentation complete; Milestone 2
(discovery + candidate workflow) implemented and committed 2026-08-18;
Milestones 3-6 not authorized)

**Completion %:** ~88% (Phases 1-5 released; Phase 6 planning + M1
documentation + M2 discovery/candidate workflow complete; implementation
milestones 3-6 pending authorization)

**Last update:** 2026-08-18

**Repository health:** Good (337/337 Python tests passing, no open defects;
adapter/MCP 48/48; connectors/vscode 28/28 TS unit tests + 2/2 integration
tests passing)

**Blocking issues:** None. Phase 5 released and closed (2026-08-18, baseline
`8231dce`). Phase 6 planning baseline approved (D-P1..D-P9), M1 doc-before-code
complete, and M2 (discovery + candidate workflow) implemented; M3-M6 not yet
authorized.

---

## Current Phase

Phase 1 released (baseline `7ceac80`). Phase 2 — Monitoring Engine released
(commit `ae0a6c2`, manifest `2c6e3eb`, 99/99 tests). ADR-0001 accepted
(commit `74d23b5`). Phase 3 — Scoring / Recommendation / Fallback implemented
and released (implementation `d6dd3c9`, manifest `ff4b8a7`, closure
`c6327f4`, approval `8370ba0`; 162/162 tests):

* Scoring engine (`scoring/`): normalized `scores` table (ADR-0001), aging,
  operational dimensions derived from monitoring, no fabricated values.
* Recommendation engine (`recommendation/`): built-in + custom profiles,
  deterministic ranking, explainability, provenance records.
* Fallback engine (`fallback/`): deterministic chain, eligibility from
  monitoring, recovery handling.
* CLI: `score`, `recommend`, `fallback` subcommands.
* Tests: 162/162 passing (59 new in Phase 3).

Phase 4 — Dashboard / Reporting / History authorized 2026-08-17 (plan
baseline `f9316e4`). Documentation step (Article 11 doc-before-code) completed
in `36d4aef`; implementation completed in `c49ea9b` (release commit):

* `dashboard/engine.py` - read-only aggregate views (overview, provider,
  score, recommendation, event).
* `dashboard/reports.py` - deterministic plain-text report builders
  (`providers`, `scores`, `recommendations`, `monitoring`, `overview`).
* `dashboard/history.py` - append-only event-derived score/availability
  history; point-in-time snapshots deferred pending ADR-0004.
* CLI: `dashboard status`, `dashboard report <name>`, `dashboard history`.
* No schema changes, no new dependencies, no new config keys/event types.
* Tests: 216/216 passing (54 new in Phase 4).
* Phase 4 release approved and closed (2026-08-17, commit `3c47c61`,
  manifest `docs/release/PHASE4-RELEASE-MANIFEST.md` status = closure
  accepted, baseline `c49ea9b`).

Phase 5 — Connectors (VS Code / MCP) approved 2026-08-17 (revised planning
proposal). Milestones 1-3 complete:

* Milestone 1 (docs): `docs/review/PHASE5-CONNECTORS-SPEC.md`, spec v1.2
  Section 19 - Connectors (Phase 5).
* Milestone 2 (adapter + MCP server): `connectors/adapter.py` (single
  read-only application interface delegating to Phase 1-4 modules,
  stdlib MCP subset over stdio, Tools capability only, legacy protocol era
  `2024-10-07`..`2025-11-25`), `connectors/mcp/` (`server.py`, `tools.py`).
  46 new tests (adapter 19, MCP 27); 262 Python tests total.
* Milestone 3 (VS Code extension): `connectors/vscode/` - 7 commands, reports
  tree view + webview panels, read-only CLI invocation, isolated npm graph
  (D-4). 27 offline TS unit tests + 2 real VS Code integration tests.
  Approved and closed by owner 2026-08-18.
* Milestone 4 (full connector regression) VERIFIED (2026-08-18): complete
  Python regression 262/262 (184s), Phase 5 MCP/adapter tests 46/46 (35s),
  VS Code offline unit tests 27/27, real VS Code integration tests 2/2;
  `git diff --check` clean; M1-M3 baseline `5cff03b` intact.
* Milestone 5 (hardening / release readiness) complete (2026-08-18): 3 new
  tests closing genuine coverage gaps (MCP `-32603` internal-error mapping;
  MCP empty database returns empty for every tool, never fabricated; VS Code
  `package.json` command/activationEvents consistency with `FEATURES`);
  living docs refreshed.

Milestones 1-4 are complete and closed; the Phase 5 release package (manifest
+ closure) was approved and the phase CLOSED 2026-08-18 (baseline `8231dce`,
manifest `docs/release/PHASE5-RELEASE-MANIFEST.md` status = closure accepted
in `handover/PHASE-5-CLOSURE.md`). The documented transitive npm
vulnerabilities (serialize-javascript / mocha via `@vscode/test-cli`) are
accepted; no unrelated dependency upgrades are performed.

Configuration alignment is maintained (`config.toml` == `templates/config.toml`).

Phase 6 — Ecosystem Intelligence authorized 2026-08-18. Planning baseline
approved (D-P1..D-P9) as commit `8f01b10`
(`docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md`). Milestone 1
(doc-before-code, Article 11) complete:

* `AI-Hub Project Specification v1.2.md` Section 20 - Ecosystem Intelligence
  (Phase 6): discovery candidates (D-P1), provenance-aware benchmark storage
  (D-P3), deterministic read-only trend analysis, security/mutation
  boundaries, config/events/dependencies.
* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md` - proposal spec
  (discovery + benchmark + trend + model registry; CLI-only D-P6; milestones
  and acceptance criteria).
* ADR-0005 (D-P1 discovery candidate representation) and ADR-0006 (D-P3
  benchmark result storage), both ACCEPTED. ADR-0004 remains reserved for the
  deferred score-snapshots decision (D-P8).
* Living docs refreshed. No implementation code changes.

Milestone 2 (discovery + candidate workflow) authorized and implemented
(2026-08-18, owner authorization against M1 baseline `d32324a`):

* Additive `discovery_candidates` table (ADR-0005 DDL; state CHECK
  `DISCOVERED/PENDING_REVIEW/APPROVED/REJECTED`; `provider_name` UNIQUE) in
  `database/schema.sql`, added to `EXPECTED_TABLES`.
* `discovery/` module - `sources.py` (curated JSON import, record validation,
  secret scanning, URL sanitization, injectable urllib transport) and
  `engine.py` (candidate lifecycle add/list/queue/approve/reject; per-dataset
  atomic validation; duplicate reporting; controlled network run with
  snapshot-before-analysis, D-P2).
* `discovery approve/reject` are deterministic candidate-state transitions
  only in M2; provider/model materialization belongs to Milestone 3.
* New whitelisted events: `DISCOVERY_CANDIDATE_ADDED`,
  `DISCOVERY_IMPORT_COMPLETE`, `DISCOVERY_IMPORT_ERROR`,
  `DISCOVERY_CANDIDATE_APPROVED`, `DISCOVERY_CANDIDATE_REJECTED`.
* `[discovery]` config keys validated and mirrored in `config.toml` /
  `templates/config.toml` (`enabled` master switch default false;
  `allowlisted_urls` default empty; `timeout_seconds`; `import_dir`).
* CLI (additive): `discovery import`, `discovery run --allow-network`,
  `discovery list [--state]`, `discovery approve`, `discovery reject`.
* Tests: `tests/test_discovery.py` + `tests/test_discovery_cli.py`; full
  Python suite 337/337 (264 base + 73 new); adapter/MCP 48/48; VS Code 28/28
  unit + 2/2 integration; `git diff --check` clean. No benchmark/trend/model
  registry code (M3-M5), no connectors changes (D-P6), `requirements.txt` and
  npm graph unchanged.

Milestone 3 (approval materialization + model registry) requires a separate
owner authorization (D-P9 sequential gates).

Release documents:

* `docs/release/PHASE1-RELEASE-MANIFEST.md` (immutable, git SHA `7ceac80`)
* `docs/release/PHASE2-RELEASE-MANIFEST.md` (immutable, git SHA `ae0a6c2`)
* `docs/release/PHASE3-RELEASE-MANIFEST.md` (immutable, git SHA `ff4b8a7`)
* `docs/release/PHASE4-RELEASE-MANIFEST.md` (immutable, git SHA `c49ea9b`,
  closure accepted)
* `docs/release/PHASE5-RELEASE-MANIFEST.md` (immutable, git SHA `8231dce`,
  closure accepted)
* `docs/review/PHASE3-IMPLEMENTATION-PLAN.md`
* `docs/review/PHASE3-SCORING-SPEC.md`
* `docs/review/PHASE4-IMPLEMENTATION-PLAN.md`
* `docs/review/PHASE4-DASHBOARD-SPEC.md`
* `docs/review/PHASE5-CONNECTORS-SPEC.md`

## Architecture Maturity

* Specifications: v1.2 approved; agent-logging, project-registry, monitoring
  and scoring proposal specs documented.
* ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0005, ADR-0006 ACCEPTED (ADR-0004
  reserved for the deferred score-snapshots decision, D-P8).
* Reviews: R-01..R-08 amendments applied; final review PASS; Phase 2 and
  Phase 3 plans approved 2026-08-01; Phase 5 connectors spec in review.

## Pending Owner Decisions

* Authorize Phase 6 Milestone 3 (approval materialization + model registry)
  implementation when ready (D-P9 sequential gates)
* Owner-run `npm install` inside `connectors/vscode/` for local builds
  (already executed for verification; required for any later rebuilds)

## Next Milestone

Phase 6 Milestone 3 (approval materialization + model registry: approve ->
provider (+models) via governed ops; `core/models.py`; `MODEL_*` events;
`model list`), once authorized by the owner.

## Open Documentation Items

* `projects/registry.json` seed conformance (`renamed_to`,
  `has_credentials_remote`) - non-blocking

## Risk Assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Provider API endpoints change rapidly | High | Seed is metadata only; `monitor validate` reports status |
| Architecture drift | Medium | ADRs + specs + reviews |
| Temporary outages mistaken for retirement | Medium | Lifecycle rules (v1.2 Section 5) enforced in Phase 2 |
| Schema drift between spec and implementation | Low | Schema tests assert spec columns |
| Network dependence of health checks | Medium | Injected transports; tests run offline |
| Score staleness | Medium | Aging multipliers (v1.2 Section 4) + configurable boundaries |
