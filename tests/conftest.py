"""Shared test fixtures."""

from __future__ import annotations

import pytest

from database import database as db_util


@pytest.fixture()
def db_path(tmp_path):
    """A database file path inside a temporary directory."""
    return tmp_path / "test" / "ai_hub.db"


@pytest.fixture()
def conn(db_path):
    """A connection to an initialized database."""
    connection = db_util.initialize(db_path)
    yield connection
    connection.close()
