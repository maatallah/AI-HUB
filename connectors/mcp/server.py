"""Bounded stdio MCP server (Phase 5).

Implements a deliberately bounded MCP subset (PHASE5-CONNECTORS-SPEC section
2): legacy-era handshake over stdio, JSON-RPC 2.0, newline-delimited UTF-8,
Tools capability only. This module performs protocol dispatch, argument
validation and result/error serialization - it contains NO AI-Hub decision
logic (all intelligence comes from ``connectors.adapter`` delegations).

Supported primitives: ``initialize``, ``notifications/initialized``, ``ping``,
``tools/list``, ``tools/call``.

Not supported: resources, prompts, sampling, roots, logging, completions,
batches, progress notifications, HTTP/SSE transports, modern-era
``2026-07-28``.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

from connectors.mcp import tools

#: Bounded legacy-era protocol revisions that may be negotiated.
PROTOCOL_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")

#: Server identity reported during the initialize handshake.
SERVER_INFO = {"name": "ai-hub", "version": "1.0.0"}

#: JSON-RPC 2.0 / MCP error codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class McpError(Exception):
    """A JSON-RPC error with a code, message and optional data."""

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class McpServer:
    """A stateful stdio MCP server bound to an open read-only connection."""

    def __init__(self, conn):
        self._conn = conn
        self._list_changed = False

    # -- JSON-RPC plumbing -------------------------------------------------

    def handle_message(self, message: str) -> Optional[str]:
        """Process one newline-delimited message; return a response line (or
        ``None`` for notifications / empty input)."""
        stripped = message.strip()
        if not stripped:
            return None
        try:
            request = json.loads(stripped)
        except json.JSONDecodeError:
            return self._error_response(None, PARSE_ERROR, "Parse error")
        if not isinstance(request, dict):
            return self._error_response(None, INVALID_REQUEST, "Invalid request")
        request_id = request.get("id")
        if "method" not in request or not isinstance(request["method"], str):
            return self._error_response(
                request_id, INVALID_REQUEST, "Invalid request"
            )
        method = request["method"]
        params = request.get("params")
        has_id = "id" in request
        try:
            result = self._dispatch(method, params)
        except McpError as exc:
            return self._error_response(request_id, exc.code, exc.message, exc.data)
        except Exception as exc:  # pragma: no cover - defensive
            return self._error_response(
                request_id, INTERNAL_ERROR, "Internal error: {}".format(exc)
            )
        if not has_id:
            return None
        return json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "result": result},
            ensure_ascii=False,
        )

    def _dispatch(self, method: str, params: Any) -> Any:
        if method == "initialize":
            return self._initialize(params)
        if method == "notifications/initialized":
            return None
        if method == "ping":
            return {}
        if method == "tools/list":
            return self._tools_list(params)
        if method == "tools/call":
            return self._tools_call(params)
        raise McpError(METHOD_NOT_FOUND, "Method not found: {}".format(method))

    # -- handshake ---------------------------------------------------------

    def _initialize(self, params: Any) -> dict:
        if not isinstance(params, dict):
            raise McpError(INVALID_PARAMS, "initialize params must be an object")
        requested = params.get("protocolVersion")
        if requested not in PROTOCOL_VERSIONS:
            raise McpError(
                INVALID_PARAMS,
                "Unsupported protocol version",
                data={"supported": list(PROTOCOL_VERSIONS), "requested": requested},
            )
        self._protocol_version = requested
        return {
            "protocolVersion": requested,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
            "instructions": (
                "Read-only AI-Hub intelligence boundary. Tools return "
                "structured text; connectors never write to AI-Hub data."
            ),
        }

    # -- tools -------------------------------------------------------------

    def _tools_list(self, params: Any) -> dict:
        if params is not None and not isinstance(params, dict):
            raise McpError(INVALID_PARAMS, "tools/list params must be an object")
        return {"tools": tools.tool_definitions(), "nextCursor": None}

    def _tools_call(self, params: Any) -> dict:
        if not isinstance(params, dict):
            raise McpError(INVALID_PARAMS, "tools/call params must be an object")
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not name:
            raise McpError(INVALID_PARAMS, "Missing or invalid tool name")
        if not isinstance(arguments, dict):
            raise McpError(INVALID_PARAMS, "Tool arguments must be an object")
        try:
            result = tools.call_tool(self._conn, name, arguments)
        except ValueError as exc:
            raise McpError(INVALID_PARAMS, str(exc))
        except Exception as exc:
            return {
                "content": [{"type": "text", "text": str(exc)}],
                "isError": True,
            }
        text = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        return {"content": [{"type": "text", "text": text}], "isError": False}

    # -- errors ------------------------------------------------------------

    def _error_response(self, request_id: Any, code: int, message: str, data: Any = None):
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return json.dumps(
            {"jsonrpc": "2.0", "id": request_id, "error": error},
            ensure_ascii=False,
        )

    # -- stdio loop --------------------------------------------------------

    def serve_stdio(self, stdin=None, stdout=None):
        """Read newline-delimited messages from stdin and write responses to
        stdout, flushing after every response. Diagnostics go to stderr."""
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            response = self.handle_message(line)
            if response is not None:
                stdout.write(response + "\n")
                stdout.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m connectors.mcp.server",
        description="Bounded read-only stdio MCP server for AI-Hub.",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to the AI-Hub SQLite database (default: database/ai_hub.db).",
    )
    args = parser.parse_args(argv)

    from database import database as db_util

    db_path = args.db or str(db_util.DEFAULT_DB_PATH)
    conn = db_util.connect(db_path)
    # Enforce read-only at the database level (query-only guard).
    conn.execute("PRAGMA query_only = ON")
    server = McpServer(conn)
    try:
        server.serve_stdio()
    finally:
        conn.close()


if __name__ == "__main__":
    main()