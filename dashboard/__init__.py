"""AI-Hub dashboard (Phase 4).

Read-only dashboard aggregation views, deterministic plain-text report
builders and append-only event-derived history (v1.2 Section 18). None of
these modules write to the database (Constitution Article 1).
"""

from __future__ import annotations

from dashboard.engine import (
    OVERVIEW_STATUSES,
    event_view,
    overview,
    provider_view,
    recommendation_view,
    score_view,
)
from dashboard.history import (
    AVAILABILITY_EVENT_TYPES,
    SCORE_EVENT_TYPES,
    availability_history,
    score_history,
)
from dashboard.reports import (
    report_monitoring,
    report_overview,
    report_providers,
    report_recommendations,
    report_scores,
)

__all__ = [
    "AVAILABILITY_EVENT_TYPES",
    "OVERVIEW_STATUSES",
    "SCORE_EVENT_TYPES",
    "availability_history",
    "event_view",
    "overview",
    "provider_view",
    "recommendation_view",
    "report_monitoring",
    "report_overview",
    "report_providers",
    "report_recommendations",
    "report_scores",
    "score_history",
    "score_view",
]
