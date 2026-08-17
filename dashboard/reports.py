"""Deterministic dashboard report builders (Phase 4).

Reports are plain-text/tab-separated so they are grep-able and
connector-safe (v1.2 Section 18.2; approved PHASE4-IMPLEMENTATION-PLAN D-1).
There is no GUI in Phase 4.

Every report is self-describing (column headers) and deterministic: explicit
columns and ordering with no hidden sorting (Constitution Article 7). A
generated-at timestamp is optional and injected by the caller so tests pass a
fixed value, preserving deterministic output.
"""

from __future__ import annotations

from typing import Optional

from dashboard import engine


def _render_table(title: str, headers, rows, generated_at: Optional[str]) -> str:
    """Render a self-describing tab-separated table with a title."""
    lines = [f"# {title}"]
    if generated_at is not None:
        lines.append(f"# generated_at: {generated_at}")
    lines.append("\t".join(headers))
    for row in rows:
        lines.append(
            "\t".join(
                "" if row[h] is None else str(row[h]) for h in headers
            )
        )
    return "\n".join(lines) + "\n"


def report_overview(conn, generated_at: Optional[str] = None) -> str:
    """Headline dashboard summary (counts and status breakdown)."""
    data = engine.overview(conn)
    lines = ["# dashboard overview"]
    if generated_at is not None:
        lines.append(f"# generated_at: {generated_at}")
    lines.append(f"total_providers\t{data['total_providers']}")
    lines.append(f"total_models\t{data['total_models']}")
    lines.append(f"scored_models\t{data['scored_models']}")
    lines.append(f"scored_providers\t{data['scored_providers']}")
    for status in engine.OVERVIEW_STATUSES:
        lines.append(f"{status.lower()}_providers\t{data['status_counts'][status]}")
    return "\n".join(lines) + "\n"


def report_providers(conn, generated_at: Optional[str] = None) -> str:
    """Provider status table: status, availability, model/score counts."""
    headers = (
        "id",
        "name",
        "status",
        "availability_state",
        "consecutive_failures",
        "model_count",
        "score_count",
    )
    return _render_table(
        "providers", headers, engine.provider_view(conn), generated_at
    )


def report_scores(conn, generated_at: Optional[str] = None) -> str:
    """Score coverage summary plus the full score table."""
    headers = (
        "provider_name",
        "model_identifier",
        "dimension",
        "value",
        "confidence",
        "source",
        "scored_at",
    )
    return _render_table(
        "scores", headers, engine.score_view(conn), generated_at
    )


def report_recommendations(conn, limit: int = 100, generated_at: Optional[str] = None) -> str:
    """Provenance summary: recent recommendation records."""
    headers = (
        "requested_at",
        "profile",
        "task",
        "provider_name",
        "model_identifier",
        "decision_version",
        "confidence",
    )
    return _render_table(
        "recommendations", headers, engine.recommendation_view(conn, limit=limit), generated_at
    )


def report_monitoring(conn, generated_at: Optional[str] = None) -> str:
    """Availability/health summary from the monitoring engine."""
    headers = (
        "provider_name",
        "state",
        "reason",
        "consecutive_failures",
        "last_success",
        "last_failure",
    )
    from monitoring import availability

    return _render_table(
        "monitoring", headers, availability.list_availability(conn), generated_at
    )


#: Available report names mapped to their builders (used by the CLI).
REPORT_BUILDERS = {
    "providers": report_providers,
    "scores": report_scores,
    "recommendations": report_recommendations,
    "monitoring": report_monitoring,
    "overview": report_overview,
}
