"""Integration tests for the dashboard CLI subcommands."""

from __future__ import annotations

import sqlite3

import pytest

import app.main as main
from core import providers
from database import database as db_util
from scoring import ingest


@pytest.fixture()
def cli_conn(tmp_path, monkeypatch):
    """Point the CLI at a temporary database and expose its connection."""
    db_file = tmp_path / "cli.db"
    conn = db_util.initialize(db_file)

    def _load_config(path=None):
        from app.config import validate

        return validate(
            {
                "database": {"path": str(db_file)},
                "monitoring": {
                    "enabled": True,
                    "interval_minutes": 60,
                    "timeout_seconds": 10,
                    "failure_threshold": 3,
                    "latency_threshold_ms": 10000,
                },
                "scoring": {
                    "aging_fresh_days": 30,
                    "aging_aging_days": 90,
                    "aging_old_days": 180,
                    "derive_operational": True,
                },
                "fallback": {"max_chain_length": 5},
                "recommendation": {
                    "default_profile": "coding",
                    "decision_version": "3.0.0",
                },
                "dashboard": {"refresh_seconds": 60},
                "logging": {"level": "INFO"},
            }
        )

    monkeypatch.setattr(main, "load_config", _load_config)
    yield conn
    conn.close()


def _run(args, capsys):
    main.main(args)
    return capsys.readouterr().out


def _add_provider(conn, name="Acme"):
    return providers.add_provider(conn, name, status="ACTIVE")


def _add_model(conn, provider_id, identifier="acme-1"):
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier)"
        " VALUES (?, 'Acme Model', ?)",
        (provider_id, identifier),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (identifier,)
    ).fetchone()["id"]


def test_dashboard_status_empty(cli_conn, capsys):
    out = _run(["dashboard", "status"], capsys)
    assert "total_providers\t0" in out
    assert "active_providers\t0" in out


def test_dashboard_status_counts(cli_conn, capsys):
    _add_provider(cli_conn, name="Alpha")
    out = _run(["dashboard", "status"], capsys)
    assert "total_providers\t1" in out
    assert "active_providers\t1" in out


def test_dashboard_report_providers(cli_conn, capsys):
    _add_provider(cli_conn, name="Alpha")
    out = _run(["dashboard", "report", "providers"], capsys)
    assert "# providers" in out
    assert "Alpha\tACTIVE" in out


def test_dashboard_report_scores(cli_conn, capsys):
    pid = _add_provider(cli_conn, name="Alpha")
    mid = _add_model(cli_conn, pid)
    ingest.set_score(cli_conn, mid, "coding", 85, source="MANUAL")
    out = _run(["dashboard", "report", "scores"], capsys)
    assert "coding\t85.0" in out


def test_dashboard_report_unknown_rejected(cli_conn, capsys):
    """Unknown report names are rejected by argparse's choices (exit 2)."""
    from io import StringIO
    import sys

    buffer = StringIO()
    old = sys.stderr
    sys.stderr = buffer
    try:
        main.main(["dashboard", "report", "bogus"])
    except SystemExit as exc:
        assert exc.code == 2
    finally:
        sys.stderr = old
    assert "invalid choice: 'bogus'" in buffer.getvalue()


def test_dashboard_history_model_required(cli_conn, capsys):
    from io import StringIO
    import sys

    buffer = StringIO()
    old = sys.stderr
    sys.stderr = buffer
    try:
        main.main(["dashboard", "history"])
    except SystemExit as exc:
        assert exc.code == 1
    finally:
        sys.stderr = old
    assert "--model is required" in buffer.getvalue()


def test_dashboard_history_score_series(cli_conn, capsys):
    pid = _add_provider(cli_conn, name="Alpha")
    mid = _add_model(cli_conn, pid)
    ingest.set_score(cli_conn, mid, "coding", 80, source="MANUAL")
    ingest.set_score(cli_conn, mid, "coding", 90, source="MANUAL")
    out = _run(["dashboard", "history", "--model", str(mid)], capsys)
    assert "occurred_at\tdimension\tvalue\tconfidence\tsource" in out
    assert "coding\t80.0" in out
    assert "coding\t90.0" in out


def test_dashboard_history_dimension_filter(cli_conn, capsys):
    pid = _add_provider(cli_conn, name="Alpha")
    mid = _add_model(cli_conn, pid)
    ingest.set_score(cli_conn, mid, "coding", 80, source="MANUAL")
    ingest.set_score(cli_conn, mid, "reasoning", 85, source="MANUAL")
    out = _run(["dashboard", "history", "--model", str(mid), "--dimension", "coding"], capsys)
    assert "coding\t80.0" in out
    assert "reasoning" not in out


def test_dashboard_history_availability(cli_conn, capsys):
    from monitoring import availability

    pid = _add_provider(cli_conn, name="Alpha")
    availability.apply_lifecycle(cli_conn, pid, "DEGRADED", "Repeated failures.")
    out = _run(["dashboard", "history", "--availability"], capsys)
    assert "occurred_at\tevent_type\tentity_type\tentity_id" in out
    assert "MONITOR_STATUS_CHANGED" in out


def test_dashboard_history_no_data(cli_conn, capsys):
    out = _run(["dashboard", "history", "--model", "1"], capsys)
    assert "No score history." in out


def test_cli_does_not_modify_engine_state(cli_conn, capsys):
    """Running dashboard commands must not write events or rows."""
    pid = _add_provider(cli_conn, name="Alpha")
    _add_model(cli_conn, pid)
    before = cli_conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    _run(["dashboard", "status"], capsys)
    _run(["dashboard", "report", "providers"], capsys)
    _run(["dashboard", "history", "--availability"], capsys)
    after = cli_conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert after == before
