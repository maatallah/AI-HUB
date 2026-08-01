# ADR-0001: Model Score Representation

**Status:** ACCEPTED

**Date:** 2026-07-31

**Acceptance date:** 2026-08-01

**Acceptance note:** Accepted before Phase 3 (Scoring Engine). The normalized
`scores` table is added to `database/schema.sql`; the v1.1 scalar score
columns on `models` are retained for backward compatibility and superseded by
the `scores` table (their retirement is documented).

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

**Accepted: Option B - normalized `scores` table.**

A normalized `scores` table is introduced at the start of Phase 3 (Scoring
Engine) to satisfy v1.2 Section 1.2:

```
scores:
  id, model_id, dimension, value, confidence, source, scored_at, created_at
```

The v1.1 scalar score columns on `models` (`coding_score`, `reasoning_score`,
`latency_score`, `reliability_score`, `score_source`, `confidence_level`) are
superseded. They are retained in the schema for backward compatibility with
existing rows; new scores are stored in the `scores` table. Their removal is
deferred to a later cleanup migration.

## Consequences

* Positive: Phase 1 schema is stable and migration-free; v1.2 requirements
  remain satisfiable without redesign.
* Positive: score dimensions stay extensible (Article 9).
* Positive: per-score confidence, source and timestamp are native (v1.2
  Section 1.2).
* Negative: the v1.1 scalar columns on `models` remain present but redundant;
  their retirement is deferred to a cleanup migration.
* Follow-up: the `scores` table is added to `database/schema.sql`; the
  Architecture Specification v1.1 and Implementation Specification v1.2 are
  updated to reference it.

## Acceptance Criteria

This ADR is accepted when the Phase 3 planning agrees to the normalized
`scores` table and the specifications are updated accordingly.

**Acceptance status:** DONE (2026-08-01) - `scores` table added to
`database/schema.sql`; v1.2 Section 1.2 updated.
