# ADR-0001: Model Score Representation

**Status:** PROPOSED

**Date:** 2026-07-31

**Author:** Phase 1 Implementation Agent

---

## Context

Two specifications describe model scoring differently.

The **Architecture Specification v1.1 (Section 8)** models scores as scalar
columns on the `models` table:

```
coding_score, reasoning_score, latency_score, reliability_score,
score_source, confidence_level
```

The **Implementation Specification v1.2 (Section 1.2)** requires every model
to maintain independent scores across more dimensions:

* Capability: Coding, Reasoning, Mathematics, Long-context handling, Vision,
  Tool Calling
* Operational: Availability, Reliability, Latency, Cost, Stability

v1.2 also requires that every score records `value`, `confidence`,
`timestamp` and `source` (v1.2 Section 1.2).

## Problem

The scalar columns defined in v1.1 cannot represent v1.2's full dimension
set (Mathematics, Long-context, Vision, Tool Calling, Cost, Stability are
missing), nor can they carry a per-score timestamp. Adding a dimension would
require a schema migration - contradicting Constitution Article 9
(extensibility without redesign).

## Options Considered

### Option A - Keep scalar columns (v1.1 as-is)

Pro: matches v1.1 literally.

Con: cannot represent v1.2 dimensions or per-score timestamps; every new
dimension needs a migration. Fails Constitution Article 9.

### Option B - Normalized `scores` table

```
scores:
  id, model_id, dimension, value, confidence, source, scored_at, created_at
```

Pro: any dimension (including custom benchmarks, Article 9) is a row, not a
migration; per-score confidence and timestamp are native; matches v1.2.

Con: diverges from the literal v1.1 column list; Phase 1 registry does not
need scores yet.

## Decision

**Not decided yet - proposed for Phase 3.**

For Phase 1, the `models` table keeps the v1.1 scalar columns
(`coding_score`, `reasoning_score`, `latency_score`, `reliability_score`,
`score_source`, `confidence_level`), because scoring is out of Phase 1 scope.

The recommendation is to introduce a normalized `scores` table at the start
of Phase 3 (Scoring Engine) to satisfy v1.2 Section 1.2, superseding the
scalar score columns on `models`.

## Consequences

* Positive: Phase 1 schema is stable and migration-free; v1.2 requirements
  remain satisfiable without redesign.
* Positive: score dimensions stay extensible (Article 9).
* Negative: a migration or column retirement will be needed when Phase 3
  begins; the v1.1 scalar columns become redundant.
* Follow-up: update `database/schema.sql` and the `models` section of the
  Architecture Specification when this ADR is accepted.

## Acceptance Criteria

This ADR is accepted when the Phase 3 planning agrees to the normalized
`scores` table and the specifications are updated accordingly.
