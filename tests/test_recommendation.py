"""Tests for the recommendation engine and profiles."""

from __future__ import annotations

import pytest

from core import providers
from monitoring import availability as availability_mod
from recommendation import profiles, recommend
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


def _score_many(conn, mid, coding=None, reasoning=None, cost=None):
    if coding is not None:
        ingest.set_score(conn, mid, "coding", coding, confidence=1.0, source="MANUAL")
    if reasoning is not None:
        ingest.set_score(conn, mid, "reasoning", reasoning, confidence=1.0, source="MANUAL")
    if cost is not None:
        ingest.set_score(conn, mid, "cost", cost, confidence=1.0, source="MANUAL")


# --- profiles ----------------------------------------------------------------


def test_builtin_profile_weights_sum_to_one():
    for name, weights in profiles.BUILTIN_PROFILES.items():
        assert abs(sum(weights.values()) - 1.0) < 1e-9, name


def test_get_profile_builtin(conn):
    weights = profiles.get_profile(conn, "coding")
    assert weights["coding"] == pytest.approx(0.40)


def test_get_profile_unknown_rejected(conn):
    with pytest.raises(profiles.ProfileError):
        profiles.get_profile(conn, "nope")


def test_set_and_get_custom_profile(conn):
    profiles.set_custom_profile(conn, "my", {"coding": 0.6, "availability": 0.4})
    weights = profiles.get_profile(conn, "my")
    assert weights["coding"] == pytest.approx(0.6)


def test_custom_profile_weights_must_sum_to_one(conn):
    with pytest.raises(profiles.ProfileError):
        profiles.set_custom_profile(conn, "bad", {"coding": 0.5, "availability": 0.2})


def test_cannot_override_builtin_profile(conn):
    with pytest.raises(profiles.ProfileError):
        profiles.set_custom_profile(conn, "coding", {"coding": 1.0})


def test_list_profiles_includes_custom(conn):
    profiles.set_custom_profile(conn, "my", {"coding": 1.0})
    names = profiles.list_profiles(conn)
    assert "coding" in names
    assert "my" in names


# --- recommendation ----------------------------------------------------------


def test_recommend_ranks_by_score(conn):
    p1 = _provider(conn, "Alpha")
    p2 = _provider(conn, "Beta")
    m1 = _model(conn, p1, "alpha-1")
    m2 = _model(conn, p2, "beta-1")
    _score_many(conn, m1, coding=90, reasoning=70)
    _score_many(conn, m2, coding=60, reasoning=60)
    results = recommend(conn, "python", profile="coding")
    assert len(results) == 2
    assert results[0].model_identifier == "alpha-1"
    assert results[0].final_score > results[1].final_score


def test_recommend_filters_ineligible_status(conn):
    p1 = _provider(conn, "Good")
    p2 = _provider(conn, "Bad", status="OFFLINE", reason="down")
    m1 = _model(conn, p1, "good-1")
    m2 = _model(conn, p2, "bad-1")
    _score_many(conn, m1, coding=90)
    _score_many(conn, m2, coding=95)
    results = recommend(conn, "python")
    assert [r.model_identifier for r in results] == ["good-1"]


def test_recommend_degraded_flagged(conn):
    p1 = _provider(conn, "Deg", status="DEGRADED", reason="flaky")
    m1 = _model(conn, p1, "deg-1")
    _score_many(conn, m1, coding=90)
    results = recommend(conn, "python")
    assert len(results) == 1
    assert any("provider degraded" in f for f in results[0].flags)


def test_recommend_filters_context_window(conn):
    p1 = _provider(conn, "Small")
    m1 = _model(conn, p1, "small-1", context_window=2048)
    _score_many(conn, m1, coding=95)
    results = recommend(conn, "python", min_context_window=4096)
    assert results == []


def test_recommend_filters_required_capabilities(conn):
    p1 = _provider(conn, "NoTools")
    m1 = _model(conn, p1, "notools-1", tools=0)
    _score_many(conn, m1, coding=95)
    assert recommend(conn, "python", required_capabilities=("tool_calling",)) == []
    m2 = _model(conn, p1, "tools-1", tools=1)
    _score_many(conn, m2, coding=90)
    results = recommend(conn, "python", required_capabilities=("tool_calling",))
    assert [r.model_identifier for r in results] == ["tools-1"]


def test_recommend_missing_dimension_flagged(conn):
    p1 = _provider(conn, "NoCost")
    m1 = _model(conn, p1, "nocost-1")
    _score_many(conn, m1, coding=90)
    results = recommend(conn, "python", profile="free")
    assert len(results) == 1
    assert "insufficient data" in results[0].flags[0]


def test_recommend_is_deterministic(conn):
    p1 = _provider(conn, "Alpha")
    p2 = _provider(conn, "Beta")
    m1 = _model(conn, p1, "alpha-1")
    m2 = _model(conn, p2, "beta-1")
    _score_many(conn, m1, coding=90, reasoning=70)
    _score_many(conn, m2, coding=90, reasoning=70)
    a = recommend(conn, "python")
    b = recommend(conn, "python")
    assert [r.model_identifier for r in a] == [r.model_identifier for r in b]
    assert [r.final_score for r in a] == [r.final_score for r in b]


def test_recommend_explanation_present(conn):
    p1 = _provider(conn, "Alpha")
    m1 = _model(conn, p1, "alpha-1")
    _score_many(conn, m1, coding=90)
    results = recommend(conn, "python")
    assert "Final score" in results[0].explanation
    assert "coding" in results[0].explanation


def test_recommend_operational_derived(conn):
    p1 = _provider(conn, "Alpha")
    m1 = _model(conn, p1, "alpha-1")
    _score_many(conn, m1, coding=90)
    availability_mod.update_availability(conn, p1, "OK")
    results = recommend(conn, "python", profile="free")
    assert results[0].dimensions["availability"]["value"] == 100.0
