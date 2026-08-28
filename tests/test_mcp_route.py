"""Tests for the MCP routing decision tools (post-v1 M2)."""

from __future__ import annotations

import datetime

import pytest

from connectors import adapter
from connectors.mcp import tools
from core import providers
from recommendation.decision import (
    DecisionError,
    STATUS_CONSTRAINT_UNSATISFIABLE,
    STATUS_NO_CANDIDATE,
    STATUS_OK,
    build_decision_envelope,
)
from scoring import ingest

NOW = datetime.datetime(2026, 8, 28, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _seed(conn, name="Alpha", identifier="alpha-1", coding=90):
    p = providers.add_provider(conn, name, status="ACTIVE")
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier, context_window)"
        " VALUES (?, ?, ?, 32000)",
        (p, identifier, identifier),
    )
    conn.commit()
    m = conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (identifier,)
    ).fetchone()["id"]
    ingest.set_score(conn, m, "coding", coding, confidence=1.0, source="MANUAL")
    return p, m


# --- registration --------------------------------------------------------------


def test_route_decide_registered_in_tools_and_definitions():
    assert "route.decide" in tools.TOOLS
    names = [d["name"] for d in tools.tool_definitions()]
    assert "route.decide" in names


def test_route_record_registered_in_tools_and_definitions():
    assert "route.record" in tools.TOOLS
    names = [d["name"] for d in tools.tool_definitions()]
    assert "route.record" in names


# --- route.decide schema conformance -------------------------------------------


def test_route_decide_schema_conforms_to_contract():
    entry = next(d for d in tools.tool_definitions() if d["name"] == "route.decide")
    schema = entry["inputSchema"]
    props = schema["properties"]
    assert set(props) == {
        "task",
        "profile",
        "min_context_window",
        "required_capabilities",
        "allowed_providers",
        "denied_providers",
        "allowed_models",
        "denied_models",
        "max_stale_days",
        "limit",
    }
    assert "task" in schema["required"]
    assert schema["additionalProperties"] is False


def test_route_record_schema():
    entry = next(d for d in tools.tool_definitions() if d["name"] == "route.record")
    schema = entry["inputSchema"]
    assert "envelope" in schema["properties"]
    assert "envelope" in schema["required"]
    assert schema["additionalProperties"] is False


# --- delegation ----------------------------------------------------------------


def test_route_decide_delegates_to_adapter(conn):
    _seed(conn)
    result = tools.call_tool(conn, "route.decide", {"task": "python"})
    direct = adapter.route_decide(conn, "python")
    assert result == direct
    assert result["status"] == STATUS_OK


def test_route_decide_uses_full_vocabulary(conn):
    _, m = _seed(conn, "Acme", "acme-turbo", coding=90)
    result = tools.call_tool(
        conn,
        "route.decide",
        {
            "task": "python",
            "profile": "reasoning",
            "min_context_window": 4096,
            "required_capabilities": ["tool_calling", "json"],
            "allowed_providers": ["Acme"],
            "denied_providers": [],
            "allowed_models": ["acme-turbo"],
            "denied_models": [],
            "max_stale_days": 100,
            "limit": 5,
        },
    )
    req = result["request"]
    assert req["profile"] == "reasoning"
    assert req["constraints"]["min_context_window"] == 4096
    assert req["freshness"] == {"max_stale_days": 100}


def test_route_decide_no_candidate_via_tool(conn):
    result = tools.call_tool(conn, "route.decide", {"task": "python"})
    assert result["status"] == STATUS_NO_CANDIDATE


def test_route_decide_constraint_via_tool(conn):
    p, _ = _seed(conn)
    result = tools.call_tool(
        conn, "route.decide", {"task": "python", "denied_providers": [p]}
    )
    assert result["status"] == STATUS_CONSTRAINT_UNSATISFIABLE


def test_route_record_delegates_to_adapter(conn):
    _seed(conn)
    env = build_decision_envelope(conn, "python")
    result = tools.call_tool(conn, "route.record", {"envelope": env})
    rows = conn.execute("SELECT * FROM recommendations").fetchall()
    assert result["count"] == len(rows) == len(env["candidates"])
    assert set(result.keys()) == {"decision_id", "recorded_ids", "count"}


# --- invalid input / error behavior --------------------------------------------


def test_route_decide_requires_task(conn):
    with pytest.raises(ValueError):
        tools.call_tool(conn, "route.decide", {})
    with pytest.raises(ValueError):
        tools.call_tool(conn, "route.decide", {"task": ""})
    with pytest.raises(ValueError):
        tools.call_tool(conn, "route.decide", {"task": "  "})


def test_route_decide_rejects_wrong_types(conn):
    with pytest.raises(ValueError):
        tools.call_tool(conn, "route.decide", {"task": "python", "limit": "x"})
    with pytest.raises(ValueError):
        tools.call_tool(
            conn, "route.decide", {"task": "python", "required_capabilities": "tool_calling"}
        )
    with pytest.raises(ValueError):
        tools.call_tool(
            conn, "route.decide", {"task": "python", "min_context_window": "high"}
        )


def test_route_decide_propagates_decision_errors(conn):
    with pytest.raises(DecisionError):
        tools.call_tool(
            conn, "route.decide", {"task": "python", "required_capabilities": ["magic"]}
        )


def test_route_record_requires_envelope_object(conn):
    with pytest.raises(ValueError):
        tools.call_tool(conn, "route.record", {})
    with pytest.raises(ValueError):
        tools.call_tool(conn, "route.record", {"envelope": []})
    with pytest.raises(ValueError):
        tools.call_tool(conn, "route.record", {"envelope": "not-an-object"})


def test_route_record_propagates_validation_errors(conn):
    _seed(conn)
    env = build_decision_envelope(conn, "python")
    env["contract_version"] = "999"
    with pytest.raises(DecisionError):
        tools.call_tool(conn, "route.record", {"envelope": env})
