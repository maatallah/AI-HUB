"""Read-only MCP tool registry (Phase 5).

Each tool is a thin, stateless mapping from MCP arguments to a
``connectors.adapter`` call. Tools carry no decision logic: they validate
their inputs and delegate (PHASE5-CONNECTORS-SPEC section 5).
"""

from __future__ import annotations

from typing import Any

from connectors import adapter

ReportName = str


def _require_str(arguments: dict, name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def _require_int(arguments: dict, name: str) -> int:
    value = arguments.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer.")
    return value


def _optional_str(arguments: dict, name: str) -> Any:
    value = arguments.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string.")
    return value


def _optional_int(arguments: dict, name: str) -> Any:
    value = arguments.get(name)
    if value is None:
        return None
    return _require_int(arguments, name)


def _provider_status(conn, arguments: dict) -> dict:
    return adapter.provider_status(conn)


def _model_scores(conn, arguments: dict) -> list:
    return adapter.model_scores(conn, model_id=_optional_int(arguments, "model_id"))


def _recommend_top(conn, arguments: dict) -> list:
    task = _require_str(arguments, "task")
    profile = _optional_str(arguments, "profile") or "coding"
    return adapter.recommend_top(conn, task, profile=profile, limit=_optional_int(arguments, "limit"))


def _fallback_chain(conn, arguments: dict) -> dict:
    task = _require_str(arguments, "task")
    profile = _optional_str(arguments, "profile") or "coding"
    max_chain_length = _optional_int(arguments, "max_chain_length") or 5
    return adapter.fallback_chain(
        conn, task, profile=profile, max_chain_length=max_chain_length
    )


def _dashboard_report(conn, arguments: dict) -> str:
    name = _require_str(arguments, "name")
    limit = _optional_int(arguments, "limit") or 100
    generated_at = _optional_str(arguments, "generated_at")
    return adapter.dashboard_report(conn, name, limit=limit, generated_at=generated_at)


def _score_history(conn, arguments: dict) -> list:
    model_id = _require_int(arguments, "model_id")
    dimension = _optional_str(arguments, "dimension")
    limit = _optional_int(arguments, "limit") or 1000
    return adapter.score_history(conn, model_id, dimension=dimension, limit=limit)


def _availability_history(conn, arguments: dict) -> list:
    provider_id = _optional_int(arguments, "provider_id")
    limit = _optional_int(arguments, "limit") or 1000
    return adapter.availability_history(conn, provider_id=provider_id, limit=limit)


#: Fixed tool set (alphabetical by name for deterministic ``tools/list``).
_TOOL_DEFS = [
    {
        "name": "availability_history",
        "description": (
            "Reconstructed availability/health history for a provider "
            "(optional provider_id; optional limit). Read-only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider_id": {"type": "integer"},
                "limit": {"type": "integer"},
            },
            "additionalProperties": False,
        },
        "handler": _availability_history,
    },
    {
        "name": "dashboard_report",
        "description": (
            "Render a named dashboard report (overview, providers, scores, "
            "recommendations, monitoring) as text. Read-only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "limit": {"type": "integer"},
                "generated_at": {"type": "string"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
        "handler": _dashboard_report,
    },
    {
        "name": "fallback_chain",
        "description": (
            "Deterministic primary + fallback recommendation chain for a task. "
            "Read-only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "profile": {"type": "string"},
                "max_chain_length": {"type": "integer"},
            },
            "required": ["task"],
            "additionalProperties": False,
        },
        "handler": _fallback_chain,
    },
    {
        "name": "model_scores",
        "description": (
            "Current model scores (optionally filtered by model_id). Read-only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"model_id": {"type": "integer"}},
            "additionalProperties": False,
        },
        "handler": _model_scores,
    },
    {
        "name": "provider_status",
        "description": (
            "Provider view (status, availability, model/score counts) plus "
            "availability rows. Read-only."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": _provider_status,
    },
    {
        "name": "recommend_top",
        "description": (
            "Ranked read-only model recommendations for a task. Never records "
            "provenance."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "profile": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["task"],
            "additionalProperties": False,
        },
        "handler": _recommend_top,
    },
    {
        "name": "score_history",
        "description": (
            "Per-model score series (oldest first); optional dimension. Read-only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "model_id": {"type": "integer"},
                "dimension": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["model_id"],
            "additionalProperties": False,
        },
        "handler": _score_history,
    },
]

#: Public read-only view of the tool set (deterministic order).
TOOLS = tuple(d["name"] for d in _TOOL_DEFS)


def tool_definitions():
    """Return ``tools/list`` payload entries (name, description, inputSchema)."""
    return [
        {
            "name": d["name"],
            "description": d["description"],
            "inputSchema": d["inputSchema"],
        }
        for d in _TOOL_DEFS
    ]


def call_tool(conn, name: str, arguments: dict):
    """Validate and invoke a tool by name; returns its plain result.

    Raises ``ValueError`` for unknown tools and invalid arguments and lets
    adapter/engine exceptions propagate so the server maps them to errors or
    ``isError`` results.
    """
    for d in _TOOL_DEFS:
        if d["name"] == name:
            if arguments is None:
                arguments = {}
            return d["handler"](conn, arguments)
    raise ValueError(f"Unknown tool: {name}")