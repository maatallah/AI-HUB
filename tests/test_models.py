"""Tests for the Phase 6 Milestone 3 governed model registry (core.models).

Owner decision (M3, Option A): ``archive_model`` records the ``MODEL_ARCHIVED``
event with a required reason; the ``models`` row is retained unchanged and
``list_models`` keeps returning it. No model lifecycle state, no schema
column, no monitoring-availability coupling.
"""

from __future__ import annotations

import json

import pytest

from core import events, providers
from core import models as models_registry


def _add_provider(conn, name="Acme"):
    return providers.add_provider(conn, name, status="ACTIVE")


def _add_model(conn, provider_id, identifier="acme-turbo", **kw):
    return models_registry.add_model(
        conn,
        provider_id,
        model_name="Acme Turbo",
        model_identifier=identifier,
        **kw,
    )


def _event_payloads(conn, event_type):
    rows = conn.execute(
        "SELECT * FROM events WHERE event_type = ? ORDER BY id", (event_type,)
    ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


# ---------------------------------------------------------------------------
# event vocabulary
# ---------------------------------------------------------------------------

def test_model_events_whitelisted():
    assert {"MODEL_ADDED", "MODEL_UPDATED", "MODEL_ARCHIVED"} <= events.EVENT_TYPES


# ---------------------------------------------------------------------------
# add_model
# ---------------------------------------------------------------------------

def test_add_model_creates_row_and_event(conn):
    provider_id = _add_provider(conn)
    model_id = _add_model(conn, provider_id)
    row = models_registry.get_model(conn, model_id)
    assert row["provider_id"] == provider_id
    assert row["model_name"] == "Acme Turbo"
    assert row["model_identifier"] == "acme-turbo"
    payloads = _event_payloads(conn, "MODEL_ADDED")
    assert len(payloads) == 1
    assert payloads[0]["provider_id"] == provider_id
    assert payloads[0]["model_identifier"] == "acme-turbo"


def test_add_model_requires_existing_provider(conn):
    with pytest.raises(models_registry.ModelRegistryError):
        _add_model(conn, 999)


def test_add_model_requires_name(conn):
    provider_id = _add_provider(conn)
    with pytest.raises(models_registry.ModelRegistryError):
        models_registry.add_model(conn, provider_id, model_name="  ", model_identifier="m")


def test_add_model_requires_identifier(conn):
    provider_id = _add_provider(conn)
    with pytest.raises(models_registry.ModelRegistryError):
        models_registry.add_model(conn, provider_id, model_name="M", model_identifier="")


def test_add_model_rejects_bad_context_window(conn):
    provider_id = _add_provider(conn)
    for bad in (0, -5, True, 1.5):
        with pytest.raises(models_registry.ModelRegistryError):
            _add_model(conn, provider_id, context_window=bad)


def test_add_model_rejects_non_boolean_flags(conn):
    provider_id = _add_provider(conn)
    with pytest.raises(models_registry.ModelRegistryError):
        _add_model(conn, provider_id, supports_tools=1)
    with pytest.raises(models_registry.ModelRegistryError):
        _add_model(conn, provider_id, supports_json="yes")


def test_add_model_accepts_metadata(conn):
    provider_id = _add_provider(conn)
    model_id = _add_model(
        conn,
        provider_id,
        context_window=128000,
        supports_tools=True,
        supports_streaming=True,
        supports_json=True,
        supports_vision=False,
    )
    row = models_registry.get_model(conn, model_id)
    assert row["context_window"] == 128000
    assert row["supports_tools"] == 1
    assert row["supports_streaming"] == 1
    assert row["supports_json"] == 1
    assert row["supports_vision"] == 0


def test_add_model_duplicate_identifier_per_provider_rejected(conn):
    provider_id = _add_provider(conn)
    _add_model(conn, provider_id, identifier="m-1")
    with pytest.raises(models_registry.ModelRegistryError) as exc_info:
        _add_model(conn, provider_id, identifier="m-1")
    assert "already exists" in str(exc_info.value)


def test_add_model_same_identifier_different_providers_allowed(conn):
    p1 = _add_provider(conn, "Alpha")
    p2 = _add_provider(conn, "Beta")
    _add_model(conn, p1, identifier="shared")
    _add_model(conn, p2, identifier="shared")  # no error


# ---------------------------------------------------------------------------
# get / list
# ---------------------------------------------------------------------------

def test_get_model_missing_returns_none(conn):
    assert models_registry.get_model(conn, 999) is None


def test_list_models_ordered_with_provider_name(conn):
    p1 = _add_provider(conn, "Zulu")
    p2 = _add_provider(conn, "Alpha")
    _add_model(conn, p1, identifier="z-1")
    _add_model(conn, p2, identifier="a-1")
    rows = models_registry.list_models(conn)
    assert [r["provider_name"] for r in rows] == ["Alpha", "Zulu"]
    assert [r["model_identifier"] for r in rows] == ["a-1", "z-1"]


def test_list_models_filter_by_provider(conn):
    p1 = _add_provider(conn, "Alpha")
    p2 = _add_provider(conn, "Beta")
    _add_model(conn, p1, identifier="a-1")
    _add_model(conn, p2, identifier="b-1")
    rows = models_registry.list_models(conn, provider_id=p1)
    assert [r["model_identifier"] for r in rows] == ["a-1"]


def test_list_models_empty(conn):
    assert models_registry.list_models(conn) == []


# ---------------------------------------------------------------------------
# update_model
# ---------------------------------------------------------------------------

def test_update_model_updates_and_events(conn):
    provider_id = _add_provider(conn)
    model_id = _add_model(conn, provider_id)
    updated = models_registry.update_model(
        conn, model_id, model_name="Acme Ultra", supports_vision=True
    )
    assert updated["model_name"] == "Acme Ultra"
    assert updated["supports_vision"] == 1
    payloads = _event_payloads(conn, "MODEL_UPDATED")
    assert payloads[-1]["changed_fields"] == ["model_name", "supports_vision"]


def test_update_model_unknown_field_rejected(conn):
    provider_id = _add_provider(conn)
    model_id = _add_model(conn, provider_id)
    with pytest.raises(models_registry.ModelRegistryError):
        models_registry.update_model(conn, model_id, bogus=1)


def test_update_model_no_fields_rejected(conn):
    provider_id = _add_provider(conn)
    model_id = _add_model(conn, provider_id)
    with pytest.raises(models_registry.ModelRegistryError):
        models_registry.update_model(conn, model_id)


def test_update_model_missing_model_rejected(conn):
    with pytest.raises(models_registry.ModelRegistryError):
        models_registry.update_model(conn, 999, model_name="M")


def test_update_model_duplicate_identifier_rejected(conn):
    provider_id = _add_provider(conn)
    _add_model(conn, provider_id, identifier="m-1")
    model_id = _add_model(conn, provider_id, identifier="m-2")
    with pytest.raises(models_registry.ModelRegistryError):
        models_registry.update_model(conn, model_id, model_identifier="m-1")


def test_update_model_invalid_value_rejected(conn):
    provider_id = _add_provider(conn)
    model_id = _add_model(conn, provider_id)
    with pytest.raises(models_registry.ModelRegistryError):
        models_registry.update_model(conn, model_id, context_window=-1)


# ---------------------------------------------------------------------------
# archive_model (Phase 6 M3 Option A: event-only archival)
# ---------------------------------------------------------------------------

def test_archive_model_requires_reason(conn):
    provider_id = _add_provider(conn)
    model_id = _add_model(conn, provider_id)
    with pytest.raises(models_registry.ModelRegistryError):
        models_registry.archive_model(conn, model_id, reason=None)
    with pytest.raises(models_registry.ModelRegistryError):
        models_registry.archive_model(conn, model_id, reason="   ")
    assert not _event_payloads(conn, "MODEL_ARCHIVED")


def test_archive_model_missing_model_rejected(conn):
    with pytest.raises(models_registry.ModelRegistryError):
        models_registry.archive_model(conn, 999, reason="retired")


def test_archive_model_retains_row_unchanged_and_events(conn):
    provider_id = _add_provider(conn)
    model_id = _add_model(
        conn, provider_id, context_window=1000, supports_tools=True
    )
    before = dict(models_registry.get_model(conn, model_id))
    result = models_registry.archive_model(conn, model_id, reason="retired")
    assert result == dict(models_registry.get_model(conn, model_id))
    assert dict(models_registry.get_model(conn, model_id)) == before  # unchanged
    assert models_registry.get_model(conn, model_id) is not None  # never deleted
    payloads = _event_payloads(conn, "MODEL_ARCHIVED")
    assert len(payloads) == 1
    assert payloads[0]["reason"] == "retired"
    assert payloads[0]["model_identifier"] == "acme-turbo"


def test_archive_model_still_listed_and_updatable(conn):
    """Option A: no hidden archival filtering; update is not blocked."""
    provider_id = _add_provider(conn)
    model_id = _add_model(conn, provider_id)
    models_registry.archive_model(conn, model_id, reason="retired")
    ids = [r["id"] for r in models_registry.list_models(conn)]
    assert model_id in ids
    updated = models_registry.update_model(conn, model_id, model_name="Renamed")
    assert updated["model_name"] == "Renamed"
