"""Tests that the database schema matches the specification."""

from __future__ import annotations

import sqlite3

import pytest

from database import database as db_util


def _columns(conn, table):
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def _foreign_keys(conn, table):
    return conn.execute(f"PRAGMA foreign_key_list({table})").fetchall()


def test_expected_tables_present(conn):
    assert db_util.EXPECTED_TABLES == {
        "providers",
        "models",
        "availability",
        "events",
        "preferences",
        "recommendations",
    }
    assert db_util.EXPECTED_TABLES <= db_util.table_names(conn)


def test_providers_columns(conn):
    assert {
        "id", "name", "company", "api_type", "base_url", "documentation_url",
        "status", "status_reason", "notes", "created_at", "updated_at",
    } <= _columns(conn, "providers")


def test_models_columns(conn):
    assert {
        "id", "provider_id", "model_name", "model_identifier", "context_window",
        "supports_tools", "supports_streaming", "supports_json", "supports_vision",
        "coding_score", "reasoning_score", "latency_score", "reliability_score",
        "score_source", "confidence_level", "created_at", "updated_at",
    } <= _columns(conn, "models")


def test_availability_columns(conn):
    assert {
        "id", "provider_id", "model_id", "state", "reason", "quota_type",
        "reset_at", "last_success", "last_failure", "consecutive_failures",
        "created_at", "updated_at",
    } <= _columns(conn, "availability")


def test_events_columns(conn):
    assert {
        "id", "event_type", "entity_type", "entity_id", "payload", "occurred_at",
    } <= _columns(conn, "events")


def test_preferences_columns(conn):
    assert {"key", "value", "value_type", "updated_at"} <= _columns(conn, "preferences")


def test_recommendations_columns(conn):
    assert {
        "id", "task", "profile", "provider_id", "model_id", "decision_version",
        "score_breakdown", "explanation", "confidence", "requested_at", "created_at",
    } <= _columns(conn, "recommendations")


def test_models_references_providers(conn):
    fks = _foreign_keys(conn, "models")
    assert any(fk["table"] == "providers" for fk in fks)


def test_provider_status_constraint(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO providers (name, status) VALUES ('Bad', 'BOGUS')"
        )
        conn.commit()


def test_provider_status_constraint_allows_lifecycle_states(conn):
    for status in ("NEW", "EVALUATING", "ACTIVE", "LIMITED", "DEGRADED", "OFFLINE", "ARCHIVED"):
        conn.execute(
            "INSERT INTO providers (name, status) VALUES (?, ?)",
            (f"Provider-{status}", status),
        )
    conn.commit()
    assert len(db_util.table_names(conn) - db_util.EXPECTED_TABLES) == 0


def test_availability_state_constraint(conn):
    conn.execute("INSERT INTO providers (name, status) VALUES ('P', 'ACTIVE')")
    conn.commit()
    provider_id = conn.execute("SELECT id FROM providers WHERE name='P'").fetchone()["id"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO availability (provider_id, state) VALUES (?, 'BOGUS')",
            (provider_id,),
        )
        conn.commit()


def test_boolean_flag_constraint(conn):
    conn.execute("INSERT INTO providers (name) VALUES ('P')")
    conn.commit()
    provider_id = conn.execute("SELECT id FROM providers WHERE name='P'").fetchone()["id"]
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO models (provider_id, model_name, model_identifier, supports_tools)"
            " VALUES (?, 'M', 'm-1', 2)",
            (provider_id,),
        )
        conn.commit()


def test_models_unique_per_provider_identifier(conn):
    conn.execute("INSERT INTO providers (name) VALUES ('P')")
    conn.commit()
    provider_id = conn.execute("SELECT id FROM providers WHERE name='P'").fetchone()["id"]
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier)"
        " VALUES (?, 'M', 'm-1')",
        (provider_id,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO models (provider_id, model_name, model_identifier)"
            " VALUES (?, 'M2', 'm-1')",
            (provider_id,),
        )
        conn.commit()
