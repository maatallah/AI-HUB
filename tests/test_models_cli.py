"""Integration tests for the model list CLI subcommand (Phase 6 M3)."""

from __future__ import annotations

import pytest

import app.main as main
from core import models as models_registry
from core import providers
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


def _run(args, capsys):
    main.main(args)
    return capsys.readouterr().out


def _seed(cli_conn, provider_name="Acme", identifier="acme-turbo"):
    provider_id = providers.add_provider(cli_conn, provider_name, status="ACTIVE")
    model_id = models_registry.add_model(
        cli_conn, provider_id, model_name="Acme Turbo", model_identifier=identifier
    )
    return provider_id, model_id


def test_model_list_empty(cli_conn, capsys):
    out = _run(["model", "list"], capsys)
    assert "No models found." in out


def test_model_list_shows_models(cli_conn, capsys):
    provider_id, model_id = _seed(cli_conn)
    out = _run(["model", "list"], capsys)
    assert f"#{model_id} acme-turbo provider=Acme" in out


def test_model_list_filter_by_provider(cli_conn, capsys):
    _, _ = _seed(cli_conn, "Acme", "acme-turbo")
    other_id, other_model = _seed(cli_conn, "Beta", "beta-1")
    out = _run(["model", "list", "--provider", str(other_id)], capsys)
    assert "beta-1" in out
    assert "acme-turbo" not in out


def test_model_list_unknown_provider_reports_nothing(cli_conn, capsys):
    out = _run(["model", "list", "--provider", "999"], capsys)
    assert "No models found." in out


def test_model_list_invalid_provider_argument(cli_conn, capsys):
    with pytest.raises(SystemExit):
        _run(["model", "list", "--provider", "abc"], capsys)
