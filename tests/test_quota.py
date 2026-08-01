"""Tests for the quota monitoring architecture."""

from __future__ import annotations

import pytest

from core import events, providers
from monitoring import availability, quota


def _add(conn, status="ACTIVE", name="Gemini"):
    return providers.add_provider(conn, name, status=status)


def test_record_quota_signal_active_to_limited(conn):
    pid = _add(conn)
    updated = quota.record_quota_signal(conn, pid, "daily")
    assert updated["status"] == "LIMITED"
    assert updated["status_reason"] == "Quota exhausted."


def test_record_quota_signal_custom_reason(conn):
    pid = _add(conn)
    updated = quota.record_quota_signal(conn, pid, "rate", "Rate limit exceeded.")
    assert updated["status"] == "LIMITED"
    assert updated["status_reason"] == "Rate limit exceeded."


def test_record_quota_signal_degraded_not_moved(conn):
    """v1.2 Section 5 only legalizes ACTIVE -> LIMITED; a DEGRADED provider
    records the quota signal but is not moved by quota alone."""
    pid = _add(conn)
    availability.apply_lifecycle(conn, pid, "DEGRADED", "High latency.")
    updated = quota.record_quota_signal(conn, pid, "monthly")
    assert updated["status"] == "DEGRADED"
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    assert "QUOTA_SIGNAL" in [e["event_type"] for e in evts]


def test_record_quota_signal_invalid_type_rejected(conn):
    pid = _add(conn)
    with pytest.raises(quota.QuotaError):
        quota.record_quota_signal(conn, pid, "weekly")


def test_record_quota_signal_missing_provider_rejected(conn):
    with pytest.raises(quota.QuotaError):
        quota.record_quota_signal(conn, 999, "daily")


def test_record_quota_signal_records_event(conn):
    pid = _add(conn)
    quota.record_quota_signal(conn, pid, "daily")
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    assert "QUOTA_SIGNAL" in [e["event_type"] for e in evts]


def test_quota_type_and_reset_stored_on_availability(conn):
    pid = _add(conn)
    quota.record_quota_signal(conn, pid, "daily")
    row = availability.get_availability(conn, pid)
    assert row["quota_type"] == "daily"


def test_classify_status_code_429(conn):
    assert quota.classify_status_code(429) == "rate"


def test_classify_status_code_200_none():
    assert quota.classify_status_code(200) is None


def test_set_quota_reset_records_timestamp(conn):
    pid = _add(conn)
    quota.record_quota_signal(conn, pid, "daily")
    quota.set_quota_reset(conn, pid, "2026-08-02 00:00:00")
    row = availability.get_availability(conn, pid)
    assert row["reset_at"] == "2026-08-02 00:00:00"


def test_detect_quota_reset_limited_to_active(conn):
    pid = _add(conn)
    quota.record_quota_signal(conn, pid, "daily")
    assert providers.get_provider(conn, pid)["status"] == "LIMITED"
    quota.set_quota_reset(conn, pid, "2026-08-01 12:00:00")
    updated = quota.detect_quota_reset(conn, pid)
    assert updated["status"] == "ACTIVE"
    assert updated["status_reason"] is None


def test_detect_quota_reset_without_reset_rejected(conn):
    pid = _add(conn)
    quota.record_quota_signal(conn, pid, "daily")
    with pytest.raises(quota.QuotaError):
        quota.detect_quota_reset(conn, pid)


def test_detect_quota_reset_not_limited_noop(conn):
    pid = _add(conn)
    updated = quota.detect_quota_reset(conn, pid)
    assert updated["status"] == "ACTIVE"


def test_detect_quota_reset_records_event(conn):
    pid = _add(conn)
    quota.record_quota_signal(conn, pid, "daily")
    quota.set_quota_reset(conn, pid, "2026-08-01 12:00:00")
    quota.detect_quota_reset(conn, pid)
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    assert "MONITOR_STATUS_CHANGED" in [e["event_type"] for e in evts]
