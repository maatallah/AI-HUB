"""Discovery candidate lifecycle (Phase 6 Milestone 2).

Implements the review-gated candidate workflow approved as decision D-P1
(ADR-0005): a dedicated ``discovery_candidates`` table with its own state set
``DISCOVERED -> PENDING_REVIEW -> APPROVED | REJECTED`` and full provenance.
Candidates are never ``providers`` rows; the provider lifecycle and its
``providers.status`` CHECK constraint are preserved untouched.

M2 scope note: ``discovery approve`` performs the deterministic candidate state
transition and records the audit event ONLY. Materializing provider/model rows
through ``core.providers``/``core.models`` belongs to Phase 6 Milestone 3 and
is deliberately not implemented here. Nothing auto-approves (Articles 1, 2).

Guarantees:

* candidates retained, never deleted (Article 5)
* deterministic listing and transitions (Article 7)
* unknown/failed inputs reported, never fabricated (Article 10)
* every add/import/approve/reject records an append-only event (Article 8)
* duplicate acquisition is reported, never silent
* network fetch (D-P2) requires a non-empty allowlist and records an
  immutable snapshot before analysis
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Optional, Sequence

from core import events
from discovery import sources

#: The four legal candidate states (ADR-0005, D-P1).
CANDIDATE_STATES = ("DISCOVERED", "PENDING_REVIEW", "APPROVED", "REJECTED")

#: State a candidate is created in (imported/fetched, not yet queued).
INITIAL_STATE = "DISCOVERED"

#: State candidates are queued in for human review.
REVIEW_STATE = "PENDING_REVIEW"

#: Candidate source classifications.
SOURCE_TYPES = ("curated", "network")

#: Deterministic legal transitions (documented in v1.2 Section 20.2.1).
VALID_TRANSITIONS = {
    "DISCOVERED": {"PENDING_REVIEW"},
    "PENDING_REVIEW": {"APPROVED", "REJECTED"},
    "APPROVED": set(),
    "REJECTED": set(),
}


class DiscoveryError(ValueError):
    """Raised when a discovery operation violates the candidate workflow."""


def _content_hash(provider_name: str, payload) -> str:
    """Deterministic integrity stamp over the candidate's stored content."""
    canonical = json.dumps(
        {"provider_name": provider_name, "payload": payload}, sort_keys=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def get_candidate(conn, candidate_id: int):
    """Return a single candidate row or None (mirrors core.providers)."""
    return conn.execute(
        "SELECT * FROM discovery_candidates WHERE id = ?", (candidate_id,)
    ).fetchone()


def list_candidates(conn, state: Optional[str] = None) -> Sequence[sqlite3.Row]:
    """List candidates in deterministic id order, optionally filtered by state."""
    if state is not None and state not in CANDIDATE_STATES:
        raise DiscoveryError(
            f"Invalid candidate state {state!r}. Must be one of {list(CANDIDATE_STATES)}."
        )
    if state is not None:
        return conn.execute(
            "SELECT * FROM discovery_candidates WHERE state = ? ORDER BY id", (state,)
        ).fetchall()
    return conn.execute(
        "SELECT * FROM discovery_candidates ORDER BY id"
    ).fetchall()


def add_candidate(
    conn,
    provider_name: str,
    payload,
    source_type: str,
    source_ref,
    submitter: str,
) -> int:
    """Create a candidate in ``DISCOVERED`` state and record its ADDED event."""
    if not provider_name or not provider_name.strip():
        raise DiscoveryError("Provider name is required.")
    if source_type not in SOURCE_TYPES:
        raise DiscoveryError(
            f"Invalid source_type {source_type!r}. Must be one of {list(SOURCE_TYPES)}."
        )
    if not submitter or not submitter.strip():
        raise DiscoveryError("submitter is required.")
    name = provider_name.strip()
    try:
        sources.validate_payload(payload)
    except sources.CandidateSourceError as exc:
        raise DiscoveryError(str(exc)) from exc
    content_hash = _content_hash(name, payload)
    try:
        cursor = conn.execute(
            "INSERT INTO discovery_candidates"
            " (provider_name, source_type, source_ref, payload, state,"
            "  content_hash, submitter)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                source_type,
                source_ref,
                json.dumps(payload, sort_keys=True),
                INITIAL_STATE,
                content_hash,
                submitter.strip(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise DiscoveryError(
            f"Provider candidate {name!r} already exists (provider_name must be unique)."
        ) from exc

    candidate_id = cursor.lastrowid
    events.record_event(
        conn,
        "DISCOVERY_CANDIDATE_ADDED",
        entity_type="candidate",
        entity_id=candidate_id,
        payload={
            "provider_name": name,
            "source_type": source_type,
            "source_ref": source_ref,
            "content_hash": content_hash,
            "state": INITIAL_STATE,
        },
    )
    return candidate_id


def queue_candidate(conn, candidate_id: int) -> None:
    """Move a ``DISCOVERED`` candidate to ``PENDING_REVIEW`` for review.

    The enclosing import/run records a ``DISCOVERY_IMPORT_COMPLETE`` event that
    documents the queueing; no dedicated per-candidate event exists by design.
    """
    row = get_candidate(conn, candidate_id)
    if row is None:
        raise DiscoveryError(f"Candidate {candidate_id} not found.")
    if row["state"] != INITIAL_STATE:
        raise DiscoveryError(
            f"Candidate {candidate_id} is in state {row['state']!r}; expected {INITIAL_STATE!r}."
        )
    conn.execute(
        "UPDATE discovery_candidates SET state = ? WHERE id = ?",
        (REVIEW_STATE, candidate_id),
    )
    conn.commit()


def _complete_review(
    conn, candidate_id: int, to_state: str, reason, event_type: str
) -> dict:
    """Deterministic PENDING_REVIEW -> APPROVED|REJECTED transition + event."""
    if to_state not in VALID_TRANSITIONS[REVIEW_STATE]:
        raise DiscoveryError(
            f"Candidate {candidate_id} cannot transition to {to_state!r}."
        )
    if to_state == "REJECTED" and not (reason and reason.strip()):
        raise DiscoveryError("Rejecting a candidate requires an explicit reason.")
    row = get_candidate(conn, candidate_id)
    if row is None:
        raise DiscoveryError(f"Candidate {candidate_id} not found.")
    if row["state"] != REVIEW_STATE:
        raise DiscoveryError(
            f"Candidate {candidate_id} is in state {row['state']!r}; only "
            f"{REVIEW_STATE!r} candidates can be approved or rejected. "
            "No silent state rewrite."
        )
    reason_value = reason.strip() if reason else None
    try:
        conn.execute(
            "UPDATE discovery_candidates SET state = ?, reviewed_at = datetime('now'),"
            " reason = ? WHERE id = ? AND state = ?",
            (to_state, reason_value, candidate_id, REVIEW_STATE),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise DiscoveryError(f"Could not review candidate {candidate_id}: {exc}") from exc
    events.record_event(
        conn,
        event_type,
        entity_type="candidate",
        entity_id=candidate_id,
        payload={
            "provider_name": row["provider_name"],
            "from": REVIEW_STATE,
            "to": to_state,
            "reason": reason_value,
        },
    )
    return dict(get_candidate(conn, candidate_id))


def approve_candidate(conn, candidate_id: int, reason: Optional[str] = None) -> dict:
    """Approve a ``PENDING_REVIEW`` candidate (state transition only in M2)."""
    return _complete_review(
        conn, candidate_id, "APPROVED", reason, "DISCOVERY_CANDIDATE_APPROVED"
    )


def reject_candidate(conn, candidate_id: int, reason: str) -> dict:
    """Reject a ``PENDING_REVIEW`` candidate. Retained, never deleted."""
    return _complete_review(
        conn, candidate_id, "REJECTED", reason, "DISCOVERY_CANDIDATE_REJECTED"
    )


def record_import_error(conn, source_ref: str, submitter: str, message: str) -> None:
    """Record a DISCOVERY_IMPORT_ERROR event for a failed acquisition unit."""
    events.record_event(
        conn,
        "DISCOVERY_IMPORT_ERROR",
        entity_type="discovery",
        payload={"source_ref": source_ref, "submitter": submitter, "error": message},
    )


def import_candidates(
    conn,
    records,
    source_type: str,
    source_ref: str,
    submitter: str,
    snapshot: Optional[dict] = None,
) -> dict:
    """Import validated candidate records into the review queue.

    *records* is an iterable of ``(provider_name, payload)`` pairs. Every
    record is validated BEFORE anything is written, so a dataset containing an
    invalid record fails atomically (nothing is inserted). Duplicate provider
    names (existing candidate, existing provider, or repeated within the same
    dataset) are deterministically skipped and reported - never silent
    (Articles 5, 10).
    """
    if source_type not in SOURCE_TYPES:
        raise DiscoveryError(
            f"Invalid source_type {source_type!r}. Must be one of {list(SOURCE_TYPES)}."
        )
    records = list(records)
    for index, (name, payload) in enumerate(records):
        if not name or not name.strip():
            raise DiscoveryError(f"{source_ref} record {index}: provider name is required.")
        try:
            sources.validate_payload(payload)
        except sources.CandidateSourceError as exc:
            raise DiscoveryError(f"{source_ref} record {index}: {exc}") from exc

    existing_candidates = {
        row["provider_name"]
        for row in conn.execute("SELECT provider_name FROM discovery_candidates").fetchall()
    }
    existing_providers = {
        row["name"] for row in conn.execute("SELECT name FROM providers").fetchall()
    }

    added_ids: list[int] = []
    skipped: list[str] = []
    seen: set[str] = set()
    for name, payload in records:
        key = name.strip()
        if key in seen or key in existing_candidates or key in existing_providers:
            skipped.append(key)
            continue
        seen.add(key)
        candidate_id = add_candidate(conn, key, payload, source_type, source_ref, submitter)
        queue_candidate(conn, candidate_id)
        added_ids.append(candidate_id)

    event_payload = {
        "source_type": source_type,
        "source_ref": source_ref,
        "added": added_ids,
        "skipped": skipped,
    }
    if snapshot is not None:
        event_payload["snapshot"] = snapshot
    events.record_event(
        conn,
        "DISCOVERY_IMPORT_COMPLETE",
        entity_type="discovery",
        payload=event_payload,
    )
    return {"added": added_ids, "skipped": skipped}


def import_file(conn, path, submitter: str) -> dict:
    """Import one curated JSON file into the review queue."""
    try:
        records = sources.parse_curated_file(path)
    except sources.CandidateSourceError as exc:
        raise DiscoveryError(str(exc)) from exc
    return import_candidates(conn, records, "curated", str(path), submitter)


def run_network(
    conn,
    urls: Sequence[str],
    timeout_seconds: int,
    submitter: str,
    transport=None,
) -> dict:
    """Fetch allowlisted public metadata endpoints (D-P2) into candidates.

    Requires a non-empty allowlist; each configured URL is fetched with the
    given (injectable) transport, snapshotted before analysis, and imported
    atomically per URL. A failing URL records a DISCOVERY_IMPORT_ERROR event
    and does not stop the remaining URLs (best effort, fully audited).
    """
    if not urls:
        raise DiscoveryError(
            "Network discovery requires a non-empty allowlist "
            "(discovery.allowlisted_urls); network is disabled by default (D-P2)."
        )
    fetched: list[str] = []
    added: list[int] = []
    skipped: list[str] = []
    failed: list[str] = []
    for url in urls:
        try:
            status, body, snapshot = sources.fetch_url(url, timeout_seconds, transport)
            if status != 200:
                raise sources.CandidateSourceError(
                    f"Unexpected HTTP status {status} from {snapshot['url']}."
                )
            records = sources.extract_records_from_content(body, snapshot["url"])
            result = import_candidates(
                conn, records, "network", snapshot["url"], submitter, snapshot=snapshot
            )
            fetched.append(snapshot["url"])
            added.extend(result["added"])
            skipped.extend(result["skipped"])
        except (sources.CandidateSourceError, DiscoveryError) as exc:
            failed.append(url)
            record_import_error(conn, url, submitter, str(exc))
        except Exception as exc:
            failed.append(url)
            record_import_error(conn, url, submitter, f"Network discovery failure: {exc}")
    return {"fetched": fetched, "added": added, "skipped": skipped, "failed": failed}