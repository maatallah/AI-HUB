"""Tests for the read-only trend analysis module (Phase 6, trend milestone)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from core import providers
from dashboard import history as dashboard_history
from trend import analysis as trend


def _add_provider(conn, name="Acme", status="ACTIVE"):
    reason = None if status == "ACTIVE" else "for test"
    return providers.add_provider(conn, name, status=status, status_reason=reason)


def _model(conn, provider_id, identifier="acme-1"):
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier)"
        " VALUES (?, 'Acme Model', ?)",
        (provider_id, identifier),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (identifier,)
    ).fetchone()["id"]


def _score_event(conn, model_id, dimension, value, occurred_at):
    conn.execute(
        "INSERT INTO events (event_type, entity_type, entity_id, payload, occurred_at)"
        " VALUES ('SCORE_RECORDED', 'model', ?, ?, ?)",
        (model_id, json.dumps({"dimension": dimension, "value": value}), occurred_at),
    )
    conn.commit()


def _health_event(conn, provider_id, event_type, occurred_at, payload=None):
    conn.execute(
        "INSERT INTO events (event_type, entity_type, entity_id, payload, occurred_at)"
        " VALUES (?, 'provider', ?, ?, ?)",
        (event_type, provider_id, json.dumps(payload or {}), occurred_at),
    )
    conn.commit()


def _days(base, n):
    return (datetime.fromisoformat(base) + timedelta(days=n)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# --- score direction --------------------------------------------------------


def test_score_trend_up(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 70, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 80, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 90, "2026-03-01 00:00:00")
    results = trend.score_trend(conn, mid)
    assert len(results) == 1
    r = results[0]
    assert r["dimension"] == "coding"
    assert r["direction"] == trend.DIRECTION_UP
    assert r["magnitude"] == pytest.approx(0.2)
    assert r["first"] == 70.0
    assert r["last"] == 90.0
    assert r["point_count"] == 3
    assert r["series_count"] == 3


def test_score_trend_down(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 90, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 80, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 70, "2026-03-01 00:00:00")
    r = trend.score_trend(conn, mid)[0]
    assert r["direction"] == trend.DIRECTION_DOWN
    assert r["magnitude"] == pytest.approx(-0.2)


def test_score_trend_stable_within_band(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 80, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 80, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 84, "2026-03-01 00:00:00")
    r = trend.score_trend(conn, mid)[0]
    assert r["direction"] == trend.DIRECTION_STABLE
    assert r["magnitude"] == pytest.approx(0.04)


def test_score_trend_positive_boundary_is_stable(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 80, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 80, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 85, "2026-03-01 00:00:00")
    r = trend.score_trend(conn, mid)[0]
    assert r["magnitude"] == pytest.approx(0.05)
    assert r["direction"] == trend.DIRECTION_STABLE


def test_score_trend_negative_boundary_is_stable(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 80, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 80, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 75, "2026-03-01 00:00:00")
    r = trend.score_trend(conn, mid)[0]
    assert r["magnitude"] == pytest.approx(-0.05)
    assert r["direction"] == trend.DIRECTION_STABLE


def test_score_trend_just_past_band_is_up_or_down(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 80, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 80, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 86, "2026-03-01 00:00:00")
    assert trend.score_trend(conn, mid)[0]["direction"] == trend.DIRECTION_UP
    conn.execute("DELETE FROM events")
    conn.commit()
    _score_event(conn, mid, "coding", 80, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 80, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 74, "2026-03-01 00:00:00")
    assert trend.score_trend(conn, mid)[0]["direction"] == trend.DIRECTION_DOWN


def test_score_trend_magnitude_formula(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 55, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 60, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 93, "2026-03-01 00:00:00")
    r = trend.score_trend(conn, mid)[0]
    assert r["magnitude"] == pytest.approx((93.0 - 55.0) / 100.0)


def test_score_trend_stability_is_population_standard_deviation(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 70, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 80, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 90, "2026-03-01 00:00:00")
    r = trend.score_trend(conn, mid)[0]
    expected = ((70.0 - 80.0) ** 2 + (80.0 - 80.0) ** 2 + (90.0 - 80.0) ** 2) / 3
    assert r["stability"] == pytest.approx(expected**0.5)
    assert r["stdev"] == "population"


# --- insufficient data ------------------------------------------------------


def test_score_trend_insufficient_data(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 80, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 90, "2026-02-01 00:00:00")
    r = trend.score_trend(conn, mid)[0]
    assert r["direction"] == trend.DIRECTION_INSUFFICIENT
    assert r["magnitude"] is None
    assert r["stability"] is None
    assert r["first"] is None
    assert r["last"] is None
    assert r["point_count"] == 2
    assert r["min_points"] == 3


def test_score_trend_exactly_min_points_is_sufficient(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 80, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 80, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 80, "2026-03-01 00:00:00")
    r = trend.score_trend(conn, mid)[0]
    assert r["direction"] == trend.DIRECTION_STABLE
    assert r["point_count"] == 3


def test_score_trend_no_history_is_empty(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    assert trend.score_trend(conn, mid) == []


# --- window anchoring -------------------------------------------------------


def test_score_trend_default_window_anchored_to_last_point(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 10, _days("2026-01-01 00:00:00", 0))
    _score_event(conn, mid, "coding", 80, _days("2026-01-01 00:00:00", 60))
    _score_event(conn, mid, "coding", 90, _days("2026-01-01 00:00:00", 100))
    r = trend.score_trend(conn, mid, min_points=2)[0]
    assert r["series_count"] == 3
    assert r["point_count"] == 2
    assert r["first"] == 80.0
    assert r["last"] == 90.0


def test_score_trend_explicit_window_days(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 10, _days("2026-01-01 00:00:00", 0))
    _score_event(conn, mid, "coding", 80, _days("2026-01-01 00:00:00", 60))
    _score_event(conn, mid, "coding", 90, _days("2026-01-01 00:00:00", 100))
    r = trend.score_trend(conn, mid, window_days=120)[0]
    assert r["point_count"] == 3
    assert r["first"] == 10.0
    assert r["last"] == 90.0
    assert r["magnitude"] == pytest.approx(0.8)


def test_score_trend_window_days_excludes_old_points_to_insufficient(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 10, _days("2026-01-01 00:00:00", 0))
    _score_event(conn, mid, "coding", 80, _days("2026-01-01 00:00:00", 60))
    _score_event(conn, mid, "coding", 90, _days("2026-01-01 00:00:00", 100))
    r = trend.score_trend(conn, mid)[0]
    assert r["point_count"] == 2
    assert r["direction"] == trend.DIRECTION_INSUFFICIENT


# --- per-dimension grouping -------------------------------------------------


def test_score_trend_per_dimension_grouping(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 50, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 60, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 70, "2026-03-01 00:00:00")
    _score_event(conn, mid, "reasoning", 80, "2026-01-01 00:00:00")
    _score_event(conn, mid, "reasoning", 85, "2026-02-01 00:00:00")
    _score_event(conn, mid, "reasoning", 90, "2026-03-01 00:00:00")
    results = trend.score_trend(conn, mid)
    assert [r["dimension"] for r in results] == ["coding", "reasoning"]
    by_dim = {r["dimension"]: r for r in results}
    assert by_dim["coding"]["magnitude"] == pytest.approx(0.2)
    assert by_dim["reasoning"]["magnitude"] == pytest.approx(0.1)
    filtered = trend.score_trend(conn, mid, dimension="coding")
    assert [r["dimension"] for r in filtered] == ["coding"]


# --- series passthrough -----------------------------------------------------


def test_score_trend_series_passed_through_unchanged(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 70, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 75, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 80, "2026-03-01 00:00:00")
    r = trend.score_trend(conn, mid)[0]
    raw = dashboard_history.score_history(conn, mid)
    assert len(raw) == 3
    assert r["series"] == list(raw)
    assert r["points"] == list(raw)


# --- read-only + determinism ------------------------------------------------


def test_score_trend_deterministic(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    for i, v in enumerate([80, 85, 90], start=1):
        _score_event(conn, mid, "coding", v, f"2026-0{i}-01 00:00:00")
    assert trend.score_trend(conn, mid) == trend.score_trend(conn, mid)


def test_trend_read_only(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    _score_event(conn, mid, "coding", 80, "2026-01-01 00:00:00")
    _score_event(conn, mid, "coding", 85, "2026-02-01 00:00:00")
    _score_event(conn, mid, "coding", 90, "2026-03-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-01-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_FAILED", "2026-02-01 00:00:00")
    events_before = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    tables_before = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    trend.score_trend(conn, mid)
    trend.availability_trend(conn)
    events_after = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    tables_after = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert events_after == events_before
    assert tables_after == tables_before


# --- argument validation ----------------------------------------------------


def test_score_trend_unknown_model_raises(conn):
    with pytest.raises(trend.TrendError):
        trend.score_trend(conn, 999)


def test_score_trend_invalid_args_raise(conn):
    pid = _add_provider(conn)
    mid = _model(conn, pid)
    with pytest.raises(trend.TrendError):
        trend.score_trend(conn, mid, window_days=0)
    with pytest.raises(trend.TrendError):
        trend.score_trend(conn, mid, min_points=0)


# --- availability -----------------------------------------------------------


def test_availability_trend_mapping(conn):
    pid = _add_provider(conn)
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-01-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-02-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_FAILED", "2026-03-01 00:00:00")
    r = trend.availability_trend(conn, provider_id=pid)[0]
    assert r["first"] == 1.0
    assert r["last"] == 0.0
    assert r["numeric_count"] == 3
    assert r["direction"] == trend.DIRECTION_DOWN
    assert r["magnitude"] == pytest.approx(-1.0)


def test_availability_trend_up(conn):
    pid = _add_provider(conn)
    _health_event(conn, pid, "HEALTH_CHECK_FAILED", "2026-01-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_FAILED", "2026-02-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-03-01 00:00:00")
    r = trend.availability_trend(conn, provider_id=pid)[0]
    assert r["direction"] == trend.DIRECTION_UP
    assert r["magnitude"] == pytest.approx(1.0)


def test_availability_trend_stable(conn):
    pid = _add_provider(conn)
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-01-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-02-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-03-01 00:00:00")
    r = trend.availability_trend(conn, provider_id=pid)[0]
    assert r["direction"] == trend.DIRECTION_STABLE
    assert r["magnitude"] == pytest.approx(0.0)


def test_availability_trend_unknown_excluded(conn):
    pid = _add_provider(conn)
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-01-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-02-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_UNKNOWN", "2026-03-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_FAILED", "2026-04-01 00:00:00")
    r = trend.availability_trend(conn, provider_id=pid)[0]
    assert r["excluded_unknown"] == 1
    assert r["numeric_count"] == 3
    assert r["first"] == 1.0
    assert r["last"] == 0.0
    assert r["direction"] == trend.DIRECTION_DOWN


def test_availability_trend_transitions_not_numeric(conn):
    pid = _add_provider(conn)
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-01-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-02-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_FAILED", "2026-03-01 00:00:00")
    _health_event(
        conn,
        pid,
        "MONITOR_STATUS_CHANGED",
        "2026-04-01 00:00:00",
        {"from": "ACTIVE", "to": "DEGRADED"},
    )
    r = trend.availability_trend(conn, provider_id=pid)[0]
    assert r["excluded_transitions"] == 1
    assert r["numeric_count"] == 3
    assert r["point_count"] == 3
    assert r["direction"] == trend.DIRECTION_DOWN


def test_availability_trend_only_transitions_is_insufficient(conn):
    pid = _add_provider(conn)
    _health_event(
        conn,
        pid,
        "MONITOR_STATUS_CHANGED",
        "2026-01-01 00:00:00",
        {"from": "ACTIVE", "to": "DEGRADED"},
    )
    r = trend.availability_trend(conn, provider_id=pid)[0]
    assert r["direction"] == trend.DIRECTION_INSUFFICIENT
    assert r["numeric_count"] == 0
    assert r["excluded_transitions"] == 1
    assert r["point_count"] == 0


def test_availability_trend_insufficient_data(conn):
    pid = _add_provider(conn)
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-01-01 00:00:00")
    r = trend.availability_trend(conn, provider_id=pid)[0]
    assert r["direction"] == trend.DIRECTION_INSUFFICIENT
    assert r["magnitude"] is None
    assert r["point_count"] == 1
    assert r["min_points"] == 3


def test_availability_trend_default_window_anchored_to_last_point(conn):
    pid = _add_provider(conn)
    _health_event(conn, pid, "HEALTH_CHECK_OK", _days("2026-01-01 00:00:00", 0))
    _health_event(conn, pid, "HEALTH_CHECK_OK", _days("2026-01-01 00:00:00", 60))
    _health_event(conn, pid, "HEALTH_CHECK_FAILED", _days("2026-01-01 00:00:00", 100))
    r = trend.availability_trend(conn, provider_id=pid, min_points=2)[0]
    assert r["series_count"] == 3
    assert r["point_count"] == 2
    assert r["first"] == 1.0
    assert r["last"] == 0.0


def test_availability_trend_grouped_by_provider(conn):
    pid_a = _add_provider(conn, "Alpha")
    pid_b = _add_provider(conn, "Beta")
    _health_event(conn, pid_a, "HEALTH_CHECK_OK", "2026-01-01 00:00:00")
    _health_event(conn, pid_a, "HEALTH_CHECK_OK", "2026-02-01 00:00:00")
    _health_event(conn, pid_a, "HEALTH_CHECK_OK", "2026-03-01 00:00:00")
    _health_event(conn, pid_b, "HEALTH_CHECK_FAILED", "2026-01-01 00:00:00")
    _health_event(conn, pid_b, "HEALTH_CHECK_FAILED", "2026-02-01 00:00:00")
    _health_event(conn, pid_b, "HEALTH_CHECK_OK", "2026-03-01 00:00:00")
    results = trend.availability_trend(conn)
    assert [r["provider_id"] for r in results] == [pid_a, pid_b]
    assert results[0]["direction"] == trend.DIRECTION_STABLE
    assert results[1]["direction"] == trend.DIRECTION_UP
    filtered = trend.availability_trend(conn, provider_id=pid_b)
    assert [r["provider_id"] for r in filtered] == [pid_b]


def test_availability_trend_unknown_provider_raises(conn):
    with pytest.raises(trend.TrendError):
        trend.availability_trend(conn, provider_id=999)


def test_availability_trend_series_passed_through_unchanged(conn):
    pid = _add_provider(conn)
    _health_event(conn, pid, "HEALTH_CHECK_OK", "2026-01-01 00:00:00")
    _health_event(conn, pid, "HEALTH_CHECK_UNKNOWN", "2026-02-01 00:00:00")
    _health_event(
        conn,
        pid,
        "MONITOR_STATUS_CHANGED",
        "2026-03-01 00:00:00",
        {"from": "ACTIVE", "to": "DEGRADED"},
    )
    r = trend.availability_trend(conn, provider_id=pid)[0]
    raw = dashboard_history.availability_history(conn, provider_id=pid)
    assert r["series"] == list(raw)
    assert len(r["series"]) == 3
    assert [p["event_type"] for p in r["points"]] == ["HEALTH_CHECK_OK"]