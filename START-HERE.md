# START-HERE.md

# AI-Hub

**Current Project Version**

Architecture Specification: **v1.1**

Implementation Specification: **v1.2**

Project Status: **Phase 1 Released – Ready for Phase 2 (after owner actions)**

---

# Welcome

Before writing a single line of code, read this repository in the following order.

1. `README.md`
2. `CONSTITUTION.md`
3. `AI-Hub Project Specification v1.2.md` (Architecture v1.1 included)
4. `spec/agent-logging.md` (ADR-0002)
5. `spec/project-registry.md` (ADR-0003)
6. `handover/AGENT-HANDOVER.md`
7. `handover/CURRENT-STATE.md`
8. `handover/NEXT-STEPS.md`
9. `handover/SESSION-SUMMARY.md`
10. `docs/release/PHASE1-RELEASE-MANIFEST.md`

Do not begin implementation until these documents have been reviewed.

---

# Project Mission

AI-Hub is a repository-independent intelligence platform that monitors AI providers, evaluates models, recommends the most appropriate AI for a task, and builds safe fallback chains.

Its purpose is to help developers make informed decisions—not to automatically control their development environment.

---

# Current Development Phase

**Phase 1 – Repository Foundation (RELEASED, baseline `7ceac80`)**

Deliverables:

* Create repository structure
* Create SQLite database
* Implement documented schema
* Create manual provider registry
* Implement configuration system
* No online monitoring yet
* No VS Code integration yet

Runtime directories created by the project (ADR-0002/ADR-0003):

* `logs/` — agent session logs (see `spec/agent-logging.md`)
* `projects/` — project registry (`projects/registry.json`, see
  `spec/project-registry.md`)

---

# Mandatory Rules

* Never modify user API keys.
* Never modify editor configuration automatically.
* Never silently remove providers.
* Recommendations must always be explainable.
* Unknown information must remain marked as unknown.
* Architecture changes require an ADR.
* Behaviour changes require specification updates.

---

# Before Every Commit

Confirm:

☐ Specifications remain consistent.

☐ Constitution is respected.

☐ No undocumented architectural change.

☐ Session summary updated.

☐ Next recommended task identified.

---

# Current Highest Priority

Implement the repository skeleton exactly as defined in the specifications.

No optimisation.

No additional features.

No architectural redesign.

---

# Repository Authority

When documentation and implementation disagree:

**Documentation is authoritative.**

The implementation must be corrected or the documentation must be formally updated through an Architecture Decision Record (ADR).
