"""Discovery candidate sources (Phase 6 Milestone 2).

Parsing, validation and controlled network fetching for provider/model
candidate metadata. This module is pure (no database, no events): it turns
curated JSON files or gated network responses into validated candidate
records. The candidate lifecycle lives in :mod:`discovery.engine`.

Curated import file format (JSON, one file per import unit):

    {
        "provider": {
            "name": "Acme AI",
            "company": "Acme",
            "api_type": "OpenAI Compatible",
            "base_url": "https://api.acme.example/v1",
            "documentation_url": "https://docs.acme.example"
        },
        "models": [
            {
                "model_name": "Acme Turbo",
                "model_identifier": "acme-turbo",
                "context_window": 128000,
                "supports_tools": true,
                "supports_streaming": true,
                "supports_json": true,
                "supports_vision": false
            }
        ]
    }

A file may also be a JSON *array* of such objects. ``name`` is lifted into the
candidate's ``provider_name`` column; the remaining provider metadata becomes
the stored ``payload`` (company, api_type, base_url, documentation_url,
models).

Network fetching (decision D-P2) is strictly allowlisted and user-gated: only
http(s) URLs, never credentials or secret-like query keys (Article 6). The raw
response is snapshotted (URL, fetched_at, content hash, size) before any
analysis so determinism holds (Article 7). Transports are injectable so tests
run fully offline (same pattern as ``monitoring/health.py``).
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import parse_qs, urlparse, urlunparse

#: Keywords that mark a payload key as a potential secret (mirrors
#: ``app/config.py.SECRET_KEYWORDS`` - Constitution Article 6).
from app.config import SECRET_KEYWORDS

#: Allowed provider metadata keys in a candidate payload.
VALID_PAYLOAD_KEYS = frozenset(
    {"company", "api_type", "base_url", "documentation_url", "models"}
)

#: Allowed keys inside a model record.
VALID_MODEL_KEYS = frozenset(
    {
        "model_name",
        "model_identifier",
        "context_window",
        "supports_tools",
        "supports_streaming",
        "supports_json",
        "supports_vision",
    }
)

#: Required per-model keys.
REQUIRED_MODEL_KEYS = ("model_name", "model_identifier")

#: Allowed keys on the ``provider`` object of a curated record.
VALID_PROVIDER_KEYS = frozenset(
    {"name", "company", "api_type", "base_url", "documentation_url"}
)


class CandidateSourceError(ValueError):
    """Raised when candidate source content is invalid or cannot be fetched."""


def sanitize_url(url: str) -> str:
    """Validate and normalize an http(s) URL, rejecting credentials.

    Never stored URLs may embed credentials (Article 6); URLs whose query
    strings carry secret-like keys are rejected too (R-01 discipline).
    """
    if not isinstance(url, str) or not url.strip():
        raise CandidateSourceError("URL must be a non-empty string.")
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise CandidateSourceError(
            f"URL {url!r} must use http(s); got scheme {scheme!r}."
        )
    if not parsed.hostname:
        raise CandidateSourceError(f"URL {url!r} has no host.")
    if parsed.username is not None or parsed.password is not None:
        raise CandidateSourceError(
            f"URL {url!r} embeds credentials; URLs must never contain "
            "credentials (Constitution Article 6)."
        )
    for key in parse_qs(parsed.query):
        if any(word in key.lower() for word in SECRET_KEYWORDS):
            raise CandidateSourceError(
                f"URL {url!r} carries a secret-like query key {key!r}."
            )
    return urlunparse(
        (scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, "")
    )


def _check_no_secrets(value, path: str) -> None:
    """Reject any nested key (dicts and lists) that resembles a credential.

    Reuses the ``app.config._reject_secrets`` pattern (SECRET_KEYWORDS),
    extended to cover candidate payload lists.
    """
    if isinstance(value, dict):
        for key, child in value.items():
            location = f"{path}.{key}" if path else key
            if any(word in key.lower() for word in SECRET_KEYWORDS):
                raise CandidateSourceError(
                    f"Payload key {location!r} looks like a secret and is not "
                    "permitted. AI-Hub never stores raw credentials "
                    "(Constitution Article 6)."
                )
            _check_no_secrets(child, location)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_no_secrets(child, f"{path}[{index}]")


def validate_model(model, path: str) -> None:
    """Validate a single model metadata record."""
    if not isinstance(model, dict):
        raise CandidateSourceError(f"{path} must be a JSON object.")
    unknown = set(model) - VALID_MODEL_KEYS
    if unknown:
        raise CandidateSourceError(
            f"{path} has unknown keys {sorted(unknown)}. Allowed: {sorted(VALID_MODEL_KEYS)}."
        )
    for key in REQUIRED_MODEL_KEYS:
        value = model.get(key)
        if not isinstance(value, str) or not value.strip():
            raise CandidateSourceError(f"{path}.{key} is required and must be a non-empty string.")
    for key in ("supports_tools", "supports_streaming", "supports_json", "supports_vision"):
        value = model.get(key)
        if value is not None and not isinstance(value, bool):
            raise CandidateSourceError(f"{path}.{key} must be a boolean.")
    context_window = model.get("context_window")
    if context_window is not None and (
        not isinstance(context_window, int) or context_window <= 0
    ):
        raise CandidateSourceError(f"{path}.context_window must be a positive integer/null.")


def validate_payload(payload) -> None:
    """Validate candidate payload metadata (keys, types, secrets, URLs)."""
    if not isinstance(payload, dict):
        raise CandidateSourceError("Candidate payload must be a JSON object.")
    unknown = set(payload) - VALID_PAYLOAD_KEYS
    if unknown:
        raise CandidateSourceError(
            f"Unknown payload keys {sorted(unknown)}. Allowed: {sorted(VALID_PAYLOAD_KEYS)}."
        )
    _check_no_secrets(payload, "payload")
    for key in ("company", "api_type"):
        value = payload.get(key)
        if value is not None and not isinstance(value, str):
            raise CandidateSourceError(f"payload.{key} must be a string.")
    for key in ("base_url", "documentation_url"):
        value = payload.get(key)
        if value is not None:
            sanitize_url(value)  # raises CandidateSourceError on any problem
    models = payload.get("models")
    if models is None:
        return
    if not isinstance(models, list):
        raise CandidateSourceError("payload.models must be a list.")
    for index, model in enumerate(models):
        validate_model(model, f"payload.models[{index}]")


def validate_record(record) -> Tuple[str, dict]:
    """Validate one curated record and return ``(provider_name, payload)``."""
    if not isinstance(record, dict):
        raise CandidateSourceError("Curated record must be a JSON object.")
    provider = record.get("provider")
    if not isinstance(provider, dict):
        raise CandidateSourceError("Curated record requires a 'provider' object.")
    unknown = set(provider) - VALID_PROVIDER_KEYS
    if unknown:
        raise CandidateSourceError(
            f"provider has unknown keys {sorted(unknown)}. Allowed: {sorted(VALID_PROVIDER_KEYS)}."
        )
    name = provider.get("name")
    if not isinstance(name, str) or not name.strip():
        raise CandidateSourceError("provider.name is required and must be a non-empty string.")
    payload = {
        key: provider[key] for key in ("company", "api_type", "base_url", "documentation_url")
        if key in provider and provider[key] is not None
    }
    payload["models"] = record.get("models", [])
    validate_payload(payload)
    return name.strip(), payload


def parse_curated_file(path) -> List[Tuple[str, dict]]:
    """Parse and validate a curated JSON file. Returns validated records."""
    file_path = Path(path)
    if not file_path.is_file():
        raise CandidateSourceError(f"Import file not found: {file_path}")
    try:
        text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CandidateSourceError(f"Could not read {file_path}: {exc}") from exc
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise CandidateSourceError(f"Invalid JSON in {file_path}: {exc}") from exc
    records = data if isinstance(data, list) else [data]
    result: List[Tuple[str, dict]] = []
    for index, record in enumerate(records):
        try:
            result.append(validate_record(record))
        except CandidateSourceError as exc:
            raise CandidateSourceError(f"{file_path} record {index}: {exc}") from exc
    return result


def default_transport(url: str, timeout_seconds: int):
    """Real HTTP GET transport using stdlib urllib."""
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return getattr(response, "status", 200), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def fetch_url(url: str, timeout_seconds: int, transport=None) -> Tuple[int, bytes, dict]:
    """Fetch an allowlisted URL, returning ``(status, body, snapshot)``.

    The snapshot (URL, fetched_at, content hash, size) is taken immediately on
    reception, before any analysis, so downstream determinism holds (Article 7).
    """
    sanitized = sanitize_url(url)
    if transport is None:
        transport = default_transport
    try:
        status, body = transport(sanitized, timeout_seconds)
    except Exception as exc:
        raise CandidateSourceError(
            f"Network fetch failed for {sanitized}: {exc}"
        ) from exc
    if not isinstance(body, bytes):
        body = str(body).encode("utf-8")
    snapshot = {
        "url": sanitized,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": hashlib.sha256(body).hexdigest(),
        "size": len(body),
    }
    return status, body, snapshot


def extract_records_from_content(content, source_ref: str) -> List[Tuple[str, dict]]:
    """Parse validated candidate records out of fetched content."""
    text = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise CandidateSourceError(f"Unparseable content from {source_ref}: {exc}") from exc
    records = data if isinstance(data, list) else [data]
    result: List[Tuple[str, dict]] = []
    for index, record in enumerate(records):
        try:
            result.append(validate_record(record))
        except CandidateSourceError as exc:
            raise CandidateSourceError(f"{source_ref} record {index}: {exc}") from exc
    return result