"""Scoring engine (Phase 3).

Public API:
  * ``set_score`` / ``list_scores`` - stored scores in the ADR-0001 ``scores``
    table (sources: MANUAL, BENCHMARK, AUTOMATED_TEST, USER_FEEDBACK,
    OFFICIAL_INFORMATION).
  * ``effective_score`` - aged, deterministic score for a model dimension,
    combining stored scores with operational dimensions derived from Phase 2
    monitoring data.
  * ``derive_score`` - derived operational scores (availability, reliability,
    latency).

Rules (Constitution Article 10): missing scores are never fabricated. A model
without a score for a dimension simply has no score.
"""

from __future__ import annotations

from scoring.derive import DERIVED_DIMENSIONS, derive_score
from scoring.engine import effective_score, list_scores
from scoring.ingest import ALLOWED_SOURCES, ScoreError, set_score

__all__ = [
    "ALLOWED_SOURCES",
    "DERIVED_DIMENSIONS",
    "ScoreError",
    "derive_score",
    "effective_score",
    "list_scores",
    "set_score",
]
