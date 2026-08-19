"""Governed model registry operations (Phase 6 Milestone 3).

The ``models`` table is the authoritative registry of models belonging to
registered providers. Phase 6 Milestone 3 introduces the first governed
operations on it (previously models were writable only by raw SQL in tests),
so discovery approval materialization and any future governed callers have a
single, audited path that emits the reserved ``MODEL_*`` events
(``core/events.py``).

Operations:

* ``add_model`` - create a model row under an existing provider; emits
  ``MODEL_ADDED``.
* ``get_model`` / ``list_models`` - read-only lookups (never fabricate).
* ``update_model`` - update model metadata; emits ``MODEL_UPDATED``.
* ``archive_model`` - record governed archival of a model. Owner decision
  (Phase 6 M3, Option A): the ``MODEL_ARCHIVED`` event carries the archival
  record; the ``models`` row is retained UNCHANGED and ``list_models`` keeps
  returning it (Article 5). No archival column exists or is added to
  ``models``; no model lifecycle state is invented; monitoring availability
  stays a separate domain.

Guarantees:

* provider/model rows are never deleted (Article 5)
* model identity is UNIQUE per provider (``model_identifier``)
* every mutation records an append-only event (Article 8)
* errors are raised deterministically, never silent
"""

from __future__ import annotations

import sqlite3
from typing import Optional, Sequence

from core import events

#: Fields that may be updated by :func:`update_model`. Mirrors the model
#: metadata keys validated by ``discovery.sources`` for candidate models so
#: materialization and registry updates accept the same vocabulary. The
#: deprecated v1.1 scalar score columns are not part of the governed metadata
#: surface; scores are managed through the normalized ``scores`` table
#: (ADR-0001) via ``scoring.ingest``.
UPDATABLE_FIELDS = (
    "model_name",
    "model_identifier",
    "context_window",
    "supports_tools",
    "supports_streaming",
    "supports_json",
    "supports_vision",
)


class ModelRegistryError(ValueError):
    """Raised when a model registry operation violates the rules."""


def _validate_model_name(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelRegistryError(
            "Model name is required and must be a non-empty string."
        )
    return value.strip()


def _validate_identifier(value) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ModelRegistryError(
            "Model identifier is required and must be a non-empty string."
        )
    return value.strip()


def _validate_context_window(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ModelRegistryError(
            "context_window must be a positive integer or null."
        )
    return value


def _validate_flag(value, name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ModelRegistryError(f"{name} must be a boolean.")


def _require_provider(conn, provider_id: int) -> None:
    row = conn.execute(
        "SELECT id FROM providers WHERE id = ?", (provider_id,)
    ).fetchone()
    if row is None:
        raise ModelRegistryError(f"Provider {provider_id} not found.")


def add_model(
    conn,
    provider_id: int,
    model_name: str,
    model_identifier: str,
    context_window=None,
    supports_tools=False,
    supports_streaming=False,
    supports_json=False,
    supports_vision=False,
) -> int:
    """Add a model to an existing provider. Returns the new model id."""
    _require_provider(conn, provider_id)
    name = _validate_model_name(model_name)
    identifier = _validate_identifier(model_identifier)
    window = _validate_context_window(context_window)
    flags = {
        "supports_tools": _validate_flag(supports_tools, "supports_tools"),
        "supports_streaming": _validate_flag(supports_streaming, "supports_streaming"),
        "supports_json": _validate_flag(supports_json, "supports_json"),
        "supports_vision": _validate_flag(supports_vision, "supports_vision"),
    }

    try:
        cursor = conn.execute(
            "INSERT INTO models"
            " (provider_id, model_name, model_identifier, context_window,"
            "  supports_tools, supports_streaming, supports_json, supports_vision)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                provider_id,
                name,
                identifier,
                window,
                flags["supports_tools"],
                flags["supports_streaming"],
                flags["supports_json"],
                flags["supports_vision"],
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ModelRegistryError(
            f"Model {identifier!r} already exists for provider {provider_id}."
        ) from exc
    except Exception as exc:
        conn.rollback()
        raise ModelRegistryError(
            f"Could not add model {identifier!r}: {exc}"
        ) from exc

    model_id = cursor.lastrowid
    events.record_event(
        conn,
        "MODEL_ADDED",
        entity_type="model",
        entity_id=model_id,
        payload={
            "provider_id": provider_id,
            "model_name": name,
            "model_identifier": identifier,
            "context_window": window,
            "supports_tools": flags["supports_tools"],
            "supports_streaming": flags["supports_streaming"],
            "supports_json": flags["supports_json"],
            "supports_vision": flags["supports_vision"],
        },
    )
    return model_id


def get_model(conn, model_id: int):
    """Return a single model row or None (mirrors core.providers.get_provider)."""
    return conn.execute(
        "SELECT * FROM models WHERE id = ?", (model_id,)
    ).fetchone()


def list_models(conn, provider_id: Optional[int] = None) -> Sequence[sqlite3.Row]:
    """List models in deterministic order, optionally filtered by provider.

    Returns model rows enriched with the owning provider name. Retained model
    rows (including any archived under the Option A event-only archival) are
    always listed - no hidden filtering or archival semantics.
    """
    if provider_id is not None:
        return conn.execute(
            "SELECT m.*, p.name AS provider_name"
            " FROM models m JOIN providers p ON p.id = m.provider_id"
            " WHERE m.provider_id = ?"
            " ORDER BY p.name, m.model_identifier",
            (provider_id,),
        ).fetchall()
    return conn.execute(
        "SELECT m.*, p.name AS provider_name"
        " FROM models m JOIN providers p ON p.id = m.provider_id"
        " ORDER BY p.name, m.model_identifier"
    ).fetchall()


def update_model(conn, model_id: int, **fields) -> dict:
    """Update model metadata. Records a MODEL_UPDATED event.

    Accepted keys are those in :data:`UPDATABLE_FIELDS`. No model lifecycle
    state is stored, so nothing is blocked on an unpersisted archival state
    (owner decision, Phase 6 M3 Option A).
    """
    unknown = set(fields) - set(UPDATABLE_FIELDS)
    if unknown:
        raise ModelRegistryError(
            f"Unknown model fields: {sorted(unknown)}. Allowed: {list(UPDATABLE_FIELDS)}."
        )
    if not fields:
        raise ModelRegistryError("No fields provided to update.")

    existing = get_model(conn, model_id)
    if existing is None:
        raise ModelRegistryError(f"Model {model_id} not found.")

    assignments = []
    params = []
    for key in UPDATABLE_FIELDS:
        if key not in fields:
            continue
        value = fields[key]
        if key == "model_name":
            value = _validate_model_name(value)
        elif key == "model_identifier":
            value = _validate_identifier(value)
        elif key == "context_window":
            value = _validate_context_window(value)
        else:
            value = _validate_flag(value, key)
        assignments.append(f"{key} = ?")
        params.append(value)
    assignments.append("updated_at = datetime('now')")
    params.append(model_id)

    try:
        conn.execute(
            f"UPDATE models SET {', '.join(assignments)} WHERE id = ?", params
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ModelRegistryError(
            f"Could not update model {model_id}: {exc}"
        ) from exc
    except Exception as exc:
        conn.rollback()
        raise ModelRegistryError(
            f"Could not update model {model_id}: {exc}"
        ) from exc

    events.record_event(
        conn,
        "MODEL_UPDATED",
        entity_type="model",
        entity_id=model_id,
        payload={"changed_fields": list(fields)},
    )
    return dict(get_model(conn, model_id))


def archive_model(conn, model_id: int, reason: str) -> dict:
    """Record governed archival of a model (Phase 6 M3, Option A).

    The archival record is the required, non-empty ``MODEL_ARCHIVED`` event.
    The ``models`` row is retained UNCHANGED and is never deleted (Article 5);
    ``list_models`` continues to return it. No schema column, no model
    lifecycle state and no monitoring-availability coupling are introduced.
    """
    if not reason or not reason.strip():
        raise ModelRegistryError(
            "archive_model requires an explicit, non-empty reason."
        )
    existing = get_model(conn, model_id)
    if existing is None:
        raise ModelRegistryError(f"Model {model_id} not found.")

    events.record_event(
        conn,
        "MODEL_ARCHIVED",
        entity_type="model",
        entity_id=model_id,
        payload={
            "provider_id": existing["provider_id"],
            "model_name": existing["model_name"],
            "model_identifier": existing["model_identifier"],
            "reason": reason.strip(),
        },
    )
    return dict(get_model(conn, model_id))
