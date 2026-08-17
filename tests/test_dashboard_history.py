"""Tests for the dashboard history reconstruction (append-only event model)."""

from __future__ import annotations

from core import events, providers
from dashboard import history
from monitoring import availability as availability_mod
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


# --- score history ----------------------------------------------------------


def test_score_history_empty(conn):
    pid = _add(conn)
    mid = _model(conn, pid)
    assert history.score_history(conn, mid) == []


def test_score_history_from_recorded_and_updated(conn):
    pid = _add(conn)
    mid = _model(conn, pid)
    ingest.set_score(conn, mid, "coding", 80, confidence=0.9, source="MANUAL")
    ingest.set_score(conn, mid, "coding", 90, confidence=0.95, source="MANUAL")
    series = history.score_history(conn, mid)
    assert len(series) == 2
    assert series[0]["dimension"] == "coding"
    assert series[0]["value"] == 80.0
    assert series[1]["value"] == 90.0
    assert series[1]["confidence"] == 0.95


def test_score_history_ordered_by_event_id(conn):
    pid = _add(conn)
    mid = _model(conn, pid)
    ingest.set_score(conn, mid, "coding", 70, source="MANUAL")
    ingest.set_score(conn, mid, "reasoning", 85, source="MANUAL")
    ingest.set_score(conn, mid, "coding", 95, source="MANUAL")
    series = history.score_history(conn, mid)
    values = [(r["dimension"], r["value"]) for r in series]
    assert values == [("coding", 70.0), ("reasoning", 85.0), ("coding", 95.0)]


def test_score_history_filtered_by_dimension(conn):
    pid = _add(conn)
    mid = _model(conn, pid)
    ingest.set_score(conn, mid, "coding", 70, source="MANUAL")
    ingest.set_score(conn, mid, "reasoning", 85, source="MANUAL")
    series = history.score_history(conn, mid, dimension="coding")
    assert len(series) == 1
    assert series[0]["dimension"] == "coding"


def test_score_history_scoped_to_model(conn):
    pid = _add(conn)
    mid_a = _model(conn, pid, "a")
    mid_b = _model(conn, pid, "b")
    ingest.set_score(conn, mid_a, "coding", 70, source="MANUAL")
    ingest.set_score(conn, mid_b, "coding", 95, source="MANUAL")
    series = history.score_history(conn, mid_a)
    assert len(series) == 1
    assert series[0]["value"] == 70.0


def test_score_history_unknown_model_empty(conn):
    assert history.score_history(conn, 999) == []


# --- availability history ---------------------------------------------------


def test_availability_history_empty(conn):
    assert history.availability_history(conn) == []


def test_availability_history_state_transitions(conn):
    pid = _add(conn, name="Acme")
    availability_mod.apply_lifecycle(conn, pid, "DEGRADED", "Repeated failures.")
    availability_mod.apply_lifecycle(conn, pid, "OFFLINE", "Repeated failures.")
    series = history.availability_history(conn, provider_id=pid)
    transitions = [
        r for r in series if r["event_type"] == "MONITOR_STATUS_CHANGED"
    ]
    assert [r["from"] for r in transitions] == ["ACTIVE", "DEGRADED"]
    assert [r["to"] for r in transitions] == ["DEGRADED", "OFFLINE"]


def test_availability_history_health_events(conn):
    pid = _add(conn, name="Acme")
    events.record_event(
        conn, "HEALTH_CHECK_OK", entity_type="provider", entity_id=pid,
        payload={"name": "Acme", "latency_ms": 2500, "status_code": 200},
    )
    series = history.availability_history(conn, provider_id=pid)
    assert len(series) == 1
    assert series[0]["event_type"] == "HEALTH_CHECK_OK"
    assert series[0]["latency_ms"] == 2500


def test_availability_history_provider_filter(conn):
    pid_a = _add(conn, name="Alpha")
    pid_b = _add(conn, name="Beta")
    availability_mod.apply_lifecycle(conn, pid_a, "DEGRADED", "Repeated failures.")
    availability_mod.apply_lifecycle(conn, pid_b, "DEGRADED", "Repeated failures.")
    series = history.availability_history(conn, provider_id=pid_a)
    assert all(r["entity_id"] == pid_a for r in series)


# --- read-only + determinism ------------------------------------------------


def test_history_does_not_write(conn):
    pid = _add(conn)
    mid = _model(conn, pid)
    ingest.set_score(conn, mid, "coding", 80, source="MANUAL")
    availability_mod.apply_lifecycle(conn, pid, "DEGRADED", "Repeated failures.")
    before = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    history.score_history(conn, mid)
    history.availability_history(conn)
    after = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert after == before


def test_history_deterministic(conn):
    pid = _add(conn)
    mid = _model(conn, pid)
    ingest.set_score(conn, mid, "coding", 80, source="MANUAL")
    ingest.set_score(conn, mid, "coding", 85, source="MANUAL")
    availability_mod.apply_lifecycle(conn, pid, "DEGRADED", "Repeated failures.")
    first = history.score_history(conn, mid)
    second = history.score_history(conn, mid)
    assert first == second
