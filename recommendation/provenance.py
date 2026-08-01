"""Decision provenance for recommendations (Phase 3).

Every recommendation is recorded in the ``recommendations`` table (v1.2
Section 8) with the score breakdown, explanation, decision version and
confidence, plus an append-only RECOMMENDATION_CREATED event. This enables
auditing and comparison across AI-Hub versions (Constitution Articles 4, 8).
"""

from __future__ import annotations

import json
import uuid
from typing import Optional

from core import events
from recommendation.engine import Recommendation


class ProvenanceError(ValueError):
    """Raised when a provenance record cannot be written."""


def record_recommendation(
    conn,
    recommendation: Recommendation,
    decision_version: str,
) -> dict:
    """Persist a recommendation decision with full provenance.

    Returns the stored ``recommendations`` row as a dict. The id is a UUID;
    recommendation *content* remains deterministic (Article 7).
    """
    if not recommendation:
        raise ProvenanceError("A recommendation is required to record provenance.")
    if not decision_version or not str(decision_version).strip():
        raise ProvenanceError("decision_version is required.")

    rec_id = str(uuid.uuid4())
    breakdown = {
        dimension: {
            "value": round(info["value"], 4),
            "weight": round(info["weight"], 4),
            "contribution": round(info["contribution"], 4),
            "confidence": round(info["confidence"], 4),
            "source": info["source"],
        }
        for dimension, info in recommendation.breakdown.items()
    }
    try:
        conn.execute(
            "INSERT INTO recommendations"
            " (id, task, profile, provider_id, model_id, decision_version,"
            "  score_breakdown, explanation, confidence)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                rec_id,
                recommendation.task,
                recommendation.profile,
                recommendation.provider_id,
                recommendation.model_id,
                decision_version,
                json.dumps(breakdown, sort_keys=True),
                recommendation.explanation,
                recommendation.confidence,
            ),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise ProvenanceError(f"Could not record recommendation: {exc}") from exc

    events.record_event(
        conn,
        "RECOMMENDATION_CREATED",
        entity_type="model",
        entity_id=recommendation.model_id,
        payload={
            "recommendation_id": rec_id,
            "provider_id": recommendation.provider_id,
            "model_identifier": recommendation.model_identifier,
            "profile": recommendation.profile,
            "task": recommendation.task,
            "decision_version": decision_version,
            "final_score": recommendation.final_score,
            "confidence": recommendation.confidence,
        },
    )
    return dict(
        conn.execute(
            "SELECT * FROM recommendations WHERE id = ?", (rec_id,)
        ).fetchone()
    )


def list_recommendations(conn, limit: int = 100):
    """List provenance records, newest first, with provider/model names."""
    return conn.execute(
        "SELECT r.*, p.name AS provider_name, m.model_identifier"
        " FROM recommendations r"
        " JOIN providers p ON p.id = r.provider_id"
        " LEFT JOIN models m ON m.id = r.model_id"
        " ORDER BY r.requested_at DESC, r.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
