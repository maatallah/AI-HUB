"""Tests for database creation and connectivity."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from database import database as db_util


def test_initialize_creates_db_file(db_path):
    assert not db_path.exists()
    db_util.initialize(db_path)
    assert db_path.exists()


def test_initialize_is_idempotent(conn):
    db_path = Path(conn.execute("PRAGMA database_list").fetchone()[2])
    db_util.initialize(db_path)
    assert db_path.exists()


def test_foreign_keys_enforced(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO models (provider_id, model_name, model_identifier)"
            " VALUES (999, 'Ghost', 'ghost-1')"
        )
        conn.commit()


def test_connection_has_row_factory(conn):
    row = conn.execute("SELECT 1 AS value").fetchone()
    assert row["value"] == 1


def test_validate_schema_passes(conn):
    assert db_util.validate_schema(conn) is True


def test_validate_schema_detects_missing_table(db_path):
    conn = db_util.initialize(db_path)
    conn.execute("DROP TABLE recommendations")
    conn.commit()
    try:
        with pytest.raises(db_util.DatabaseError) as exc_info:
            db_util.validate_schema(conn)
        assert "recommendations" in str(exc_info.value)
    finally:
        conn.close()
