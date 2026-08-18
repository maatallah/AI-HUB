# ADR-0006: Benchmark Result Storage and Ingestion

**Status:** ACCEPTED

**Date:** 2026-08-18

**Author:** Phase 6 M1 Release Engineer

**Acceptance date:** 2026-08-18

**Acceptance note:** Accepted with the owner's approval of Phase 6 planning
decision **D-P3** and the Phase 6 Milestone 1 (doc-before-code) milestone
(2026-08-18). This ADR satisfies D-P3's "ADR before implementation"
requirement.

**Related documents:**

* `AI-Hub Project Specification v1.2` - Section 20 (Ecosystem Intelligence,
  Phase 6); Section 1.2/1.3 (score categories and sources; `BENCHMARK`)
* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-PLANNING.md` (planning baseline,
  D-P3)
* `docs/review/PHASE6-ECOSYSTEM-INTELLIGENCE-SPEC.md` (proposal spec,
  Section 3)
* `decisions/0001-model-score-representation.md` (normalized `scores` table;
  "any dimension is a row, never a migration")
* `scoring/ingest.py` (`ALLOWED_SOURCES` includes `BENCHMARK`),
  `database/schema.sql` (`scores` table and source CHECK)

---

## Context

`BENCHMARK` is a permitted `scores.source` (`scoring/ingest.py:19`;
CHECK at `database/schema.sql:80`), and ADR-0001 already makes any dimension a
row in the normalized `scores` table. However, no benchmark ingestion
pipeline exists: `BENCHMARK` can only be passed as a single-score source
string to `set_score`, with no batch import, no run metadata, and no audit
trail of "which benchmark, when, from where".

## Problem

How should published benchmark results be ingested so that AI-Hub stores them
as provenance-backed `BENCHMARK`-sourced scores while preserving the raw
values, source attribution and retrieval metadata, without fabricating data
and without breaking the `scores` model?

## Options Considered

### Option A - Dedicated provenance-aware benchmark tables (recommended)

Additive `benchmark_runs` and `benchmark_results` tables (run identity,
version, origin, content hash, submitter, mapping) that preserve raw metric
values independently of the score mapping; mapped values update the `scores`
table with `source = 'BENCHMARK'` via the existing upsert semantics.

Pro: raw values and retrieval metadata never lost; mapping documented per run;
auditable and reproducible within documented limitations (Article 8);
scores model untouched (ADR-0001 preserved).

Con: two new additive tables (requires this ADR - satisfied).

### Option B - Schema-free mapping only

Encode benchmark identity in dimension names (e.g. `benchmark:mmlu`) or in
the score `scored_at`/payload, with no dedicated tables.

Pro: no new tables.

Con: raw values and run-level provenance are degraded; UNIQUE
(model_id, dimension) and the canonical dimension vocabulary become polluted;
trend/audit queries are fragile. Rejected.

## Decision

Adopt **Option A - persistent, provenance-aware benchmark storage** (D-P3).

* New additive tables `benchmark_runs` and `benchmark_results` (schema sketch
  in the Phase 6 proposal spec, Section 3.2) preserving source attribution
  and retrieval metadata (origin, fetched_at, content hash, imported_at,
  submitter) and every raw value (`metric`, `raw_value`, deterministic
  `norm_value`).
* Mapped, validated rows update the `scores` table with `source = 'BENCHMARK'`
  through the existing `scoring.ingest.set_score` upsert (UNIQUE
  (model_id, dimension)); normalization to 0-100 is deterministic and the
  metric->dimension formula is recorded on the run `mapping`.
* Batch ingestion is atomic per file (any invalid row fails the whole import
  with a recorded error; no partial writes); `--dry-run` validates without
  mutation.
* Benchmark data is **never fabricated** (Article 10); raw values always
  remain queryable via `benchmark_results`.
* Every successful import records a `BENCHMARK_IMPORTED` event (whitelist
  extension; Article 8).
* Ageing (v1.2 Section 4) applies to ingested scores unchanged; `scored_at` =
  run date.

## Consequences

* Positive: provenance and reproducibility for every benchmark import;
  raw-vs-mapped values both preserved.
* Positive: ADR-0001 normalized scores model untouched; recommendation
  formula unaffected.
* Positive: additive schema pattern matches ADR-0001/ADR-0005 precedent.
* Negative: two new tables and a validation/mapping layer to implement
  (Phase 6 Milestone 4).
* Follow-up: implement `benchmark/` module, storage and CLI in Phase 6
  Milestone 4; extend `core/events.py` with `BENCHMARK_IMPORTED`.

**Numbering note:** ADR-0004 is reserved for the deferred point-in-time score
snapshots decision (referenced as such across the specification and phase
closures; deferred by D-P8). ADR-0005 (discovery candidates, D-P1) and this
ADR-0006 are the Phase 6 decisions.

## Acceptance Criteria

This ADR is accepted when:

* the owner approves D-P3 and Milestone 1 (2026-08-18) - DONE
* v1.2 Section 20 and the Phase 6 proposal spec document the persistent,
  provenance-aware benchmark storage - DONE (Milestone 1)
* the `benchmark/` module and storage are implemented behind the M4 milestone
  gate with tests (atomic import, dry-run, provenance, no fabrication,
  BENCHMARK-source score mapping)