"""Event-derived score and availability history (Phase 4).

History is reconstructed read-only from the append-only ``events`` table
(v1.2 Section 18.3). It never rewrites or deletes events (Constitution
Article 5) and never fabricates missing data (Constitution Article 10): an
event that is absent simply has no history.

Score series come from ``SCORE_RECORDED`` / ``SCORE_UPDATED`` events;
availability series from ``MONITOR_STATUS_CHANGED`` and ``HEALTH_CHECK_*``
events.

Point-in-time snapshots are deferred: they require ADR-0004 approval and are
not implemented here.
"""

from __future__ import annotations

import json
from typing import Optional, Sequence

#: Score event types that carry the per-dimension score value.
SCORE_EVENT_TYPES = ("SCORE_RECORDED", "SCORE_UPDATED")

#: Availability/health event types used for the availability series.
AVAILABILITY_EVENT_TYPES = (
    "MONITOR_STATUS_CHANGED",
    "HEALTH_CHECK_OK",
    "HEALTH_CHECK_FAILED",
    "HEALTH_CHECK_UNKNOWN",
)


def score_history(
    conn,
    model_id: int,
    dimension: Optional[str] = None,
    limit: int = 1000,
) -> Sequence[dict]:
    """Reconstruct a per-model score series from score events.

    Returns a deterministic list of records (oldest first):
    ``[(occurred_at, dimension, value, confidence, source)]``. SCORE_UPDATED
    records report the new value. Records are ordered by event id (append
    order), then occurred_at, so reconstruction is stable.
    """
    query = (
        "SELECT id, event_type, occurred_at, payload FROM events"
        " WHERE entity_type = 'model' AND entity_id = ?"
        "   AND event_type IN ({})"
    ).format(",".join("?" * len(SCORE_EVENT_TYPES)))
    params = [model_id, *SCORE_EVENT_TYPES]
    query += " ORDER BY id ASC LIMIT ?"
    params.append(limit)

    series = []
    for row in conn.execute(query, params).fetchall():
        payload = json.loads(row["payload"] or "{}")
        if dimension is not None and payload.get("dimension") != dimension:
            continue
        if row["event_type"] == "SCORE_UPDATED":
            value = payload.get("to")
        else:
            value = payload.get("value")
        series.append(
            {
                "occurred_at": row["occurred_at"],
                "dimension": payload.get("dimension"),
                "value": value,
                "confidence": payload.get("confidence"),
                "source": payload.get("source"),
            }
        )
    return series


def availability_history(
    conn,
    provider_id: Optional[int] = None,
    limit: int = 1000,
) -> Sequence[dict]:
    """Reconstruct an availability/health series from monitoring events.

    Returns deterministic records (oldest first) combining state transitions
    (``MONITOR_STATUS_CHANGED``) and health-check outcomes
    (``HEALTH_CHECK_*`` with latency samples when present). Filtered to a
    provider when ``provider_id`` is given.
    """
    query = (
        "SELECT id, event_type, entity_type, entity_id, occurred_at, payload"
        " FROM events WHERE event_type IN ({})"
    ).format(",".join("?" * len(AVAILABILITY_EVENT_TYPES)))
    params = [*AVAILABILITY_EVENT_TYPES]
    if provider_id is not None:
        query += " AND entity_type = 'provider' AND entity_id = ?"
        params.append(provider_id)
    query += " ORDER BY id ASC LIMIT ?"
    params.append(limit)

    series = []
    for row in conn.execute(query, params).fetchall():
        payload = json.loads(row["payload"] or "{}")
        record = {
            "occurred_at": row["occurred_at"],
            "event_type": row["event_type"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
        }
        if row["event_type"] == "MONITOR_STATUS_CHANGED":
            record["from"] = payload.get("from")
            record["to"] = payload.get("to")
            record["reason"] = payload.get("reason")
        else:
            record["latency_ms"] = payload.get("latency_ms")
            record["status_code"] = payload.get("status_code")
        series.append(record)
    return series
