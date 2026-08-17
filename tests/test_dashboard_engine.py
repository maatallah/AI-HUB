"""Tests for the dashboard aggregation engine (read-only views)."""

from __future__ import annotations

from core import events, providers
from dashboard import engine
from monitoring import availability as availability_mod
from recommendation import provenance
from scoring import ingest


def _add(conn, name="Acme", status="ACTIVE"):
    reason = None if status == "ACTIVE" else "for test"
    return providers.add_provider(conn, name, status=status, status_reason=reason)


def _model(conn, provider_id, model_identifier="acme-1"):
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier)"
        " VALUES (?, 'Acme Model', ?)",
        (provider_id, model_identifier),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (model_identifier,)
    ).fetchone()["id"]


# --- overview ---------------------------------------------------------------


def test_overview_empty_db(conn):
    data = engine.overview(conn)
    assert data["total_providers"] == 0
    assert data["total_models"] == 0
    assert data["scored_models"] == 0
    assert data["scored_providers"] == 0
    assert data["status_counts"] == {
        "ACTIVE": 0, "LIMITED": 0, "DEGRADED": 0, "OFFLINE": 0,
    }


def test_overview_counts_and_statuses(conn):
    _add(conn, name="Alpha", status="ACTIVE")
    _add(conn, name="Beta", status="LIMITED")
    _add(conn, name="Gamma", status="DEGRADED")
    _add(conn, name="Delta", status="OFFLINE")
    data = engine.overview(conn)
    assert data["total_providers"] == 4
    assert data["total_models"] == 0
    assert data["status_counts"]["ACTIVE"] == 1
    assert data["status_counts"]["LIMITED"] == 1
    assert data["status_counts"]["DEGRADED"] == 1
    assert data["status_counts"]["OFFLINE"] == 1


def test_overview_scored_models_and_providers(conn):
    pid = _add(conn)
    mid = _model(conn, pid)
    ingest.set_score(conn, mid, "coding", 80, source="MANUAL")
    data = engine.overview(conn)
    assert data["scored_models"] == 1
    assert data["scored_providers"] == 1


# --- provider_view ----------------------------------------------------------


def test_provider_view_empty(conn):
    assert engine.provider_view(conn) == []


def test_provider_view_counts(conn):
    pid = _add(conn, name="Zeta")
    _model(conn, pid, "zeta-1")
    _model(conn, pid, "zeta-2")
    mid = _model(conn, pid, "zeta-3")
    ingest.set_score(conn, mid, "coding", 80, source="MANUAL")
    rows = engine.provider_view(conn)
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "Zeta"
    assert row["status"] == "ACTIVE"
    assert row["model_count"] == 3
    assert row["score_count"] == 1


def test_provider_view_availability_join(conn):
    pid = _add(conn, name="Alpha")
    availability_mod.update_availability(conn, pid, "FAILED")
    availability_mod.update_availability(conn, pid, "FAILED")
    row = engine.provider_view(conn)[0]
    assert row["availability_state"] == "ACTIVE"
    assert row["consecutive_failures"] == 2


def test_provider_view_ordered_by_name(conn):
    pid_a = _add(conn, name="Zeta")
    pid_b = _add(conn, name="Alpha")
    _model(conn, pid_a, "z-1")
    _model(conn, pid_b, "a-1")
    rows = engine.provider_view(conn)
    names = [r["name"] for r in rows]
    assert names == ["Alpha", "Zeta"]


# --- score_view -------------------------------------------------------------


def test_score_view_empty(conn):
    assert engine.score_view(conn) == []


def test_score_view_joins_names(conn):
    pid = _add(conn, name="Acme")
    mid = _model(conn, pid)
    ingest.set_score(conn, mid, "coding", 85, source="MANUAL")
    rows = engine.score_view(conn)
    assert len(rows) == 1
    assert rows[0]["provider_name"] == "Acme"
    assert rows[0]["model_identifier"] == "acme-1"
    assert rows[0]["dimension"] == "coding"
    assert rows[0]["value"] == 85.0


def test_score_view_filtered_by_model(conn):
    pid = _add(conn, name="Acme")
    mid_a = _model(conn, pid, "a")
    mid_b = _model(conn, pid, "b")
    ingest.set_score(conn, mid_a, "coding", 80, source="MANUAL")
    ingest.set_score(conn, mid_b, "coding", 90, source="MANUAL")
    rows = engine.score_view(conn, model_id=mid_b)
    assert len(rows) == 1
    assert rows[0]["model_identifier"] == "b"


def test_score_view_does_not_write(conn):
    pid = _add(conn, name="Acme")
    mid = _model(conn, pid)
    ingest.set_score(conn, mid, "coding", 80, source="MANUAL")
    before = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    engine.score_view(conn)
    after = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert after == before


# --- recommendation_view ----------------------------------------------------


def test_recommendation_view_empty(conn):
    assert engine.recommendation_view(conn) == []


def test_recommendation_view_records_and_order(conn):
    pid = _add(conn, name="Acme")
    mid = _model(conn, pid)
    for i in range(3):
        provenance.record_recommendation(
            conn,
            _dummy_recommendation(pid, mid, i),
            decision_version="3.0.0",
        )
    rows = engine.recommendation_view(conn)
    assert len(rows) == 3
    assert rows[0]["provider_name"] == "Acme"
    assert rows[0]["model_identifier"] == "acme-1"


def _dummy_recommendation(pid, mid, seq):
    from recommendation.engine import Recommendation

    return Recommendation(
        task="python",
        profile="coding",
        provider_id=pid,
        provider_name="Acme",
        model_id=mid,
        model_identifier="acme-1",
        final_score=90.0,
        dimensions={},
        breakdown={},
        confidence=0.9,
        explanation=f"test {seq}",
        flags=(),
    )


# --- event_view -------------------------------------------------------------


def test_event_view_empty(conn):
    assert engine.event_view(conn) == []


def test_event_view_newest_first(conn):
    pid = _add(conn, name="Acme")
    mid = _model(conn, pid)
    ingest.set_score(conn, mid, "coding", 80, source="MANUAL")
    ingest.set_score(conn, mid, "coding", 90, source="MANUAL")
    rows = engine.event_view(conn)
    types = [r["event_type"] for r in rows]
    assert types[0] == "SCORE_UPDATED"
    assert types[1] == "SCORE_RECORDED"


def test_event_view_filtered_by_type(conn):
    pid = _add(conn, name="Acme")
    mid = _model(conn, pid)
    ingest.set_score(conn, mid, "coding", 80, source="MANUAL")
    rows = engine.event_view(conn, event_type="SCORE_RECORDED")
    assert len(rows) == 1
    assert rows[0]["event_type"] == "SCORE_RECORDED"
    rows = engine.event_view(conn, event_type="HEALTH_CHECK_OK")
    assert rows == []


def test_event_view_respects_limit(conn):
    pid = _add(conn, name="Acme")
    mid = _model(conn, pid)
    for i in range(5):
        events.record_event(
            conn, "PROVIDER_UPDATED", entity_type="provider", entity_id=pid,
            payload={"n": i},
        )
    rows = engine.event_view(conn, limit=2)
    assert len(rows) == 2
