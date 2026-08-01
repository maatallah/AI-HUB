"""Fallback engine (Phase 3).

Builds and selects the fallback chain (v1.2 Section 7):

  * The chain is the deterministic recommendation ranking: primary + up to
    ``max_chain_length`` fallbacks.
  * Eligibility is derived from monitoring outputs (``providers.status`` /
    ``availability.state``) - fallback never probes providers itself and never
    modifies the provider lifecycle (v1.2 Section 9).
  * ACTIVE/LIMITED providers are preferred; DEGRADED is a last resort and is
    flagged; OFFLINE/ARCHIVED/NEW/EVALUATING are never selected.
  * On a failure signal for the current provider, the next eligible provider
    in the chain is selected (FALLBACK_TRIGGERED event). Recovery returns to
    the primary when it becomes eligible again (FALLBACK_RECOVERED event).

Every decision is deterministic (Constitution Article 7).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from core import events
from recommendation import Recommendation, recommend

#: Fully eligible provider states (preferred).
PREFERRED_STATUSES = ("ACTIVE", "LIMITED")

#: Last-resort state (flagged).
LAST_RESORT_STATUSES = ("DEGRADED",)


class FallbackError(ValueError):
    """Raised when a fallback operation violates the rules."""


@dataclass(frozen=True)
class Chain:
    """A deterministic fallback chain: primary + ordered fallbacks."""

    task: str
    profile: str
    recommendations: Sequence[Recommendation]
    max_chain_length: int

    @property
    def primary(self) -> Optional[Recommendation]:
        return self.recommendations[0] if self.recommendations else None

    @property
    def fallbacks(self) -> Sequence[Recommendation]:
        return self.recommendations[1:]

    def __len__(self) -> int:
        return len(self.recommendations)


def _provider_status(conn, provider_id: int) -> str:
    row = conn.execute(
        "SELECT status FROM providers WHERE id = ?", (provider_id,)
    ).fetchone()
    if row is None:
        raise FallbackError(f"Provider {provider_id} not found.")
    return row["status"]


def is_eligible(status: str, allow_last_resort: bool = True) -> bool:
    """Return True if a provider state may be selected in a chain."""
    if status in PREFERRED_STATUSES:
        return True
    if status in LAST_RESORT_STATUSES and allow_last_resort:
        return True
    return False


def build_chain(
    conn,
    task: str,
    profile: str = "coding",
    max_chain_length: int = 5,
    **recommend_kwargs,
) -> Chain:
    """Build the fallback chain: primary + up to max_chain_length fallbacks.

    The ranking comes from :func:`recommendation.recommend` (already filtered
    to eligible providers and deterministically sorted). Only providers
    eligible at build time are included.
    """
    if max_chain_length < 1:
        raise FallbackError("max_chain_length must be >= 1.")
    ranked = recommend(
        conn, task, profile=profile, derive_operational=True, **recommend_kwargs
    )
    eligible = [
        r for r in ranked if is_eligible(_provider_status(conn, r.provider_id))
    ]
    return Chain(
        task=task,
        profile=profile,
        recommendations=eligible[: max_chain_length + 1],
        max_chain_length=max_chain_length,
    )


def select_fallback(
    conn,
    chain: Chain,
    current_provider_id: int,
    *,
    reason: str = "Provider unavailable",
    record_event: bool = True,
) -> Optional[Recommendation]:
    """Select the next eligible provider after the current one.

    Walks the chain in ranking order from the current provider; the first
    eligible provider that follows it is selected. Preferred statuses
    (ACTIVE/LIMITED) are used when present; DEGRADED is considered only when
    no preferred alternative remains after the current position. Returns None
    when the chain is exhausted.
    """
    current = next(
        (r for r in chain.recommendations if r.provider_id == current_provider_id),
        None,
    )
    if current is None:
        raise FallbackError(
            f"Provider {current_provider_id} is not part of the chain."
        )

    after_current = chain.recommendations[chain.recommendations.index(current) + 1:]
    preferred = [
        r for r in after_current
        if _provider_status(conn, r.provider_id) in PREFERRED_STATUSES
    ]
    if preferred:
        selected = preferred[0]
    else:
        last_resort = [
            r for r in after_current
            if _provider_status(conn, r.provider_id) in LAST_RESORT_STATUSES
        ]
        selected = last_resort[0] if last_resort else None

    if selected is None:
        if record_event:
            events.record_event(
                conn,
                "FALLBACK_TRIGGERED",
                entity_type="provider",
                entity_id=current_provider_id,
                payload={
                    "from": current_provider_id,
                    "to": None,
                    "reason": reason,
                    "chain_exhausted": True,
                },
            )
        return None

    if record_event:
        events.record_event(
            conn,
            "FALLBACK_TRIGGERED",
            entity_type="provider",
            entity_id=current_provider_id,
            payload={
                "from": current_provider_id,
                "to": selected.provider_id,
                "reason": reason,
                "selected_model": selected.model_identifier,
            },
        )
    return selected


def check_recovery(
    conn,
    chain: Chain,
    *,
    reason: str = "Primary provider recovered",
    record_event: bool = True,
) -> Optional[Recommendation]:
    """Return the primary when it is eligible again (recovery).

    Emits FALLBACK_RECOVERED when the primary is ACTIVE/LIMITED and is the
    top of the chain. Returns the primary Recommendation or None.
    """
    primary = chain.primary
    if primary is None:
        return None
    status = _provider_status(conn, primary.provider_id)
    if status in PREFERRED_STATUSES:
        if record_event:
            events.record_event(
                conn,
                "FALLBACK_RECOVERED",
                entity_type="provider",
                entity_id=primary.provider_id,
                payload={
                    "provider": primary.provider_id,
                    "model": primary.model_identifier,
                    "reason": reason,
                },
            )
        return primary
    return None
