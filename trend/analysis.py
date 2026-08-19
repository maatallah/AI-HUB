"""Deterministic read-only trend analysis (Phase 6, trend milestone).

Trend analysis is a derived/read-only layer over the append-only,
event-derived series in ``dashboard.history`` (v1.2 Section 20.4; proposal
spec Section 5). It never writes to the database, never emits events (no
``TREND_*`` event types exist or are created) and never creates or alters
tables (ADR-0004 / D-P8 snapshots remain deferred).

Approved semantics (owner, 2026-08-19, against the ``98696d1`` baseline):

* Direction: ``up`` / ``down`` / ``stable`` / ``insufficient_data``.
* Stable band: absolute normalized delta ``<= 5%`` (``STABLE_BAND``), applied
  symmetrically at both the positive and negative boundary.
* Magnitude: normalized delta ``(last - first) / domain`` over the request
  window. The domain is 100 for normalized scores (exactly ``(last - first)
  / 100``) and 1 for the availability success/failure scalar
  (domain-relative normalization, owner Option 1). No other normalization or
  smoothing is applied.
* Stability: population standard deviation of the windowed numeric series
  (the windowed series is the complete observed series, not a sample of a
  larger population).
* Minimum points: ``min_points`` (default 3); fewer valid numeric points in
  the window yields ``insufficient_data`` with the threshold exposed. No
  direction/magnitude/stability is fabricated (Constitution Article 10).
* Window: ``window_days`` (default 90) anchored to the most recent point of
  the analyzed series (not wall-clock), so results are deterministic from
  persisted data (Constitution Article 7).
* Score dimensions: each dimension is analyzed as its own independent series
  (never combined); a ``dimension`` filter restricts the calculation.
* Availability scalar: only ``HEALTH_CHECK_OK`` (1.0) and
  ``HEALTH_CHECK_FAILED`` (0.0) are numeric trend points (owner Option A);
  ``HEALTH_CHECK_UNKNOWN`` is excluded from the numeric calculation and
  ``MONITOR_STATUS_CHANGED`` is never converted into a numeric point. Latency
  is not part of the trend scalar; the complete raw history is passed through
  unchanged.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from dashboard import history as dashboard_history

#: Direction labels (v1.2 Section 20.4; proposal spec Section 5).
DIRECTION_UP = "up"
DIRECTION_DOWN = "down"
DIRECTION_STABLE = "stable"
DIRECTION_INSUFFICIENT = "insufficient_data"

#: Stable band: absolute normalized delta of at most 5% of the series domain.
STABLE_BAND = 0.05

#: Normalized score value domain (0-100).
SCORE_DOMAIN = 100.0

#: Availability success/failure scalar domain (0-1, owner Option A mapping).
AVAILABILITY_DOMAIN = 1.0

#: Health-check outcomes that contribute numeric availability trend points.
#: HEALTH_CHECK_UNKNOWN is excluded from the numeric scalar and
#: MONITOR_STATUS_CHANGED is never converted into a numeric point.
AVAILABILITY_NUMERIC = {
    "HEALTH_CHECK_OK": 1.0,
    "HEALTH_CHECK_FAILED": 0.0,
}


class TrendError(ValueError):
    """Raised when a trend request is invalid."""


def _validate_args(window_days, min_points) -> None:
    if not isinstance(window_days, int) or window_days <= 0:
        raise TrendError("window_days must be a positive integer.")
    if not isinstance(min_points, int) or min_points < 1:
        raise TrendError("min_points must be an integer >= 1.")


def _parse_ts(ts):
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        raise TrendError(f"Unparseable timestamp {ts!r} in history series.")


def _numeric_points(series) -> List[tuple]:
    """Convert records with a numeric value into (occurred_at, value, record)."""
    points: List[tuple] = []
    for rec in series:
        try:
            value = float(rec.get("value"))
        except (TypeError, ValueError):
            continue
        points.append((rec["occurred_at"], value, rec))
    points.sort(key=lambda p: p[0])
    return points


def _window(points, window_days) -> List[tuple]:
    """Keep points within ``window_days`` of the most recent point."""
    if not points:
        return []
    anchor = _parse_ts(max(p[0] for p in points))
    boundary = anchor - timedelta(days=window_days)
    return [p for p in points if _parse_ts(p[0]) >= boundary]


def _trend_calc(points, min_points, domain) -> dict:
    """Compute direction, magnitude and stability for a windowed numeric series."""
    n = len(points)
    if n < min_points:
        return {
            "direction": DIRECTION_INSUFFICIENT,
            "magnitude": None,
            "stability": None,
            "first": None,
            "last": None,
            "point_count": n,
        }
    first = points[0][1]
    last = points[-1][1]
    magnitude = (last - first) / domain
    if magnitude > STABLE_BAND:
        direction = DIRECTION_UP
    elif magnitude < -STABLE_BAND:
        direction = DIRECTION_DOWN
    else:
        direction = DIRECTION_STABLE
    values = [p[1] for p in points]
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    stability = variance ** 0.5
    return {
        "direction": direction,
        "magnitude": magnitude,
        "stability": stability,
        "first": first,
        "last": last,
        "point_count": n,
    }


def _require_model(conn, model_id: int) -> None:
    row = conn.execute("SELECT id FROM models WHERE id = ?", (model_id,)).fetchone()
    if row is None:
        raise TrendError(f"Model {model_id!r} not found.")


def _require_provider(conn, provider_id: int) -> None:
    row = conn.execute("SELECT id FROM providers WHERE id = ?", (provider_id,)).fetchone()
    if row is None:
        raise TrendError(f"Provider {provider_id!r} not found.")


def _score_result(model_id: int, dimension, records, window_days, min_points) -> dict:
    points = _numeric_points(records)
    win = _window(points, window_days)
    calc = _trend_calc(win, min_points, SCORE_DOMAIN)
    return {
        "kind": "score",
        "model_id": model_id,
        "dimension": dimension,
        "series": list(records),
        "points": [p[2] for p in win],
        "direction": calc["direction"],
        "magnitude": calc["magnitude"],
        "stability": calc["stability"],
        "first": calc["first"],
        "last": calc["last"],
        "point_count": calc["point_count"],
        "series_count": len(records),
        "window_days": window_days,
        "min_points": min_points,
        "domain": SCORE_DOMAIN,
        "stdev": "population",
    }


def score_trend(
    conn,
    model_id: int,
    dimension: Optional[str] = None,
    window_days: int = 90,
    min_points: int = 3,
) -> List[dict]:
    """Analyze the normalized score series for a model (read-only).

    Each dimension is analyzed as its own independent series (never combined).
    With ``dimension=None`` every dimension with history is returned, ordered
    by dimension name; with ``dimension`` only that dimension is analyzed.
    Returns a list of per-dimension result dicts (possibly empty).
    """
    _validate_args(window_days, min_points)
    _require_model(conn, model_id)
    series = dashboard_history.score_history(conn, model_id)
    groups: dict = {}
    for rec in series:
        d = rec.get("dimension")
        if d is None:
            continue
        if dimension is not None and d != dimension:
            continue
        groups.setdefault(d, []).append(rec)
    return [
        _score_result(model_id, d, groups[d], window_days, min_points)
        for d in sorted(groups)
    ]


def _availability_result(provider_id, records, window_days, min_points) -> dict:
    numeric: List[tuple] = []
    excluded_unknown = 0
    excluded_transitions = 0
    for rec in records:
        event_type = rec.get("event_type")
        if event_type == "HEALTH_CHECK_UNKNOWN":
            excluded_unknown += 1
        elif event_type == "MONITOR_STATUS_CHANGED":
            excluded_transitions += 1
        elif event_type in AVAILABILITY_NUMERIC:
            numeric.append(
                (rec["occurred_at"], AVAILABILITY_NUMERIC[event_type], rec)
            )
    numeric.sort(key=lambda p: p[0])
    win = _window(numeric, window_days)
    calc = _trend_calc(win, min_points, AVAILABILITY_DOMAIN)
    return {
        "kind": "availability",
        "provider_id": provider_id,
        "series": list(records),
        "points": [p[2] for p in win],
        "direction": calc["direction"],
        "magnitude": calc["magnitude"],
        "stability": calc["stability"],
        "first": calc["first"],
        "last": calc["last"],
        "point_count": calc["point_count"],
        "numeric_count": len(numeric),
        "series_count": len(records),
        "excluded_unknown": excluded_unknown,
        "excluded_transitions": excluded_transitions,
        "window_days": window_days,
        "min_points": min_points,
        "domain": AVAILABILITY_DOMAIN,
        "stdev": "population",
    }


def availability_trend(
    conn,
    provider_id: Optional[int] = None,
    window_days: int = 90,
    min_points: int = 3,
) -> List[dict]:
    """Analyze the availability success/failure scalar per provider (read-only).

    Health checks are the only numeric trend points (owner Option A):
    ``HEALTH_CHECK_OK`` -> 1.0 and ``HEALTH_CHECK_FAILED`` -> 0.0.
    ``HEALTH_CHECK_UNKNOWN`` is excluded from the numeric calculation and
    ``MONITOR_STATUS_CHANGED`` is never converted into a numeric point. The
    complete raw history is passed through unchanged. With ``provider_id=None``
    every provider with history is returned, grouped by provider; with a
    ``provider_id`` only that provider is analyzed.
    """
    _validate_args(window_days, min_points)
    if provider_id is not None:
        _require_provider(conn, provider_id)
    series = dashboard_history.availability_history(conn, provider_id=provider_id)
    groups: dict = {}
    for rec in series:
        if rec.get("entity_id") is None:
            continue
        groups.setdefault(rec["entity_id"], []).append(rec)
    return [
        _availability_result(pid, groups[pid], window_days, min_points)
        for pid in sorted(groups)
    ]