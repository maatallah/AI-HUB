"""Shared read-only adapter (Phase 5).

``connectors/adapter.py`` is the single, stable read-only application
interface used by both connectors (MCP server and VS Code extension).

Design rules (PHASE5-CONNECTORS-SPEC sections 4-5):

  * Every function delegates to an existing, verified Phase 1-4 public API -
    the adapter executes no SQL and duplicates no decision logic.
  * Functions receive an already-open SQLite connection and return plain
    dict/list structures (JSON-serializable) so connectors never touch
    database internals or dataclass internals.
  * The adapter never mutates state: no writes, no events, no provenance
    (Constitution Articles 1, 5).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Optional, Sequence

from core import providers
from dashboard import engine as dashboard_engine
from dashboard import history as dashboard_history
from dashboard import reports as dashboard_reports
from fallback import build_chain
from monitoring import availability as availability_mod
from recommendation import recommend

__all__ = [
    "availability_history",
    "dashboard_report",
    "fallback_chain",
    "model_scores",
    "provider_list",
    "provider_status",
    "recommend_top",
    "score_history",
]


def _rows_to_dicts(rows: Sequence[Any]) -> list:
    """Convert ``sqlite3.Row`` sequences held by engine views to ``dict``."""
    return [dict(row) for row in rows]


def provider_status(conn) -> dict:
    """Provider view plus availability, both read-only."""
    providers_rows = _rows_to_dicts(dashboard_engine.provider_view(conn))
    availability_rows = _rows_to_dicts(availability_mod.list_availability(conn))
    return {"providers": providers_rows, "availability": availability_rows}


def model_scores(conn, model_id: Optional[int] = None) -> list:
    """Current scores (reuses ``scoring.list_scores`` semantics)."""
    return _rows_to_dicts(dashboard_engine.score_view(conn, model_id=model_id))


def recommend_top(
    conn,
    task: str,
    profile: str = "coding",
    limit: Optional[int] = None,
) -> list:
    """Ranked recommendations (read-only; never records provenance)."""
    return [
        asdict(r)
        for r in recommend(conn, task, profile=profile, limit=limit)
    ]


def fallback_chain(
    conn,
    task: str,
    profile: str = "coding",
    max_chain_length: int = 5,
) -> dict:
    """Priority-ordered fallback chain as a JSON-serializable structure."""
    chain = build_chain(conn, task, profile=profile, max_chain_length=max_chain_length)
    return {
        "task": chain.task,
        "profile": chain.profile,
        "max_chain_length": chain.max_chain_length,
        "primary": asdict(chain.primary) if chain.primary else None,
        "fallbacks": [asdict(r) for r in chain.fallbacks],
    }


def dashboard_report(
    conn,
    name: str,
    limit: int = 100,
    generated_at: Optional[str] = None,
) -> str:
    """Render a named dashboard report via``REPORT_BUILDERS``."""
    try:
        builder = dashboard_reports.REPORT_BUILDERS[name]
    except KeyError:
        raise ValueError(
            "Unknown report {!r}; available: {}".format(
                name, ", ".join(sorted(dashboard_reports.REPORT_BUILDERS))
            )
        )
    if name == "recommendations":
        return builder(conn, limit=limit, generated_at=generated_at)
    return builder(conn, generated_at=generated_at)


def score_history(
    conn,
    model_id: int,
    dimension: Optional[str] = None,
    limit: int = 1000,
) -> list:
    """Reconstructed per-model score series as plain records."""
    return list(
        dashboard_history.score_history(conn, model_id, dimension=dimension, limit=limit)
    )


def availability_history(
    conn,
    provider_id: Optional[int] = None,
    limit: int = 1000,
) -> list:
    """Reconstructed availability/health series as plain records."""
    return list(
        dashboard_history.availability_history(conn, provider_id=provider_id, limit=limit)
    )


def provider_list(conn, status: Optional[str] = None) -> list:
    """Provider list (optionally filtered by status) as plain records."""
    return _rows_to_dicts(providers.list_providers(conn, status=status))