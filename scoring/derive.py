"""Derived operational scores computed from monitoring data (Phase 3).

Operational dimensions are derived deterministically from Phase 2 monitoring
outputs at read time - they are never stored in the ``scores`` table and never
fabricated. When monitoring data is absent, the derived score is ``None``
(Constitution Article 10).

Sources:
  * ``availability`` table: state, consecutive_failures, updated_at.
  * ``providers.status`` lifecycle state.
  * ``HEALTH_CHECK_OK`` events: latency_ms.
"""

from __future__ import annotations

import json
from typing import Optional

from monitoring import availability as availability_mod

#: Dimensions derived rather than stored in the ``scores`` table.
#: Operational dimensions come from monitoring (v1.2 Section 1.2); the
#: ``context_window`` dimension is derived from the ``models`` table (used by
#: the long_context profile, v1.2 Section 2).
DERIVED_DIMENSIONS = ("availability", "reliability", "latency", "context_window")

#: Context window (tokens) that maps to a full score of 100.
CONTEXT_WINDOW_FULL = 131072

#: Source reported for derived scores (automated measurement).
SOURCE = "AUTOMATED_TEST"

#: Runtime state -> normalized availability score (v1.2 Section 6).
AVAILABILITY_STATE_VALUES = {
    "ACTIVE": 100.0,
    "LIMITED": 70.0,
    "DEGRADED": 40.0,
    "OFFLINE": 0.0,
    "ARCHIVED": None,  # excluded from recommendations entirely
}

#: Default confidence for monitoring-derived measurements.
DERIVED_CONFIDENCE = 0.8


class DeriveError(ValueError):
    """Raised when a derived score cannot be computed."""


def _model_provider(conn, model_id: int) -> int:
    row = conn.execute(
        "SELECT provider_id FROM models WHERE id = ?", (model_id,)
    ).fetchone()
    if row is None:
        raise DeriveError(f"Model {model_id} not found.")
    return row["provider_id"]


def _base(dimension: str, value: float, scored_at: Optional[str]) -> Optional[dict]:
    if value is None:
        return None
    return {
        "dimension": dimension,
        "value": value,
        "confidence": DERIVED_CONFIDENCE,
        "source": SOURCE,
        "scored_at": scored_at,
    }


def derive_availability(conn, model_id: int) -> Optional[dict]:
    """Availability from the provider lifecycle state (0-100) or None.

    ARCHIVED returns None (excluded from recommendations). NEW/EVALUATING have
    no runtime state and therefore no derived availability (Article 10).
    """
    provider_id = _model_provider(conn, model_id)
    provider = conn.execute(
        "SELECT status FROM providers WHERE id = ?", (provider_id,)
    ).fetchone()
    if provider is None:
        return None
    value = AVAILABILITY_STATE_VALUES.get(provider["status"])
    if value is None:
        return None
    av = availability_mod.get_availability(conn, provider_id)
    scored_at = av["updated_at"] if av is not None else None
    return _base("availability", value, scored_at)


def derive_reliability(conn, model_id: int) -> Optional[dict]:
    """Reliability from consecutive failures (0-100) or None.

    ``max(0, 100 - consecutive_failures * 20)`` - each failure costs 20
    points. No availability row means no measurement yet (Article 10).
    """
    provider_id = _model_provider(conn, model_id)
    av = availability_mod.get_availability(conn, provider_id)
    if av is None:
        return None
    failures = int(av["consecutive_failures"] or 0)
    value = max(0.0, 100.0 - failures * 20.0)
    return _base("reliability", value, av["updated_at"])


def derive_latency(conn, model_id: int, latency_threshold_ms: int = 10000) -> Optional[dict]:
    """Latency from the latest successful health check (0-100) or None.

    0ms -> 100, latency_threshold_ms -> 0 (linear). No measurement -> None.
    """
    provider_id = _model_provider(conn, model_id)
    row = conn.execute(
        "SELECT payload, occurred_at FROM events"
        " WHERE event_type = 'HEALTH_CHECK_OK'"
        "   AND entity_type = 'provider' AND entity_id = ?"
        " ORDER BY id DESC LIMIT 1",
        (provider_id,),
    ).fetchone()
    if row is None:
        return None
    payload = json.loads(row["payload"] or "{}")
    latency = payload.get("latency_ms")
    if latency is None:
        return None
    if latency_threshold_ms <= 0:
        raise DeriveError("latency_threshold_ms must be positive.")
    value = max(0.0, 100.0 * (1.0 - float(latency) / latency_threshold_ms))
    return _base("latency", value, row["occurred_at"])


def derive_context_window(conn, model_id: int) -> Optional[dict]:
    """Context-window capability from the models table (0-100) or None.

    Linear mapping: CONTEXT_WINDOW_FULL (131072 tokens) -> 100. Unknown or
    non-positive context_window -> None (Article 10).
    """
    row = conn.execute(
        "SELECT context_window FROM models WHERE id = ?", (model_id,)
    ).fetchone()
    if row is None or not row["context_window"] or row["context_window"] <= 0:
        return None
    value = min(100.0, float(row["context_window"]) / CONTEXT_WINDOW_FULL * 100.0)
    return {
        "dimension": "context_window",
        "value": value,
        "confidence": 1.0,
        "source": "OFFICIAL_INFORMATION",
        "scored_at": None,
    }


def derive_score(conn, model_id: int, dimension: str, latency_threshold_ms: int = 10000) -> Optional[dict]:
    """Derive a dimension for a model, or None if unavailable."""
    if dimension == "availability":
        return derive_availability(conn, model_id)
    if dimension == "reliability":
        return derive_reliability(conn, model_id)
    if dimension == "latency":
        return derive_latency(conn, model_id, latency_threshold_ms)
    if dimension == "context_window":
        return derive_context_window(conn, model_id)
    return None
