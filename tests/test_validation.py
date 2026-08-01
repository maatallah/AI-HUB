"""Tests for provider seed validation."""

from __future__ import annotations

import pytest

from core import events, providers
from monitoring import validation


def _add(conn, name="OpenAI", base_url="https://api.openai.com/v1"):
    return providers.add_provider(conn, name, base_url=base_url)


def _reachable(url):
    return True


def _unreachable(url):
    return False


def test_validate_url_valid():
    status, reason = validation.validate_url("https://api.openai.com/v1")
    assert status == "valid"
    assert reason is None


def test_validate_url_invalid_scheme():
    status, reason = validation.validate_url("ftp://api.example.com")
    assert status == "invalid"


def test_validate_url_missing_is_unknown():
    status, reason = validation.validate_url(None)
    assert status == "unknown"
    status, reason = validation.validate_url("   ")
    assert status == "unknown"


def test_validate_provider_passed(conn):
    pid = _add(conn)
    result = validation.validate_provider(conn, pid)
    assert result["ok"] is True
    assert result["event_type"] == "VALIDATION_PASSED"


def test_validate_provider_missing_base_url_unknown(conn):
    pid = providers.add_provider(conn, "Blackbox AI")
    result = validation.validate_provider(conn, pid)
    assert result["event_type"] == "VALIDATION_UNKNOWN"
    assert result["ok"] is False
    assert result["base_url_valid"] is False


def test_validate_provider_invalid_base_url_failed(conn):
    pid = providers.add_provider(conn, "Bad", base_url="not-a-url")
    result = validation.validate_provider(conn, pid)
    assert result["event_type"] == "VALIDATION_FAILED"


def test_validate_provider_unreachable_failed(conn):
    pid = _add(conn)
    result = validation.validate_provider(
        conn, pid, reachability_check=True, transport=_unreachable
    )
    assert result["event_type"] == "VALIDATION_FAILED"
    assert result["reachable"] is False


def test_validate_provider_reachable_passed(conn):
    pid = _add(conn)
    result = validation.validate_provider(
        conn, pid, reachability_check=True, transport=_reachable
    )
    assert result["event_type"] == "VALIDATION_PASSED"
    assert result["reachable"] is True


def test_validate_provider_records_event(conn):
    pid = _add(conn)
    validation.validate_provider(conn, pid)
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    assert evts[0]["event_type"] == "VALIDATION_PASSED"


def test_validate_provider_unknown_records_event(conn):
    pid = providers.add_provider(conn, "MiniMax")
    validation.validate_provider(conn, pid)
    evts = events.list_events(conn, entity_type="provider", entity_id=pid)
    assert evts[0]["event_type"] == "VALIDATION_UNKNOWN"


def test_validate_provider_missing_raises(conn):
    with pytest.raises(validation.ValidationError):
        validation.validate_provider(conn, 999)


def test_validate_seed_does_not_modify_providers(conn):
    pid = _add(conn, name="OpenAI")
    before = providers.get_provider(conn, pid)
    validation.validate_seed(conn)
    after = providers.get_provider(conn, pid)
    assert dict(after) == dict(before)


def test_validate_seed_returns_all_providers(conn):
    _add(conn, name="Alpha")
    _add(conn, name="Beta")
    results = validation.validate_seed(conn)
    assert len(results) == 2
