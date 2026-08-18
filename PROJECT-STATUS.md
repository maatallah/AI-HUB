# PROJECT-STATUS.md

# AI-Hub — Project Dashboard

> Open in 30 seconds and know where the project stands.

---

**Current version:** v1.2 (Architecture v1.1 + Implementation Spec v1.2)

**Current phase:** Phase 5 — Connectors (VS Code / MCP) (Milestones 1-3
complete and closed; Milestone 4 full regression next; Phase 4 released)

**Completion %:** ~75% (Phases 1-4 released; Phase 5 Milestones 1-3 complete)

**Last update:** 2026-08-18

**Repository health:** Good (262/262 Python tests passing, no open defects;
connectors/vscode 27/27 TS unit tests + 2/2 integration tests passing)

**Blocking issues:** None. Phase 5 Milestones 1-3 (documentation, adapter +
MCP server, VS Code extension) complete; Milestones 4-5 (full regression,
release package) gated on owner approval.

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

Milestones 4 (full connector regression) and 5 (Phase 5 release package +
closure) pending owner approval. The documented transitive npm vulnerabilities
(serialize-javascript / mocha via `@vscode/test-cli`) are accepted; no
unrelated dependency upgrades are performed.

Configuration alignment is maintained (`config.toml` == `templates/config.toml`).

Release documents:

* `docs/release/PHASE1-RELEASE-MANIFEST.md` (immutable, git SHA `7ceac80`)
* `docs/release/PHASE2-RELEASE-MANIFEST.md` (immutable, git SHA `ae0a6c2`)
* `docs/release/PHASE3-RELEASE-MANIFEST.md` (immutable, git SHA `ff4b8a7`)
* `docs/release/PHASE4-RELEASE-MANIFEST.md` (immutable, git SHA `c49ea9b`,
  closure accepted)
* `docs/review/PHASE3-IMPLEMENTATION-PLAN.md`
* `docs/review/PHASE3-SCORING-SPEC.md`
* `docs/review/PHASE4-IMPLEMENTATION-PLAN.md`
* `docs/review/PHASE4-DASHBOARD-SPEC.md`
* `docs/review/PHASE5-CONNECTORS-SPEC.md`

## Architecture Maturity

* Specifications: v1.2 approved; agent-logging, project-registry, monitoring
  and scoring proposal specs documented.
* ADRs: ADR-0001, ADR-0002, ADR-0003 ACCEPTED.
* Reviews: R-01..R-08 amendments applied; final review PASS; Phase 2 and
  Phase 3 plans approved 2026-08-01; Phase 5 connectors spec in review.

## Pending Owner Decisions

* Approve Milestone 4 (full connector regression) - next step
* Approve Milestone 5 (Phase 5 release package + closure) at the end
* Owner-run `npm install` inside `connectors/vscode/` for local builds
  (already executed for verification; required for any later rebuilds)

## Next Milestone

Phase 5 Milestone 4 (full connector regression baseline), then Milestone 5
(Phase 5 release package + closure).

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
