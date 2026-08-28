"""Tests for the post-v1 routing decision envelope (DECIDE) and RECORD."""

from __future__ import annotations

import datetime
import json
from dataclasses import replace

import pytest

from core import providers
from recommendation import recommend
from recommendation.decision import (
    CONTRACT_VERSION,
    DecisionError,
    DEFAULT_POLICY,
    STATUS_CONSTRAINT_UNSATISFIABLE,
    STATUS_INSUFFICIENT_DATA,
    STATUS_NO_CANDIDATE,
    STATUS_OK,
    build_decision_envelope,
    record_decision,
)
from scoring import ingest

NOW = datetime.datetime(2026, 8, 21, 12, 0, 0, tzinfo=datetime.timezone.utc)

FINGERPRINT_TABLES = (
    "providers",
    "models",
    "scores",
    "availability",
    "events",
    "recommendations",
    "preferences",
)

TOP_LEVEL_FIELDS = {
    "contract_version",
    "status",
    "created_at",
    "request",
    "policy",
    "total_eligible",
    "candidates",
    "selected",
    "fallback_chain",
    "rationale",
    "provenance",
    "warnings",
}
CANDIDATE_FIELDS = {
    "rank",
    "provider_id",
    "provider_name",
    "provider_status",
    "model_id",
    "model_identifier",
    "final_score",
    "confidence",
    "breakdown",
    "flags",
}
REQUEST_FIELDS = {"task", "profile", "constraints", "freshness", "limit"}
CONSTRAINT_FIELDS = {
    "min_context_window",
    "required_capabilities",
    "allowed_providers",
    "denied_providers",
    "allowed_models",
    "denied_models",
}
POLICY_FIELDS = {
    "decision_version",
    "resolved_weights",
    "aging_days",
    "latency_threshold_ms",
    "derive_operational",
    "max_chain_length",
}


def _provider(conn, name, status="ACTIVE", reason=None):
    return providers.add_provider(conn, name, status=status, status_reason=reason)


def _model(conn, pid, identifier, context_window=32000, tools=0, vision=0, json=0, streaming=0):
    conn.execute(
        "INSERT INTO models (provider_id, model_name, model_identifier, context_window,"
        " supports_tools, supports_vision, supports_json, supports_streaming)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (pid, identifier, identifier, context_window, tools, vision, json, streaming),
    )
    conn.commit()
    return conn.execute(
        "SELECT id FROM models WHERE model_identifier=?", (identifier,)
    ).fetchone()["id"]


def _score_many(conn, mid, coding=None, reasoning=None, cost=None):
    if coding is not None:
        ingest.set_score(conn, mid, "coding", coding, confidence=1.0, source="MANUAL")
    if reasoning is not None:
        ingest.set_score(conn, mid, "reasoning", reasoning, confidence=1.0, source="MANUAL")
    if cost is not None:
        ingest.set_score(conn, mid, "cost", cost, confidence=1.0, source="MANUAL")


def _backdated_score(conn, mid, dimension, value, days_ago):
    conn.execute(
        "INSERT INTO scores (model_id, dimension, value, confidence, source, scored_at)"
        " VALUES (?, ?, ?, 1.0, 'MANUAL', datetime('now', ?))",
        (mid, dimension, value, f"-{days_ago} days"),
    )
    conn.commit()


def _decide(conn, **kwargs):
    kwargs.setdefault("now", NOW)
    return build_decision_envelope(conn, kwargs.pop("task", "python"), **kwargs)


def _fingerprint(conn):
    fp = {}
    for table in FINGERPRINT_TABLES:
        fp[table] = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
    fp["events_max_rowid"] = conn.execute(
        "SELECT MAX(rowid) AS m FROM events"
    ).fetchone()["m"]
    return fp


# --- schema conformance -------------------------------------------------------


def test_envelope_contains_every_contract_field(conn):
    p = _provider(conn, "Alpha")
    m = _model(conn, p, "alpha-1")
    _score_many(conn, m, coding=90)
    env = _decide(conn)
    assert set(env) == TOP_LEVEL_FIELDS
    assert set(env["request"]) == REQUEST_FIELDS
    assert set(env["request"]["constraints"]) == CONSTRAINT_FIELDS
    assert set(env["request"]["freshness"]) == {"max_stale_days"}
    assert set(env["policy"]) == POLICY_FIELDS
    for cand in env["candidates"]:
        assert set(cand) == CANDIDATE_FIELDS
    assert env["contract_version"] == CONTRACT_VERSION == "1"


# --- statuses -----------------------------------------------------------------


def test_status_ok_with_evidence(conn):
    p = _provider(conn, "Alpha")
    m = _model(conn, p, "alpha-1")
    _score_many(conn, m, coding=90)
    env = _decide(conn)
    assert env["status"] == STATUS_OK
    assert len(env["candidates"]) == 1
    assert env["selected"] == {"rank": 0}


def test_status_no_candidate_on_empty_registry(conn):
    env = _decide(conn)
    assert env["status"] == STATUS_NO_CANDIDATE
    assert env["candidates"] == []
    assert env["selected"] is None
    assert env["fallback_chain"] == []
    assert any("eligibility" in w for w in env["warnings"])


def test_status_constraint_unsatisfiable_when_filters_empty_set(conn):
    p = _provider(conn, "Alpha")
    m = _model(conn, p, "alpha-1")
    _score_many(conn, m, coding=90)
    env = _decide(conn, denied_providers=[p])
    assert env["status"] == STATUS_CONSTRAINT_UNSATISFIABLE
    assert env["candidates"] == []
    assert any("denied_providers" in w for w in env["warnings"])


def test_status_insufficient_data_without_any_evidence(conn):
    p = _provider(conn, "Alpha")
    _model(conn, p, "alpha-1")
    policy = replace(DEFAULT_POLICY, derive_operational=False)
    env = _decide(conn, policy=policy)
    assert env["status"] == STATUS_INSUFFICIENT_DATA
    assert len(env["candidates"]) == 1
    assert all(
        info["source"] is None
        for c in env["candidates"]
        for info in c["breakdown"].values()
    )
    assert any("no candidate has evidence" in w for w in env["warnings"])


def test_invalid_inputs_raise_typed_errors(conn):
    with pytest.raises(DecisionError):
        _decide(conn, task="")
    with pytest.raises(DecisionError):
        _decide(conn, task="   ")
    with pytest.raises(DecisionError):
        _decide(conn, min_context_window=0)
    with pytest.raises(DecisionError):
        _decide(conn, max_stale_days=-1)
    with pytest.raises(DecisionError):
        _decide(conn, limit=0)
    with pytest.raises(DecisionError):
        _decide(conn, required_capabilities=("telepathy",))
    from recommendation.profiles import ProfileError

    with pytest.raises(ProfileError):
        _decide(conn, profile="nope")


# --- determinism and zero-write -----------------------------------------------


def test_identical_inputs_identical_json(conn):
    p = _provider(conn, "Alpha")
    m = _model(conn, p, "alpha-1")
    _score_many(conn, m, coding=90, reasoning=70)
    a = json.dumps(_decide(conn), sort_keys=True)
    b = json.dumps(_decide(conn), sort_keys=True)
    assert a == b


@pytest.mark.parametrize(
    "seed",
    ["empty", "evidence", "no_scores", "constraint_unsatisfiable", "insufficient_data"],
)
def test_decide_never_writes(conn, seed):
    if seed != "empty":
        p = _provider(conn, "Alpha")
        m = _model(conn, p, "alpha-1")
        if seed == "evidence":
            _score_many(conn, m, coding=90)
        elif seed == "no_scores":
            pass
        elif seed == "constraint_unsatisfiable":
            _score_many(conn, m, coding=90)
        elif seed == "insufficient_data":
            pass
    kwargs = {}
    if seed == "constraint_unsatisfiable":
        kwargs["denied_providers"] = [p]
    if seed == "insufficient_data":
        policy = replace(DEFAULT_POLICY, derive_operational=False)
        kwargs["policy"] = policy
    before = _fingerprint(conn)
    env = _decide(conn, **kwargs)
    after = _fingerprint(conn)
    assert before == after
    assert env["provenance"] == {"decision_id": None, "recorded": False}


# --- request echo and policy --------------------------------------------------


def test_request_and_policy_echo(conn):
    p = _provider(conn, "Alpha")
    m = _model(conn, p, "alpha-1")
    _score_many(conn, m, coding=90)
    env = _decide(
        conn,
        profile="reasoning",
        min_context_window=4096,
        required_capabilities=("tool_calling",),
        allowed_providers=["Alpha"],
        allowed_models=[m],
        max_stale_days=100,
        limit=5,
    )
    req = env["request"]
    assert req["task"] == "python"
    assert req["profile"] == "reasoning"
    c = req["constraints"]
    assert c["min_context_window"] == 4096
    assert c["required_capabilities"] == ["tool_calling"]
    assert c["allowed_providers"] == ["Alpha"]
    assert c["allowed_models"] == [m]
    assert req["freshness"] == {"max_stale_days": 100}
    assert req["limit"] == 5
    pol = env["policy"]
    assert pol["decision_version"] == DEFAULT_POLICY.decision_version
    assert abs(sum(pol["resolved_weights"].values()) - 1.0) < 1e-9
    assert pol["aging_days"] == {"fresh": 30, "aging": 90, "old": 180}
    assert pol["latency_threshold_ms"] == 10000
    assert pol["derive_operational"] is True
    assert pol["max_chain_length"] == 5


# --- filters ------------------------------------------------------------------


def _seed_two(conn):
    p1 = _provider(conn, "Alpha")
    p2 = _provider(conn, "Beta")
    m1 = _model(conn, p1, "alpha-1")
    m2 = _model(conn, p2, "beta-1")
    _score_many(conn, m1, coding=90, reasoning=70)
    _score_many(conn, m2, coding=80, reasoning=60)
    return p1, p2, m1, m2


def test_allow_provider_filter(conn):
    p1, p2, m1, m2 = _seed_two(conn)
    env = _decide(conn, allowed_providers=["Beta"])
    assert [c["model_identifier"] for c in env["candidates"]] == ["beta-1"]
    assert "excluded by allowed_providers: 1" in env["warnings"]
    assert env["total_eligible"] == 1


def test_deny_provider_filter_by_id(conn):
    p1, p2, m1, m2 = _seed_two(conn)
    env = _decide(conn, denied_providers=[p2])
    assert [c["model_identifier"] for c in env["candidates"]] == ["alpha-1"]
    assert "excluded by denied_providers: 1" in env["warnings"]


def test_allow_model_filter_by_identifier(conn):
    p1, p2, m1, m2 = _seed_two(conn)
    env = _decide(conn, allowed_models=["beta-1"])
    assert [c["model_identifier"] for c in env["candidates"]] == ["beta-1"]
    assert "excluded by allowed_models: 1" in env["warnings"]


def test_deny_model_filter_by_id(conn):
    p1, p2, m1, m2 = _seed_two(conn)
    env = _decide(conn, denied_models=[m1])
    assert [c["model_identifier"] for c in env["candidates"]] == ["beta-1"]
    assert "excluded by denied_models: 1" in env["warnings"]


def test_freshness_filter_excludes_only_stale(conn):
    p = _provider(conn, "Alpha")
    fresh = _model(conn, p, "fresh-1")
    stale = _model(conn, p, "stale-1")
    _score_many(conn, fresh, coding=90)
    _backdated_score(conn, stale, "coding", 95, days_ago=200)
    env = _decide(conn, max_stale_days=100)
    assert [c["model_identifier"] for c in env["candidates"]] == ["fresh-1"]
    assert (
        "excluded by freshness.max_stale_days=100: 1" in env["warnings"]
    )


def test_freshness_filter_emptying_set_is_constraint_unsatisfiable(conn):
    p = _provider(conn, "Alpha")
    m = _model(conn, p, "alpha-1")
    _backdated_score(conn, m, "coding", 90, days_ago=400)
    env = _decide(conn, max_stale_days=30)
    assert env["status"] == STATUS_CONSTRAINT_UNSATISFIABLE
    assert any("max_stale_days=30" in w for w in env["warnings"])


def test_combined_filters_precedence_counts_are_fixed(conn):
    p1, p2, m1, m2 = _seed_two(conn)
    env = _decide(conn, denied_providers=["Alpha"], denied_models=["beta-1"])
    assert env["status"] == STATUS_CONSTRAINT_UNSATISFIABLE
    assert "excluded by denied_providers: 1" in env["warnings"]
    assert "excluded by denied_models: 1" in env["warnings"]


# --- ordering and tie-breaks ---------------------------------------------------


def test_ordering_follows_sort_key_cost_tie_break(conn):
    p1 = _provider(conn, "Alpha")
    p2 = _provider(conn, "Beta")
    m1 = _model(conn, p1, "alpha-1")
    m2 = _model(conn, p2, "zeta-9")
    _score_many(conn, m1, coding=80, reasoning=60, cost=20)
    _score_many(conn, m2, coding=80, reasoning=60, cost=60)
    env = _decide(conn)
    assert [c["model_identifier"] for c in env["candidates"]] == [
        "alpha-1",
        "zeta-9",
    ]


def test_ordering_final_tie_breaks_on_model_identifier(conn):
    p1 = _provider(conn, "Alpha")
    p2 = _provider(conn, "Beta")
    _model(conn, p1, "zeta-1")
    _model(conn, p2, "alpha-1b")
    for ident in ("zeta-1", "alpha-1b"):
        mid = conn.execute(
            "SELECT id FROM models WHERE model_identifier=?", (ident,)
        ).fetchone()["id"]
        _backdated_score(conn, mid, "coding", 75, days_ago=10)
    env = _decide(conn)
    assert [c["model_identifier"] for c in env["candidates"]] == [
        "alpha-1b",
        "zeta-1",
    ]


def test_limit_truncates_but_total_eligible_reports_full(conn):
    p1, p2, m1, m2 = _seed_two(conn)
    env = _decide(conn, limit=1)
    assert len(env["candidates"]) == 1
    assert env["total_eligible"] == 2


# --- fallback chain ------------------------------------------------------------


def test_chain_respects_max_chain_length(conn):
    ids = []
    for i in range(4):
        p = _provider(conn, f"P{i}")
        m = _model(conn, p, f"m{i}")
        _score_many(conn, m, coding=90 - i)
        ids.append(m)
    policy = replace(DEFAULT_POLICY, max_chain_length=1)
    env = _decide(conn, policy=policy)
    assert len(env["fallback_chain"]) == 1
    assert env["selected"]["rank"] == 0


def test_degraded_provider_flagged_in_candidates_and_chain(conn):
    p1 = _provider(conn, "Flaky", status="DEGRADED", reason="unstable")
    p2 = _provider(conn, "Solid")
    m1 = _model(conn, p1, "flaky-1")
    m2 = _model(conn, p2, "solid-1")
    _score_many(conn, m1, coding=99)
    _score_many(conn, m2, coding=70)
    env = _decide(conn)
    top = env["candidates"][0]
    assert top["model_identifier"] == "flaky-1"
    assert top["provider_status"] == "DEGRADED"
    assert any("degraded" in f for f in top["flags"])
    assert "Fallback 1: Solid solid-1" in env["rationale"]


def test_offline_provider_never_in_chain(conn):
    p1 = _provider(conn, "Down", status="OFFLINE", reason="dead")
    p2 = _provider(conn, "Up")
    m1 = _model(conn, p1, "down-1")
    m2 = _model(conn, p2, "up-1")
    _score_many(conn, m1, coding=99)
    _score_many(conn, m2, coding=50)
    env = _decide(conn)
    assert all(c["model_identifier"] != "down-1" for c in env["candidates"])
    ranked = recommend(conn, "python")
    assert [r.model_identifier for r in ranked] == ["up-1"]


def test_rationale_carries_primary_explanation(conn):
    p = _provider(conn, "Alpha")
    m = _model(conn, p, "alpha-1")
    _score_many(conn, m, coding=90)
    env = _decide(conn)
    assert "Final score" in env["rationale"]
    assert "Recommendation for task 'python'" in env["rationale"]


# --- RECORD DECISION -----------------------------------------------------------


def _ok_envelope(conn):
    p = _provider(conn, "Alpha")
    m = _model(conn, p, "alpha-1")
    _score_many(conn, m, coding=90)
    return _decide(conn)


def test_record_persists_ranked_candidates(conn):
    env = _ok_envelope(conn)
    result = record_decision(conn, env)
    rows = conn.execute("SELECT * FROM recommendations ORDER BY rowid").fetchall()
    assert result["count"] == len(rows) == len(env["candidates"])
    assert result["decision_id"] == result["recorded_ids"][0] == rows[0]["id"]
    assert rows[0]["task"] == "python"
    assert rows[0]["profile"] == "coding"
    assert rows[0]["decision_version"] == env["policy"]["decision_version"]
    stored = json.loads(rows[0]["score_breakdown"])
    assert stored.keys() == {
        d for d in env["candidates"][0]["breakdown"]
    }
    event = conn.execute(
        "SELECT * FROM events WHERE event_type = 'RECOMMENDATION_CREATED'"
    ).fetchall()
    assert len(event) == len(rows)
    payload = json.loads(event[0]["payload"])
    assert payload["recommendation_id"] == rows[0]["id"]


def test_record_rejects_malformed_envelopes(conn):
    good = _ok_envelope(conn)
    with pytest.raises(DecisionError):
        record_decision(conn, [])
    bad_version = dict(good, contract_version="999")
    with pytest.raises(DecisionError):
        record_decision(conn, bad_version)
    bad_status = dict(good, status="MAYBE")
    with pytest.raises(DecisionError):
        record_decision(conn, bad_status)
    no_task = dict(good, request=dict(good["request"], task=""))
    with pytest.raises(DecisionError):
        record_decision(conn, no_task)
    empty_candidates = dict(good, candidates=[])
    with pytest.raises(DecisionError):
        record_decision(conn, empty_candidates)
    bad_rank = dict(good, candidates=[dict(good["candidates"][0], rank=3)])
    with pytest.raises(DecisionError):
        record_decision(conn, bad_rank)
    dup = dict(
        good,
        candidates=[good["candidates"][0], dict(good["candidates"][0], rank=1)],
    )
    with pytest.raises(DecisionError):
        record_decision(conn, dup)
    assert conn.execute("SELECT COUNT(*) AS n FROM recommendations").fetchone()["n"] == 0


def test_record_rejects_foreign_references(conn):
    env = _ok_envelope(conn)
    foreign = dict(
        env, candidates=[dict(env["candidates"][0], provider_id=9999)]
    )
    with pytest.raises(DecisionError):
        record_decision(conn, foreign)
    foreign_model = dict(env, candidates=[dict(env["candidates"][0], model_id=9999)])
    with pytest.raises(DecisionError):
        record_decision(conn, foreign_model)
    assert conn.execute("SELECT COUNT(*) AS n FROM recommendations").fetchone()["n"] == 0


def test_record_is_append_only_on_re_record(conn):
    env = _ok_envelope(conn)
    first = record_decision(conn, env)
    second = record_decision(conn, env)
    assert first["recorded_ids"] != second["recorded_ids"]
    count = conn.execute("SELECT COUNT(*) AS n FROM recommendations").fetchone()["n"]
    assert count == 2 * len(env["candidates"])
    for rec_id in first["recorded_ids"]:
        row = conn.execute(
            "SELECT * FROM recommendations WHERE id = ?", (rec_id,)
        ).fetchone()
        assert row is not None


def test_decide_after_record_still_zero_write(conn):
    env = _ok_envelope(conn)
    record_decision(conn, env)
    before = _fingerprint(conn)
    _decide(conn)
    assert _fingerprint(conn) == before


# --- F2: validation typing hardening (M2 R7) -----------------------------------


def test_record_missing_breakdown_dimension_raises_typed_error(conn):
    env = _ok_envelope(conn)
    first_breakdown = env["candidates"][0]["breakdown"]
    missing = next(iter(first_breakdown.keys()))
    good = env["candidates"][0].copy()
    good["breakdown"] = {
        d: info for d, info in first_breakdown.items() if d != missing
    }
    bad = dict(env, candidates=[good])
    with pytest.raises(DecisionError) as exc:
        record_decision(conn, bad)
    assert "missing dimensions from resolved_weights" in str(exc.value)


def test_record_breakdown_non_object_dimension_raises_typed_error(conn):
    env = _ok_envelope(conn)
    first = env["candidates"][0].copy()
    first["breakdown"] = dict(first["breakdown"])
    first["breakdown"]["cost"] = "not-an-object"
    bad = dict(env, candidates=[first])
    with pytest.raises(DecisionError):
        record_decision(conn, bad)


def test_record_missing_aged_field_raises_typed_error(conn):
    env = _ok_envelope(conn)
    first = env["candidates"][0].copy()
    first["breakdown"] = {
        d: {k: v for k, v in info.items() if k != "aged"}
        for d, info in first["breakdown"].items()
    }
    bad = dict(env, candidates=[first])
    with pytest.raises(DecisionError):
        record_decision(conn, bad)


def test_record_missing_source_field_raises_typed_error(conn):
    env = _ok_envelope(conn)
    first = env["candidates"][0].copy()
    first["breakdown"] = {
        d: {k: v for k, v in info.items() if k != "source"}
        for d, info in first["breakdown"].items()
    }
    bad = dict(env, candidates=[first])
    with pytest.raises(DecisionError):
        record_decision(conn, bad)


def test_record_bad_breakdown_value_type_raises_typed_error(conn):
    env = _ok_envelope(conn)
    first = env["candidates"][0].copy()
    first["breakdown"] = dict(first["breakdown"])
    first["breakdown"]["cost"] = dict(first["breakdown"]["cost"], value="high")
    bad = dict(env, candidates=[first])
    with pytest.raises(DecisionError):
        record_decision(conn, bad)


def test_record_valid_envelope_still_accepted(conn):
    env = _ok_envelope(conn)
    result = record_decision(conn, env)
    assert result["count"] == len(env["candidates"])
