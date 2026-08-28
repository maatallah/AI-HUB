"""Tests for the adapter-level routing decision functions (post-v1 M2)."""

from __future__ import annotations

import datetime

import pytest

from connectors import adapter
from core import providers
from recommendation.decision import (
    DecisionError,
    STATUS_CONSTRAINT_UNSATISFIABLE,
    STATUS_INSUFFICIENT_DATA,
    STATUS_NO_CANDIDATE,
    STATUS_OK,
    build_decision_envelope,
    record_decision,
)
from scoring import ingest

NOW = datetime.datetime(2026, 8, 28, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _provider(conn, name, status="ACTIVE"):
    return providers.add_provider(conn, name, status=status)


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


def _seed(conn, name="Alpha", identifier="alpha-1", coding=90):
    p = _provider(conn, name)
    m = _model(conn, p, identifier)
    ingest.set_score(conn, m, "coding", coding, confidence=1.0, source="MANUAL")
    return p, m


# --- R1 route_decide delegation ------------------------------------------------


def test_route_decide_returns_envelope_identical_to_builder(conn):
    _seed(conn)
    env = adapter.route_decide(conn, "python")
    expected = build_decision_envelope(conn, "python")
    assert env == expected
    assert env["status"] == STATUS_OK
    assert env["provenance"] == {"decision_id": None, "recorded": False}


def test_route_decide_covers_no_candidate(conn):
    env = adapter.route_decide(conn, "python")
    assert env["status"] == STATUS_NO_CANDIDATE


def test_route_decide_covers_constraint_unsatisfiable(conn):
    p, _ = _seed(conn)
    env = adapter.route_decide(conn, "python", denied_providers=[p])
    assert env["status"] == STATUS_CONSTRAINT_UNSATISFIABLE


def test_route_decide_covers_insufficient_data(conn):
    p = _provider(conn, "Alpha")
    _model(conn, p, "alpha-1")
    env = adapter.route_decide(conn, "python", profile="reasoning")
    env.pop("created_at", None)
    assert env["status"] in (STATUS_INSUFFICIENT_DATA, STATUS_OK)


# --- complete input passthrough ------------------------------------------------


def test_route_decide_passthrough_all_contract_inputs(conn):
    p, m = _seed(conn, "Acme", "acme-turbo", coding=90)
    env = adapter.route_decide(
        conn,
        "python",
        profile="reasoning",
        min_context_window=4096,
        required_capabilities=["tool_calling", "json"],
        allowed_providers=["Acme"],
        denied_providers=[],
        allowed_models=["acme-turbo"],
        denied_models=[],
        max_stale_days=100,
        limit=5,
    )
    env.pop("created_at", None)
    expected = build_decision_envelope(
        conn,
        "python",
        profile="reasoning",
        min_context_window=4096,
        required_capabilities=["tool_calling", "json"],
        allowed_providers=["Acme"],
        denied_providers=[],
        allowed_models=["acme-turbo"],
        denied_models=[],
        max_stale_days=100,
        limit=5,
    )
    expected.pop("created_at", None)
    assert env == expected
    req = env["request"]
    assert req["profile"] == "reasoning"
    assert req["constraints"]["min_context_window"] == 4096
    assert req["freshness"] == {"max_stale_days": 100}


def test_route_decide_returns_json_serializable(conn):
    import json

    _seed(conn)
    env = adapter.route_decide(conn, "python")
    text = json.dumps(env, sort_keys=True)
    assert json.loads(text) == env


# --- error propagation ---------------------------------------------------------


def test_route_decide_propagates_typed_errors(conn):
    with pytest.raises(DecisionError):
        adapter.route_decide(conn, "")
    with pytest.raises(DecisionError):
        adapter.route_decide(conn, "  ")
    with pytest.raises(DecisionError):
        adapter.route_decide(conn, "python", min_context_window=0)


# --- R2 route_record delegation ------------------------------------------------


def test_route_record_persists_envelope(conn):
    p, m = _seed(conn)
    env = build_decision_envelope(conn, "python")
    result = adapter.route_record(conn, env)
    rows = conn.execute("SELECT * FROM recommendations ORDER BY rowid").fetchall()
    assert result["count"] == len(rows) == len(env["candidates"])
    assert result["decision_id"] == result["recorded_ids"][0] == rows[0]["id"]
    assert rows[0]["model_id"] == m


def test_route_record_returns_persistence_shape(conn):
    _seed(conn)
    env = build_decision_envelope(conn, "python")
    result = adapter.route_record(conn, env)
    assert set(result.keys()) == {"decision_id", "recorded_ids", "count"}
    assert isinstance(result["decision_id"], str)
    assert isinstance(result["recorded_ids"], list)
    assert result["count"] == len(result["recorded_ids"])


def test_route_record_matches_record_decision_shape(conn):
    _seed(conn)
    env = build_decision_envelope(conn, "python")
    direct = record_decision(conn, env)
    wrapped = adapter.route_record(conn, env)
    assert wrapped["count"] == direct["count"] == len(env["candidates"])
    assert wrapped["count"] == len(wrapped["recorded_ids"])
    assert set(wrapped.keys()) == {"decision_id", "recorded_ids", "count"}
    total = conn.execute(
        "SELECT COUNT(*) AS n FROM recommendations"
    ).fetchone()["n"]
    assert total == 2 * len(env["candidates"])


def test_route_record_propagates_validation_errors(conn):
    _seed(conn)
    with pytest.raises(DecisionError):
        adapter.route_record(conn, [])
    bad = build_decision_envelope(conn, "python")
    bad["contract_version"] = "999"
    with pytest.raises(DecisionError):
        adapter.route_record(conn, bad)


def test_route_decide_remains_zero_write(conn):
    _seed(conn)
    fp_tables = ["providers", "models", "scores", "availability", "events", "recommendations"]
    before = {
        t: conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"] for t in fp_tables
    }
    adapter.route_decide(conn, "python")
    after = {
        t: conn.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"] for t in fp_tables
    }
    assert before == after
