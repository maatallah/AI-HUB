"""Integration tests for the trend CLI subcommands (Phase 6, trend milestone)."""

from __future__ import annotations

import pytest

import app.main as main
from core import events, providers
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
    return capsys.readouterr().out


def _seed_model(cli_conn):
    provider_id = providers.add_provider(cli_conn, "Acme", status="ACTIVE")
    cli_conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier)"
        " VALUES (?, 'Acme Turbo', 'acme-turbo')",
        (provider_id,),
    )
    cli_conn.commit()
    model_id = cli_conn.execute(
        "SELECT id FROM models WHERE model_identifier='acme-turbo'"
    ).fetchone()["id"]
    return provider_id, model_id


def _seed_scores(cli_conn, model_id):
    ingest.set_score(cli_conn, model_id, "coding", 80, source="MANUAL")
    ingest.set_score(cli_conn, model_id, "coding", 85, source="MANUAL")
    ingest.set_score(cli_conn, model_id, "coding", 90, source="MANUAL")


def _seed_health(cli_conn, provider_id):
    events.record_event(
        cli_conn, "HEALTH_CHECK_OK", entity_type="provider", entity_id=provider_id
    )
    events.record_event(
        cli_conn, "HEALTH_CHECK_OK", entity_type="provider", entity_id=provider_id,
        payload={"latency_ms": 3000},
    )
    events.record_event(
        cli_conn, "HEALTH_CHECK_FAILED", entity_type="provider", entity_id=provider_id,
        payload={"latency_ms": 5000},
    )


def test_trend_scores_no_history(cli_conn, capsys):
    _, model_id = _seed_model(cli_conn)
    out = _run(["trend", "scores", "--model", str(model_id)], capsys)
    assert "No score history." in out


def test_trend_scores_up(cli_conn, capsys):
    _, model_id = _seed_model(cli_conn)
    _seed_scores(cli_conn, model_id)
    out = _run(["trend", "scores", "--model", str(model_id)], capsys)
    assert "model=acme-turbo (Acme)" in out
    assert "dimension=coding" in out
    assert "direction=up" in out
    assert "magnitude=0.1" in out
    assert "points=3/3" in out


def test_trend_scores_dimension_filter(cli_conn, capsys):
    _, model_id = _seed_model(cli_conn)
    _seed_scores(cli_conn, model_id)
    ingest.set_score(cli_conn, model_id, "reasoning", 70, source="MANUAL")
    ingest.set_score(cli_conn, model_id, "reasoning", 80, source="MANUAL")
    ingest.set_score(cli_conn, model_id, "reasoning", 90, source="MANUAL")
    out = _run(
        ["trend", "scores", "--model", str(model_id), "--dimension", "coding"],
        capsys,
    )
    assert "dimension=coding" in out
    assert "reasoning" not in out


def test_trend_scores_default_and_overridden_window_days(cli_conn, capsys):
    _, model_id = _seed_model(cli_conn)
    _seed_scores(cli_conn, model_id)
    out_default = _run(["trend", "scores", "--model", str(model_id)], capsys)
    assert "window_days=90" in out_default
    out_overridden = _run(
        ["trend", "scores", "--model", str(model_id), "--days", "45"], capsys
    )
    assert "window_days=45" in out_overridden


def test_trend_scores_insufficient_data_exposes_min_points(cli_conn, capsys):
    _, model_id = _seed_model(cli_conn)
    ingest.set_score(cli_conn, model_id, "coding", 90, source="MANUAL")
    out = _run(["trend", "scores", "--model", str(model_id)], capsys)
    assert "direction=insufficient_data" in out
    assert "min_points=3" in out
    assert "points=1/1" in out


def test_trend_scores_requires_model(cli_conn, capsys):
    with pytest.raises(SystemExit):
        _run(["trend", "scores"], capsys)


def test_trend_scores_unknown_model(cli_conn, capsys):
    with pytest.raises(SystemExit) as exc:
        _run(["trend", "scores", "--model", "999"], capsys)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "not found" in err


def test_trend_scores_invalid_days(cli_conn, capsys):
    _, model_id = _seed_model(cli_conn)
    with pytest.raises(SystemExit) as exc:
        _run(["trend", "scores", "--model", str(model_id), "--days", "0"], capsys)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "Error:" in err


def test_trend_availability_no_history(cli_conn, capsys):
    providers.add_provider(cli_conn, "Acme", status="ACTIVE")
    out = _run(["trend", "availability"], capsys)
    assert "No availability history." in out


def test_trend_availability_down(cli_conn, capsys):
    provider_id, _ = _seed_model(cli_conn)
    _seed_health(cli_conn, provider_id)
    out = _run(["trend", "availability", "--provider", str(provider_id)], capsys)
    assert f"provider={provider_id}" in out
    assert "direction=down" in out
    assert "magnitude=-1.0" in out
    assert "points=3/3" in out
    assert "excluded_unknown=0" in out
    assert "excluded_transitions=0" in out


def test_trend_availability_all_providers_grouped(cli_conn, capsys):
    provider_a, _ = _seed_model(cli_conn)
    provider_b = providers.add_provider(cli_conn, "Beta", status="ACTIVE")
    _seed_health(cli_conn, provider_a)
    _seed_health(cli_conn, provider_b)
    out = _run(["trend", "availability"], capsys)
    assert f"provider={provider_a}" in out
    assert f"provider={provider_b}" in out


def test_trend_availability_insufficient_data_exposes_min_points(cli_conn, capsys):
    provider_id, _ = _seed_model(cli_conn)
    events.record_event(
        cli_conn, "HEALTH_CHECK_OK", entity_type="provider", entity_id=provider_id
    )
    out = _run(["trend", "availability", "--provider", str(provider_id)], capsys)
    assert "direction=insufficient_data" in out
    assert "min_points=3" in out
    assert "points=1/1" in out


def test_trend_availability_unknown_provider(cli_conn, capsys):
    with pytest.raises(SystemExit) as exc:
        _run(["trend", "availability", "--provider", "999"], capsys)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "not found" in err


def test_trend_is_read_only(cli_conn, capsys):
    provider_id, model_id = _seed_model(cli_conn)
    _seed_scores(cli_conn, model_id)
    _seed_health(cli_conn, provider_id)
    before = cli_conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    _run(["trend", "scores", "--model", str(model_id)], capsys)
    _run(["trend", "availability", "--provider", str(provider_id)], capsys)
    after = cli_conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert after == before