"""Provider health checks (Phase 2).

Performs HTTP reachability checks against a provider's documented base_url.
Safety rules:

  * no authentication headers, no secrets, no request payloads
  * a provider without a base_url returns UNKNOWN (Constitution Article 10:
    unknown information remains unknown, never fabricated)
  * results are classified as OK / FAILED / UNKNOWN

Checks use a configurable transport so tests can inject a fake without any
real network access.
"""

from __future__ import annotations

import time
import urllib.request
from dataclasses import dataclass
from typing import Optional

from core import events

#: Classification of a single health check result.
OK = "OK"
FAILED = "FAILED"
UNKNOWN = "UNKNOWN"

#: Result states that represent a successful check.
SUCCESS_STATES = (OK,)

#: Response status codes considered a success by default.
_HTTP_SUCCESS = (200, 201, 202, 204, 301, 302, 303, 304, 307, 308)

#: HTTP status codes that indicate quota / rate-limit exhaustion.
QUOTA_STATUS_CODES = (429,)


class HealthCheckError(RuntimeError):
    """Raised when a health check cannot be executed."""


@dataclass(frozen=True)
class HealthResult:
    """Outcome of a single health check."""

    state: str
    status_code: Optional[int] = None
    latency_ms: Optional[int] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.state == OK


def default_transport(url: str, timeout_seconds: int, latency_threshold_ms: int):
    """Real HTTP transport using urllib. Returns a HealthResult."""
    started = time.monotonic()
    try:
        request = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            latency = int((time.monotonic() - started) * 1000)
            status = getattr(response, "status", 200)
            return _classify(status, latency, latency_threshold_ms)
    except urllib.error.HTTPError as exc:
        latency = int((time.monotonic() - started) * 1000)
        return _classify(exc.code, latency, latency_threshold_ms)
    except Exception as exc:
        return HealthResult(state=FAILED, error=str(exc))


def _classify(status_code: int, latency_ms: int, latency_threshold_ms: int) -> HealthResult:
    if status_code in _HTTP_SUCCESS and latency_ms <= latency_threshold_ms:
        return HealthResult(state=OK, status_code=status_code, latency_ms=latency_ms)
    if latency_ms > latency_threshold_ms:
        return HealthResult(
            state=FAILED,
            status_code=status_code,
            latency_ms=latency_ms,
            error=f"Latency {latency_ms}ms exceeds threshold {latency_threshold_ms}ms",
        )
    return HealthResult(state=FAILED, status_code=status_code, latency_ms=latency_ms)


def check_provider(
    conn,
    provider_id: int,
    timeout_seconds: int = 10,
    latency_threshold_ms: int = 10000,
    transport=None,
) -> HealthResult:
    """Run a health check against a provider's base_url.

    ``transport`` defaults to the real HTTP transport; tests inject a fake.
    Always records a HEALTH_CHECK_* event.
    """
    row = conn.execute(
        "SELECT id, name, base_url FROM providers WHERE id = ?", (provider_id,)
    ).fetchone()
    if row is None:
        raise HealthCheckError(f"Provider {provider_id} not found.")

    base_url = row["base_url"]
    if not base_url:
        result = HealthResult(state=UNKNOWN, error="base_url is not set")
        events.record_event(
            conn,
            "HEALTH_CHECK_UNKNOWN",
            entity_type="provider",
            entity_id=provider_id,
            payload={"name": row["name"], "error": result.error},
        )
        return result

    if transport is None:
        transport = default_transport

    try:
        result = transport(base_url, timeout_seconds, latency_threshold_ms)
    except Exception as exc:
        result = HealthResult(state=FAILED, error=str(exc))

    event_type = {
        OK: "HEALTH_CHECK_OK",
        FAILED: "HEALTH_CHECK_FAILED",
        UNKNOWN: "HEALTH_CHECK_UNKNOWN",
    }[result.state]
    events.record_event(
        conn,
        event_type,
        entity_type="provider",
        entity_id=provider_id,
        payload={
            "name": row["name"],
            "base_url": base_url,
            "status_code": result.status_code,
            "latency_ms": result.latency_ms,
            "error": result.error,
        },
    )
    return result
