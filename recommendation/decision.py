"""Routing decision plane (post-v1 contract).

Implements the committed Routing Decision Contract
(``docs/review/POST-V1-ROUTING-DECISION-CONTRACT.md``) and the M1 scope
(``docs/review/POST-V1-ADAPTIVE-ROUTING-M1-SCOPE.md``):

* **DECIDE** (:func:`build_decision_envelope`) is a pure, unconditionally
  read-only computation: persisted state + request arguments in, decision
  envelope out. Zero writes, zero events, zero monitoring - under every input
  combination (contract Section 11). It adds no decision logic of its own;
  ranking/scoring come from the existing Phase 3 engines.
* **RECORD DECISION** (:func:`record_decision`) is a separate operation that
  persists a previously produced envelope through the existing append-only
  provenance path (``recommendation.provenance.record_recommendation``).
  Owner-mandated invariant: **DECIDE never writes. RECORD never decides.**

Envelope statuses (contract Section 10): ``OK``, ``NO_CANDIDATE``,
``CONSTRAINT_UNSATISFIABLE``, ``INSUFFICIENT_DATA``.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional, Sequence

from app.config import DEFAULT_CONFIG
from fallback.engine import is_eligible
from recommendation.engine import Recommendation, recommend
from recommendation.explain import build_explanation
from recommendation.profiles import get_profile
from recommendation.provenance import record_recommendation
from scoring.engine import age_days

#: Wire-format version of the envelope (contract Section 15).
CONTRACT_VERSION = "1"

#: Normative envelope statuses (contract Section 10).
STATUS_OK = "OK"
STATUS_NO_CANDIDATE = "NO_CANDIDATE"
STATUS_CONSTRAINT_UNSATISFIABLE = "CONSTRAINT_UNSATISFIABLE"
STATUS_INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
STATUSES = (
    STATUS_OK,
    STATUS_NO_CANDIDATE,
    STATUS_CONSTRAINT_UNSATISFIABLE,
    STATUS_INSUFFICIENT_DATA,
)

#: Capability vocabulary accepted by the contract (contract Section 3 #4).
VALID_CAPABILITIES = ("tool_calling", "vision", "streaming", "json")


class DecisionError(ValueError):
    """Raised when a decision request or envelope violates the contract."""


@dataclass(frozen=True)
class DecisionPolicy:
    """Effective policy parameters echoed in every envelope."""

    decision_version: str
    default_profile: str
    aging_fresh_days: int
    aging_aging_days: int
    aging_old_days: int
    latency_threshold_ms: int
    derive_operational: bool
    max_chain_length: int

    @classmethod
    def from_config(cls, config) -> "DecisionPolicy":
        return cls(
            decision_version=config.recommendation_decision_version,
            default_profile=config.recommendation_default_profile,
            aging_fresh_days=config.scoring_aging_fresh_days,
            aging_aging_days=config.scoring_aging_aging_days,
            aging_old_days=config.scoring_aging_old_days,
            latency_threshold_ms=config.monitoring_latency_threshold_ms,
            derive_operational=config.scoring_derive_operational,
            max_chain_length=config.fallback_max_chain_length,
        )


def _default_policy() -> DecisionPolicy:
    scoring = DEFAULT_CONFIG["scoring"]
    monitoring = DEFAULT_CONFIG["monitoring"]
    return DecisionPolicy(
        decision_version=DEFAULT_CONFIG["recommendation"]["decision_version"],
        default_profile=DEFAULT_CONFIG["recommendation"]["default_profile"],
        aging_fresh_days=scoring["aging_fresh_days"],
        aging_aging_days=scoring["aging_aging_days"],
        aging_old_days=scoring["aging_old_days"],
        latency_threshold_ms=monitoring["latency_threshold_ms"],
        derive_operational=scoring["derive_operational"],
        max_chain_length=DEFAULT_CONFIG["fallback"]["max_chain_length"],
    )


DEFAULT_POLICY = _default_policy()


def _validate_task(task) -> str:
    if not isinstance(task, str) or not task.strip():
        raise DecisionError("task must be a non-empty string.")
    return task


def _validate_positive_int(name, value) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise DecisionError(f"{name} must be a positive integer or null.")
    return value


def _validate_refs(name, values) -> tuple:
    if values is None:
        return ()
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise DecisionError(f"{name} must be a sequence of ids or names.")
    refs = []
    for ref in values:
        if isinstance(ref, bool):
            raise DecisionError(f"{name} entries must be ids or names.")
        if isinstance(ref, int):
            refs.append(ref)
        elif isinstance(ref, str) and ref.strip():
            refs.append(ref.strip())
        else:
            raise DecisionError(f"{name} entries must be ids or names.")
    return tuple(refs)


def _matches(refs: Sequence, id_value: int, name_value: str) -> bool:
    for ref in refs:
        if isinstance(ref, int) and ref == id_value:
            return True
        if isinstance(ref, str) and ref == name_value:
            return True
    return False


def _provider_status(conn, provider_id: int) -> Optional[str]:
    row = conn.execute(
        "SELECT status FROM providers WHERE id = ?", (provider_id,)
    ).fetchone()
    return row["status"] if row is not None else None


def _newest_stored_age_days(conn, model_id: int, dimensions) -> Optional[int]:
    """Age (days) of the newest stored score across weighted dimensions.

    Returns None when the candidate has no stored evidence at all; derived
    operational dimensions are read-time computations and carry no scored_at.
    """
    placeholders = ", ".join("?" for _ in dimensions)
    row = conn.execute(
        "SELECT MAX(scored_at) AS newest FROM scores"
        f" WHERE model_id = ? AND dimension IN ({placeholders})",
        (model_id, *dimensions),
    ).fetchone()
    newest = row["newest"] if row is not None else None
    if not newest:
        return None
    return age_days(newest)


def build_decision_envelope(
    conn,
    task: str,
    *,
    profile: Optional[str] = None,
    min_context_window: Optional[int] = None,
    required_capabilities: Sequence[str] = (),
    allowed_providers: Sequence = (),
    denied_providers: Sequence = (),
    allowed_models: Sequence = (),
    denied_models: Sequence = (),
    max_stale_days: Optional[int] = None,
    limit: Optional[int] = None,
    policy: Optional[DecisionPolicy] = None,
    now: Optional[datetime.datetime] = None,
) -> dict:
    """Compute the routing decision envelope (read-only; contract Sections 3-11).

    ``now`` defaults to the current UTC time and exists so tests can pin the
    evaluation instant (same-instant determinism, Constitution Article 7).
    """
    policy = policy or DEFAULT_POLICY
    task = _validate_task(task)
    min_context_window = _validate_positive_int(
        "min_context_window", min_context_window
    )
    max_stale_days = _validate_positive_int("max_stale_days", max_stale_days)
    limit = _validate_positive_int("limit", limit)

    capabilities = tuple(required_capabilities or ())
    unknown = [c for c in capabilities if c not in VALID_CAPABILITIES]
    if unknown:
        raise DecisionError(
            f"required_capabilities entries must be from {list(VALID_CAPABILITIES)};"
            f" got {unknown}."
        )

    allow_p = _validate_refs("allowed_providers", allowed_providers)
    deny_p = _validate_refs("denied_providers", denied_providers)
    allow_m = _validate_refs("allowed_models", allowed_models)
    deny_m = _validate_refs("denied_models", denied_models)

    profile_name = profile or policy.default_profile
    weights = get_profile(conn, profile_name)  # ProfileError: typed input error

    ranked = list(
        recommend(
            conn,
            task,
            profile=profile_name,
            min_context_window=min_context_window,
            required_capabilities=capabilities,
            derive_operational=policy.derive_operational,
            fresh_days=policy.aging_fresh_days,
            aging_days=policy.aging_aging_days,
            old_days=policy.aging_old_days,
            latency_threshold_ms=policy.latency_threshold_ms,
        )
    )

    created_at = (now or datetime.datetime.now(datetime.timezone.utc)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    request_echo = {
        "task": task,
        "profile": profile_name,
        "constraints": {
            "min_context_window": min_context_window,
            "required_capabilities": sorted(capabilities),
            "allowed_providers": list(allow_p),
            "denied_providers": list(deny_p),
            "allowed_models": list(allow_m),
            "denied_models": list(deny_m),
        },
        "freshness": {"max_stale_days": max_stale_days},
        "limit": limit,
    }
    policy_echo = {
        "decision_version": policy.decision_version,
        "resolved_weights": dict(weights),
        "aging_days": {
            "fresh": policy.aging_fresh_days,
            "aging": policy.aging_aging_days,
            "old": policy.aging_old_days,
        },
        "latency_threshold_ms": policy.latency_threshold_ms,
        "derive_operational": policy.derive_operational,
        "max_chain_length": policy.max_chain_length,
    }

    def _envelope(status, candidates, warnings, rationale, fallback_chain) -> dict:
        selected = {"rank": 0} if candidates else None
        return {
            "contract_version": CONTRACT_VERSION,
            "status": status,
            "created_at": created_at,
            "request": request_echo,
            "policy": policy_echo,
            "total_eligible": len(candidates),
            "candidates": candidates,
            "selected": selected,
            "fallback_chain": fallback_chain,
            "rationale": rationale,
            "provenance": {"decision_id": None, "recorded": False},
            "warnings": warnings,
        }

    if not ranked:
        return _envelope(
            STATUS_NO_CANDIDATE,
            [],
            [
                "no eligible candidates after registry eligibility filters"
                " (provider status, context window, required capabilities)"
            ],
            "No eligible candidate exists for this request.",
            [],
        )

    warnings: list[str] = []
    filtered: list = []
    for rec in ranked:
        if allow_p and not _matches(allow_p, rec.provider_id, rec.provider_name):
            continue
        if deny_p and _matches(deny_p, rec.provider_id, rec.provider_name):
            continue
        if allow_m and not _matches(allow_m, rec.model_id, rec.model_identifier):
            continue
        if deny_m and _matches(deny_m, rec.model_id, rec.model_identifier):
            continue
        filtered.append(rec)

    if allow_p:
        excluded = sum(
            1
            for r in ranked
            if not _matches(allow_p, r.provider_id, r.provider_name)
        )
        warnings.append(f"excluded by allowed_providers: {excluded}")
    if deny_p:
        excluded = sum(
            1 for r in ranked if _matches(deny_p, r.provider_id, r.provider_name)
        )
        warnings.append(f"excluded by denied_providers: {excluded}")
    if allow_m:
        excluded = sum(
            1 for r in ranked if not _matches(allow_m, r.model_id, r.model_identifier)
        )
        warnings.append(f"excluded by allowed_models: {excluded}")
    if deny_m:
        excluded = sum(
            1 for r in ranked if _matches(deny_m, r.model_id, r.model_identifier)
        )
        warnings.append(f"excluded by denied_models: {excluded}")

    if max_stale_days is not None:
        kept = []
        stale_count = 0
        for rec in filtered:
            age = _newest_stored_age_days(conn, rec.model_id, weights)
            if age is not None and age > max_stale_days:
                stale_count += 1
            else:
                kept.append(rec)
        if stale_count:
            filtered = kept
            warnings.append(
                f"excluded by freshness.max_stale_days={max_stale_days}:"
                f" {stale_count}"
            )

    if not filtered:
        return _envelope(
            STATUS_CONSTRAINT_UNSATISFIABLE,
            [],
            warnings
            or ["all eligible candidates were excluded by caller constraints"],
            "Every eligible candidate was excluded by caller constraints.",
            [],
        )

    total_eligible = len(filtered)
    shown = filtered[:limit] if limit is not None else filtered

    has_evidence = any(
        any(info["source"] is not None for info in rec.breakdown.values())
        for rec in filtered
    )

    candidates = []
    for rank, rec in enumerate(shown):
        breakdown = {
            dimension: {
                "value": round(info["value"], 4),
                "weight": round(info["weight"], 4),
                "contribution": round(info["contribution"], 4),
                "confidence": round(info["confidence"], 4),
                "source": info["source"],
                "aged": round(info["aged"], 4) if info["aged"] is not None else None,
            }
            for dimension, info in rec.breakdown.items()
        }
        candidates.append(
            {
                "rank": rank,
                "provider_id": rec.provider_id,
                "provider_name": rec.provider_name,
                "provider_status": _provider_status(conn, rec.provider_id),
                "model_id": rec.model_id,
                "model_identifier": rec.model_identifier,
                "final_score": rec.final_score,
                "confidence": rec.confidence,
                "breakdown": breakdown,
                "flags": list(rec.flags),
            }
        )

    if not has_evidence:
        status = STATUS_INSUFFICIENT_DATA
        warnings.append(
            "no candidate has evidence for any profile-weighted dimension"
        )
    else:
        status = STATUS_OK

    chain = [
        rec
        for rec in shown
        if is_eligible(_provider_status(conn, rec.provider_id) or "")
    ][: policy.max_chain_length + 1]

    rationale = shown[0].explanation
    fallbacks = chain[1:]
    if fallbacks:
        lines = [
            f"Fallback {i}: {rec.provider_name} {rec.model_identifier}"
            + (f" ({', '.join(rec.flags)})" if rec.flags else "")
            for i, rec in enumerate(fallbacks, start=1)
        ]
        rationale += "\n\nFallback chain:\n" + "\n".join(lines)

    envelope = _envelope(
        status,
        candidates,
        warnings,
        rationale,
        [{"rank": rec_rank} for rec_rank in range(1, len(chain))],
    )
    envelope["total_eligible"] = total_eligible
    return envelope


# --- RECORD DECISION -----------------------------------------------------------


def _require(condition, message) -> None:
    if not condition:
        raise DecisionError(message)


def validate_envelope(envelope) -> dict:
    """Validate a previously produced envelope for RECORD (typed errors)."""
    _require(isinstance(envelope, dict), "envelope must be a JSON object.")
    _require(
        envelope.get("contract_version") == CONTRACT_VERSION,
        f"envelope contract_version must be {CONTRACT_VERSION!r}.",
    )
    status = envelope.get("status")
    _require(status in STATUSES, f"envelope status must be one of {list(STATUSES)}.")
    request = envelope.get("request")
    _require(isinstance(request, dict), "envelope.request is required.")
    task = request.get("task")
    _require(
        isinstance(task, str) and task.strip(),
        "envelope.request.task must be a non-empty string.",
    )
    prof = request.get("profile")
    _require(
        isinstance(prof, str) and prof.strip(),
        "envelope.request.profile must be a non-empty string.",
    )
    policy_block = envelope.get("policy")
    _require(isinstance(policy_block, dict), "envelope.policy is required.")
    version = policy_block.get("decision_version")
    _require(
        isinstance(version, str) and version.strip(),
        "envelope.policy.decision_version must be a non-empty string.",
    )
    weights = policy_block.get("resolved_weights")
    _require(
        isinstance(weights, dict) and weights,
        "envelope.policy.resolved_weights must be a non-empty object.",
    )
    candidates = envelope.get("candidates")
    _require(
        isinstance(candidates, list) and candidates,
        "envelope has no candidates to record.",
    )
    seen = set()
    for position, cand in enumerate(candidates):
        _require(
            isinstance(cand, dict), f"candidate {position} must be an object."
        )
        label = f"candidate {position}"
        _require(cand.get("rank") == position, f"{label} rank must be {position}.")
        pid = cand.get("provider_id")
        _require(
            isinstance(pid, int) and not isinstance(pid, bool),
            f"{label} provider_id must be an integer.",
        )
        mid = cand.get("model_id")
        _require(
            isinstance(mid, int) and not isinstance(mid, bool),
            f"{label} model_id must be an integer.",
        )
        _require(
            (pid, mid) not in seen,
            f"{label} duplicates provider/model of an earlier candidate.",
        )
        seen.add((pid, mid))
        _require(
            isinstance(cand.get("final_score"), (int, float)),
            f"{label} final_score must be a number.",
        )
        _require(
            isinstance(cand.get("confidence"), (int, float)),
            f"{label} confidence must be a number.",
        )
        breakdown = cand.get("breakdown")
        _require(
            isinstance(breakdown, dict) and breakdown,
            f"{label} breakdown must be a non-empty object.",
        )
        flags = cand.get("flags")
        _require(
            isinstance(flags, list) and all(isinstance(f, str) for f in flags),
            f"{label} flags must be a list of strings.",
        )
    return envelope


def record_decision(conn, envelope) -> dict:
    """Persist a previously produced envelope (RECORD DECISION).

    Validates the envelope, then appends one ``recommendations`` row per
    ranked candidate through the existing provenance path plus its
    RECOMMENDATION_CREATED event. Never updates or deletes anything;
    re-recording the same envelope creates new ids (append-only).
    Returns ``{"decision_id", "recorded_ids", "count"}``.
    """
    validate_envelope(envelope)
    task = envelope["request"]["task"]
    profile = envelope["request"]["profile"]
    version = envelope["policy"]["decision_version"]
    weights = envelope["policy"]["resolved_weights"]

    for cand in envelope["candidates"]:
        if conn.execute(
            "SELECT 1 FROM providers WHERE id = ?", (cand["provider_id"],)
        ).fetchone() is None:
            raise DecisionError(
                f"candidate rank {cand['rank']}: provider_id"
                f" {cand['provider_id']} does not exist."
            )
        if conn.execute(
            "SELECT 1 FROM models WHERE id = ?", (cand["model_id"],)
        ).fetchone() is None:
            raise DecisionError(
                f"candidate rank {cand['rank']}: model_id"
                f" {cand['model_id']} does not exist."
            )

    recorded_ids: list[str] = []
    for cand in envelope["candidates"]:
        explanation = build_explanation(
            task,
            profile,
            {
                "provider_name": cand["provider_name"],
                "model_identifier": cand["model_identifier"],
            },
            cand["final_score"],
            cand["breakdown"],
            weights,
            cand["flags"],
        )
        rec = Recommendation(
            task=task,
            profile=profile,
            provider_id=cand["provider_id"],
            provider_name=cand["provider_name"],
            model_id=cand["model_id"],
            model_identifier=cand["model_identifier"],
            final_score=cand["final_score"],
            dimensions={},
            breakdown=cand["breakdown"],
            confidence=cand["confidence"],
            explanation=explanation,
            flags=tuple(cand["flags"]),
        )
        row = record_recommendation(conn, rec, version)
        recorded_ids.append(row["id"])

    return {
        "decision_id": recorded_ids[0],
        "recorded_ids": recorded_ids,
        "count": len(recorded_ids),
    }
