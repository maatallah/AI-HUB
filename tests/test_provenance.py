"""Tests for recommendation provenance records."""

from __future__ import annotations

import json

import pytest

from core import events, providers
from recommendation import list_recommendations, recommend, record_recommendation
from scoring import ingest


def _provider(conn, name):
    return providers.add_provider(conn, name, status="ACTIVE")


def _model(conn, pid, identifier):
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier)"
        " VALUES (?, ?, ?)",
        (pid, identifier, identifier),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (identifier,)
    ).fetchone()["id"]


def _top_recommendation(conn):
    pid = _provider(conn, "Alpha")
    mid = _model(conn, pid, "alpha-1")
    ingest.set_score(conn, mid, "coding", 90, confidence=1.0, source="MANUAL")
    ingest.set_score(conn, mid, "reasoning", 80, confidence=1.0, source="MANUAL")
    return recommend(conn, "python")[0]


def test_record_recommendation_writes_row(conn):
    rec = _top_recommendation(conn)
    row = record_recommendation(conn, rec, decision_version="3.0.0")
    assert row["task"] == "python"
    assert row["profile"] == "coding"
    assert row["provider_id"] == rec.provider_id
    assert row["model_id"] == rec.model_id
    assert row["decision_version"] == "3.0.0"
    assert row["confidence"] == rec.confidence
    assert row["explanation"] == rec.explanation


def test_record_recommendation_breakdown_json(conn):
    rec = _top_recommendation(conn)
    row = record_recommendation(conn, rec, decision_version="3.0.0")
    breakdown = json.loads(row["score_breakdown"])
    assert "coding" in breakdown
    assert "contribution" in breakdown["coding"]
    assert "source" in breakdown["coding"]


def test_record_recommendation_records_event(conn):
    rec = _top_recommendation(conn)
    record_recommendation(conn, rec, decision_version="3.0.0")
    types = [e["event_type"] for e in events.list_events(conn)]
    assert "RECOMMENDATION_CREATED" in types


def test_record_recommendation_requires_version(conn):
    rec = _top_recommendation(conn)
    with pytest.raises(Exception):
        record_recommendation(conn, rec, decision_version="")


def test_list_recommendations_newest_first(conn):
    rec1 = _top_recommendation(conn)
    record_recommendation(conn, rec1, decision_version="3.0.0")
    record_recommendation(conn, rec1, decision_version="3.0.0")
    rows = list_recommendations(conn)
    assert len(rows) == 2
    assert rows[0]["provider_name"] == "Alpha"


def test_recommendations_have_unique_ids(conn):
    rec1 = _top_recommendation(conn)
    a = record_recommendation(conn, rec1, decision_version="3.0.0")
    b = record_recommendation(conn, rec1, decision_version="3.0.0")
    assert a["id"] != b["id"]
