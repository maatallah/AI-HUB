"""SQLite database access for AI-Hub.

Phase 1 scope: connection management, schema initialization and schema
introspection. No provider or model business logic lives here.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

#: Relative location of the default database file (see config default).
DEFAULT_DB_PATH = Path("database") / "ai_hub.db"

#: Schema file shipped with the repository.
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

#: Tables defined by the specification (v1.1 Section 8 / v1.2 Section 8)
#: plus the normalized scores table (ADR-0001).
EXPECTED_TABLES = {
    "providers",
    "models",
    "scores",
    "availability",
    "events",
    "preferences",
    "recommendations",
}


class DatabaseError(RuntimeError):
    """Raised when the database is unavailable or inconsistent."""


def connect(db_path=DEFAULT_DB_PATH):
    """Open a connection to the SQLite database, creating its directory if needed.

    Foreign key enforcement is always enabled.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize(db_path=DEFAULT_DB_PATH):
    """Create the database file and apply the schema. Idempotent."""
    conn = connect(db_path)
    try:
        conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return conn


def table_names(conn):
    """Return the set of user tables present in the database."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {row["name"] for row in rows}


def validate_schema(conn):
    """Verify that every table required by the specification exists.

    Raises DatabaseError if any table is missing.
    """
    missing = EXPECTED_TABLES - table_names(conn)
    if missing:
        raise DatabaseError(
            "Schema validation failed - missing tables: {}".format(
                ", ".join(sorted(missing))
            )
        )
    return True
