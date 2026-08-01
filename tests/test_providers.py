"""Tests for the manual provider registry."""

from __future__ import annotations

import pytest

from core import events, providers


def _pid(conn, name="Gemini"):
    return conn.execute(
        "SELECT id FROM providers WHERE name = ?", (name,)
    ).fetchone()["id"]


def test_add_provider_defaults_to_new(conn):
    pid = providers.add_provider(conn, "Gemini", company="Google")
    row = providers.get_provider(conn, pid)
    assert row["status"] == "NEW"
    assert row["company"] == "Google"


def test_add_provider_records_event(conn):
    pid = providers.add_provider(conn, "Gemini")
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    assert [e["event_type"] for e in evts] == ["PROVIDER_ADDED"]


def test_add_provider_duplicate_name_rejected(conn):
    providers.add_provider(conn, "Gemini")
    with pytest.raises(providers.RegistryError):
        providers.add_provider(conn, "Gemini")


def test_add_provider_empty_name_rejected(conn):
    with pytest.raises(providers.RegistryError):
        providers.add_provider(conn, "   ")


def test_add_provider_invalid_status_rejected(conn):
    with pytest.raises(providers.RegistryError):
        providers.add_provider(conn, "X", status="BOGUS")


def test_add_provider_nonactive_requires_reason(conn):
    with pytest.raises(providers.RegistryError):
        providers.add_provider(conn, "X", status="LIMITED")


def test_add_provider_nonactive_with_reason_ok(conn):
    pid = providers.add_provider(conn, "X", status="LIMITED", status_reason="Daily quota")
    assert providers.get_provider(conn, pid)["status"] == "LIMITED"


def test_list_providers_empty(conn):
    assert providers.list_providers(conn) == []


def test_list_providers_ordered_by_name(conn):
    providers.add_provider(conn, "Zeta")
    providers.add_provider(conn, "Alpha")
    names = [r["name"] for r in providers.list_providers(conn)]
    assert names == ["Alpha", "Zeta"]


def test_list_providers_filter_by_status(conn):
    providers.add_provider(conn, "A")
    providers.add_provider(conn, "B", status="ACTIVE")
    providers.add_provider(conn, "C", status="ACTIVE")
    active = providers.list_providers(conn, status="ACTIVE")
    assert {r["name"] for r in active} == {"B", "C"}


def test_update_provider_fields(conn):
    pid = providers.add_provider(conn, "Gemini")
    providers.update_provider(conn, pid, company="Google", api_type="Native")
    row = providers.get_provider(conn, pid)
    assert row["company"] == "Google"
    assert row["api_type"] == "Native"


def test_update_provider_unknown_field_rejected(conn):
    pid = providers.add_provider(conn, "Gemini")
    with pytest.raises(providers.RegistryError):
        providers.update_provider(conn, pid, api_key="sk-x")


def test_update_provider_missing_raises(conn):
    with pytest.raises(providers.RegistryError):
        providers.update_provider(conn, 999, company="X")


def test_update_status_requires_reason_for_nonactive(conn):
    pid = providers.add_provider(conn, "Gemini")
    with pytest.raises(providers.RegistryError):
        providers.update_provider(conn, pid, status="OFFLINE")
    providers.update_provider(conn, pid, status="OFFLINE", status_reason="No response")


def test_update_status_change_logs_event(conn):
    pid = providers.add_provider(conn, "Gemini")
    providers.update_provider(conn, pid, status="ACTIVE", status_reason=None)
    providers.update_provider(conn, pid, status="LIMITED", status_reason="Quota")
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    types = [e["event_type"] for e in evts]
    assert "PROVIDER_STATUS_CHANGED" in types


def test_archive_provider_requires_reason(conn):
    pid = providers.add_provider(conn, "Gemini")
    with pytest.raises(providers.RegistryError):
        providers.archive_provider(conn, pid, "")


def test_archive_provider_preserves_record(conn):
    pid = providers.add_provider(conn, "Gemini", status="ACTIVE")
    archived = providers.archive_provider(conn, pid, "Officially retired")
    assert archived["status"] == "ARCHIVED"
    assert archived["status_reason"] == "Officially retired"
    # Record is preserved, not deleted.
    assert providers.get_provider(conn, pid) is not None
    assert any(r["status"] == "ARCHIVED" for r in providers.list_providers(conn))


def test_archive_provider_records_event(conn):
    pid = providers.add_provider(conn, "Gemini", status="ACTIVE")
    providers.archive_provider(conn, pid, "Retired")
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    assert "PROVIDER_ARCHIVED" in [e["event_type"] for e in evts]


def test_archive_already_archived_rejected(conn):
    pid = providers.add_provider(conn, "Gemini", status="ACTIVE")
    providers.archive_provider(conn, pid, "Retired")
    with pytest.raises(providers.RegistryError):
        providers.archive_provider(conn, pid, "Again")


def test_archive_missing_provider_rejected(conn):
    with pytest.raises(providers.RegistryError):
        providers.archive_provider(conn, 999, "Gone")


def test_events_are_append_only(conn):
    """No update/delete operation is exposed by the events module."""
    assert not hasattr(events, "update_event")
    assert not hasattr(events, "delete_event")
