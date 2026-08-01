"""Fallback engine (Phase 3)."""

from __future__ import annotations

from fallback.engine import (
    LAST_RESORT_STATUSES,
    PREFERRED_STATUSES,
    Chain,
    FallbackError,
    build_chain,
    check_recovery,
    is_eligible,
    select_fallback,
)

__all__ = [
    "LAST_RESORT_STATUSES",
    "PREFERRED_STATUSES",
    "Chain",
    "FallbackError",
    "build_chain",
    "check_recovery",
    "is_eligible",
    "select_fallback",
]
