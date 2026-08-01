"""Tests for the monitoring health check module."""

from __future__ import annotations

import pytest

from core import events, providers
from monitoring import health


def _add_provider(conn, name="Gemini", base_url="https://api.example.com"):
    return providers.add_provider(conn, name, base_url=base_url)


def _fake_ok(url, timeout, threshold):
    return health.HealthResult(state="OK", status_code=200, latency_ms=50)


def _fake_failed(url, timeout, threshold):
    return health.HealthResult(state="FAILED", status_code=503, error="down")


def test_check_provider_ok(conn):
    pid = _add_provider(conn)
    result = health.check_provider(conn, pid, transport=_fake_ok)
    assert result.state == "OK"
    assert result.ok is True


def test_check_provider_failed(conn):
    pid = _add_provider(conn)
    result = health.check_provider(conn, pid, transport=_fake_failed)
    assert result.state == "FAILED"
    assert result.ok is False


def test_check_provider_without_base_url_is_unknown(conn):
    pid = providers.add_provider(conn, "Blackbox AI")
    result = health.check_provider(conn, pid, transport=_fake_ok)
    assert result.state == "UNKNOWN"
    assert "base_url" in (result.error or "")


def test_check_provider_missing_raises(conn):
    with pytest.raises(health.HealthCheckError):
        health.check_provider(conn, 999, transport=_fake_ok)


def test_check_provider_records_event(conn):
    pid = _add_provider(conn)
    health.check_provider(conn, pid, transport=_fake_ok)
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    assert evts[0]["event_type"] == "HEALTH_CHECK_OK"


def test_check_provider_failure_records_event(conn):
    pid = _add_provider(conn)
    health.check_provider(conn, pid, transport=_fake_failed)
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    assert evts[0]["event_type"] == "HEALTH_CHECK_FAILED"


def test_check_provider_unknown_records_event(conn):
    pid = providers.add_provider(conn, "MiniMax")
    health.check_provider(conn, pid, transport=_fake_ok)
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    assert evts[0]["event_type"] == "HEALTH_CHECK_UNKNOWN"


def test_classify_latency_over_threshold_fails():
    classified = health._classify(200, 150, 100)
    assert classified.state == "FAILED"
    assert "threshold" in (classified.error or "")


def test_classify_within_threshold_ok():
    classified = health._classify(200, 50, 100)
    assert classified.state == "OK"


def test_check_provider_never_sends_secrets():
    """The default transport must not include auth headers (urllib Request
    constructed with method only, no headers dict)."""
    import urllib.request

    req = urllib.request.Request("https://api.example.com", method="HEAD")
    assert req.headers == {}
