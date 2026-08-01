"""Tests for availability tracking and lifecycle transitions."""

from __future__ import annotations

import pytest

from core import events, providers
from monitoring import availability


def _add(conn, status="ACTIVE", name="Gemini"):
    return providers.add_provider(conn, name, status=status)


def test_update_availability_success_resets_failures(conn):
    pid = _add(conn)
    availability.update_availability(conn, pid, "FAILED")
    availability.update_availability(conn, pid, "FAILED")
    row = availability.get_availability(conn, pid)
    assert row["consecutive_failures"] == 2
    availability.update_availability(conn, pid, "OK")
    row = availability.get_availability(conn, pid)
    assert row["consecutive_failures"] == 0
    assert row["state"] == "ACTIVE"


def test_update_availability_failure_increments(conn):
    pid = _add(conn)
    availability.update_availability(conn, pid, "FAILED")
    availability.update_availability(conn, pid, "FAILED")
    row = availability.get_availability(conn, pid)
    assert row["consecutive_failures"] == 2
    assert row["last_failure"] is not None


def test_update_availability_creates_row(conn):
    pid = _add(conn)
    assert availability.get_availability(conn, pid) is None
    availability.update_availability(conn, pid, "OK")
    assert availability.get_availability(conn, pid) is not None


def test_update_availability_invalid_state_rejected(conn):
    pid = _add(conn)
    with pytest.raises(ValueError):
        availability.update_availability(conn, pid, "BOGUS")


def test_apply_lifecycle_active_to_degraded(conn):
    pid = _add(conn)
    updated = availability.apply_lifecycle(conn, pid, "DEGRADED", "Repeated failures.")
    assert updated["status"] == "DEGRADED"
    assert updated["status_reason"] == "Repeated failures."


def test_apply_lifecycle_requires_reason_for_nonactive(conn):
    pid = _add(conn)
    with pytest.raises(ValueError):
        availability.apply_lifecycle(conn, pid, "DEGRADED", "")


def test_apply_lifecycle_illegal_transition_rejected(conn):
    pid = _add(conn)  # ACTIVE
    with pytest.raises(ValueError):
        availability.apply_lifecycle(conn, pid, "ARCHIVED", "nope")
    with pytest.raises(ValueError):
        availability.apply_lifecycle(conn, pid, "OFFLINE", "nope")


def test_apply_lifecycle_no_automatic_archival(conn):
    pid = _add(conn)
    with pytest.raises(ValueError):
        availability.apply_lifecycle(conn, pid, "ARCHIVED", "auto")


def test_apply_lifecycle_degraded_to_offline(conn):
    pid = _add(conn)
    availability.apply_lifecycle(conn, pid, "DEGRADED", "Repeated failures.")
    updated = availability.apply_lifecycle(
        conn, pid, "OFFLINE", "Repeated monitoring failures beyond configured threshold."
    )
    assert updated["status"] == "OFFLINE"


def test_apply_lifecycle_offline_to_active(conn):
    pid = providers.add_provider(
        conn, "X", status="OFFLINE", status_reason="Down"
    )
    updated = availability.apply_lifecycle(conn, pid, "ACTIVE", "Successful recovery.")
    assert updated["status"] == "ACTIVE"
    assert updated["status_reason"] is None


def test_apply_lifecycle_records_events(conn):
    pid = _add(conn)
    availability.apply_lifecycle(conn, pid, "DEGRADED", "Repeated failures.")
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    types = [e["event_type"] for e in evts]
    assert "MONITOR_STATUS_CHANGED" in types
    assert "PROVIDER_STATUS_CHANGED" in types


def test_apply_lifecycle_same_status_noop(conn):
    pid = _add(conn)
    before = providers.get_provider(conn, pid)
    updated = availability.apply_lifecycle(conn, pid, "ACTIVE")
    assert updated["status"] == before["status"]


def test_list_availability_ordered(conn):
    pid_a = _add(conn, name="Zeta")
    pid_b = _add(conn, name="Alpha")
    availability.update_availability(conn, pid_a, "FAILED")
    availability.update_availability(conn, pid_b, "OK")
    rows = availability.list_availability(conn)
    names = [r["provider_name"] for r in rows]
    assert names == ["Alpha", "Zeta"]
