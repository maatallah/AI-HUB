"""Score ingestion into the ``scores`` table (Phase 3).

Stores explicit scores with value (0-100), confidence (0-1), source and
scored_at (v1.2 Section 1.2/1.3). The ``scores`` table holds the current value
per (model, dimension) per ADR-0001. Every insert/update is recorded as an
append-only event (SCORE_RECORDED / SCORE_UPDATED) for history and
traceability (Constitution Articles 5, 8).

No score is ever fabricated: ingest only accepts explicitly supplied values.
"""

from __future__ import annotations

from typing import Optional

from core import events

#: Allowed score sources (v1.2 Section 1.3).
ALLOWED_SOURCES = ("MANUAL", "BENCHMARK", "AUTOMATED_TEST", "USER_FEEDBACK", "OFFICIAL_INFORMATION")


class ScoreError(ValueError):
    """Raised when a score operation violates the rules."""


def _validate_dimension(dimension: str) -> str:
    if not dimension or not str(dimension).strip():
        raise ScoreError("Dimension is required.")
    return str(dimension).strip()


def _validate_value(value) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScoreError("Score value must be a number.")
    value = float(value)
    if not (0.0 <= value <= 100.0):
        raise ScoreError("Score value must be between 0 and 100 (v1.2 Section 3).")
    return value


def _validate_confidence(confidence) -> Optional[float]:
    if confidence is None:
        return None
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ScoreError("Confidence must be a number between 0 and 1.")
    confidence = float(confidence)
    if not (0.0 <= confidence <= 1.0):
        raise ScoreError("Confidence must be between 0 and 1.")
    return confidence


def _validate_source(source: str) -> str:
    if source not in ALLOWED_SOURCES:
        raise ScoreError(
            f"Invalid source {source!r}. Allowed: {list(ALLOWED_SOURCES)} (v1.2 Section 1.3)."
        )
    return source


def _require_model(conn, model_id: int) -> None:
    row = conn.execute("SELECT id FROM models WHERE id = ?", (model_id,)).fetchone()
    if row is None:
        raise ScoreError(f"Model {model_id} not found.")


def set_score(
    conn,
    model_id: int,
    dimension: str,
    value,
    confidence=None,
    source: str = "MANUAL",
    scored_at: Optional[str] = None,
) -> dict:
    """Upsert the current score for a (model, dimension).

    Records SCORE_RECORDED (new) or SCORE_UPDATED (existing) events. Returns
    the stored row as a dict.
    """
    dimension = _validate_dimension(dimension)
    value = _validate_value(value)
    confidence = _validate_confidence(confidence)
    source = _validate_source(source)
    _require_model(conn, model_id)

    existing = conn.execute(
        "SELECT id, value, confidence, source FROM scores"
        " WHERE model_id = ? AND dimension = ?",
        (model_id, dimension),
    ).fetchone()

    try:
        if existing is None:
            if scored_at is None:
                conn.execute(
                    "INSERT INTO scores (model_id, dimension, value, confidence, source)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (model_id, dimension, value, confidence, source),
                )
            else:
                conn.execute(
                    "INSERT INTO scores (model_id, dimension, value, confidence, source, scored_at)"
                    " VALUES (?, ?, ?, ?, ?, ?)",
                    (model_id, dimension, value, confidence, source, scored_at),
                )
            conn.commit()
            events.record_event(
                conn,
                "SCORE_RECORDED",
                entity_type="model",
                entity_id=model_id,
                payload={
                    "dimension": dimension,
                    "value": value,
                    "confidence": confidence,
                    "source": source,
                },
            )
        else:
            if scored_at is None:
                conn.execute(
                    "UPDATE scores SET value = ?, confidence = ?, source = ?,"
                    " scored_at = datetime('now') WHERE id = ?",
                    (value, confidence, source, existing["id"]),
                )
            else:
                conn.execute(
                    "UPDATE scores SET value = ?, confidence = ?, source = ?,"
                    " scored_at = ? WHERE id = ?",
                    (value, confidence, source, scored_at, existing["id"]),
                )
            conn.commit()
            events.record_event(
                conn,
                "SCORE_UPDATED",
                entity_type="model",
                entity_id=model_id,
                payload={
                    "dimension": dimension,
                    "from": existing["value"],
                    "to": value,
                    "confidence": confidence,
                    "source": source,
                },
            )
    except Exception as exc:  # e.g. sqlite3.IntegrityError
        conn.rollback()
        raise ScoreError(f"Could not store score for model {model_id} dimension {dimension!r}: {exc}") from exc

    return dict(
        conn.execute(
            "SELECT * FROM scores WHERE model_id = ? AND dimension = ?",
            (model_id, dimension),
        ).fetchone()
    )


def list_scores(conn, model_id: Optional[int] = None):
    """List stored scores, optionally filtered by model, ordered by model + dimension."""
    if model_id is None:
        return conn.execute(
            "SELECT s.*, m.model_identifier, p.name AS provider_name"
            " FROM scores s"
            " JOIN models m ON m.id = s.model_id"
            " JOIN providers p ON p.id = m.provider_id"
            " ORDER BY p.name, m.model_identifier, s.dimension"
        ).fetchall()
    return conn.execute(
        "SELECT s.*, m.model_identifier, p.name AS provider_name"
        " FROM scores s"
        " JOIN models m ON m.id = s.model_id"
        " JOIN providers p ON p.id = m.provider_id"
        " WHERE s.model_id = ?"
        " ORDER BY s.dimension",
        (model_id,),
    ).fetchall()
