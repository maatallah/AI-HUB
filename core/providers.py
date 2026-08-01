"""Manual provider registry (Phase 1).

Required operations (NEXT-STEPS.md Step 5):
  * add provider
  * update provider
  * list providers
  * archive provider

Phase 1 has no automatic discovery and no monitoring. Every change is
performed manually by the user, and every change is recorded as an event.

Lifecycle states follow v1.2 Section 5. Providers are archived, never
deleted (Constitution Article 5). Reason is mandatory whenever status is not
ACTIVE for runtime states (v1.2 Section 6).
"""

from __future__ import annotations

from typing import Optional

from core import events

#: All lifecycle states (v1.2 Section 5).
VALID_STATUSES = ("NEW", "EVALUATING", "ACTIVE", "LIMITED", "DEGRADED", "OFFLINE", "ARCHIVED")

#: Runtime states where a reason is mandatory (v1.2 Section 6). NEW and
#: EVALUATING are lifecycle-only states and do not require a reason.
STATUSES_REQUIRING_REASON = ("LIMITED", "DEGRADED", "OFFLINE", "ARCHIVED")

#: Legal state transitions documented in v1.2 Section 5.
#: NOTE: automatic enforcement of these transitions belongs to the monitoring
#: engine (Phase 2). The manual registry permits an administrator to move a
#: provider, mirroring the "administrator archives provider" path.
LEGAL_TRANSITIONS = {
    "NEW": {"EVALUATING"},
    "EVALUATING": {"ACTIVE"},
    "ACTIVE": {"LIMITED", "DEGRADED"},
    "LIMITED": {"ACTIVE"},
    "DEGRADED": {"OFFLINE"},
    "OFFLINE": {"ACTIVE", "ARCHIVED"},
    "ARCHIVED": set(),
}

#: Fields that may be updated by update_provider.
UPDATABLE_FIELDS = (
    "name",
    "company",
    "api_type",
    "base_url",
    "documentation_url",
    "status",
    "status_reason",
    "notes",
)


class RegistryError(ValueError):
    """Raised when a registry operation violates the rules."""


def _validate_status(status: str) -> None:
    if status not in VALID_STATUSES:
        raise RegistryError(
            f"Invalid status {status!r}. Must be one of {list(VALID_STATUSES)}."
        )


def _require_reason(status: str, reason) -> None:
    if status in STATUSES_REQUIRING_REASON and not (reason and reason.strip()):
        raise RegistryError(
            f"Status '{status}' requires a reason (v1.2 Section 6)."
        )


def add_provider(
    conn,
    name: str,
    company: Optional[str] = None,
    api_type: Optional[str] = None,
    base_url: Optional[str] = None,
    documentation_url: Optional[str] = None,
    status: str = "NEW",
    status_reason: Optional[str] = None,
    notes: Optional[str] = None,
) -> int:
    """Add a provider manually. Returns the new provider id."""
    if not name or not name.strip():
        raise RegistryError("Provider name is required.")
    _validate_status(status)
    _require_reason(status, status_reason)

    try:
        cursor = conn.execute(
            "INSERT INTO providers"
            " (name, company, api_type, base_url, documentation_url, status, status_reason, notes)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                name.strip(),
                company,
                api_type,
                base_url,
                documentation_url,
                status,
                status_reason,
                notes,
            ),
        )
        conn.commit()
    except Exception as exc:  # e.g. sqlite3.IntegrityError for duplicate name
        conn.rollback()
        raise RegistryError(f"Could not add provider {name!r}: {exc}") from exc

    provider_id = cursor.lastrowid
    events.record_event(
        conn,
        "PROVIDER_ADDED",
        entity_type="provider",
        entity_id=provider_id,
        payload={"name": name.strip(), "status": status},
    )
    return provider_id


def get_provider(conn, provider_id: int):
    """Return a single provider row or None."""
    return conn.execute(
        "SELECT * FROM providers WHERE id = ?", (provider_id,)
    ).fetchone()


def list_providers(conn, status: Optional[str] = None):
    """List providers, ordered by name. Optionally filtered by status."""
    if status is not None:
        _validate_status(status)
        rows = conn.execute(
            "SELECT * FROM providers WHERE status = ? ORDER BY name", (status,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM providers ORDER BY name").fetchall()
    return rows


def update_provider(conn, provider_id: int, **fields) -> dict:
    """Update a manual provider.

    Accepted keys are those in :data:`UPDATABLE_FIELDS`. A status change
    records a PROVIDER_STATUS_CHANGED event; any other change records a
    PROVIDER_UPDATED event.
    """
    unknown = set(fields) - set(UPDATABLE_FIELDS)
    if unknown:
        raise RegistryError(
            f"Unknown provider fields: {sorted(unknown)}. Allowed: {list(UPDATABLE_FIELDS)}."
        )

    existing = get_provider(conn, provider_id)
    if existing is None:
        raise RegistryError(f"Provider {provider_id} not found.")

    new_status = fields.get("status", existing["status"])
    _validate_status(new_status)
    new_reason = fields.get("status_reason", existing["status_reason"])
    _require_reason(new_status, new_reason)

    # Build the UPDATE statement from the provided fields.
    assignments = []
    params = []
    for key in UPDATABLE_FIELDS:
        if key in fields:
            assignments.append(f"{key} = ?")
            params.append(fields[key])
    if not assignments:
        raise RegistryError("No fields provided to update.")
    assignments.append("updated_at = datetime('now')")
    params.append(provider_id)

    try:
        conn.execute(
            f"UPDATE providers SET {', '.join(assignments)} WHERE id = ?", params
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise RegistryError(f"Could not update provider {provider_id}: {exc}") from exc

    status_changed = "status" in fields and fields["status"] != existing["status"]
    if status_changed:
        events.record_event(
            conn,
            "PROVIDER_STATUS_CHANGED",
            entity_type="provider",
            entity_id=provider_id,
            payload={"from": existing["status"], "to": new_status},
        )
    else:
        events.record_event(
            conn,
            "PROVIDER_UPDATED",
            entity_type="provider",
            entity_id=provider_id,
            payload={"changed_fields": list(fields)},
        )

    return dict(get_provider(conn, provider_id))


def archive_provider(conn, provider_id: int, reason: str) -> dict:
    """Archive a provider. The provider remains in history (never deleted)."""
    if not reason or not reason.strip():
        raise RegistryError("archive_provider requires an explicit reason.")

    existing = get_provider(conn, provider_id)
    if existing is None:
        raise RegistryError(f"Provider {provider_id} not found.")
    if existing["status"] == "ARCHIVED":
        raise RegistryError(f"Provider {provider_id} is already archived.")

    try:
        conn.execute(
            "UPDATE providers SET status = 'ARCHIVED', status_reason = ?,"
            " updated_at = datetime('now') WHERE id = ?",
            (reason.strip(), provider_id),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise RegistryError(f"Could not archive provider {provider_id}: {exc}") from exc

    events.record_event(
        conn,
        "PROVIDER_ARCHIVED",
        entity_type="provider",
        entity_id=provider_id,
        payload={"reason": reason.strip(), "from": existing["status"]},
    )
    return dict(get_provider(conn, provider_id))
