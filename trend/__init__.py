"""Trend analysis (Phase 6, trend milestone).

Deterministic, read-only analysis of event-derived history (v1.2 Section
20.4; proposal spec Section 5). Trend analysis is derived/read-only over the
append-only ``events`` series reconstructed by ``dashboard.history``: it
never writes to the database, never emits events (no ``TREND_*`` event types
exist or are created) and never creates or alters tables (ADR-0004 / D-P8
snapshots remain deferred).

Governed semantics (owner-authorized 2026-08-19 against the ``98696d1``
baseline):

* Direction: ``up`` / ``down`` / ``stable`` / ``insufficient_data``.
* Stable band: absolute normalized delta ``<= 5%`` of the series domain,
  applied symmetrically at both boundaries.
* Magnitude: normalized delta ``(last - first) / domain`` where the domain
  is 100 for normalized scores and 1 for the availability success/failure
  scalar (domain-relative normalization; the score formula is exactly
  ``(last - first) / 100``).
* Stability: population standard deviation of the windowed numeric series.
* Window: ``window_days`` (default 90) anchored to the most recent point of
  the analyzed series, not wall-clock (deterministic from persisted data).
* Minimum points: fewer than ``min_points`` (default 3) valid numeric points
  in the window yields ``insufficient_data`` with the threshold exposed; no
  direction, magnitude or stability is fabricated (Constitution Article 10).
* Scores: each dimension is its own independent series (never combined); an
  optional ``dimension`` restricts the calculation.
* Availability: only ``HEALTH_CHECK_OK`` (1.0) and ``HEALTH_CHECK_FAILED``
  (0.0) are numeric trend points. ``HEALTH_CHECK_UNKNOWN`` is excluded from
  the numeric calculation and ``MONITOR_STATUS_CHANGED`` is never converted
  into a numeric point. Latency is not part of the scalar; the complete raw
  history is passed through unchanged.
"""

from trend.analysis import (
    AVAILABILITY_DOMAIN,
    AVAILABILITY_NUMERIC,
    DIRECTION_DOWN,
    DIRECTION_INSUFFICIENT,
    DIRECTION_STABLE,
    DIRECTION_UP,
    SCORE_DOMAIN,
    STABLE_BAND,
    TrendError,
    availability_trend,
    score_trend,
)

__all__ = [
    "AVAILABILITY_DOMAIN",
    "AVAILABILITY_NUMERIC",
    "DIRECTION_DOWN",
    "DIRECTION_INSUFFICIENT",
    "DIRECTION_STABLE",
    "DIRECTION_UP",
    "SCORE_DOMAIN",
    "STABLE_BAND",
    "TrendError",
    "availability_trend",
    "score_trend",
]