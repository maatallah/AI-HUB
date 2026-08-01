"""Tests for the fallback engine."""

from __future__ import annotations

import pytest

from core import events, providers
from fallback import build_chain, check_recovery, is_eligible, select_fallback
from scoring import ingest


def _provider(conn, name, status="ACTIVE", reason=None):
    return providers.add_provider(conn, name, status=status, status_reason=reason)


def _model(conn, pid, identifier, context_window=32000):
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier, context_window)"
        " VALUES (?, ?, ?, ?)",
        (pid, identifier, identifier, context_window),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (identifier,)
    ).fetchone()["id"]


def _score(conn, mid, coding, reasoning):
    ingest.set_score(conn, mid, "coding", coding, confidence=1.0, source="MANUAL")
    ingest.set_score(conn, mid, "reasoning", reasoning, confidence=1.0, source="MANUAL")


def _chain(conn, task="python", max_chain_length=5):
    p1 = _provider(conn, "Alpha")
    p2 = _provider(conn, "Beta")
    p3 = _provider(conn, "Gamma")
    m1 = _model(conn, p1, "alpha-1")
    m2 = _model(conn, p2, "beta-1")
    m3 = _model(conn, p3, "gamma-1")
    _score(conn, m1, 90, 80)
    _score(conn, m2, 70, 70)
    _score(conn, m3, 60, 60)
    return build_chain(conn, task, max_chain_length=max_chain_length), (p1, p2, p3)


def test_is_eligible():
    assert is_eligible("ACTIVE") is True
    assert is_eligible("LIMITED") is True
    assert is_eligible("DEGRADED") is True
    assert is_eligible("DEGRADED", allow_last_resort=False) is False
    assert is_eligible("OFFLINE") is False
    assert is_eligible("ARCHIVED") is False
    assert is_eligible("NEW") is False
    assert is_eligible("EVALUATING") is False


def test_build_chain_primary_is_top_ranked(conn):
    chain, (p1, p2, p3) = _chain(conn)
    assert chain.primary is not None
    assert chain.primary.provider_id == p1
    assert len(chain.fallbacks) == 2


def test_build_chain_respects_max_length(conn):
    chain, _ = _chain(conn, max_chain_length=1)
    assert len(chain.recommendations) == 2  # primary + 1 fallback


def test_build_chain_excludes_offline(conn):
    p1 = _provider(conn, "Alpha")
    p2 = _provider(conn, "Beta")
    m1 = _model(conn, p1, "alpha-1")
    m2 = _model(conn, p2, "beta-1")
    _score(conn, m1, 90, 80)
    _score(conn, m2, 70, 70)
    # simulate offline via the legal monitoring lifecycle path (Section 9)
    from monitoring import availability as availability_mod
    availability_mod.apply_lifecycle(conn, p2, "DEGRADED", "flaky")
    availability_mod.apply_lifecycle(conn, p2, "OFFLINE", "down")
    chain = build_chain(conn, "python")
    assert [r.provider_id for r in chain.recommendations] == [p1]


def test_select_fallback_skips_current(conn):
    chain, (p1, p2, p3) = _chain(conn)
    selected = select_fallback(conn, chain, p1, reason="Quota exhausted.")
    assert selected.provider_id == p2


def test_select_fallback_returns_none_when_exhausted(conn):
    chain, (p1, p2, p3) = _chain(conn)
    selected = select_fallback(conn, chain, p3)
    assert selected is None


def test_select_fallback_unknown_provider_rejected(conn):
    chain, (p1, p2, p3) = _chain(conn)
    with pytest.raises(Exception):
        select_fallback(conn, chain, 999)


def test_select_fallback_records_event(conn):
    chain, (p1, p2, p3) = _chain(conn)
    select_fallback(conn, chain, p1, reason="Quota exhausted.")
    types = [e["event_type"] for e in events.list_events(conn)]
    assert "FALLBACK_TRIGGERED" in types


def test_check_recovery_returns_primary(conn):
    chain, (p1, p2, p3) = _chain(conn)
    primary = check_recovery(conn, chain)
    assert primary.provider_id == p1
    types = [e["event_type"] for e in events.list_events(conn)]
    assert "FALLBACK_RECOVERED" in types


def test_check_recovery_none_when_primary_degraded(conn):
    from monitoring import availability as availability_mod
    chain, (p1, p2, p3) = _chain(conn)
    availability_mod.apply_lifecycle(conn, p1, "DEGRADED", "flaky")
    assert check_recovery(conn, chain) is None
