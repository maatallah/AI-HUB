"""AI-Hub monitoring engine (Phase 2).

Provides provider health checks, availability tracking, lifecycle state
preparation, quota monitoring architecture, and seed validation.

Monitoring never modifies provider information directly (v1.2 Section 9);
state transitions are applied through the existing legal transition rules.
"""

from monitoring.health import (
    FAILED,
    OK,
    UNKNOWN,
    HealthResult,
    check_provider,
    default_transport,
)
from monitoring.availability import (
    apply_lifecycle,
    get_availability,
    list_availability,
    update_availability,
)
from monitoring.quota import record_quota_signal
from monitoring.validation import validate_seed

__all__ = [
    "FAILED",
    "OK",
    "UNKNOWN",
    "HealthResult",
    "apply_lifecycle",
    "check_provider",
    "default_transport",
    "get_availability",
    "list_availability",
    "record_quota_signal",
    "update_availability",
    "validate_seed",
]
