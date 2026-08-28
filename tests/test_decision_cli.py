"""Integration tests for the route decide / route record CLI (post-v1 M1)."""

from __future__ import annotations

import json

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
                "discovery": {
                    "enabled": False,
                    "allowlisted_urls": [],
                    "timeout_seconds": 10,
                    "import_dir": "data/discovery",
                },
                "benchmark": {"import_dir": "data/benchmarks"},
                "trend": {"window_days": 90, "min_points": 3},
                "logging": {"level": "INFO"},
            }
        )

    monkeypatch.setattr(main, "load_config", _load_config)
    yield conn
    conn.close()


def _run(args, capsys):
    main.main(args)
    captured = capsys.readouterr()
    assert captured.err == ""
    return captured.out


def _seed(cli_conn, name="Acme", identifier="acme-turbo", coding=90):
    pid = providers.add_provider(cli_conn, name, status="ACTIVE")
    cli_conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier, context_window)"
        " VALUES (?, ?, ?, 32000)",
        (pid, identifier, identifier),
    )
    cli_conn.commit()
    mid = cli_conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (identifier,)
    ).fetchone()["id"]
    if coding is not None:
        ingest.set_score(cli_conn, mid, "coding", coding, confidence=1.0, source="MANUAL")
    return pid, mid


def test_route_decide_text_output(cli_conn, capsys):
    _seed(cli_conn)
    out = _run(["route", "decide", "--task", "python"], capsys)
    assert "Status: OK" in out
    assert "Selected: Acme acme-turbo" in out


def test_route_decide_json_envelope(cli_conn, capsys):
    _, mid = _seed(cli_conn)
    out = _run(["route", "decide", "--task", "python", "--json"], capsys)
    env = json.loads(out)
    assert env["contract_version"] == "1"
    assert env["status"] == "OK"
    assert env["provenance"] == {"decision_id": None, "recorded": False}
    assert env["candidates"][0]["model_id"] == mid


def test_route_decide_json_deterministic_bytes(cli_conn, capsys):
    _seed(cli_conn)
    first = _run(
        ["route", "decide", "--task", "python", "--json", "--limit", "5"], capsys
    )
    second = _run(
        ["route", "decide", "--task", "python", "--json", "--limit", "5"], capsys
    )
    a, b = json.loads(first), json.loads(second)
    a.pop("created_at"), b.pop("created_at")
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_route_decide_filters_apply(cli_conn, capsys):
    _seed(cli_conn, "Acme", "acme-turbo", coding=90)
    _seed(cli_conn, "Beta", "beta-1", coding=70)
    out = _run(
        ["route", "decide", "--task", "python", "--deny-provider", "Acme"], capsys
    )
    assert "Selected: Beta beta-1" in out


def test_route_decide_no_candidate_status(cli_conn, capsys):
    out = _run(["route", "decide", "--task", "python"], capsys)
    assert "Status: NO_CANDIDATE" in out


def test_route_decide_unknown_profile_fails(cli_conn, capsys):
    with pytest.raises(SystemExit):
        main.main(["route", "decide", "--task", "python", "--profile", "nope"])
    assert "Error:" in capsys.readouterr().err


def test_route_decide_rejects_invalid_capability(cli_conn, capsys):
    with pytest.raises(SystemExit):
        main.main(["route", "decide", "--task", "python", "--capability", "magic"])
    capsys.readouterr()


def test_route_record_round_trip(cli_conn, capsys):
    _, mid = _seed(cli_conn)
    envelope_json = _run(
        ["route", "decide", "--task", "python", "--json"], capsys
    )
    import io
    import sys as _sys

    old = _sys.stdin
    _sys.stdin = io.StringIO(envelope_json)
    try:
        out = _run(["route", "record"], capsys)
    finally:
        _sys.stdin = old
    assert "Recorded 1 recommendation(s)." in out
    rows = cli_conn.execute("SELECT * FROM recommendations").fetchall()
    assert len(rows) == 1
    assert rows[0]["model_id"] == mid
    assert f"decision_id={rows[0]['id']}" in out
    event = cli_conn.execute(
        "SELECT COUNT(*) AS n FROM events WHERE event_type='RECOMMENDATION_CREATED'"
    ).fetchone()["n"]
    assert event == 1


def test_route_record_rejects_garbage_stdin(cli_conn, capsys):
    import io
    import sys as _sys

    old = _sys.stdin
    _sys.stdin = io.StringIO("{not json")
    try:
        with pytest.raises(SystemExit):
            main.main(["route", "record"])
    finally:
        _sys.stdin = old
    assert "Error:" in capsys.readouterr().err


def test_route_record_rejects_empty_envelope(cli_conn, capsys):
    import io
    import sys as _sys

    old = _sys.stdin
    _sys.stdin = io.StringIO(json.dumps({"contract_version": "1", "status": "OK"}))
    try:
        with pytest.raises(SystemExit):
            main.main(["route", "record"])
    finally:
        _sys.stdin = old
    assert "Error:" in capsys.readouterr().err


def test_decide_writes_nothing_between_records(cli_conn, capsys):
    _seed(cli_conn)
    before = cli_conn.execute("SELECT COUNT(*) AS n FROM recommendations").fetchone()["n"]
    _run(["route", "decide", "--task", "python", "--json"], capsys)
    after = cli_conn.execute("SELECT COUNT(*) AS n FROM recommendations").fetchone()["n"]
    assert before == after == 0


def test_route_record_provenance_error_is_handled(cli_conn, capsys, monkeypatch):
    """F3: a provenance failure during RECORD exits 1 with error text, no traceback."""
    import io
    import sys as _sys
    from recommendation.provenance import ProvenanceError

    _seed(cli_conn)
    envelope_json = _run(
        ["route", "decide", "--task", "python", "--json"], capsys
    )

    def _boom(conn, envelope):
        raise ProvenanceError("simulated provenance failure")

    monkeypatch.setattr(main, "record_decision", _boom)
    old = _sys.stdin
    _sys.stdin = io.StringIO(envelope_json)
    try:
        with pytest.raises(SystemExit) as exc:
            main.main(["route", "record"])
    finally:
        _sys.stdin = old
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Error: simulated provenance failure" in captured.err
    assert "Traceback" not in captured.err
