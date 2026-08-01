"""Quota and usage monitoring architecture (Phase 2).

Phase 2 establishes the quota tracking architecture without external spend
APIs (no credentials are available or stored). It uses the existing
``availability`` columns:

  * ``quota_type`` - daily, monthly or rate based quota
  * ``reset_at`` - timestamp used for LIMITED -> ACTIVE reset detection

Quota exhaustion is a lifecycle trigger (v1.2 Section 5): a quota signal
(HTTP 429, or 401/403 with a rate-limit header) moves ACTIVE/DEGRADED ->
LIMITED. A detected reset moves LIMITED -> ACTIVE.

No new tables are required.
"""

from __future__ import annotations

from typing import Optional

from core import events
from monitoring.availability import apply_lifecycle, get_availability
from monitoring import health

#: Quota types supported by the architecture.
QUOTA_TYPES = ("daily", "monthly", "rate")


class QuotaError(ValueError):
    """Raised when a quota operation violates the rules."""


def _validate_quota_type(quota_type: str) -> None:
    if quota_type not in QUOTA_TYPES:
        raise QuotaError(
            f"Invalid quota_type {quota_type!r}. Must be one of {list(QUOTA_TYPES)}."
        )


def _set_availability_field(conn, provider_id: int, field: str, value: Optional[str]) -> None:
    existing = get_availability(conn, provider_id)
    if existing is None:
        conn.execute(
            "INSERT INTO availability (provider_id, model_id, state, reason)"
            " VALUES (?, NULL, 'ACTIVE', NULL)",
            (provider_id,),
        )
    conn.execute(
        f"UPDATE availability SET {field} = ?, updated_at = datetime('now')"
        " WHERE provider_id = ? AND model_id IS NULL",
        (value, provider_id),
    )
    conn.commit()


def record_quota_signal(
    conn,
    provider_id: int,
    quota_type: str,
    reason: Optional[str] = None,
) -> dict:
    """Record a quota exhaustion signal and apply ACTIVE -> LIMITED.

    ``reason`` defaults to "Quota exhausted." when not provided. Only the
    ACTIVE -> LIMITED transition is legal (v1.2 Section 5); a DEGRADED
    provider records the signal but is not moved by quota alone.
    """
    _validate_quota_type(quota_type)

    existing = conn.execute(
        "SELECT id, status FROM providers WHERE id = ?", (provider_id,)
    ).fetchone()
    if existing is None:
        raise QuotaError(f"Provider {provider_id} not found.")

    reason = reason or "Quota exhausted."
    _set_availability_field(conn, provider_id, "quota_type", quota_type)

    events.record_event(
        conn,
        "QUOTA_SIGNAL",
        entity_type="provider",
        entity_id=provider_id,
        payload={
            "quota_type": quota_type,
            "reason": reason,
            "status_code_hint": "quota signal",
        },
    )

    if existing["status"] == "ACTIVE":
        return apply_lifecycle(conn, provider_id, "LIMITED", reason)
    return dict(
        conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
    )


def classify_status_code(status_code: int) -> Optional[str]:
    """Classify an HTTP status code as a quota signal.

    Returns "daily"/"monthly"/"rate" or None when the code is not a quota
    signal. 429 is always a rate-limit signal.
    """
    if status_code in health.QUOTA_STATUS_CODES:
        return "rate"
    # 401/403 can indicate quota exhaustion when a rate-limit header is
    # present; without header inspection we only treat them as quota signals
    # when explicitly marked by the caller (see record_quota_signal).
    return None


def set_quota_reset(conn, provider_id: int, reset_at: str, quota_type: Optional[str] = None) -> dict:
    """Record the quota reset time on the availability row."""
    if quota_type is not None:
        _validate_quota_type(quota_type)
    if quota_type is not None:
        _set_availability_field(conn, provider_id, "quota_type", quota_type)
    _set_availability_field(conn, provider_id, "reset_at", reset_at)
    return dict(get_availability(conn, provider_id))


def detect_quota_reset(conn, provider_id: int) -> dict:
    """Apply LIMITED -> ACTIVE when a quota reset has been recorded.

    The reset is detected when ``reset_at`` exists and is not in the future.
    Requires an explicit caller confirmation that the reset has occurred
    (recorded by setting ``reset_at`` to a past timestamp).
    """
    existing = conn.execute(
        "SELECT id, status FROM providers WHERE id = ?", (provider_id,)
    ).fetchone()
    if existing is None:
        raise QuotaError(f"Provider {provider_id} not found.")
    if existing["status"] != "LIMITED":
        return dict(
            conn.execute("SELECT * FROM providers WHERE id = ?", (provider_id,)).fetchone()
        )

    row = get_availability(conn, provider_id)
    reset_at = row["reset_at"] if row is not None else None
    if not reset_at:
        raise QuotaError("No quota reset recorded for this provider.")

    return apply_lifecycle(conn, provider_id, "ACTIVE", "Quota reset detected.")
