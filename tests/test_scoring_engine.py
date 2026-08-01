"""Tests for the scoring engine (derived + stored scores, aging)."""

from __future__ import annotations

import json

import pytest

from core import events, providers
from monitoring import availability as availability_mod
from scoring import derive, engine, ingest


_counter = 0


def _model(conn, provider_status="ACTIVE", context_window=32000):
    global _counter
    _counter += 1
    reason = "for test" if provider_status != "ACTIVE" else None
    pid = providers.add_provider(
        conn, f"Acme-{_counter}", status=provider_status, status_reason=reason
    )
    model_identifier = f"acme-{_counter}"
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier, context_window)"
        " VALUES (?, 'Acme Model', ?, ?)",
        (pid, model_identifier, context_window),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (model_identifier,)
    ).fetchone()["id"]


# --- stored score ingestion -------------------------------------------------


def test_set_score_new_records_event(conn):
    mid = _model(conn)
    row = ingest.set_score(conn, mid, "coding", 85, confidence=0.9, source="MANUAL")
    assert row["dimension"] == "coding"
    assert row["value"] == 85.0
    types = [e["event_type"] for e in events.list_events(conn)]
    assert "SCORE_RECORDED" in types
    assert "SCORE_UPDATED" not in types


def test_set_score_update_records_update_event(conn):
    mid = _model(conn)
    ingest.set_score(conn, mid, "coding", 85, confidence=0.9, source="MANUAL")
    row = ingest.set_score(conn, mid, "coding", 90, confidence=0.95, source="MANUAL")
    assert row["value"] == 90.0
    types = [e["event_type"] for e in events.list_events(conn)]
    assert "SCORE_UPDATED" in types


def test_set_score_invalid_value_rejected(conn):
    mid = _model(conn)
    with pytest.raises(ingest.ScoreError):
        ingest.set_score(conn, mid, "coding", 150, source="MANUAL")
    with pytest.raises(ingest.ScoreError):
        ingest.set_score(conn, mid, "coding", -5, source="MANUAL")


def test_set_score_invalid_source_rejected(conn):
    mid = _model(conn)
    with pytest.raises(ingest.ScoreError):
        ingest.set_score(conn, mid, "coding", 80, source="BOGUS")


def test_set_score_unknown_model_rejected(conn):
    with pytest.raises(ingest.ScoreError):
        ingest.set_score(conn, 999, "coding", 80, source="MANUAL")


def test_unique_dimension_per_model_enforced(conn):
    mid = _model(conn)
    ingest.set_score(conn, mid, "coding", 80, source="MANUAL")
    ingest.set_score(conn, mid, "coding", 85, source="MANUAL")  # upsert, not a new row
    rows = conn.execute("SELECT * FROM scores WHERE model_id=?", (mid,)).fetchall()
    assert len(rows) == 1
    assert rows[0]["value"] == 85.0


# --- derived operational scores ---------------------------------------------


def test_derive_availability_active(conn):
    mid = _model(conn, provider_status="ACTIVE")
    availability_mod.update_availability(conn, _provider_of(conn, mid), "OK")
    d = derive.derive_availability(conn, mid)
    assert d["value"] == 100.0
    assert d["source"] == "AUTOMATED_TEST"


def _provider_of(conn, model_id):
    return conn.execute(
        "SELECT provider_id FROM models WHERE id=?", (model_id,)
    ).fetchone()["provider_id"]


def test_derive_availability_maps_states(conn):
    for status, expected in [("LIMITED", 70.0), ("DEGRADED", 40.0), ("OFFLINE", 0.0)]:
        mid = _model(conn, provider_status=status)
        d = derive.derive_availability(conn, mid)
        assert d["value"] == expected, status


def test_derive_availability_archived_none(conn):
    mid = _model(conn, provider_status="ARCHIVED")
    assert derive.derive_availability(conn, mid) is None


def test_derive_availability_no_runtime_state_none(conn):
    mid = _model(conn, provider_status="NEW")
    assert derive.derive_availability(conn, mid) is None


def test_derive_reliability_no_failures(conn):
    mid = _model(conn)
    availability_mod.update_availability(conn, _provider_of(conn, mid), "OK")
    assert derive.derive_reliability(conn, mid)["value"] == 100.0


def test_derive_reliability_failures_reduce_score(conn):
    mid = _model(conn)
    pid = _provider_of(conn, mid)
    availability_mod.update_availability(conn, pid, "FAILED")
    availability_mod.update_availability(conn, pid, "FAILED")
    assert derive.derive_reliability(conn, mid)["value"] == 60.0


def test_derive_reliability_no_data_none(conn):
    mid = _model(conn)
    assert derive.derive_reliability(conn, mid) is None


def test_derive_latency_from_health_event(conn):
    mid = _model(conn)
    pid = _provider_of(conn, mid)
    events.record_event(
        conn, "HEALTH_CHECK_OK", entity_type="provider", entity_id=pid,
        payload={"name": "Acme", "latency_ms": 2500, "status_code": 200},
    )
    d = derive.derive_latency(conn, mid, latency_threshold_ms=10000)
    assert d["value"] == pytest.approx(75.0)


def test_derive_latency_no_measurement_none(conn):
    mid = _model(conn)
    assert derive.derive_latency(conn, mid) is None


def test_derive_score_unknown_dimension_none(conn):
    mid = _model(conn)
    assert derive.derive_score(conn, mid, "coding") is None


# --- effective score + aging -------------------------------------------------


def test_effective_score_stored_value(conn):
    mid = _model(conn)
    ingest.set_score(conn, mid, "coding", 80, confidence=1.0, source="MANUAL")
    eff = engine.effective_score(conn, mid, "coding")
    assert eff["value"] == 80.0
    assert eff["derived"] is False


def test_effective_score_derived_when_enabled(conn):
    mid = _model(conn)
    availability_mod.update_availability(conn, _provider_of(conn, mid), "OK")
    eff = engine.effective_score(conn, mid, "availability")
    assert eff["value"] == 100.0
    assert eff["derived"] is True


def test_effective_score_derived_disabled_falls_back_to_stored(conn):
    mid = _model(conn)
    ingest.set_score(conn, mid, "availability", 55, confidence=1.0, source="MANUAL")
    eff = engine.effective_score(conn, mid, "availability", derive_operational=False)
    assert eff["value"] == 55.0
    assert eff["derived"] is False


def test_effective_score_missing_dimension_none(conn):
    mid = _model(conn)
    assert engine.effective_score(conn, mid, "coding") is None


def test_age_multiplier_boundaries():
    assert engine.age_multiplier("2026-01-01 00:00:00", fresh_days=30, aging_days=90, old_days=180) in (
        1.00, 0.90, 0.75, 0.50,
    )
    assert engine.age_multiplier(None) == 1.00
    assert engine.age_multiplier("garbage") == 1.00


def test_age_days_zero_for_missing():
    assert engine.age_days(None) == 0
    assert engine.age_days("bad-date") == 0


def test_effective_score_confidence_aged(conn):
    mid = _model(conn)
    ingest.set_score(conn, mid, "coding", 80, confidence=1.0, source="MANUAL", scored_at="2020-01-01 00:00:00")
    eff = engine.effective_score(conn, mid, "coding")
    assert eff["age_multiplier"] == 0.50
    assert eff["confidence"] == pytest.approx(0.50)


def test_list_scores_joins_model_and_provider(conn):
    mid = _model(conn)
    ingest.set_score(conn, mid, "coding", 80, source="MANUAL")
    rows = ingest.list_scores(conn)
    assert len(rows) == 1
    assert rows[0]["provider_name"].startswith("Acme-")
    assert rows[0]["model_identifier"].startswith("acme-")
