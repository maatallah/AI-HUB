"""Tests for the dashboard report builders (determinism, formatting, read-only)."""

from __future__ import annotations

from core import providers
from dashboard import reports
from monitoring import availability as availability_mod
from recommendation import provenance
from scoring import ingest


def _add(conn, name="Acme", status="ACTIVE"):
    reason = None if status == "ACTIVE" else "for test"
    return providers.add_provider(conn, name, status=status, status_reason=reason)


def _model(conn, provider_id, model_identifier="acme-1"):
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier)"
        " VALUES (?, 'Acme Model', ?)",
        (provider_id, model_identifier),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (model_identifier,)
    ).fetchone()["id"]


def _dummy_recommendation(pid, mid, seq):
    from recommendation.engine import Recommendation

    return Recommendation(
        task="python",
        profile="coding",
        provider_id=pid,
        provider_name="Acme",
        model_id=mid,
        model_identifier="acme-1",
        final_score=90.0,
        dimensions={},
        breakdown={},
        confidence=0.9,
        explanation=f"test {seq}",
        flags=(),
    )


# --- overview report --------------------------------------------------------


def test_report_overview_empty(conn):
    text = reports.report_overview(conn)
    assert "total_providers\t0" in text
    assert "total_models\t0" in text
    assert "scored_models\t0" in text
    assert "active_providers\t0" in text


def test_report_overview_counts(conn):
    _add(conn, name="Alpha", status="ACTIVE")
    _add(conn, name="Beta", status="LIMITED")
    text = reports.report_overview(conn)
    assert "total_providers\t2" in text
    assert "active_providers\t1" in text
    assert "limited_providers\t1" in text


# --- providers report -------------------------------------------------------


def test_report_providers_headers_and_rows(conn):
    _add(conn, name="Alpha")
    text = reports.report_providers(conn)
    assert text.startswith("# providers")
    assert "id\tname\tstatus\tavailability_state" in text
    assert "1\tAlpha\tACTIVE" in text


def test_report_providers_empty(conn):
    text = reports.report_providers(conn)
    assert "id\tname\tstatus" in text
    # title + header only, no data rows
    assert text.count("\n") == 2
    assert not text.splitlines()[-1].startswith(("1\t", "2\t"))


def test_report_providers_ordered(conn):
    _add(conn, name="Zeta")
    _add(conn, name="Alpha")
    text = reports.report_providers(conn)
    lines = text.splitlines()
    data = [ln for ln in lines if ln and not ln.startswith("#")]
    names = [ln.split("\t")[1] for ln in data[1:]]
    assert names == ["Alpha", "Zeta"]


# --- scores report ----------------------------------------------------------


def test_report_scores_headers(conn):
    _add(conn, name="Acme")
    text = reports.report_scores(conn)
    assert text.startswith("# scores")
    assert "provider_name\tmodel_identifier\tdimension\tvalue" in text


def test_report_scores_rows(conn):
    pid = _add(conn, name="Acme")
    mid = _model(conn, pid)
    ingest.set_score(conn, mid, "coding", 85, source="MANUAL")
    text = reports.report_scores(conn)
    assert "Acme\tacme-1\tcoding\t85.0" in text


# --- recommendations report -------------------------------------------------


def test_report_recommendations_empty(conn):
    text = reports.report_recommendations(conn)
    assert text.startswith("# recommendations")
    assert "requested_at\tprofile\ttask\tprovider_name" in text


def test_report_recommendations_rows(conn):
    pid = _add(conn, name="Acme")
    mid = _model(conn, pid)
    provenance.record_recommendation(
        conn, _dummy_recommendation(pid, mid, 1), decision_version="3.0.0"
    )
    text = reports.report_recommendations(conn)
    assert "coding\tpython\tAcme\tacme-1" in text


# --- monitoring report ------------------------------------------------------


def test_report_monitoring_empty(conn):
    text = reports.report_monitoring(conn)
    assert text.startswith("# monitoring")
    assert "provider_name\tstate\treason" in text


def test_report_monitoring_rows(conn):
    pid = _add(conn, name="Acme")
    availability_mod.update_availability(conn, pid, "OK")
    text = reports.report_monitoring(conn)
    assert "Acme\tACTIVE" in text


# --- determinism ------------------------------------------------------------


def test_reports_deterministic(conn):
    pid = _add(conn, name="Zeta")
    pid_b = _add(conn, name="Alpha")
    _model(conn, pid, "z-1")
    mid = _model(conn, pid_b, "a-1")
    ingest.set_score(conn, mid, "coding", 80, source="MANUAL")
    availability_mod.update_availability(conn, pid_b, "OK")

    builders = [
        reports.report_overview,
        reports.report_providers,
        reports.report_scores,
        reports.report_monitoring,
    ]
    for builder in builders:
        first = builder(conn)
        second = builder(conn)
        assert first == second, builder.__name__


def test_generated_at_injected(conn):
    text = reports.report_overview(conn, generated_at="2026-01-01T00:00:00")
    assert "# generated_at: 2026-01-01T00:00:00" in text
    # absent by default -> no timestamp line
    plain = reports.report_overview(conn)
    assert "generated_at" not in plain


# --- read-only --------------------------------------------------------------


def test_reports_do_not_write(conn):
    _add(conn, name="Acme")
    before = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    for builder in (
        reports.report_overview,
        reports.report_providers,
        reports.report_scores,
        reports.report_monitoring,
        reports.report_recommendations,
    ):
        builder(conn)
    after = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert after == before
