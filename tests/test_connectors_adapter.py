"""Tests for the shared read-only connector adapter (Phase 5).

The adapter must be the sole connector access boundary, delegate to existing
engines (never duplicate logic), and never mutate state.
"""

from __future__ import annotations

import pytest

from connectors import adapter
from core import providers
from dashboard import engine as dashboard_engine
from dashboard import history as dashboard_history
from dashboard import reports as dashboard_reports
from monitoring import availability as availability_mod
from recommendation import provenance
from scoring import ingest


def _provider(conn, name, status="ACTIVE", reason=None):
    return providers.add_provider(conn, name, status=status, status_reason=reason)


def _model(conn, pid, identifier, context_window=32000, tools=0, vision=0, json=0, streaming=0):
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier, context_window,"
        " supports_tools, supports_vision, supports_json, supports_streaming)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (pid, identifier, identifier, context_window, tools, vision, json, streaming),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (identifier,)
    ).fetchone()["id"]


def _score(conn, mid, dimension, value):
    ingest.set_score(conn, mid, dimension, value, confidence=1.0, source="MANUAL")


def _seed_recommendation_data(conn):
    p1 = _provider(conn, "Alpha")
    p2 = _provider(conn, "Beta")
    m1 = _model(conn, p1, "alpha-1")
    m2 = _model(conn, p2, "beta-1")
    _score(conn, m1, "coding", 90)
    _score(conn, m1, "reasoning", 70)
    _score(conn, m2, "coding", 60)
    _score(conn, m2, "reasoning", 60)
    return p1, p2, m1, m2


# --- delegation (identical to direct engine calls) ---------------------------


def test_provider_status_matches_engine(conn):
    p1 = _provider(conn, "Alpha")
    availability_mod.apply_lifecycle(conn, p1, "DEGRADED", "Repeated failures.")
    data = adapter.provider_status(conn)
    assert list(data) == ["providers", "availability"]
    direct_view = [dict(r) for r in dashboard_engine.provider_view(conn)]
    direct_avail = [dict(r) for r in availability_mod.list_availability(conn)]
    assert data["providers"] == direct_view
    assert data["availability"] == direct_avail


def test_model_scores_matches_engine(conn):
    _seed_recommendation_data(conn)
    assert adapter.model_scores(conn) == [dict(r) for r in dashboard_engine.score_view(conn)]


def test_model_scores_filtered_matches_engine(conn):
    p1, p2, m1, m2 = _seed_recommendation_data(conn)
    result = adapter.model_scores(conn, model_id=m1)
    assert result  # one row per scored dimension
    assert {r["model_id"] for r in result} == {m1}


def test_recommend_top_matches_engine(conn):
    _seed_recommendation_data(conn)
    result = adapter.recommend_top(conn, "python", profile="coding")
    assert [r["model_identifier"] for r in result] == ["alpha-1", "beta-1"]


def test_recommend_top_never_records_provenance(conn):
    _seed_recommendation_data(conn)
    adapter.recommend_top(conn, "python", profile="coding")
    assert provenance.list_recommendations(conn) == []


def test_fallback_chain_structure(conn):
    _seed_recommendation_data(conn)
    chain = adapter.fallback_chain(conn, "python", profile="coding", max_chain_length=2)
    assert chain["task"] == "python"
    assert chain["max_chain_length"] == 2
    assert chain["primary"]["model_identifier"] == "alpha-1"
    assert [r["model_identifier"] for r in chain["fallbacks"]] == ["beta-1"]


def test_dashboard_report_all_names(conn):
    _seed_recommendation_data(conn)
    for name in dashboard_reports.REPORT_BUILDERS:
        text = adapter.dashboard_report(conn, name)
        assert isinstance(text, str)
        assert text


def test_dashboard_report_unknown_raises(conn):
    with pytest.raises(ValueError):
        adapter.dashboard_report(conn, "nope")


def test_score_history_matches_engine(conn):
    p1 = _provider(conn, "Acme")
    m1 = _model(conn, p1, "acme-1")
    _score(conn, m1, "coding", 70)
    assert adapter.score_history(conn, m1) == dashboard_history.score_history(conn, m1)


def test_availability_history_matches_engine(conn):
    p1 = _provider(conn, "Acme")
    availability_mod.apply_lifecycle(conn, p1, "DEGRADED", "Repeated failures.")
    assert adapter.availability_history(conn) == dashboard_history.availability_history(conn)


def test_provider_list_matches_engine(conn):
    _provider(conn, "Alpha")
    _provider(conn, "Beta", status="LIMITED", reason="for test")
    assert adapter.provider_list(conn) == [dict(r) for r in providers.list_providers(conn)]
    limited = adapter.provider_list(conn, status="LIMITED")
    assert [r["name"] for r in limited] == ["Beta"]


# --- read-only + determinism -------------------------------------------------


def _snapshot(conn):
    return conn.execute("SELECT * FROM events ORDER BY id").fetchall()


def test_adapter_calls_do_not_write(conn):
    p1, p2, m1, m2 = _seed_recommendation_data(conn)
    availability_mod.apply_lifecycle(conn, p1, "DEGRADED", "Repeated failures.")
    before = _snapshot(conn)
    adapter.provider_status(conn)
    adapter.model_scores(conn)
    adapter.recommend_top(conn, "python")
    adapter.fallback_chain(conn, "python")
    adapter.dashboard_report(conn, "scores")
    adapter.score_history(conn, m1)
    adapter.availability_history(conn)
    adapter.provider_list(conn)
    assert _snapshot(conn) == before


def test_adapter_deterministic(conn):
    _seed_recommendation_data(conn)
    first = adapter.recommend_top(conn, "python", profile="coding")
    second = adapter.recommend_top(conn, "python", profile="coding")
    assert first == second
    assert adapter.dashboard_report(conn, "scores") == adapter.dashboard_report(conn, "scores")


def test_empty_no_data_is_empty_not_fabricated(conn):
    assert adapter.provider_status(conn)["providers"] == []
    assert adapter.model_scores(conn) == []
    assert adapter.recommend_top(conn, "python") == []
    assert adapter.score_history(conn, 999) == []
    assert adapter.availability_history(conn) == []
