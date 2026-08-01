"""Recommendation engine (Phase 3).

Deterministic, explainable model ranking (v1.2 Sections 2, 3, 7):

  1. Load profile weights.
  2. Filter models: eligible provider status, context sufficiency, required
     capabilities (v1.2 Section 7 Step 2).
  3. Score each dimension via ``scoring.engine.effective_score`` (aging
     applied; operational dimensions derived from monitoring).
  4. Final = sum(profile weight x dimension score); no hidden weighting.
  5. Sort deterministically (v1.2 Section 7 Step 4).

Missing dimensions contribute 0 and are flagged "insufficient data" in the
explanation (Constitution Article 10 - never fabricated).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from recommendation import profiles as profile_mod
from recommendation.explain import build_explanation
from scoring import engine as scoring_engine

#: Provider statuses eligible for recommendation (v1.2 Section 7 Step 2).
#: DEGRADED is allowed but always flagged in the explanation.
ELIGIBLE_STATUSES = ("ACTIVE", "LIMITED", "DEGRADED")


class RecommendationError(ValueError):
    """Raised when a recommendation cannot be produced."""


@dataclass(frozen=True)
class Recommendation:
    """A single ranked recommendation for one model."""

    task: str
    profile: str
    provider_id: int
    provider_name: str
    model_id: int
    model_identifier: str
    final_score: float
    dimensions: dict  # dimension -> effective score dict
    breakdown: dict  # dimension -> {value, weight, contribution, confidence, source, aged}
    confidence: float
    explanation: str
    flags: Sequence[str]  # warnings (degraded provider, insufficient data)


def _eligible_models(conn, min_context_window: Optional[int], required_capabilities: Sequence[str]):
    """Yield (provider, model) rows that pass the Section 7 Step 2 filters."""
    query = (
        "SELECT p.id AS provider_id, p.name AS provider_name, p.status AS status,"
        " m.id AS model_id, m.model_identifier, m.context_window"
        " FROM models m JOIN providers p ON p.id = m.provider_id"
        " ORDER BY p.name, m.model_identifier"
    )
    cap_columns = {
        "tool_calling": "supports_tools",
        "vision": "supports_vision",
        "streaming": "supports_streaming",
        "json": "supports_json",
    }
    for row in conn.execute(query).fetchall():
        if row["status"] not in ELIGIBLE_STATUSES:
            continue
        if min_context_window and (row["context_window"] or 0) < min_context_window:
            continue
        missing = [
            cap for cap in required_capabilities
            if cap in cap_columns
        ]
        if missing:
            # validate capabilities from the model row via a re-query below
            model = conn.execute(
                "SELECT supports_tools, supports_streaming, supports_json, supports_vision"
                " FROM models WHERE id = ?",
                (row["model_id"],),
            ).fetchone()
            ok = all(
                model[cap_columns[cap]] == 1 for cap in missing
            )
            if not ok:
                continue
        yield row


def _dimension_sort_value(dimensions: dict, name: str) -> Optional[float]:
    score = dimensions.get(name)
    return score["value"] if score else None


def recommend(
    conn,
    task: str,
    profile: str = "coding",
    *,
    min_context_window: Optional[int] = None,
    required_capabilities: Sequence[str] = (),
    derive_operational: bool = True,
    fresh_days: int = 30,
    aging_days: int = 90,
    old_days: int = 180,
    latency_threshold_ms: int = 10000,
    limit: Optional[int] = None,
) -> Sequence[Recommendation]:
    """Rank eligible models deterministically and return recommendations."""
    weights = profile_mod.get_profile(conn, profile)
    results = []

    for row in _eligible_models(conn, min_context_window, required_capabilities):
        dimensions = {}
        for dimension in weights:
            score = scoring_engine.effective_score(
                conn,
                row["model_id"],
                dimension,
                derive_operational=derive_operational,
                fresh_days=fresh_days,
                aging_days=aging_days,
                old_days=old_days,
                latency_threshold_ms=latency_threshold_ms,
            )
            if score is not None:
                dimensions[dimension] = score

        final = 0.0
        breakdown = {}
        weighted_conf = 0.0
        total_weight = 0.0
        for dimension, weight in weights.items():
            score = dimensions.get(dimension)
            value = score["value"] if score else 0.0
            conf = score["confidence"] if score else 0.0
            contribution = weight * value
            final += contribution
            weighted_conf += weight * conf
            total_weight += weight
            breakdown[dimension] = {
                "value": value,
                "weight": weight,
                "contribution": contribution,
                "confidence": conf,
                "source": score["source"] if score else None,
                "aged": score["age_multiplier"] if score else None,
            }
        confidence = (weighted_conf / total_weight) if total_weight else 0.0
        confidence = min(1.0, max(0.0, confidence))

        flags = []
        if row["status"] == "DEGRADED":
            flags.append("provider degraded (last resort)")
        missing = [d for d in weights if dimensions.get(d) is None]
        if missing:
            flags.append(f"insufficient data: {', '.join(missing)}")

        explanation = build_explanation(
            task, profile, row, final, breakdown, weights, flags
        )
        results.append(
            Recommendation(
                task=task,
                profile=profile,
                provider_id=row["provider_id"],
                provider_name=row["provider_name"],
                model_id=row["model_id"],
                model_identifier=row["model_identifier"],
                final_score=round(final, 4),
                dimensions=dimensions,
                breakdown=breakdown,
                confidence=round(confidence, 4),
                explanation=explanation,
                flags=tuple(flags),
            )
        )

    results.sort(key=_sort_key)
    if limit is not None:
        results = results[:limit]
    return results


def _sort_key(r: Recommendation):
    """v1.2 Section 7 Step 4 deterministic ordering.

    Final Score desc, Availability desc, Reliability desc, Cost asc,
    Latency asc, model_identifier asc. Missing dimensions sort last in each
    descending key and last in ascending keys (never fabricated, Article 10).
    """
    availability = _dimension_sort_value(r.dimensions, "availability")
    reliability = _dimension_sort_value(r.dimensions, "reliability")
    cost = _dimension_sort_value(r.dimensions, "cost")
    latency = _dimension_sort_value(r.dimensions, "latency")
    return (
        -r.final_score,
        -(availability if availability is not None else -1.0),
        -(reliability if reliability is not None else -1.0),
        (cost if cost is not None else 1e9),
        (latency if latency is not None else 1e9),
        r.model_identifier,
    )
