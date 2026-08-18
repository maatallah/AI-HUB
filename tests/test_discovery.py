"""Tests for the Phase 6 Milestone 2 discovery candidate workflow."""

from __future__ import annotations

import json

import pytest

from core import events, providers
from discovery import engine as discovery
from discovery import sources


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _payload(provider_meta=None, models=None):
    meta = dict(
        provider_meta
        or {
            "company": "Acme",
            "api_type": "OpenAI Compatible",
            "base_url": "https://api.acme.example/v1",
            "documentation_url": "https://docs.acme.example",
        }
    )
    meta["models"] = models if models is not None else [
        {"model_name": "Acme Turbo", "model_identifier": "acme-turbo"}
    ]
    return meta


def _record(name="Acme", **meta):
    return {
        "provider": {"name": name, **meta},
        "models": [{"model_name": "Acme Turbo", "model_identifier": "acme-turbo"}],
    }


def _write_json(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _event_payloads(conn, event_type):
    rows = conn.execute(
        "SELECT * FROM events WHERE event_type = ? ORDER BY id", (event_type,)
    ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def _event_types(conn):
    return [row["event_type"] for row in events.list_events(conn)]


def _add_queued(conn, name="Acme", source_type="curated"):
    cid = discovery.add_candidate(
        conn, name, _payload(), source_type, "tests/import.json", "test"
    )
    discovery.queue_candidate(conn, cid)
    return cid


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------

def test_discovery_candidates_table_present(conn):
    names = {row["name"] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    )}
    assert "discovery_candidates" in names


def test_discovery_candidate_state_constraint(conn):
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO discovery_candidates"
            " (provider_name, source_type, payload, state, content_hash, submitter)"
            " VALUES ('Bad', 'curated', '{}', 'BOGUS', 'h', 'test')"
        )
        conn.commit()


def test_discovery_candidate_provider_name_unique(conn):
    _add_queued(conn)
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO discovery_candidates (provider_name, source_type, payload, state, content_hash, submitter)"
            " VALUES ('Acme', 'curated', '{}', 'DISCOVERED', 'h', 'test')"
        )
        conn.commit()


# ---------------------------------------------------------------------------
# add / list
# ---------------------------------------------------------------------------

def test_add_candidate_records_row_and_event(conn):
    cid = discovery.add_candidate(
        conn, "Acme", _payload(), "curated", "tests/import.json", "test"
    )
    row = discovery.get_candidate(conn, cid)
    assert row["provider_name"] == "Acme"
    assert row["source_type"] == "curated"
    assert row["source_ref"] == "tests/import.json"
    assert row["state"] == "DISCOVERED"
    assert row["submitter"] == "test"
    assert len(row["content_hash"]) == 64
    assert discovery._content_hash("Acme", _payload()) == row["content_hash"]
    payloads = _event_payloads(conn, "DISCOVERY_CANDIDATE_ADDED")
    assert len(payloads) == 1
    assert payloads[0]["provider_name"] == "Acme"
    assert payloads[0]["state"] == "DISCOVERED"


def test_add_candidate_requires_name(conn):
    with pytest.raises(discovery.DiscoveryError):
        discovery.add_candidate(conn, "  ", _payload(), "curated", "ref", "test")


def test_add_candidate_rejects_bad_source_type(conn):
    with pytest.raises(discovery.DiscoveryError):
        discovery.add_candidate(conn, "Acme", _payload(), "marine", "ref", "test")


def test_add_candidate_rejects_secret_keys(conn):
    with pytest.raises(discovery.DiscoveryError):
        discovery.add_candidate(
            conn, "Acme", _payload(provider_meta={"api_key": "sk-123"}), "curated", "ref", "test"
        )


def test_add_candidate_rejects_secret_inside_model(conn):
    models = [{"model_name": "M", "model_identifier": "m-1", "access_token": "x"}]
    with pytest.raises(discovery.DiscoveryError):
        discovery.add_candidate(conn, "Acme", _payload(models=models), "curated", "ref", "test")


def test_add_candidate_rejects_unknown_payload_keys(conn):
    with pytest.raises(discovery.DiscoveryError):
        discovery.add_candidate(
            conn, "Acme", _payload(provider_meta={"mystery": 1}), "curated", "ref", "test"
        )


def test_add_candidate_duplicate_name_rejected(conn):
    discovery.add_candidate(conn, "Acme", _payload(), "curated", "ref", "test")
    with pytest.raises(discovery.DiscoveryError) as exc_info:
        discovery.add_candidate(conn, "Acme", _payload(), "curated", "ref", "test")
    assert "already exists" in str(exc_info.value)


def test_list_candidates_deterministic_order(conn):
    _add_queued(conn, "Zulu")
    _add_queued(conn, "Alpha")
    _add_queued(conn, "Mike")
    rows = discovery.list_candidates(conn)
    assert [r["provider_name"] for r in rows] == ["Zulu", "Alpha", "Mike"]


def test_list_candidates_filter_by_state(conn):
    _add_queued(conn)
    discovery.approve_candidate(conn, 1, reason="ok")
    rows = discovery.list_candidates(conn, state="PENDING_REVIEW")
    assert len(rows) == 0
    rows = discovery.list_candidates(conn, state="APPROVED")
    assert len(rows) == 1


def test_list_candidates_bad_state_rejected(conn):
    with pytest.raises(discovery.DiscoveryError):
        discovery.list_candidates(conn, state="BOGUS")


# ---------------------------------------------------------------------------
# queue / review discipline (acceptance criterion 10)
# ---------------------------------------------------------------------------

def test_queue_moves_to_pending_review(conn):
    cid = discovery.add_candidate(conn, "Acme", _payload(), "curated", "ref", "test")
    discovery.queue_candidate(conn, cid)
    assert discovery.get_candidate(conn, cid)["state"] == "PENDING_REVIEW"
    assert _event_types(conn) == ["DISCOVERY_CANDIDATE_ADDED"]


def test_queue_non_discovered_fails(conn):
    cid = _add_queued(conn)
    with pytest.raises(discovery.DiscoveryError) as exc_info:
        discovery.queue_candidate(conn, cid)
    assert "DISCOVERED" in str(exc_info.value)


def test_approve_pending_review_sets_state_and_event(conn):
    cid = _add_queued(conn)
    result = discovery.approve_candidate(conn, cid, reason="looks good")
    assert result["state"] == "APPROVED"
    assert result["reviewed_at"] is not None
    assert result["reason"] == "looks good"
    payloads = _event_payloads(conn, "DISCOVERY_CANDIDATE_APPROVED")
    assert payloads[-1]["to"] == "APPROVED"
    assert payloads[-1]["from"] == "PENDING_REVIEW"
    assert payloads[-1]["provider_name"] == "Acme"


def test_approve_on_discovered_fails_no_silent_rewrite(conn):
    cid = discovery.add_candidate(conn, "Acme", _payload(), "curated", "ref", "test")
    with pytest.raises(discovery.DiscoveryError) as exc_info:
        discovery.approve_candidate(conn, cid)
    assert "PENDING_REVIEW" in str(exc_info.value)
    assert discovery.get_candidate(conn, cid)["state"] == "DISCOVERED"
    assert not _event_payloads(conn, "DISCOVERY_CANDIDATE_APPROVED")


def test_approve_twice_fails(conn):
    cid = _add_queued(conn)
    discovery.approve_candidate(conn, cid)
    with pytest.raises(discovery.DiscoveryError):
        discovery.approve_candidate(conn, cid)


def test_approve_unknown_candidate_fails(conn):
    with pytest.raises(discovery.DiscoveryError):
        discovery.approve_candidate(conn, 999)


def test_reject_requires_reason(conn):
    cid = _add_queued(conn)
    with pytest.raises(discovery.DiscoveryError):
        discovery.reject_candidate(conn, cid, reason=None)
    with pytest.raises(discovery.DiscoveryError):
        discovery.reject_candidate(conn, cid, reason="   ")
    assert discovery.get_candidate(conn, cid)["state"] == "PENDING_REVIEW"


def test_reject_retains_row(conn):
    cid = _add_queued(conn)
    result = discovery.reject_candidate(conn, cid, reason="not a fit")
    assert result["state"] == "REJECTED"
    assert result["reviewed_at"] is not None
    assert result["reason"] == "not a fit"
    assert discovery.get_candidate(conn, cid) is not None  # never deleted (Article 5)
    payloads = _event_payloads(conn, "DISCOVERY_CANDIDATE_REJECTED")
    assert payloads[-1]["to"] == "REJECTED"


def test_reject_on_discovered_fails(conn):
    cid = discovery.add_candidate(conn, "Acme", _payload(), "curated", "ref", "test")
    with pytest.raises(discovery.DiscoveryError):
        discovery.reject_candidate(conn, cid, reason="nope")
    assert discovery.get_candidate(conn, cid)["state"] == "DISCOVERED"


def test_rejected_cannot_be_approved(conn):
    cid = _add_queued(conn)
    discovery.reject_candidate(conn, cid, reason="nope")
    with pytest.raises(discovery.DiscoveryError):
        discovery.approve_candidate(conn, cid)


def test_approve_does_not_materialize_provider_or_models_m2_gate(conn):
    """M2 scope pin: approve is a candidate-state transition only."""
    cid = _add_queued(conn, name="Acme")
    discovery.approve_candidate(conn, cid, reason="ok")
    rows = providers.list_providers(conn)
    assert len(rows) == 0
    model_count = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
    assert model_count == 0


# ---------------------------------------------------------------------------
# curated import (atomic validation, duplicate handling, provenance)
# ---------------------------------------------------------------------------

def test_import_file_creates_queued_candidates(conn, tmp_path):
    path = _write_json(tmp_path, "acme.json", _record())
    result = discovery.import_file(conn, path, submitter="test")
    assert len(result["added"]) == 1
    assert result["skipped"] == []
    row = discovery.get_candidate(conn, result["added"][0])
    assert row["state"] == "PENDING_REVIEW"
    assert row["source_type"] == "curated"
    assert row["source_ref"] == str(path)
    assert "Acme" in row["payload"]
    types = _event_types(conn)
    assert "DISCOVERY_CANDIDATE_ADDED" in types
    assert "DISCOVERY_IMPORT_COMPLETE" in types


def test_import_array_file(conn, tmp_path):
    path = _write_json(tmp_path, "multi.json", [_record("Alpha"), _record("Beta")])
    result = discovery.import_file(conn, path, submitter="test")
    assert len(result["added"]) == 2
    names = [r["provider_name"] for r in discovery.list_candidates(conn)]
    assert names == ["Alpha", "Beta"]


def test_import_invalid_json_fails_without_writes(conn, tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(discovery.DiscoveryError) as exc_info:
        discovery.import_file(conn, path, submitter="test")
    assert "Invalid JSON" in str(exc_info.value)
    assert discovery.list_candidates(conn) == []
    types = _event_types(conn)
    assert "DISCOVERY_IMPORT_ERROR" not in types  # raised to caller before any write


def test_import_missing_file_fails(conn, tmp_path):
    with pytest.raises(discovery.DiscoveryError):
        discovery.import_file(conn, tmp_path / "nope.json", submitter="test")


def test_import_invalid_record_fails_atomically(conn, tmp_path):
    records = [_record("Alpha"), {"provider": {"name": 123}}, _record("Beta")]
    path = _write_json(tmp_path, "mixed.json", records)
    with pytest.raises(discovery.DiscoveryError):
        discovery.import_file(conn, path, submitter="test")
    assert discovery.list_candidates(conn) == []  # nothing partially written


def test_import_secret_in_payload_fails_atomically(conn, tmp_path):
    records = [_record("Alpha"), _record("Beta", api_key="sk-9")]
    path = _write_json(tmp_path, "secret.json", records)
    with pytest.raises(discovery.DiscoveryError):
        discovery.import_file(conn, path, submitter="test")
    assert discovery.list_candidates(conn) == []


def test_import_duplicate_reported_not_silent(conn, tmp_path):
    first = _write_json(tmp_path, "a.json", _record("Alpha"))
    result = discovery.import_file(conn, first, submitter="test")
    assert len(result["added"]) == 1
    second = _write_json(tmp_path, "b.json", [_record("Alpha"), _record("Beta")])
    result = discovery.import_file(conn, second, submitter="test")
    assert len(result["added"]) == 1  # Beta is new
    assert result["skipped"] == ["Alpha"]  # Alpha reported, never silent
    complete = _event_payloads(conn, "DISCOVERY_IMPORT_COMPLETE")[-1]
    assert complete["skipped"] == ["Alpha"]
    assert len(discovery.list_candidates(conn)) == 2


def test_import_skips_existing_provider_name(conn, tmp_path):
    providers.add_provider(conn, "Acme", status="ACTIVE")
    path = _write_json(tmp_path, "acme.json", _record("Acme"))
    result = discovery.import_file(conn, path, submitter="test")
    assert result["added"] == []
    assert result["skipped"] == ["Acme"]


def test_import_rerun_deterministic(conn, tmp_path):
    path = _write_json(tmp_path, "a.json", _record("Alpha"))
    first = discovery.import_file(conn, path, submitter="test")
    second = discovery.import_file(conn, path, submitter="test")
    assert len(first["added"]) == 1
    assert second["added"] == []
    assert second["skipped"] == ["Alpha"]


def test_import_records_import_complete_provenance(conn, tmp_path):
    path = _write_json(tmp_path, "a.json", _record("Acme"))
    discovery.import_file(conn, path, submitter="cli:discovery import")
    complete = _event_payloads(conn, "DISCOVERY_IMPORT_COMPLETE")[-1]
    assert complete["source_type"] == "curated"
    assert complete["source_ref"] == str(path)
    assert len(complete["added"]) == 1
    added = _event_payloads(conn, "DISCOVERY_CANDIDATE_ADDED")
    assert added[0]["content_hash"]
    assert added[0]["source_ref"] == str(path)


# ---------------------------------------------------------------------------
# sources: url safety + payload validation
# ---------------------------------------------------------------------------

def test_sanitize_url_accepts_https():
    assert sources.sanitize_url("https://api.example.com/v1") == "https://api.example.com/v1"


def test_sanitize_url_rejects_credentials():
    with pytest.raises(sources.CandidateSourceError):
        sources.sanitize_url("https://user:pass@api.example.com/v1")


def test_sanitize_url_rejects_secret_query_key():
    with pytest.raises(sources.CandidateSourceError):
        sources.sanitize_url("https://api.example.com/v1?api_key=abc")


def test_sanitize_url_rejects_non_http():
    with pytest.raises(sources.CandidateSourceError):
        sources.sanitize_url("ftp://example.com")


def test_validate_payload_accepts_minimal():
    sources.validate_payload({"models": []})
    sources.validate_payload({"models": [{"model_name": "M", "model_identifier": "m"}]})


def test_validate_payload_rejects_bad_model():
    with pytest.raises(sources.CandidateSourceError):
        sources.validate_payload({"models": [{"model_name": "M"}]})


def test_validate_payload_rejects_bad_bool():
    with pytest.raises(sources.CandidateSourceError):
        sources.validate_payload(
            {"models": [{"model_name": "M", "model_identifier": "m", "supports_tools": 1}]}
        )


def test_validate_payload_rejects_secret_backed_url_in_payload():
    with pytest.raises(sources.CandidateSourceError):
        sources.validate_payload(
            {"base_url": "https://user:pass@api.example.com/v1", "models": []}
        )


# ---------------------------------------------------------------------------
# network fetch (D-P2): allowlist gate, snapshot, injectable transport
# ---------------------------------------------------------------------------

def _fake_transport(payload, status=200):
    body = json.dumps(payload).encode("utf-8")

    def transport(url, timeout_seconds):
        return status, body

    return transport


def test_run_network_requires_non_empty_allowlist(conn):
    with pytest.raises(discovery.DiscoveryError) as exc_info:
        discovery.run_network(conn, [], 10, submitter="test")
    assert "allowlist" in str(exc_info.value)


def test_run_network_imports_and_snapshots(conn):
    transport = _fake_transport([_record("Acme")])
    result = discovery.run_network(
        conn, ["https://api.example.com/providers"], 10, submitter="test", transport=transport
    )
    assert len(result["added"]) == 1
    assert result["failed"] == []
    row = discovery.get_candidate(conn, result["added"][0])
    assert row["source_type"] == "network"
    assert row["state"] == "PENDING_REVIEW"
    complete = _event_payloads(conn, "DISCOVERY_IMPORT_COMPLETE")
    snapshot = complete[0]["snapshot"]
    assert snapshot["url"] == "https://api.example.com/providers"
    assert snapshot["fetched_at"]
    assert snapshot["content_hash"]
    assert snapshot["size"] > 0


def test_run_network_imports_multiple_allowlisted_urls(conn):
    def transport(url, timeout):
        name = "Alpha" if url.endswith("/a") else "Beta"
        return 200, json.dumps([_record(name)]).encode("utf-8")

    result = discovery.run_network(
        conn, ["https://api.example.com/a", "https://api.example.com/b"], 10,
        submitter="test", transport=transport,
    )
    assert len(result["added"]) == 2
    assert len(discovery.list_candidates(conn)) == 2


def test_run_network_non_200_recorded_as_error(conn):
    transport = _fake_transport({"oops": True}, status=503)
    result = discovery.run_network(
        conn, ["https://api.example.com/providers"], 10, submitter="test", transport=transport
    )
    assert result["added"] == []
    assert result["failed"] == ["https://api.example.com/providers"]
    errors = _event_payloads(conn, "DISCOVERY_IMPORT_ERROR")
    assert "503" in errors[0]["error"]
    assert discovery.list_candidates(conn) == []


def test_run_network_unparseable_content_recorded_as_error(conn):
    transport = lambda url, timeout: (200, b"<html>not json</html>")  # noqa: E731
    result = discovery.run_network(
        conn, ["https://api.example.com/providers"], 10, submitter="test", transport=transport
    )
    assert result["failed"] == ["https://api.example.com/providers"]
    assert "Unparseable" in _event_payloads(conn, "DISCOVERY_IMPORT_ERROR")[-1]["error"]


def test_run_network_transport_exception_recorded_as_error(conn):
    def transport(url, timeout):
        raise OSError("boom")

    result = discovery.run_network(
        conn, ["https://api.example.com/providers"], 10, submitter="test", transport=transport
    )
    assert result["failed"] == ["https://api.example.com/providers"]
    assert "boom" in _event_payloads(conn, "DISCOVERY_IMPORT_ERROR")[-1]["error"]


def test_run_network_credential_url_rejected(conn):
    transport = _fake_transport([_record("Acme")])
    result = discovery.run_network(
        conn, ["https://user:pass@api.example.com/providers"], 10,
        submitter="test", transport=transport,
    )
    assert result["failed"] == ["https://user:pass@api.example.com/providers"]
    assert discovery.list_candidates(conn) == []


def test_run_network_best_effort_per_url(conn):
    good = _fake_transport([_record("Acme")])
    bad = lambda url, timeout: (200, b"<html>not json</html>")  # noqa: E731

    def transport(url, timeout):
        if "good" in url:
            return good(url, timeout)
        return bad(url, timeout)

    result = discovery.run_network(
        conn, ["https://api.example.com/good", "https://api.example.com/bad"],
        10, submitter="test", transport=transport,
    )
    assert len(result["added"]) == 1
    assert result["failed"] == ["https://api.example.com/bad"]
    errors = _event_payloads(conn, "DISCOVERY_IMPORT_ERROR")
    assert len(errors) == 1


def test_run_network_deterministic_offline(conn):
    transport = _fake_transport([_record("Alpha"), _record("Beta")])
    first = discovery.run_network(
        conn, ["https://api.example.com/providers"], 10, submitter="test", transport=transport
    )
    second = discovery.run_network(
        conn, ["https://api.example.com/providers"], 10, submitter="test", transport=transport
    )
    assert len(first["added"]) == 2
    assert second["added"] == []
    assert second["skipped"] == ["Alpha", "Beta"]


def test_record_import_error_event(conn):
    discovery.record_import_error(conn, "ref", "test", "nope")
    payloads = _event_payloads(conn, "DISCOVERY_IMPORT_ERROR")
    assert payloads[0]["error"] == "nope"
    assert payloads[0]["source_ref"] == "ref"