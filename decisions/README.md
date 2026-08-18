# decisions/

Architecture Decision Records for AI-Hub.

Every significant architectural decision is recorded here (Specification v1.1
Section 20; Constitution Article 8).

## ADR Statuses

* **PROPOSED** - under review, not yet approved
* **ACCEPTED** - approved, implementation must follow it
* **SUPERSEDED** - replaced by a later ADR

## Registered ADRs

* ADR-0001 - Model Score Representation (ACCEPTED)
* ADR-0002 - Project-Aware Agent Logging Architecture (ACCEPTED)
* ADR-0003 - Project Registry and Workspace Discovery (ACCEPTED)
* ADR-0005 - Provider/Model Discovery Candidate Representation (ACCEPTED,
  Phase 6, D-P1)
* ADR-0006 - Benchmark Result Storage and Ingestion (ACCEPTED, Phase 6, D-P3)

**Numbering note:** ADR-0004 is **reserved** for the deferred point-in-time
score snapshots decision (referenced as such in `AI-Hub Project Specification
v1.2.md` Section 18.3 and the phase closures; deferred by Phase 6 decision
D-P8). It is deliberately not used by Phase 6; the Phase 6 decisions occupy
the next sequential numbers ADR-0005 and ADR-0006.

## Process

1. A contributor identifies an architectural question.
2. An ADR is written and placed in `decisions/` with status PROPOSED.
3. The decision is reviewed and either ACCEPTED, amended, or rejected.
4. When accepted, the specifications are updated to reflect it.
