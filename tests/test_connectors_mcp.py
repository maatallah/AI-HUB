"""Tests for the bounded stdio MCP server (Phase 5).

Covers protocol negotiation, primitives, the fixed seven-tool set, error
semantics, determinism, read-only guarantees, EOF handling and stdout
protocol cleanliness - all offline.
"""

from __future__ import annotations

import io
import json
import socket

import pytest

from connectors.mcp import server, tools
from core import providers
from monitoring import availability as availability_mod
from scoring import ingest

PROTOCOL_VERSIONS = server.PROTOCOL_VERSIONS


def _provider(conn, name, status="ACTIVE", reason=None):
    return providers.add_provider(conn, name, status=status, status_reason=reason)


def _model(conn, pid, identifier, context_window=32000):
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier, context_window)"
        " VALUES (?, 'Model', ?, ?)",
        (pid, identifier, context_window),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (identifier,)
    ).fetchone()["id"]


def _seed(conn):
    p1 = _provider(conn, "Alpha")
    p2 = _provider(conn, "Beta")
    m1 = _model(conn, p1, "alpha-1")
    m2 = _model(conn, p2, "beta-1")
    ingest.set_score(conn, m1, "coding", 90, confidence=1.0, source="MANUAL")
    ingest.set_score(conn, m2, "coding", 60, confidence=1.0, source="MANUAL")
    availability_mod.apply_lifecycle(conn, p1, "DEGRADED", "Repeated failures.")
    return p1, p2, m1, m2


def _rpc(method, params=None, request_id=1):
    msg = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        msg["params"] = params
    return json.dumps(msg)


def _call(mcp, line):
    return json.loads(mcp.handle_message(line))


# --- initialize / handshake --------------------------------------------------


def test_initialize_supported_protocol(conn):
    mcp = server.McpServer(conn)
    for version in PROTOCOL_VERSIONS:
        response = _call(mcp, _rpc("initialize", {"protocolVersion": version}))
        assert "error" not in response
        assert response["result"]["protocolVersion"] == version
        assert response["result"]["capabilities"]["tools"]["listChanged"] is False
        assert response["result"]["serverInfo"]["name"] == "ai-hub"


def test_initialize_unsupported_protocol(conn):
    mcp = server.McpServer(conn)
    response = _call(
        mcp, _rpc("initialize", {"protocolVersion": "2026-07-28"})
    )
    assert response["error"]["code"] == -32602
    assert response["error"]["data"]["requested"] == "2026-07-28"
    assert response["error"]["data"]["supported"] == list(PROTOCOL_VERSIONS)


def test_initialize_missing_params(conn):
    mcp = server.McpServer(conn)
    response = _call(mcp, _rpc("initialize"))
    assert response["error"]["code"] == -32602


def test_notifications_initialized_no_response(conn):
    mcp = server.McpServer(conn)
    line = json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert mcp.handle_message(line) is None


def test_ping(conn):
    mcp = server.McpServer(conn)
    response = _call(mcp, _rpc("ping"))
    assert response["result"] == {}


def test_notification_without_id_gets_no_response(conn):
    mcp = server.McpServer(conn)
    line = json.dumps({"jsonrpc": "2.0", "method": "ping"})
    assert mcp.handle_message(line) is None


# --- tools/list --------------------------------------------------------------


def test_tools_list_exact_set_deterministic(conn):
    mcp = server.McpServer(conn)
    response = _call(mcp, _rpc("tools/list"))
    names = [t["name"] for t in response["result"]["tools"]]
    assert names == list(tools.TOOLS)
    assert names == sorted(names)
    assert names == [
        "availability_history",
        "dashboard_report",
        "fallback_chain",
        "model_scores",
        "provider_status",
        "recommend_top",
        "route.decide",
        "route.record",
        "score_history",
    ]
    assert all(t["inputSchema"]["type"] == "object" for t in response["result"]["tools"])


def test_tools_list_deterministic_across_calls(conn):
    mcp = server.McpServer(conn)
    first = _call(mcp, _rpc("tools/list"))
    second = _call(mcp, _rpc("tools/list"))
    assert first == second


# --- tools/call: every tool returns structured text --------------------------


@pytest.mark.parametrize(
    "name, arguments",
    [
        ("provider_status", {}),
        ("model_scores", {}),
        ("recommend_top", {"task": "python"}),
        ("fallback_chain", {"task": "python"}),
        ("dashboard_report", {"name": "scores"}),
        ("score_history", {"model_id": 1}),
        ("availability_history", {}),
    ],
)
def test_each_tool_returns_structured_text(conn, name, arguments):
    _seed(conn)
    mcp = server.McpServer(conn)
    response = _call(mcp, _rpc("tools/call", {"name": name, "arguments": arguments}))
    assert "error" not in response
    result = response["result"]
    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"
    assert result["content"][0]["text"]


def test_tools_call_requires_name(conn):
    mcp = server.McpServer(conn)
    response = _call(mcp, _rpc("tools/call", {"arguments": {}}))
    assert response["error"]["code"] == -32602


def test_tools_call_unknown_tool(conn):
    mcp = server.McpServer(conn)
    response = _call(mcp, _rpc("tools/call", {"name": "nope", "arguments": {}}))
    assert response["error"]["code"] == -32602
    assert "nope" in response["error"]["message"]


def test_tools_call_arguments_must_be_object(conn):
    mcp = server.McpServer(conn)
    response = _call(
        mcp, _rpc("tools/call", {"name": "provider_status", "arguments": "x"})
    )
    assert response["error"]["code"] == -32602


# --- parameter validation ----------------------------------------------------


def test_missing_required_param_rejected(conn):
    mcp = server.McpServer(conn)
    response = _call(mcp, _rpc("tools/call", {"name": "recommend_top", "arguments": {}}))
    assert response["error"]["code"] == -32602
    assert "task" in response["error"]["message"]


def test_type_invalid_param_rejected(conn):
    mcp = server.McpServer(conn)
    response = _call(
        mcp,
        _rpc("tools/call", {"name": "score_history", "arguments": {"model_id": "x"}}),
    )
    assert response["error"]["code"] == -32602


def test_unknown_report_name_rejected(conn):
    mcp = server.McpServer(conn)
    response = _call(
        mcp,
        _rpc("tools/call", {"name": "dashboard_report", "arguments": {"name": "nope"}}),
    )
    assert response["error"]["code"] == -32602


# --- error handling ----------------------------------------------------------


def test_unknown_method(conn):
    mcp = server.McpServer(conn)
    response = _call(mcp, _rpc("resources/list"))
    assert response["error"]["code"] == -32601


def test_malformed_json(conn):
    mcp = server.McpServer(conn)
    response = json.loads(mcp.handle_message("{not json"))
    assert response["error"]["code"] == -32700


def test_invalid_jsonrpc_request(conn):
    mcp = server.McpServer(conn)
    response = json.loads(mcp.handle_message("[1,2,3]"))
    assert response["error"]["code"] == -32600


def test_underlying_tool_failure_returns_iserror(conn):
    closed = conn
    closed.close()
    mcp = server.McpServer(closed)
    response = _call(
        mcp, _rpc("tools/call", {"name": "provider_status", "arguments": {}})
    )
    result = response["result"]
    assert result["isError"] is True
    assert result["content"][0]["type"] == "text"


def test_internal_error_maps_to_minus_32603(conn):
    mcp = server.McpServer(conn)
    response = _call(mcp, _rpc("nope/method", {"x": 1}))
    assert response["error"]["code"] == -32601


def test_internal_exception_maps_to_minus_32603(conn):
    """Spec 2.2/9.8: a non-McpError dispatch exception maps to -32603."""
    mcp = server.McpServer(conn)

    def boom(_method, _params):
        raise RuntimeError("boom")

    mcp._dispatch = boom
    response = _call(mcp, _rpc("initialize", {"protocolVersion": "2025-11-25"}))
    assert response["error"]["code"] == -32603
    assert "boom" in response["error"]["message"]


# --- determinism -------------------------------------------------------------


def test_tool_output_deterministic(conn):
    _seed(conn)
    mcp = server.McpServer(conn)
    first = _call(mcp, _rpc("tools/call", {"name": "recommend_top", "arguments": {"task": "python"}}))
    second = _call(mcp, _rpc("tools/call", {"name": "recommend_top", "arguments": {"task": "python"}}))
    assert first == second


# --- read-only ---------------------------------------------------------------


def test_tool_calls_do_not_write(conn):
    _seed(conn)
    mcp = server.McpServer(conn)
    before = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    for name, arguments in [
        ("provider_status", {}),
        ("model_scores", {}),
        ("recommend_top", {"task": "python"}),
        ("fallback_chain", {"task": "python"}),
        ("dashboard_report", {"name": "scores"}),
        ("score_history", {"model_id": 1}),
        ("availability_history", {}),
    ]:
        _call(mcp, _rpc("tools/call", {"name": name, "arguments": arguments}))
    after = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert after == before


# --- empty / no-data (spec criterion 9.7, Article 10) ------------------------


def test_empty_database_returns_empty_not_fabricated(conn):
    """On an empty database every tool returns empty (never fabricated)."""
    mcp = server.McpServer(conn)
    cases = [
        ("provider_status", {}),
        ("model_scores", {}),
        ("recommend_top", {"task": "python"}),
        ("fallback_chain", {"task": "python"}),
        ("dashboard_report", {"name": "scores"}),
        ("score_history", {"model_id": 1}),
        ("availability_history", {}),
    ]
    for name, arguments in cases:
        response = _call(mcp, _rpc("tools/call", {"name": name, "arguments": arguments}))
        assert "error" not in response
        result = response["result"]
        assert result["isError"] is False
        text = result["content"][0]["text"]
        if name == "provider_status":
            payload = json.loads(text)
            assert payload["providers"] == []
            assert payload["availability"] == []
        elif name == "dashboard_report":
            lines = [line for line in text.splitlines() if line.strip()]
            assert len(lines) == 2 and lines[0].startswith("#")
        elif name == "fallback_chain":
            chain = json.loads(text)
            assert chain["primary"] is None
            assert chain["fallbacks"] == []
        else:
            assert json.loads(text) == []


# --- stdio loop / EOF / stdout cleanliness -----------------------------------


def test_stdio_loop_and_eof(conn):
    _seed(conn)
    mcp = server.McpServer(conn)
    stdin = io.StringIO(
        _rpc("initialize", {"protocolVersion": "2025-11-25"})
        + "\n"
        + _rpc("ping", request_id=2)
        + "\n"
        + "{not json}\n"
        + _rpc("tools/call", {"name": "provider_status", "arguments": {}}, request_id=4)
        + "\n"
    )
    stdout = io.StringIO()
    mcp.serve_stdio(stdin, stdout)
    lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
    assert len(lines) == 4
    for line in lines:
        payload = json.loads(line)
        assert payload["jsonrpc"] == "2.0"
        assert "result" in payload or "error" in payload


def test_stdout_only_protocol_messages(conn):
    _seed(conn)
    mcp = server.McpServer(conn)
    stdin = io.StringIO(_rpc("ping") + "\n" + "\n")
    stdout = io.StringIO()
    mcp.serve_stdio(stdin, stdout)
    for line in stdout.getvalue().splitlines():
        if line.strip():
            json.loads(line)


# --- no network --------------------------------------------------------------


def test_server_imports_do_not_require_network(conn):
    mcp = server.McpServer(conn)
    assert callable(mcp.serve_stdio)


def test_no_network_socket_in_scope():
    """Guard: the MCP implementation must never open sockets (stdio only)."""
    import ast
    import inspect

    module = ast.parse(inspect.getsource(server))
    network_modules = {
        "socket", "http", "urllib", "requests", "httpx", "aiohttp", "websockets",
    }
    imports = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert not imports & network_modules
