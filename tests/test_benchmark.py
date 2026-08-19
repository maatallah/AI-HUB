"""Tests for the Phase 6 M3 benchmark ingestion (ADR-0006 / D-P3)."""

from __future__ import annotations

import json

import pytest

from benchmark import ingest as benchmark
from core import events, providers
from scoring import ingest as score_ingest


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _seed_model(conn, provider="OpenAI", identifier="gpt-4"):
    """Create a provider + model and return (provider_id, model_id)."""
    providers.add_provider(conn, provider, status="ACTIVE")
    pid = conn.execute("SELECT id FROM providers WHERE name=?", (provider,)).fetchone()["id"]
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier)"
        " VALUES (?, ?, ?)",
        (pid, identifier, identifier),
    )
    conn.commit()
    mid = conn.execute(
        "SELECT id FROM models WHERE provider_id=? AND model_identifier=?",
        (pid, identifier),
    ).fetchone()["id"]
    return pid, mid


def _doc(name="mmlu", results=None, mapping=None, **overrides):
    doc = {
        "name": name,
        "version": "5-shot",
        "origin": "https://example.com/results.json",
        "mapping": mapping
        or {"accuracy": {"dimension": "reasoning", "formula": "identity"}},
        "results": results
        or [
            {
                "provider": "OpenAI",
                "model": "gpt-4",
                "metric": "accuracy",
                "raw_value": 86.4,
            }
        ],
    }
    doc.update(overrides)
    return doc


def _write(tmp_path, name="r.json", data=None):
    path = tmp_path / name
    path.write_text(json.dumps(data if data is not None else _doc()), encoding="utf-8")
    return path


def _event_payloads(conn, event_type):
    rows = conn.execute(
        "SELECT * FROM events WHERE event_type = ? ORDER BY id", (event_type,)
    ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def _run_counts(conn):
    run = conn.execute("SELECT COUNT(*) AS n FROM benchmark_runs").fetchone()["n"]
    res = conn.execute("SELECT COUNT(*) AS n FROM benchmark_results").fetchone()["n"]
    scores = conn.execute("SELECT COUNT(*) AS n FROM scores").fetchone()["n"]
    return run, res, scores


# ---------------------------------------------------------------------------
# parsing / validation
# ---------------------------------------------------------------------------

def test_parse_requires_object(tmp_path):
    path = _write(tmp_path, data=[1, 2])
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.parse_benchmark_file(path)


def test_parse_rejects_unknown_top_level_keys(tmp_path):
    path = _write(tmp_path, data={**_doc(), "extra": True})
    with pytest.raises(benchmark.BenchmarkError) as exc:
        benchmark.parse_benchmark_file(path)
    assert "extra" in str(exc.value)


def test_parse_requires_name_version(tmp_path):
    for doc in ({"version": "1"}, {"name": "x"}):
        path = _write(tmp_path, data=doc)
        with pytest.raises(benchmark.BenchmarkError):
            benchmark.parse_benchmark_file(path)


def test_parse_requires_results_list(tmp_path):
    path = _write(tmp_path, data={**_doc(), "results": {}})
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.parse_benchmark_file(path)


def test_parse_rejects_secret_key_in_mapping(tmp_path):
    doc = _doc(
        mapping={"accuracy": {"dimension": "reasoning", "formula": "identity"}},
    )
    doc["mapping"]["api_token"] = {"dimension": "x", "formula": "identity"}
    path = _write(tmp_path, data=doc)
    with pytest.raises(benchmark.BenchmarkError) as exc:
        benchmark.parse_benchmark_file(path)
    assert "secret" in str(exc.value).lower()


def test_parse_rejects_secret_key_in_result(tmp_path):
    doc = _doc(results=[{"provider": "OpenAI", "model": "gpt-4", "metric": "accuracy",
                        "raw_value": 1.0, "access_key": "x"}])
    path = _write(tmp_path, data=doc)
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.parse_benchmark_file(path)


def test_parse_rejects_origin_with_credentials(tmp_path):
    path = _write(tmp_path, data=_doc(origin="https://user:pass@example.com/r.json"))
    with pytest.raises(benchmark.BenchmarkError) as exc:
        benchmark.parse_benchmark_file(path)
    assert "credentials" in str(exc.value)


def test_parse_rejects_origin_with_secret_query_key(tmp_path):
    path = _write(tmp_path, data=_doc(origin="https://example.com/r.json?api_key=abc"))
    with pytest.raises(benchmark.BenchmarkError) as exc:
        benchmark.parse_benchmark_file(path)
    assert "secret" in str(exc.value).lower()


def test_parse_unknown_formula_rejected(tmp_path):
    doc = _doc(
        mapping={"accuracy": {"dimension": "reasoning", "formula": "made_up"}}
    )
    path = _write(tmp_path, data=doc)
    with pytest.raises(benchmark.BenchmarkError) as exc:
        benchmark.parse_benchmark_file(path)
    assert "made_up" in str(exc.value)


def test_parse_unmapped_metric_rejected(tmp_path):
    doc = _doc(
        results=[{"provider": "OpenAI", "model": "gpt-4", "metric": "other",
                  "raw_value": 10.0}]
    )
    path = _write(tmp_path, data=doc)
    with pytest.raises(benchmark.BenchmarkError) as exc:
        benchmark.parse_benchmark_file(path)
    assert "not present in mapping" in str(exc.value)


def test_parse_invalid_raw_value_rejected(tmp_path):
    doc = _doc(results=[{"provider": "OpenAI", "model": "gpt-4",
                         "metric": "accuracy", "raw_value": "high"}])
    path = _write(tmp_path, data=doc)
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.parse_benchmark_file(path)


def test_parse_fraction_to_percent_normalizes(tmp_path):
    doc = _doc(
        mapping={"exact_match": {"dimension": "reasoning", "formula": "fraction_to_percent"}},
        results=[{"provider": "OpenAI", "model": "gpt-4",
                  "metric": "exact_match", "raw_value": 0.5}],
    )
    path = _write(tmp_path, data=doc)
    parsed = benchmark.parse_benchmark_file(path)
    assert parsed["name"] == "mmlu"
    assert parsed["mapping"]["exact_match"]["formula"] == "fraction_to_percent"


# ---------------------------------------------------------------------------
# import / persistence
# ---------------------------------------------------------------------------

def test_import_stores_run_results_and_scores(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path)
    summary = benchmark.import_file(conn, path, submitter="test")
    assert summary["run_id"] is not None
    assert summary["name"] == "mmlu"
    assert summary["results"] == 1
    assert summary["scored_dimensions"] == 1
    assert summary["duplicate_of"] is None

    run = benchmark.get_run(conn, summary["run_id"])
    assert run["name"] == "mmlu"
    assert run["version"] == "5-shot"
    assert run["origin"] == "https://example.com/results.json"
    assert run["submitter"] == "test"
    assert len(run["content_hash"]) == 64
    mapping = json.loads(run["mapping"])
    assert mapping["accuracy"] == {"dimension": "reasoning", "formula": "identity"}

    results = benchmark.list_run_results(conn, summary["run_id"])
    assert len(results) == 1
    assert results[0]["metric"] == "accuracy"
    assert results[0]["raw_value"] == 86.4
    assert results[0]["norm_value"] == 86.4

    score = conn.execute("SELECT * FROM scores").fetchone()
    assert score["source"] == "BENCHMARK"
    assert score["dimension"] == "reasoning"
    assert score["value"] == 86.4


def test_import_records_benchmark_imported_event(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path)
    summary = benchmark.import_file(conn, path, submitter="cli:test")
    payloads = _event_payloads(conn, "BENCHMARK_IMPORTED")
    assert len(payloads) == 1
    assert payloads[0]["run_id"] == summary["run_id"]
    assert payloads[0]["submitter"] == "cli:test"
    assert payloads[0]["content_hash"] == summary["content_hash"]
    assert payloads[0]["results"] == 1
    assert payloads[0]["scored_dimensions"] == 1


def test_import_uses_run_date_as_scored_at(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path, data=_doc(run_date="2026-08-01"))
    benchmark.import_file(conn, path, submitter="test")
    score = conn.execute("SELECT * FROM scores").fetchone()
    assert score["scored_at"] == "2026-08-01"


def test_import_fraction_to_percent_maps_value(conn, tmp_path):
    _seed_model(conn)
    doc = _doc(
        mapping={"exact_match": {"dimension": "reasoning", "formula": "fraction_to_percent"}},
        results=[{"provider": "OpenAI", "model": "gpt-4",
                  "metric": "exact_match", "raw_value": 0.5}],
    )
    path = _write(tmp_path, data=doc)
    benchmark.import_file(conn, path, submitter="test")
    score = conn.execute("SELECT * FROM scores").fetchone()
    assert score["value"] == 50.0


def test_import_rejects_unknown_model_atomically(conn, tmp_path):
    path = _write(tmp_path)  # no models seeded
    with pytest.raises(benchmark.BenchmarkError) as exc:
        benchmark.import_file(conn, path, submitter="test")
    assert "Unknown model" in str(exc.value)
    assert _run_counts(conn) == (0, 0, 0)


def test_import_invalid_metric_fails_atomically(conn, tmp_path):
    _seed_model(conn)
    doc = _doc(
        mapping={
            "accuracy": {"dimension": "reasoning", "formula": "identity"},
            "second": {"dimension": "reasoning", "formula": "identity"},
        },
        results=[
            {"provider": "OpenAI", "model": "gpt-4", "metric": "accuracy", "raw_value": 86.4},
            {"provider": "OpenAI", "model": "gpt-4", "metric": "accuracy", "raw_value": 90.0},
        ],
    )
    # duplicate (model, metric) within one file -> UNIQUE violation on write;
    # must be caught and leave no partial writes.
    path = _write(tmp_path, data=doc)
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.import_file(conn, path, submitter="test")
    assert _run_counts(conn) == (0, 0, 0)


def test_import_invalid_file_writes_nothing(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path, data={"bogus": True})
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.import_file(conn, path, submitter="test")
    assert _run_counts(conn) == (0, 0, 0)


def test_dry_run_mutates_nothing(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path)
    summary = benchmark.import_file(conn, path, submitter="test", dry_run=True)
    assert summary["run_id"] is None
    assert summary["dry_run"] is True
    assert summary["results"] == 1
    assert _run_counts(conn) == (0, 0, 0)
    assert not _event_payloads(conn, "BENCHMARK_IMPORTED")


def test_dry_run_validates_content(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path, data={"bad": True})
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.import_file(conn, path, submitter="test", dry_run=True)


# ---------------------------------------------------------------------------
# replay / duplicate
# ---------------------------------------------------------------------------

def test_replay_appends_new_run_and_reports_duplicate(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path)
    first = benchmark.import_file(conn, path, submitter="test")
    second = benchmark.import_file(conn, path, submitter="test")
    assert second["duplicate_of"] == first["run_id"]
    assert second["run_id"] != first["run_id"]
    assert benchmark.get_run(conn, second["run_id"]) is not None
    runs, results, scores = _run_counts(conn)
    assert runs == 2
    assert results == 2
    assert scores == 1  # upsert: UNIQUE (model_id, dimension) kept one current value


def test_replay_keeps_history_and_events(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path)
    benchmark.import_file(conn, path, submitter="test")
    benchmark.import_file(conn, path, submitter="test")
    payloads = _event_payloads(conn, "BENCHMARK_IMPORTED")
    assert len(payloads) == 2
    assert payloads[1]["duplicate_of"] == payloads[0]["run_id"]
    # history preserved: two distinct runs, both still queryable
    assert len(benchmark.list_runs(conn)) == 2


def test_changed_value_upserts_score_but_keeps_runs(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path, data=_doc())
    benchmark.import_file(conn, path, submitter="test")
    changed = _doc(results=[{"provider": "OpenAI", "model": "gpt-4",
                             "metric": "accuracy", "raw_value": 90.0}])
    path2 = _write(tmp_path, name="r2.json", data=changed)
    benchmark.import_file(conn, path2, submitter="test")
    score = conn.execute("SELECT * FROM scores").fetchone()
    assert score["value"] == 90.0  # upserted, not duplicated
    assert len(benchmark.list_runs(conn)) == 2
    updated = _event_payloads(conn, "SCORE_UPDATED")
    assert len(updated) == 1


# ---------------------------------------------------------------------------
# listing
# ---------------------------------------------------------------------------

def test_list_runs_empty(conn):
    assert benchmark.list_runs(conn) == []


def test_list_run_results_unknown_run(conn):
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.list_run_results(conn, 999)


def test_list_runs_show_result_counts(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path)
    benchmark.import_file(conn, path, submitter="test")
    runs = benchmark.list_runs(conn)
    assert len(runs) == 1
    assert runs[0]["result_count"] == 1


def test_import_requires_submitter(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path)
    with pytest.raises(benchmark.BenchmarkError):
        benchmark.import_file(conn, path, submitter="")


def test_name_override(conn, tmp_path):
    _seed_model(conn)
    path = _write(tmp_path)
    summary = benchmark.import_file(conn, path, submitter="test", name="mmlu-extra")
    assert summary["name"] == "mmlu-extra"
    assert benchmark.get_run(conn, summary["run_id"])["name"] == "mmlu-extra"
