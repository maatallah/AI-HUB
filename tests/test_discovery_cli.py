"""Integration tests for the discovery CLI subcommands (Phase 6 M2)."""

from __future__ import annotations

import json as jsonlib

import pytest

import app.main as main
from database import database as db_util


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
                "logging": {"level": "INFO"},
            }
        )

    monkeypatch.setattr(main, "load_config", _load_config)
    yield conn
    conn.close()


def _run(args):
    main.main(args)


def _record(name="Acme"):
    return {
        "provider": {
            "name": name,
            "company": "Acme",
            "api_type": "OpenAI Compatible",
            "base_url": "https://api.acme.example/v1",
            "documentation_url": "https://docs.acme.example",
        },
        "models": [{"model_name": "Acme Turbo", "model_identifier": "acme-turbo"}],
    }


def _write(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(jsonlib.dumps(data), encoding="utf-8")
    return path


def _enable_discovery(cli_conn, monkeypatch, urls=None):
    from app.config import validate

    db_file = cli_conn.execute(
        "SELECT file FROM pragma_database_list WHERE name='main'"
    ).fetchone()["file"]

    def _load_config(path=None):
        return validate(
            {
                "database": {"path": db_file},
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
                    "enabled": True,
                    "allowlisted_urls": urls or [],
                    "timeout_seconds": 10,
                    "import_dir": "data/discovery",
                },
                "benchmark": {"import_dir": "data/benchmarks"},
                "logging": {"level": "INFO"},
            }
        )

    monkeypatch.setattr(main, "load_config", _load_config)


def test_import_disabled_gate(cli_conn, capsys):
    with pytest.raises(SystemExit) as exc:
        _run(["discovery", "import"])
    assert exc.value.code == 1
    assert "Discovery is disabled" in capsys.readouterr().err


def test_run_requires_allow_network_flag(cli_conn, capsys):
    with pytest.raises(SystemExit) as exc:
        _run(["discovery", "run"])
    assert exc.value.code == 1
    assert "--allow-network" in capsys.readouterr().err


def test_run_requires_non_empty_allowlist(cli_conn, monkeypatch, capsys):
    _enable_discovery(cli_conn, monkeypatch, urls=[])
    with pytest.raises(SystemExit) as exc:
        _run(["discovery", "run", "--allow-network"])
    assert exc.value.code == 1
    assert "allowlist" in capsys.readouterr().err


def test_import_and_approve_flow(cli_conn, monkeypatch, tmp_path, capsys):
    _enable_discovery(cli_conn, monkeypatch)
    path = _write(tmp_path, "acme.json", _record("Acme"))
    _run(["discovery", "import", str(path)])
    out = capsys.readouterr().out
    assert "added=1" in out
    out = _run_ok(capsys)
    assert "#1 Acme state=PENDING_REVIEW source=curated" in out
    _run(["discovery", "approve", "1", "--reason", "ok"])
    out = capsys.readouterr().out
    assert "APPROVED" in out
    assert "materialized (provider #1)" in out
    count = cli_conn.execute("SELECT COUNT(*) FROM providers").fetchone()[0]
    assert count == 1  # M3 materializes the approved candidate
    model_count = cli_conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
    assert model_count == 1
    status = cli_conn.execute(
        "SELECT status FROM providers WHERE id = 1"
    ).fetchone()["status"]
    assert status == "NEW"


def _run_ok(capsys):
    _run(["discovery", "list"])
    return capsys.readouterr().out


def test_list_state_filter(cli_conn, monkeypatch, tmp_path, capsys):
    _enable_discovery(cli_conn, monkeypatch)
    path = _write(tmp_path, "acme.json", [_record("Alpha"), _record("Beta")])
    _run(["discovery", "import", str(path)])
    capsys.readouterr()
    _run(["discovery", "approve", "1", "--reason", "ok"])
    capsys.readouterr()
    out = _run_state(capsys, "APPROVED")
    assert "Alpha" in out
    assert "Beta" not in out


def _run_state(capsys, state):
    _run(["discovery", "list", "--state", state])
    return capsys.readouterr().out


def test_reject_requires_reason_flag(cli_conn, monkeypatch, tmp_path, capsys):
    _enable_discovery(cli_conn, monkeypatch)
    path = _write(tmp_path, "acme.json", _record("Acme"))
    _run(["discovery", "import", str(path)])
    capsys.readouterr()
    from io import StringIO
    import sys

    buffer = StringIO()
    old = sys.stderr
    sys.stderr = buffer
    try:
        _run(["discovery", "reject", "1"])
    except SystemExit as exc:
        assert exc.code == 2  # argparse: --reason is required
    finally:
        sys.stderr = old
    assert "--reason" in buffer.getvalue()


def test_reject_flow_retains_row(cli_conn, monkeypatch, tmp_path, capsys):
    _enable_discovery(cli_conn, monkeypatch)
    path = _write(tmp_path, "acme.json", _record("Acme"))
    _run(["discovery", "import", str(path)])
    capsys.readouterr()
    _run(["discovery", "reject", "1", "--reason", "not a fit"])
    out = capsys.readouterr().out
    assert "REJECTED" in out
    row = cli_conn.execute("SELECT * FROM discovery_candidates WHERE id = 1").fetchone()
    assert row is not None  # retained, never deleted


def test_approve_on_discovered_via_cli_fails(cli_conn, monkeypatch, tmp_path, capsys):
    _enable_discovery(cli_conn, monkeypatch)
    path = _write(tmp_path, "acme.json", _record("Acme"))
    _run(["discovery", "import", str(path)])
    capsys.readouterr()
    # queue already happened on import, so approve of a non-PENDING_REVIEW would
    # need a DISCOVERED row. Approving twice is the equivalent CLI discipline.
    _run(["discovery", "approve", "1", "--reason", "ok"])
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        _run(["discovery", "approve", "1", "--reason", "again"])
    assert exc.value.code == 1
    assert "PENDING_REVIEW" in capsys.readouterr().err


def test_import_directory_scan_deterministic(cli_conn, monkeypatch, tmp_path, capsys):
    _enable_discovery(cli_conn, monkeypatch)
    _write(tmp_path, "z.json", _record("Zulu"))
    _write(tmp_path, "a.json", _record("Alpha"))
    _run(["discovery", "import", str(tmp_path)])
    out = capsys.readouterr().out
    assert "added=1" in out
    out = _run_ok(capsys)
    # files are scanned in sorted order: a.json (Alpha) before z.json (Zulu)
    assert "#1 Alpha" in out
    assert "#2 Zulu" in out


def test_import_empty_directory_reports_nothing(tmp_path, cli_conn, monkeypatch, capsys):
    _enable_discovery(cli_conn, monkeypatch)
    empty = tmp_path / "empty"
    empty.mkdir()
    _run(["discovery", "import", str(empty)])
    assert "No .json files" in capsys.readouterr().out


def test_config_show_renders_discovery(cli_conn, monkeypatch, capsys):
    _run(["config", "show"])
    out = capsys.readouterr().out
    assert "[discovery]" in out
    assert "enabled = false" in out