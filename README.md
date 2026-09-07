# AI-Hub

AI Provider Intelligence and Routing Platform.

AI-Hub is an independent intelligence layer that monitors AI providers, evaluates models, recommends suitable AI resources for a given task, and builds safe fallback chains. It does not execute prompts or control development environments — it recommends.

---

## Implemented Phases

Phases 1–6 are implemented and released:

* **Phase 1 — Repository Foundation** — SQLite database, schema, configuration system, manual provider registry, append-only event log, CLI.
* **Phase 2 — Monitoring Engine** — Health checks, availability/lifecycle tracking, quota architecture, seed validation.
* **Phase 3 — Scoring / Recommendation / Fallback** — Normalized scoring engine, deterministic recommendation with provenance, fallback chain construction.
* **Phase 4 — Dashboard / Reporting / History** — Read-only aggregate views, deterministic plain-text reports, append-only event-derived history.
* **Phase 5 — Connectors** — Shared read-only adapter, MCP server over stdio, VS Code extension.
* **Phase 6 — Ecosystem Intelligence** — Discovery candidates, benchmark ingestion, approval materialization, model registry, trend analysis.

---

## Post-v1 Adaptive Routing (M1–M4)

Post-v1 adaptive routing milestones M1–M4 are complete:

* **M1** — DECIDE is unconditionally read-only (zero writes under every input combination).
* **M2** — RECORD is append-only persistence through the existing provenance path.
* **M3** — Canonical cost-direction fix (descending sort) and `decision_version` bump to `3.1.0`.
* **M4** — Configuration and template alignment (`decision_version` `3.1.0` in `config.toml` and `templates/config.toml`).

`decision_version` is `3.1.0`. `contract_version` is `"1"`.

---

## Real-World Routing Experiment

The post-v1 routing real-world experiment is closed:

* **Tasks 1–7:** PASS
* **Task 8:** BLOCKED — the approved experiment scope did not specify which function was to be refactored to async/await.
* **Classification:** COMPLETE WITH BLOCKED TASK

See `docs/review/POST-V1-ROUTING-REAL-WORLD-EXPERIMENT-CLOSURE.md` for the full closure record.

---

## Current State and Governance Boundary

Current work is reconciliation/documentation correction, tracked in:
`docs/review/POST-V1-RECONCILIATION-CORRECTIONS.md`

**Post-v1 adaptive-routing M5 is NOT AUTHORIZED.** No adaptive learning, feedback ingestion, telemetry, or other M5 implementation should be started without explicit owner authorization and an approved scope.

---

## Key Documents

| Document | Purpose |
|----------|---------|
| `CONSTITUTION.md` | Permanent governance principles |
| `START-HERE.md` | Entry point for new agents/contributors |
| `handover/CURRENT-STATE.md` | Current repository state |
| `handover/NEXT-STEPS.md` | Next steps and completed milestones |
| `handover/AGENT-HANDOVER.md` | Agent handover document |
| `docs/review/POST-V1-RECONCILIATION-CORRECTIONS.md` | Reconciliation corrections log |
| `docs/review/POST-V1-ROUTING-REAL-WORLD-EXPERIMENT-SCOPE.md` | Experiment scope |
| `docs/review/POST-V1-ROUTING-REAL-WORLD-EXPERIMENT-CLOSURE.md` | Experiment closure record |

---

Start here: `START-HERE.md`
