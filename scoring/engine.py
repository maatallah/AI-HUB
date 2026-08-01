"""Scoring engine: effective per-dimension scores with aging (Phase 3).

Combines stored scores (``scores`` table, ADR-0001) with operational
dimensions derived from monitoring. Applies the v1.2 Section 4 aging
multiplier to confidence based on ``scored_at`` age:

  * 0-30 days: 1.00 (fresh)
  * 31-90 days: 0.90 (aging)
  * 91-180 days: 0.75 (old)
  * >180 days: 0.50 (stale)

Effective confidence = stored confidence x aging multiplier (clamped to 0-1).
Missing dimensions yield no score (Article 10).
"""

from __future__ import annotations

import datetime
from typing import Optional

from scoring.derive import DERIVED_DIMENSIONS, derive_score

#: Aging confidence multipliers (v1.2 Section 4).
_FRESH = 1.00
_AGING = 0.90
_OLD = 0.75
_STALE = 0.50


def age_multiplier(
    scored_at: Optional[str],
    fresh_days: int = 30,
    aging_days: int = 90,
    old_days: int = 180,
) -> float:
    """Return the v1.2 Section 4 aging multiplier for a score timestamp."""
    age = age_days(scored_at)
    if age <= fresh_days:
        return _FRESH
    if age <= aging_days:
        return _AGING
    if age <= old_days:
        return _OLD
    return _STALE


def age_days(scored_at: Optional[str]) -> int:
    """Age of a timestamp in days (0 when absent or unparseable).

    SQLite timestamps are UTC ('YYYY-MM-DD HH:MM:SS'); ISO strings may carry a
    timezone. Comparison uses the current UTC time so aging is stable.
    """
    if not scored_at:
        return 0
    try:
        parsed = datetime.datetime.fromisoformat(str(scored_at).replace(" ", "T"))
    except ValueError:
        return 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    return max(0, (now - parsed).days)


def effective_score(
    conn,
    model_id: int,
    dimension: str,
    *,
    derive_operational: bool = True,
    fresh_days: int = 30,
    aging_days: int = 90,
    old_days: int = 180,
    latency_threshold_ms: int = 10000,
) -> Optional[dict]:
    """Compute the effective aged score for a model dimension, or None.

    Returns a dict with: dimension, value (0-100), confidence (aged, 0-1),
    source, scored_at, age_multiplier, derived (bool).
    """
    raw = None
    if dimension in DERIVED_DIMENSIONS and derive_operational:
        raw = derive_score(conn, model_id, dimension, latency_threshold_ms=latency_threshold_ms)
    if raw is None:
        stored = conn.execute(
            "SELECT value, confidence, source, scored_at FROM scores"
            " WHERE model_id = ? AND dimension = ?",
            (model_id, dimension),
        ).fetchone()
        if stored is not None:
            raw = {
                "value": stored["value"],
                "confidence": stored["confidence"],
                "source": stored["source"],
                "scored_at": stored["scored_at"],
            }
    if raw is None:
        return None

    multiplier = age_multiplier(raw["scored_at"], fresh_days, aging_days, old_days)
    confidence = raw["confidence"] if raw["confidence"] is not None else _FRESH
    effective_conf = min(_FRESH, max(0.0, confidence * multiplier))
    return {
        "dimension": dimension,
        "value": float(raw["value"]),
        "confidence": effective_conf,
        "source": raw["source"],
        "scored_at": raw["scored_at"],
        "age_multiplier": multiplier,
        "derived": dimension in DERIVED_DIMENSIONS and derive_operational,
    }


def list_scores(conn, model_id: Optional[int] = None):
    """List stored scores (see ``scoring.ingest.list_scores``)."""
    from scoring.ingest import list_scores as _list

    return _list(conn, model_id=model_id)
