# START-HERE.md

# AI-Hub

**Current Project Version**

Architecture Specification: **v1.1**

Implementation Specification: **v1.2**

Project Status: **Documentation Complete – Ready for Phase 1 Implementation**

---

# Welcome

Before writing a single line of code, read this repository in the following order.

1. `README.md`
2. `CONSTITUTION.md`
3. `docs/01-Vision.md`
4. `docs/02-Requirements.md`
5. `docs/03-Architecture.md`
6. `docs/04-Database-Schema.md`
7. `docs/06-Scoring-Engine.md`
8. `docs/07-Fallback-Engine.md`
9. `docs/09-Security.md`
10. `docs/13-Roadmap.md`
11. `handover/AGENT-HANDOVER.md`
12. `handover/CURRENT-STATE.md`
13. `handover/NEXT-STEPS.md`
14. `handover/SESSION-SUMMARY.md`

Do not begin implementation until these documents have been reviewed.

---

# Project Mission

AI-Hub is a repository-independent intelligence platform that monitors AI providers, evaluates models, recommends the most appropriate AI for a task, and builds safe fallback chains.

Its purpose is to help developers make informed decisions—not to automatically control their development environment.

---

# Current Development Phase

**Phase 1 – Repository Foundation**

Deliverables:

* Create repository structure
* Create SQLite database
* Implement documented schema
* Create manual provider registry
* Implement configuration system
* No online monitoring yet
* No VS Code integration yet

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
