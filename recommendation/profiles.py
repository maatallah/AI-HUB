"""Recommendation profiles (Phase 3).

Built-in profiles from v1.2 Section 2 with exact weights (fractions summing to
1.0). Custom profiles load from the ``preferences`` table as JSON
(``profile.<name>``) so new profiles never require a code change (Constitution
Article 9). Weights are validated at load (no hidden weighting, v1.2 Section
3).
"""

from __future__ import annotations

import json
from typing import Optional

from core import events

#: Built-in profiles (v1.2 Section 2). Dimension -> weight fraction.
BUILTIN_PROFILES: dict[str, dict[str, float]] = {
    "coding": {
        "coding": 0.40,
        "reasoning": 0.20,
        "reliability": 0.20,
        "availability": 0.15,
        "latency": 0.05,
        "cost": 0.00,
    },
    "reasoning": {
        "reasoning": 0.45,
        "coding": 0.20,
        "reliability": 0.15,
        "availability": 0.10,
        "latency": 0.05,
        "cost": 0.05,
    },
    "free": {
        "cost": 0.40,
        "availability": 0.20,
        "coding": 0.20,
        "reasoning": 0.10,
        "latency": 0.10,
    },
    "long_context": {
        "context_window": 0.40,
        "reasoning": 0.20,
        "coding": 0.20,
        "reliability": 0.10,
        "availability": 0.10,
    },
}

#: Prefix for custom profiles stored in the preferences table.
CUSTOM_PROFILE_PREFIX = "profile."


class ProfileError(ValueError):
    """Raised when a profile is invalid."""


def _validate_weights(weights: dict) -> dict:
    if not weights:
        raise ProfileError("Profile must define at least one dimension.")
    for dimension, weight in weights.items():
        if isinstance(weight, bool) or not isinstance(weight, (int, float)):
            raise ProfileError(f"Profile weight for {dimension!r} must be a number.")
        if weight < 0:
            raise ProfileError(f"Profile weight for {dimension!r} must be >= 0.")
    total = sum(weights.values())
    if abs(total - 1.0) > 1e-9:
        raise ProfileError(
            f"Profile weights must sum to 1.0; got {total:.6f} (v1.2 Section 3)."
        )
    return {dimension: float(weight) for dimension, weight in weights.items()}


def get_profile(conn, name: str) -> dict:
    """Return validated weights for a built-in or custom profile."""
    if name in BUILTIN_PROFILES:
        return dict(BUILTIN_PROFILES[name])
    row = conn.execute(
        "SELECT value FROM preferences WHERE key = ?", (CUSTOM_PROFILE_PREFIX + name,)
    ).fetchone()
    if row is None:
        raise ProfileError(
            f"Unknown profile {name!r}. Built-ins: {sorted(BUILTIN_PROFILES)}."
        )
    try:
        raw = json.loads(row["value"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"Profile {name!r} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProfileError(f"Profile {name!r} must be a JSON object of dimension weights.")
    return _validate_weights(raw)


def set_custom_profile(conn, name: str, weights: dict) -> None:
    """Store a custom profile in the preferences table (validated, atomic)."""
    if not name or not name.strip():
        raise ProfileError("Profile name is required.")
    name = name.strip()
    if name in BUILTIN_PROFILES:
        raise ProfileError(f"Cannot override built-in profile {name!r}.")
    validated = _validate_weights(weights)
    conn.execute(
        "INSERT INTO preferences (key, value, value_type, updated_at)"
        " VALUES (?, ?, 'json', datetime('now'))"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value,"
        " value_type = excluded.value_type, updated_at = datetime('now')",
        (CUSTOM_PROFILE_PREFIX + name, json.dumps(validated, sort_keys=True)),
    )
    conn.commit()
    events.record_event(
        conn,
        "PROFILE_UPDATED",
        entity_type="preference",
        payload={"profile": name, "weights": validated},
    )


def list_profiles(conn) -> list[str]:
    """List built-in and custom profile names."""
    custom = [
        row["key"][len(CUSTOM_PROFILE_PREFIX):]
        for row in conn.execute(
            "SELECT key FROM preferences WHERE key LIKE ? ESCAPE '\\' ORDER BY key",
            (CUSTOM_PROFILE_PREFIX.replace("\\", "\\\\") + "%",),
        ).fetchall()
    ]
    return sorted(BUILTIN_PROFILES) + custom
