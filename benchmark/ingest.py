"""Benchmark result ingestion (Phase 6 Milestone 3, ADR-0006 / D-P3).

Ingests published benchmark results as provenance-backed, ``BENCHMARK``-
sourced scores. Every import records one ``benchmark_runs`` row (identity,
version, origin, retrieval metadata, content hash, submitter, documented
mapping) plus one ``benchmark_results`` row per raw metric value; mapped,
validated values update the normalized ``scores`` table through the existing
``scoring.ingest.set_score`` upsert (source ``BENCHMARK``).

Guarantees (per the Phase 6 proposal spec Section 3 and v1.2 Section 20.3):

* raw values and retrieval metadata are never lost and always remain
  queryable via ``benchmark_results`` (Article 10 - never fabricated)
* normalization to 0-100 is deterministic; the metric -> (dimension,
  formula) mapping is recorded on the run (Article 7)
* batch ingestion is atomic per file: any invalid row fails the whole
  import before anything is written; ``--dry-run`` validates without
  mutation (no partial writes)
* every successful import records a ``BENCHMARK_IMPORTED`` event (Article 8)
* replay of an identical file appends a NEW audited run and reports the
  previously-imported run (never silent); history is preserved (Article 5)
* secret-like keys are rejected and URLs sanitized (Article 6)

Curated file format (JSON, one file = one run):

    {
        "name": "mmlu",
        "version": "5-shot",
        "origin": "https://example.com/results.json",   # optional; defaults to file path
        "fetched_at": "2026-08-01T00:00:00Z",            # optional retrieval timestamp
        "run_date": "2026-08-01",                        # optional; scored_at if present
        "mapping": {
            "accuracy": {"dimension": "reasoning", "formula": "identity"},
            "exact_match": {"dimension": "reasoning", "formula": "fraction_to_percent"}
        },
        "results": [
            {"provider": "OpenAI", "model": "gpt-4", "metric": "accuracy",
             "raw_value": 86.4, "confidence": 0.9}
        ]
    }

Models are resolved by (provider name, model identifier) against the
existing registry; unknown providers/models fail the whole import (no
fabrication, D-P4 registry scope only). Every result metric must appear in
the run ``mapping`` so its deterministic normalized value (0-100) is always
computable.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import parse_qs, urlparse, urlunparse

from core import events
from scoring.ingest import set_score

#: Keywords that mark a payload key as a potential secret (mirrors
#: ``app/config.py.SECRET_KEYWORDS`` - Constitution Article 6).
from app.config import SECRET_KEYWORDS

#: Allowed keys on the top-level benchmark document.
VALID_TOP_KEYS = frozenset(
    {"name", "version", "origin", "fetched_at", "run_date", "mapping", "results"}
)

#: Allowed keys inside a result record.
VALID_RESULT_KEYS = frozenset(
    {"provider", "model", "metric", "raw_value", "confidence"}
)

#: Allowed keys inside a mapping entry (metric -> entry).
VALID_MAPPING_KEYS = frozenset({"dimension", "formula"})

#: Documented deterministic normalization formulas (value -> 0-100).
#: The exact formula applied per metric is recorded on the run mapping.
FORMULAS = frozenset({"identity", "fraction_to_percent"})


class BenchmarkError(ValueError):
    """Raised when a benchmark import violates the ingestion rules."""


def _apply_formula(formula: str, raw_value: float) -> float:
    """Deterministically normalize a raw value to 0-100."""
    if formula == "identity":
        norm = float(raw_value)
    elif formula == "fraction_to_percent":
        norm = float(raw_value) * 100.0
    else:
        raise BenchmarkError(
            f"Unknown normalization formula {formula!r}. Allowed: {sorted(FORMULAS)}."
        )
    if not (0.0 <= norm <= 100.0):
        raise BenchmarkError(
            f"Normalized value {norm} for formula {formula!r} is outside 0-100."
        )
    return norm


def _check_no_secrets(value, path: str) -> None:
    """Reject any nested key (dicts and lists) that resembles a credential."""
    if isinstance(value, dict):
        for key, child in value.items():
            location = f"{path}.{key}" if path else key
            if any(word in key.lower() for word in SECRET_KEYWORDS):
                raise BenchmarkError(
                    f"Benchmark payload key {location!r} looks like a secret and "
                    "is not permitted. AI-Hub never stores raw credentials "
                    "(Constitution Article 6)."
                )
            _check_no_secrets(child, location)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_no_secrets(child, f"{path}[{index}]")


def _sanitize_origin(origin: str) -> str:
    """Normalize a source attribution string (URL or file path).

    http(s) origins are validated/sanitized (credentials and secret-like
    query keys rejected, Article 6); non-URL origins are accepted as plain
    file-path attribution text.
    """
    if not isinstance(origin, str) or not origin.strip():
        raise BenchmarkError("origin must be a non-empty string.")
    origin = origin.strip()
    if origin.lower().startswith(("http://", "https://")):
        parsed = urlparse(origin)
        if parsed.username is not None or parsed.password is not None:
            raise BenchmarkError(
                f"origin {origin!r} embeds credentials; URLs must never "
                "contain credentials (Constitution Article 6)."
            )
        for key in parse_qs(parsed.query):
            if any(word in key.lower() for word in SECRET_KEYWORDS):
                raise BenchmarkError(
                    f"origin {origin!r} carries a secret-like query key {key!r}."
                )
        return urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc,
                parsed.path or "/",
                parsed.params,
                parsed.query,
                "",
            )
        )
    return origin


def _require_text(doc, key: str) -> str:
    value = doc.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkError(f"{key} is required and must be a non-empty string.")
    return value.strip()


def _validate_mapping(mapping) -> dict:
    if not isinstance(mapping, dict):
        raise BenchmarkError("mapping must be a JSON object (metric -> entry).")
    _check_no_secrets(mapping, "mapping")
    for metric, entry in mapping.items():
        if not isinstance(metric, str) or not metric.strip():
            raise BenchmarkError("mapping keys (metric names) must be non-empty strings.")
        if not isinstance(entry, dict):
            raise BenchmarkError(f"mapping[{metric!r}] must be a JSON object.")
        unknown = set(entry) - VALID_MAPPING_KEYS
        if unknown:
            raise BenchmarkError(
                f"mapping[{metric!r}] has unknown keys {sorted(unknown)}. "
                f"Allowed: {sorted(VALID_MAPPING_KEYS)}."
            )
        dimension = entry.get("dimension")
        if not isinstance(dimension, str) or not dimension.strip():
            raise BenchmarkError(f"mapping[{metric!r}].dimension is required.")
        formula = entry.get("formula")
        if formula not in FORMULAS:
            raise BenchmarkError(
                f"mapping[{metric!r}].formula must be one of {sorted(FORMULAS)}; "
                f"got {formula!r}."
            )
    return mapping


def _validate_result(result, path: str) -> None:
    if not isinstance(result, dict):
        raise BenchmarkError(f"{path} must be a JSON object.")
    unknown = set(result) - VALID_RESULT_KEYS
    if unknown:
        raise BenchmarkError(
            f"{path} has unknown keys {sorted(unknown)}. Allowed: {sorted(VALID_RESULT_KEYS)}."
        )
    for key in ("provider", "model", "metric"):
        value = result.get(key)
        if not isinstance(value, str) or not value.strip():
            raise BenchmarkError(f"{path}.{key} is required and must be a non-empty string.")
    raw = result.get("raw_value")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise BenchmarkError(f"{path}.raw_value must be a number.")
    confidence = result.get("confidence")
    if confidence is not None:
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise BenchmarkError(f"{path}.confidence must be a number between 0 and 1.")
        if not (0.0 <= float(confidence) <= 1.0):
            raise BenchmarkError(f"{path}.confidence must be between 0 and 1.")


def parse_benchmark_file(path) -> dict:
    """Parse and fully validate a curated benchmark JSON document.

    Returns the validated document dict. Raises ``BenchmarkError`` on any
    problem (file missing, invalid JSON, unknown keys, secrets, bad types).
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise BenchmarkError(f"Import file not found: {file_path}")
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BenchmarkError(f"Could not read {file_path}: {exc}") from exc
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise BenchmarkError(f"Invalid JSON in {file_path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise BenchmarkError("Benchmark document must be a JSON object.")
    unknown = set(doc) - VALID_TOP_KEYS
    if unknown:
        raise BenchmarkError(
            f"Unknown benchmark keys {sorted(unknown)}. Allowed: {sorted(VALID_TOP_KEYS)}."
        )
    _check_no_secrets(doc, "benchmark")
    doc["name"] = _require_text(doc, "name")
    doc["version"] = _require_text(doc, "version")
    if "origin" in doc:
        doc["origin"] = _sanitize_origin(doc["origin"])
    doc.setdefault("origin", str(file_path))
    for key in ("fetched_at", "run_date"):
        if key in doc:
            value = doc[key]
            if not isinstance(value, str) or not value.strip():
                raise BenchmarkError(f"{key} must be a non-empty string.")
            doc[key] = value.strip()
    mapping = _validate_mapping(doc.get("mapping"))
    results = doc.get("results")
    if not isinstance(results, list):
        raise BenchmarkError("results must be a list.")
    for index, result in enumerate(results):
        _validate_result(result, f"results[{index}]")
    for index, result in enumerate(results):
        if result["metric"] not in mapping:
            raise BenchmarkError(
                f"results[{index}].metric {result['metric']!r} is not present in "
                "mapping; every result metric must be mapped so its normalized "
                "value (0-100) is deterministic."
            )
    return doc


def _content_hash(doc) -> str:
    """Deterministic integrity stamp over the normalized document content."""
    canonical = json.dumps(
        {
            "name": doc["name"],
            "version": doc["version"],
            "origin": doc["origin"],
            "mapping": doc.get("mapping", {}),
            "results": doc.get("results", []),
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _resolve_model_id(conn, provider_name: str, model_identifier: str) -> int:
    """Resolve a (provider, model identifier) to an existing models.id."""
    row = conn.execute(
        "SELECT m.id FROM models m"
        " JOIN providers p ON p.id = m.provider_id"
        " WHERE p.name = ? AND m.model_identifier = ?",
        (provider_name, model_identifier),
    ).fetchone()
    if row is None:
        raise BenchmarkError(
            f"Unknown model: provider {provider_name!r} / model_identifier "
            f"{model_identifier!r}. Benchmark rows must reference existing "
            "registry models (D-P4)."
        )
    return row["id"]


def _prepare_rows(conn, doc) -> tuple:
    """Resolve models and compute normalized values for every result row.

    Runs fully before any write so an invalid dataset fails atomically.
    Returns a list of ``(model_id, metric, raw_value, norm_value, confidence,
    dimension)`` tuples.
    """
    mapping = doc["mapping"]
    rows: list[tuple] = []
    for result in doc["results"]:
        model_id = _resolve_model_id(conn, result["provider"], result["model"])
        metric = result["metric"]
        entry = mapping[metric]
        raw_value = float(result["raw_value"])
        norm_value = _apply_formula(entry["formula"], raw_value)
        confidence = (
            float(result["confidence"]) if result.get("confidence") is not None else None
        )
        rows.append(
            (model_id, metric, raw_value, norm_value, confidence, entry["dimension"])
        )
    return rows


def _scored_at(doc) -> Optional[str]:
    if doc.get("run_date"):
        return doc["run_date"]
    if doc.get("fetched_at"):
        return doc["fetched_at"]
    return None


def import_file(
    conn,
    path,
    submitter: str,
    dry_run: bool = False,
    name: Optional[str] = None,
) -> dict:
    """Import one curated benchmark JSON file into persistent storage.

    * *dry_run=True* validates without mutation and returns a summary without
      a ``run_id``.
    * *name* optionally overrides the benchmark identity read from the file.
    * A replay (identical content hash and origin) appends a NEW run and
      reports ``duplicate_of`` (the existing run id) - never silent
      (Articles 5, 10).
    * Returns a summary dict with ``run_id``, ``name``, ``version``,
      ``origin``, ``content_hash``, ``results`` (row count), and
      ``scored_dimensions`` (upserted score count).
    """
    if not submitter or not submitter.strip():
        raise BenchmarkError("submitter is required.")
    doc = parse_benchmark_file(path)
    if name is not None:
        doc["name"] = _require_text({"name": name}, "name")
    rows = _prepare_rows(conn, doc)
    content_hash = _content_hash(doc)
    submitter = submitter.strip()

    duplicate_of = None
    existing = conn.execute(
        "SELECT id FROM benchmark_runs WHERE content_hash = ? AND origin = ?"
        " ORDER BY id",
        (content_hash, doc["origin"]),
    ).fetchone()
    if existing is not None:
        duplicate_of = existing["id"]

    summary = {
        "run_id": None,
        "name": doc["name"],
        "version": doc["version"],
        "origin": doc["origin"],
        "content_hash": content_hash,
        "results": len(rows),
        "scored_dimensions": 0,
        "duplicate_of": duplicate_of,
        "dry_run": dry_run,
    }
    if dry_run:
        return summary

    mapping_json = json.dumps(doc["mapping"], sort_keys=True)
    try:
        cursor = conn.execute(
            "INSERT INTO benchmark_runs"
            " (name, version, origin, fetched_at, content_hash, submitter, mapping)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                doc["name"],
                doc["version"],
                doc["origin"],
                doc.get("fetched_at"),
                content_hash,
                submitter,
                mapping_json,
            ),
        )
        run_id = cursor.lastrowid
        conn.executemany(
            "INSERT INTO benchmark_results"
            " (run_id, model_id, metric, raw_value, norm_value)"
            " VALUES (?, ?, ?, ?, ?)",
            [(run_id, r[0], r[1], r[2], r[3]) for r in rows],
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise BenchmarkError(f"Could not store benchmark run: {exc}") from exc

    scored_at = _scored_at(doc)
    scored: set[tuple] = set()
    for model_id, metric, raw_value, norm_value, confidence, dimension in rows:
        set_score(
            conn,
            model_id,
            dimension,
            norm_value,
            confidence=confidence,
            source="BENCHMARK",
            scored_at=scored_at,
        )
        scored.add((model_id, dimension))

    summary["run_id"] = run_id
    summary["scored_dimensions"] = len(scored)
    event_payload = {
        "run_id": run_id,
        "name": doc["name"],
        "version": doc["version"],
        "origin": doc["origin"],
        "content_hash": content_hash,
        "results": len(rows),
        "scored_dimensions": len(scored),
        "duplicate_of": duplicate_of,
        "submitter": submitter,
    }
    events.record_event(
        conn,
        "BENCHMARK_IMPORTED",
        entity_type="benchmark_run",
        entity_id=run_id,
        payload=event_payload,
    )
    return summary


def list_runs(conn) -> Sequence[sqlite3.Row]:
    """List benchmark runs (newest first) with their result counts."""
    return conn.execute(
        "SELECT r.*,"
        " (SELECT COUNT(*) FROM benchmark_results b WHERE b.run_id = r.id) AS result_count"
        " FROM benchmark_runs r"
        " ORDER BY r.id"
    ).fetchall()


def get_run(conn, run_id: int):
    """Return a single benchmark run row or None."""
    return conn.execute(
        "SELECT * FROM benchmark_runs WHERE id = ?", (run_id,)
    ).fetchone()


def list_run_results(conn, run_id: int) -> Sequence[sqlite3.Row]:
    """List the results of one run joined with provider/model identifiers."""
    run = get_run(conn, run_id)
    if run is None:
        raise BenchmarkError(f"Benchmark run {run_id} not found.")
    return conn.execute(
        "SELECT b.*, m.model_identifier, p.name AS provider_name"
        " FROM benchmark_results b"
        " JOIN models m ON m.id = b.model_id"
        " JOIN providers p ON p.id = m.provider_id"
        " WHERE b.run_id = ?"
        " ORDER BY p.name, m.model_identifier, b.metric",
        (run_id,),
    ).fetchall()
