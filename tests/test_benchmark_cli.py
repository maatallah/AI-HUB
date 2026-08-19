"""Integration tests for the benchmark CLI subcommands (Phase 6 M3)."""

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
                "trend": {"window_days": 90, "min_points": 3},
                "logging": {"level": "INFO"},
            }
        )

    monkeypatch.setattr(main, "load_config", _load_config)
    yield conn
    conn.close()


def _run(args):
    main.main(args)


def _seed(cli_conn, provider="OpenAI", identifier="gpt-4"):
    from core import providers

    providers.add_provider(cli_conn, provider, status="ACTIVE")
    pid = cli_conn.execute(
        "SELECT id FROM providers WHERE name=?", (provider,)
    ).fetchone()["id"]
    cli_conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier)"
        " VALUES (?, ?, ?)",
        (pid, identifier, identifier),
    )
    cli_conn.commit()


def _doc(name="mmlu", raw_value=86.4):
    return {
        "name": name,
        "version": "5-shot",
        "origin": "https://example.com/results.json",
        "mapping": {"accuracy": {"dimension": "reasoning", "formula": "identity"}},
        "results": [
            {
                "provider": "OpenAI",
                "model": "gpt-4",
                "metric": "accuracy",
                "raw_value": raw_value,
            }
        ],
    }


def _write(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(jsonlib.dumps(data), encoding="utf-8")
    return path


def test_import_and_list_flow(cli_conn, tmp_path, capsys):
    _seed(cli_conn)
    path = _write(tmp_path, "r.json", _doc())
    _run(["benchmark", "import", "--file", str(path)])
    out = capsys.readouterr().out
    assert "IMPORTED" in out
    assert "run_id=1" in out
    assert "name=mmlu" in out
    _run(["benchmark", "list"])
    out = capsys.readouterr().out
    assert "#1 mmlu" in out
    _run(["benchmark", "list", "--run", "1"])
    out = capsys.readouterr().out
    assert "gpt-4" in out
    assert "accuracy" in out


def test_dry_run_writes_nothing(cli_conn, tmp_path, capsys):
    _seed(cli_conn)
    path = _write(tmp_path, "r.json", _doc())
    _run(["benchmark", "import", "--file", str(path), "--dry-run"])
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert "run_id=None" in out
    run = cli_conn.execute("SELECT COUNT(*) AS n FROM benchmark_runs").fetchone()["n"]
    score = cli_conn.execute("SELECT COUNT(*) AS n FROM scores").fetchone()["n"]
    assert run == 0
    assert score == 0


def test_import_reports_duplicate_of(cli_conn, tmp_path, capsys):
    _seed(cli_conn)
    path = _write(tmp_path, "r.json", _doc())
    _run(["benchmark", "import", "--file", str(path)])
    capsys.readouterr()
    _run(["benchmark", "import", "--file", str(path)])
    out = capsys.readouterr().out
    assert "duplicate_of=#1" in out
    assert "run_id=2" in out


def test_import_name_override(cli_conn, tmp_path, capsys):
    _seed(cli_conn)
    path = _write(tmp_path, "r.json", _doc("mmlu"))
    _run(["benchmark", "import", "--file", str(path), "--name", "glue"])
    out = capsys.readouterr().out
    assert "name=glue" in out


def test_import_invalid_file_reports_error(cli_conn, tmp_path, capsys):
    _seed(cli_conn)
    path = _write(tmp_path, "r.json", {"bogus": True})
    _run(["benchmark", "import", "--file", str(path)])
    captured = capsys.readouterr()
    assert "failed=1" in captured.out
    assert "Unknown benchmark keys" in captured.err
    run = cli_conn.execute("SELECT COUNT(*) AS n FROM benchmark_runs").fetchone()["n"]
    assert run == 0


def test_import_missing_file_reports_error(cli_conn, tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        _run(["benchmark", "import", "--file", str(tmp_path / "missing.json")])
    assert exc.value.code == 1
    assert "not found" in capsys.readouterr().err


def test_list_empty(cli_conn, capsys):
    _run(["benchmark", "list"])
    assert "No benchmark runs." in capsys.readouterr().out


def test_import_directory_scan_deterministic(cli_conn, tmp_path, capsys):
    _seed(cli_conn)
    _write(tmp_path, "z.json", _doc("zulu"))
    _write(tmp_path, "a.json", _doc("alpha"))
    _run(["benchmark", "import", "--file", str(tmp_path)])
    out = capsys.readouterr().out
    assert "a.json: IMPORTED" in out
    assert "z.json: IMPORTED" in out
    _run(["benchmark", "list"])
    out = capsys.readouterr().out
    assert "#1 alpha" in out
    assert "#2 zulu" in out


def test_import_empty_directory_reports_nothing(cli_conn, tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    _run(["benchmark", "import", "--file", str(empty)])
    assert "No .json files" in capsys.readouterr().out


def test_config_show_renders_benchmark(cli_conn, capsys):
    _run(["config", "show"])
    out = capsys.readouterr().out
    assert "[benchmark]" in out
    assert 'import_dir = "data/benchmarks"' in out
