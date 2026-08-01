"""Availability tracking and lifecycle state preparation (Phase 2).

The ``availability`` table holds the runtime state per provider (and
optionally per model). This module:

  * records health check outcomes (success resets failure counts)
  * applies lifecycle transitions using v1.2 Section 5 legal transitions
  * enforces that reason is mandatory whenever state is not ACTIVE
  * never archives automatically (Constitution Article 1)

Monitoring never modifies provider information directly (v1.2 Section 9).
All status changes go through ``core.providers.update_provider`` so events,
reason validation and timestamps stay consistent with Phase 1 behaviour.
"""

from __future__ import annotations

from typing import Optional

from core import events
from core.providers import LEGAL_TRANSITIONS, STATUSES_REQUIRING_REASON, update_provider


def get_availability(conn, provider_id: int, model_id: Optional[int] = None):
    """Return the availability row for a provider/model, or None."""
    if model_id is None:
        return conn.execute(
            "SELECT * FROM availability WHERE provider_id = ? AND model_id IS NULL",
            (provider_id,),
        ).fetchone()
    return conn.execute(
        "SELECT * FROM availability WHERE provider_id = ? AND model_id = ?",
        (provider_id, model_id),
    ).fetchone()


def _touch_availability(conn, provider_id: int, model_id: Optional[int], **fields) -> None:
    """Create the availability row if absent, then update the given fields.

    Values that are strings are bound as parameters. ``last_success``,
    ``last_failure`` and ``updated_at`` are handled specially so the SQL
    ``datetime('now')`` expression is evaluated by SQLite rather than stored
    as a literal.
    """
    existing = get_availability(conn, provider_id, model_id)
    if existing is None:
        conn.execute(
            "INSERT INTO availability (provider_id, model_id, state, reason)"
            " VALUES (?, ?, 'ACTIVE', NULL)",
            (provider_id, model_id),
        )

    assignments = []
    params = []
    for key, value in fields.items():
        if key in ("last_success", "last_failure", "updated_at"):
            assignments.append(f"{key} = datetime('now')")
        else:
            assignments.append(f"{key} = ?")
            params.append(value)
    assignments.append("updated_at = datetime('now')")
    params.extend([provider_id, model_id])

    conn.execute(
        f"UPDATE availability SET {', '.join(assignments)}"
        " WHERE provider_id = ? AND model_id IS ?",
        params,
    )
    conn.commit()


def update_availability(conn, provider_id: int, health_state: str) -> dict:
    """Record the outcome of a health check.

    On success: state=ACTIVE, failures reset to 0, last_success set.
    On failure: consecutive_failures incremented, last_failure set.
    Does NOT change state directly - lifecycle decisions happen in
    :func:`apply_lifecycle`.
    """
    if health_state not in ("OK", "FAILED", "UNKNOWN"):
        raise ValueError(f"Invalid health state: {health_state!r}.")

    if health_state == "OK":
        _touch_availability(
            conn,
            provider_id,
            None,
            last_success="datetime('now')",
            consecutive_failures=0,
            state="ACTIVE",
            reason=None,
        )
        return dict(get_availability(conn, provider_id))

    row = get_availability(conn, provider_id)
    if row is None:
        _touch_availability(
            conn, provider_id, None, consecutive_failures=1, last_failure="datetime('now')"
        )
        return dict(get_availability(conn, provider_id))
    failures = int(row["consecutive_failures"] or 0) + 1
    _touch_availability(
        conn,
        provider_id,
        None,
        consecutive_failures=failures,
        last_failure="datetime('now')",
    )
    return dict(get_availability(conn, provider_id))


def _ensure_legal(from_status: str, to_status: str, reason: Optional[str]) -> None:
    """Validate a transition against the v1.2 Section 5 rules."""
    if to_status not in LEGAL_TRANSITIONS.get(from_status, set()):
        raise ValueError(
            f"Illegal transition {from_status!r} -> {to_status!r}."
            f" Allowed from {from_status!r}: {sorted(LEGAL_TRANSITIONS.get(from_status, set()))}."
        )
    if to_status in STATUSES_REQUIRING_REASON and not (reason and reason.strip()):
        raise ValueError(
            f"Transition to {to_status!r} requires a reason (v1.2 Section 6)."
        )


def apply_lifecycle(
    conn,
    provider_id: int,
    to_status: str,
    reason: Optional[str] = None,
) -> dict:
    """Apply a legal lifecycle transition to a provider.

    Uses ``core.providers.update_provider`` (which validates, records
    PROVIDER_STATUS_CHANGED, and stamps updated_at) and additionally records
    a MONITOR_STATUS_CHANGED event. Transitions are limited to the v1.2
    Section 5 legal table. ARCHIVED is never applied automatically.
    """
    existing = conn.execute(
        "SELECT id, status FROM providers WHERE id = ?", (provider_id,)
    ).fetchone()
    if existing is None:
        raise ValueError(f"Provider {provider_id} not found.")
    if to_status == "ARCHIVED":
        raise ValueError("Automatic archival requires explicit confirmation (Constitution Article 1).")
    if to_status == existing["status"]:
        return dict(
            conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
        )

    _ensure_legal(existing["status"], to_status, reason)
    applied_reason = None if to_status == "ACTIVE" else reason
    updated = update_provider(conn, provider_id, status=to_status, status_reason=applied_reason)
    events.record_event(
        conn,
        "MONITOR_STATUS_CHANGED",
        entity_type="provider",
        entity_id=provider_id,
        payload={
            "from": existing["status"],
            "to": to_status,
            "reason": reason,
            "origin": "monitoring",
        },
    )
    return updated


def list_availability(conn):
    """List all availability rows ordered by provider."""
    return conn.execute(
        "SELECT a.*, p.name AS provider_name"
        " FROM availability a"
        " JOIN providers p ON p.id = a.provider_id"
        " ORDER BY p.name"
    ).fetchall()
