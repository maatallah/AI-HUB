"""Dashboard aggregation engine (Phase 4).

Read-only views over providers, models, scores, availability,
recommendations and events (v1.2 Section 18.1). The dashboard never mutates
the database (Constitution Article 1).

Every view is deterministic: fixed columns and explicit ordering, with no
reliance on rowid order (Constitution Article 7). Empty inputs produce empty
(not fabricated) results (Constitution Article 10).
"""

from __future__ import annotations

from typing import Optional, Sequence

#: Provider statuses counted by :func:`overview` (v1.2 Section 5).
OVERVIEW_STATUSES = ("ACTIVE", "LIMITED", "DEGRADED", "OFFLINE")


def overview(conn) -> dict:
    """Headline counts: providers, models, scored models, status, coverage."""
    total_providers = conn.execute(
        "SELECT COUNT(*) AS n FROM providers"
    ).fetchone()["n"]
    total_models = conn.execute(
        "SELECT COUNT(*) AS n FROM models"
    ).fetchone()["n"]
    scored_models = conn.execute(
        "SELECT COUNT(DISTINCT model_id) AS n FROM scores"
    ).fetchone()["n"]
    scored_providers = conn.execute(
        "SELECT COUNT(DISTINCT m.provider_id) AS n"
        " FROM scores s JOIN models m ON m.id = s.model_id"
    ).fetchone()["n"]

    status_counts = {}
    for status in OVERVIEW_STATUSES:
        status_counts[status] = conn.execute(
            "SELECT COUNT(*) AS n FROM providers WHERE status = ?", (status,)
        ).fetchone()["n"]

    return {
        "total_providers": total_providers,
        "total_models": total_models,
        "scored_models": scored_models,
        "scored_providers": scored_providers,
        "status_counts": status_counts,
    }


def provider_view(conn):
    """Per-provider: status, availability state, model and score counts.

    Ordered by provider name, then id. Uses the provider-level availability
    row (``model_id IS NULL``).
    """
    return conn.execute(
        "SELECT p.id, p.name, p.status,"
        "       a.state AS availability_state, a.consecutive_failures,"
        "       (SELECT COUNT(*) FROM models m WHERE m.provider_id = p.id)"
        "          AS model_count,"
        "       (SELECT COUNT(*) FROM scores s JOIN models m ON m.id = s.model_id"
        "         WHERE m.provider_id = p.id) AS score_count"
        " FROM providers p"
        " LEFT JOIN availability a ON a.provider_id = p.id AND a.model_id IS NULL"
        " ORDER BY p.name, p.id"
    ).fetchall()


def score_view(conn, model_id: Optional[int] = None):
    """Current scores joined with model and provider names (read-only).

    Reuses ``scoring.list_scores`` semantics (same columns and ordering)
    without any mutation.
    """
    from scoring import list_scores

    return list_scores(conn, model_id=model_id)


def recommendation_view(conn, limit: int = 100):
    """Provenance records ordered by ``requested_at`` desc.

    Reuses ``recommendation.list_recommendations`` (read-only).
    """
    from recommendation import list_recommendations

    return list_recommendations(conn, limit=limit)


def event_view(
    conn,
    event_type: Optional[str] = None,
    limit: int = 100,
) -> Sequence:
    """Append-only event log, newest first, optionally filtered by type.

    Mirrors ``core.events.list_events`` semantics (``ORDER BY id DESC``) with
    an additional ``event_type`` filter. Read-only.
    """
    if event_type is not None:
        return conn.execute(
            "SELECT * FROM events WHERE event_type = ? ORDER BY id DESC LIMIT ?",
            (event_type, limit),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
