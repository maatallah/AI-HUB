"""Append-only event log.

Events store historical activity (v1.1 Section 8). The events table is
append-only: this module exposes no update or delete operations.

Constitution Article 5: history is preserved. Data may be archived but is
never silently discarded.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Optional, Sequence

#: Base set of event types used by the Phase 1 registry plus the Phase 2
#: monitoring engine (health checks, quota signals, seed validation).
EVENT_TYPES = {
    "PROVIDER_ADDED",
    "PROVIDER_UPDATED",
    "PROVIDER_STATUS_CHANGED",
    "PROVIDER_ARCHIVED",
    "MODEL_ADDED",
    "MODEL_UPDATED",
    "MODEL_ARCHIVED",
    "HEALTH_CHECK_OK",
    "HEALTH_CHECK_FAILED",
    "HEALTH_CHECK_UNKNOWN",
    "MONITOR_STATUS_CHANGED",
    "QUOTA_SIGNAL",
    "VALIDATION_PASSED",
    "VALIDATION_FAILED",
    "VALIDATION_UNKNOWN",
}


class EventError(ValueError):
    """Raised when an event cannot be recorded."""


def record_event(
    conn,
    event_type: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    payload: Optional[dict] = None,
) -> int:
    """Append an event. Returns the new event id."""
    if event_type not in EVENT_TYPES:
        raise EventError(f"Unknown event type: {event_type!r}.")

    serialized = json.dumps(payload) if payload is not None else None
    cursor = conn.execute(
        "INSERT INTO events (event_type, entity_type, entity_id, payload)"
        " VALUES (?, ?, ?, ?)",
        (event_type, entity_type, entity_id, serialized),
    )
    conn.commit()
    return cursor.lastrowid


def list_events(
    conn,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    limit: int = 100,
) -> Sequence[sqlite3.Row]:
    """Return events, newest first, optionally filtered by entity."""
    query = "SELECT * FROM events"
    clauses: list[str] = []
    params: list = []
    if entity_type is not None:
        clauses.append("entity_type = ?")
        params.append(entity_type)
    if entity_id is not None:
        clauses.append("entity_id = ?")
        params.append(entity_id)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    return conn.execute(query, params).fetchall()
