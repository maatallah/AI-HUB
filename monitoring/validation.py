"""Provider seed validation (Phase 2).

Validates the metadata of seeded providers:

  * ``base_url`` present, parseable, http/https scheme
  * ``documentation_url`` parseable when present
  * endpoint reachability check (optional, enabled by config)

Results are recorded through the event system (VALIDATION_*). Validation
never modifies provider records (v1.2 Section 9) and never fabricates
unknown values (Constitution Article 10). Providers with a missing base_url
are classified UNKNOWN.
"""

from __future__ import annotations

from urllib.parse import urlparse

from core import events


class ValidationError(ValueError):
    """Raised when validation input is invalid."""


def _url_scheme_ok(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def validate_url(url) -> tuple:
    """Validate a single URL string.

    Returns (status, reason) where status is one of:
      * "valid"   - http/https URL with a host
      * "invalid" - a value is present but not a valid URL
      * "unknown" - no value present (never fabricated, Article 10)
    """
    if url is None or not url.strip():
        return "unknown", "url missing (unknown, not validated)"
    url = url.strip()
    if not _url_scheme_ok(url):
        return "invalid", f"invalid url: {url!r} (expected http/https scheme with host)"
    return "valid", None


def validate_provider(conn, provider_id: int, reachability_check=False, transport=None) -> dict:
    """Validate a single provider's metadata and record a VALIDATION_* event.

    Returns a dict with keys: provider_id, name, base_url_valid,
    documentation_url_valid, reachable, ok, event_type, details.
    """
    row = conn.execute(
        "SELECT id, name, base_url, documentation_url FROM providers WHERE id = ?",
        (provider_id,),
    ).fetchone()
    if row is None:
        raise ValidationError(f"Provider {provider_id} not found.")

    base_status, base_reason = validate_url(row["base_url"])
    doc_status, doc_reason = validate_url(row["documentation_url"])

    reachable = None
    details = []
    if base_status != "valid":
        details.append(base_reason or "base_url invalid")
    if doc_status != "valid":
        details.append(doc_reason or "documentation_url invalid")

    event_type = "VALIDATION_PASSED"
    if reachability_check and base_status == "valid":
        reachable = _reachability_result(transport, row["base_url"])
        if reachable is False:
            details.append("base_url unreachable")
        if reachable is True:
            details.append("base_url reachable")

    if base_status == "unknown":
        event_type = "VALIDATION_UNKNOWN"
    elif base_status == "invalid":
        event_type = "VALIDATION_FAILED"
    elif reachable is False:
        event_type = "VALIDATION_FAILED"
    else:
        event_type = "VALIDATION_PASSED"

    events.record_event(
        conn,
        event_type,
        entity_type="provider",
        entity_id=provider_id,
        payload={
            "name": row["name"],
            "base_url": row["base_url"],
            "documentation_url": row["documentation_url"],
            "base_url_valid": base_status == "valid",
            "documentation_url_valid": doc_status == "valid",
            "reachable": reachable,
            "details": details,
        },
    )

    return {
        "provider_id": provider_id,
        "name": row["name"],
        "base_url_valid": base_status == "valid",
        "documentation_url_valid": doc_status == "valid",
        "reachable": reachable,
        "ok": event_type == "VALIDATION_PASSED",
        "event_type": event_type,
        "details": details,
    }


def _reachability_result(transport, base_url: str) -> bool:
    """Return True/False for reachability using the provided transport."""
    if transport is None:
        return None
    try:
        return bool(transport(base_url))
    except Exception:
        return False


def validate_seed(conn, reachability_check=False, transport=None) -> list:
    """Validate all providers in the registry. Returns a list of results."""
    rows = conn.execute(
        "SELECT id, name FROM providers ORDER BY name"
    ).fetchall()
    results = []
    for row in rows:
        results.append(
            validate_provider(conn, row["id"], reachability_check, transport)
        )
    return results
