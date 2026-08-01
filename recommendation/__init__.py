"""Recommendation engine (Phase 3).

Public API:
  * ``recommend`` - deterministic, explainable model ranking.
  * ``profiles`` - built-in + custom profile handling.
  * ``build_explanation`` - human-readable explanation (Article 4).
"""

from __future__ import annotations

from recommendation.engine import ELIGIBLE_STATUSES, Recommendation, RecommendationError, recommend
from recommendation.explain import build_explanation
from recommendation.profiles import ProfileError, get_profile, list_profiles, set_custom_profile
from recommendation.provenance import ProvenanceError, list_recommendations, record_recommendation

__all__ = [
    "ELIGIBLE_STATUSES",
    "ProfileError",
    "ProvenanceError",
    "Recommendation",
    "RecommendationError",
    "build_explanation",
    "get_profile",
    "list_profiles",
    "list_recommendations",
    "recommend",
    "record_recommendation",
    "set_custom_profile",
]
