"""AI-Hub command line interface (Phases 1-4).

Run from the repository root:

    python -m app.main init-db
    python -m app.main config show
    python -m app.main provider add Gemini --company Google
    python -m app.main provider list
    python -m app.main provider archive 1 --reason "Officially retired"
    python -m app.main monitor run
    python -m app.main monitor status
    python -m app.main monitor validate
    python -m app.main score list [--model N]
    python -m app.main score set --model N --dimension coding --value 85 --source MANUAL
    python -m app.main recommend --task "python" [--profile coding]
    python -m app.main recommend chain --task "python" [--max 5]
    python -m app.main fallback status
    python -m app.main dashboard status
    python -m app.main dashboard report <providers|scores|recommendations|monitoring|overview>
    python -m app.main dashboard history --model N [--dimension D]
    python -m app.main dashboard history --availability [--provider P]
    python -m app.main discovery import [path]
    python -m app.main discovery run [--allow-network] [--timeout N]
    python -m app.main discovery list [--state PENDING_REVIEW]
    python -m app.main discovery approve <id> [--reason]
    python -m app.main discovery reject <id> --reason
    python -m app.main benchmark import --file <path> [--name <benchmark>] [--dry-run]
    python -m app.main benchmark list [--run <id>]
    python -m app.main model list [--provider P]
    python -m app.main trend scores --model N [--dimension D] [--days N]
    python -m app.main trend availability [--provider P] [--days N]
    python -m app.main route decide --task T [--profile P] [--json] [filters]
    python -m app.main route record < envelope.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import ConfigError, effective_config_text, load_config
from benchmark import ingest as benchmark
from core import models as model_registry
from core import providers
from dashboard import history as dashboard_history
from dashboard import reports as dashboard_reports
from database import database as db_util
from discovery import engine as discovery
from fallback import build_chain, check_recovery
from monitoring import availability, health, validation
from recommendation import (
    ProfileError,
    RecommendationError,
    list_recommendations,
    recommend,
    record_recommendation,
)
from recommendation.decision import (
    DecisionError,
    DecisionPolicy,
    VALID_CAPABILITIES,
    build_decision_envelope,
    record_decision,
)
from scoring import ingest as score_ingest
from scoring import list_scores
from trend import analysis as trend


def _get_db(config) -> Path:
    return Path(config.database_path)


def cmd_init_db(args) -> None:
    config = load_config()
    conn = db_util.initialize(_get_db(config))
    db_util.validate_schema(conn)
    conn.close()
    print(f"Database initialized: {config.database_path}")
    print("Tables: " + ", ".join(sorted(db_util.EXPECTED_TABLES)))


def cmd_config(args) -> None:
    if args.action == "show":
        print(effective_config_text(load_config()))
    elif args.action == "validate":
        try:
            load_config(args.path)
            print("Configuration valid.")
        except ConfigError as exc:
            print(f"Configuration INVALID: {exc}")
            sys.exit(1)


def cmd_provider(args) -> None:
    conn = db_util.connect(_get_db(load_config()))
    try:
        if args.action == "add":
            provider_id = providers.add_provider(
                conn,
                name=args.name,
                company=args.company,
                api_type=args.api_type,
                base_url=args.base_url,
                documentation_url=args.documentation_url,
                status=args.status or "NEW",
                status_reason=args.reason,
                notes=args.notes,
            )
            print(f"Provider added: id={provider_id} name={args.name} status={args.status or 'NEW'}")
        elif args.action == "list":
            rows = providers.list_providers(conn, status=args.status)
            if not rows:
                print("No providers found.")
            for row in rows:
                reason = f" reason={row['status_reason']!r}" if row["status_reason"] else ""
                print(
                    f"#{row['id']} {row['name']} status={row['status']}"
                    f" company={row['company'] or '-'}{reason}"
                )
        elif args.action == "update":
            fields = {
                k: v
                for k, v in {
                    "name": args.name,
                    "company": args.company,
                    "api_type": args.api_type,
                    "base_url": args.base_url,
                    "documentation_url": args.documentation_url,
                    "status": args.status,
                    "status_reason": args.reason,
                    "notes": args.notes,
                }.items()
                if v is not None
            }
            if not fields:
                raise providers.RegistryError("No fields provided to update.")
            updated = providers.update_provider(conn, args.provider_id, **fields)
            print(f"Provider #{updated['id']} updated: status={updated['status']}")
        elif args.action == "archive":
            archived = providers.archive_provider(conn, args.provider_id, args.reason)
            print(
                f"Provider #{archived['id']} {archived['name']} archived"
                f" (reason={args.reason!r}). Record preserved in history."
            )
    except (providers.RegistryError,) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def cmd_monitor(args) -> None:
    config = load_config()
    conn = db_util.connect(_get_db(config))
    try:
        if args.action == "run":
            _monitor_run(config, conn, args.provider_id)
        elif args.action == "status":
            rows = availability.list_availability(conn)
            if not rows:
                print("No availability data yet.")
            for row in rows:
                reason = f" reason={row['reason']!r}" if row["reason"] else ""
                print(
                    f"#{row['provider_id']} {row['provider_name']} state={row['state']}"
                    f" failures={row['consecutive_failures']}{reason}"
                )
        elif args.action == "validate":
            results = validation.validate_seed(
                conn,
                reachability_check=config.monitoring_enabled,
            )
            for r in results:
                print(
                    f"{r['name']}: {r['event_type']}"
                    f" base_url_valid={r['base_url_valid']}"
                    f" reachable={r['reachable']}"
                    + (" details=" + ", ".join(r["details"]) if r["details"] else "")
                )
    except (providers.RegistryError, health.HealthCheckError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def _monitor_run(config, conn, provider_id) -> None:
    threshold = config.monitoring_failure_threshold
    if provider_id is not None:
        provider_ids = [provider_id]
    else:
        provider_ids = [r["id"] for r in conn.execute(
            "SELECT id FROM providers ORDER BY name"
        ).fetchall()]

    if not provider_ids:
        print("No providers to check.")
        return

    for pid in provider_ids:
        result = health.check_provider(
            conn,
            pid,
            timeout_seconds=config.monitoring_timeout_seconds,
            latency_threshold_ms=config.monitoring_latency_threshold_ms,
        )
        availability.update_availability(conn, pid, result.state)
        _apply_monitoring_lifecycle(conn, pid, result, threshold)
        name = conn.execute(
            "SELECT name FROM providers WHERE id = ?", (pid,)
        ).fetchone()["name"]
        latency = f" {result.latency_ms}ms" if result.latency_ms is not None else ""
        error = f" ({result.error})" if result.error else ""
        print(f"{name}: {result.state}{latency}{error}")


def _apply_monitoring_lifecycle(conn, pid, result, threshold) -> None:
    row = conn.execute(
        "SELECT p.status AS status, a.consecutive_failures AS failures"
        " FROM providers p"
        " LEFT JOIN availability a ON a.provider_id = p.id AND a.model_id IS NULL"
        " WHERE p.id = ?",
        (pid,),
    ).fetchone()
    if row is None:
        return
    status = row["status"]
    failures = int(row["failures"] or 0)

    if result.ok:
        if status == "OFFLINE":
            availability.apply_lifecycle(conn, pid, "ACTIVE", "Successful recovery.")
        return

    if status == "ACTIVE" and failures >= threshold:
        availability.apply_lifecycle(conn, pid, "DEGRADED", "Repeated failures.")
    elif status == "DEGRADED" and failures >= threshold:
        availability.apply_lifecycle(
            conn, pid, "OFFLINE", "Repeated monitoring failures beyond configured threshold."
        )


def cmd_score(args) -> None:
    config = load_config()
    conn = db_util.connect(_get_db(config))
    try:
        if args.action == "list":
            rows = list_scores(conn, model_id=args.model)
            if not rows:
                print("No scores stored.")
            for row in rows:
                print(
                    f"model={row['model_identifier']} provider={row['provider_name']}"
                    f" dimension={row['dimension']} value={row['value']}"
                    f" confidence={row['confidence']} source={row['source']}"
                    f" scored_at={row['scored_at']}"
                )
        elif args.action == "set":
            if args.model is None:
                raise score_ingest.ScoreError("--model is required.")
            stored = score_ingest.set_score(
                conn,
                args.model,
                args.dimension,
                args.value,
                confidence=args.confidence,
                source=args.source,
            )
            print(
                f"Score stored: model={stored['model_id']}"
                f" dimension={stored['dimension']} value={stored['value']}"
                f" source={stored['source']}"
            )
    except score_ingest.ScoreError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def cmd_recommend(args) -> None:
    config = load_config()
    conn = db_util.connect(_get_db(config))
    try:
        if args.action == "chain":
            chain = build_chain(
                conn,
                args.task,
                profile=args.profile or config.recommendation_default_profile,
                max_chain_length=args.max or config.fallback_max_chain_length,
            )
            if not chain.recommendations:
                print("No eligible recommendations.")
            for rank, rec in enumerate(chain.recommendations):
                label = "primary" if rank == 0 else f"fallback {rank}"
                print(
                    f"[{label}] {rec.provider_name} {rec.model_identifier}"
                    f" score={rec.final_score} confidence={rec.confidence}"
                    + (f" ({', '.join(rec.flags)})" if rec.flags else "")
                )
            return
        results = recommend(
            conn,
            args.task,
            profile=args.profile or config.recommendation_default_profile,
        )
        if not results:
            print("No eligible recommendations.")
        for rec in results:
            record_recommendation(
                conn, rec, decision_version=config.recommendation_decision_version
            )
        top = results[0]
        print(
            f"Recommended: {top.provider_name} {top.model_identifier}"
            f" score={top.final_score} confidence={top.confidence}"
            + (f" ({', '.join(top.flags)})" if top.flags else "")
        )
        print()
        print(top.explanation)
        print()
        recent = list_recommendations(conn, limit=1)
        if recent:
            print(f"Provenance id: {recent[0]['id']}")
    except RecommendationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def cmd_fallback(args) -> None:
    config = load_config()
    conn = db_util.connect(_get_db(config))
    try:
        if args.action == "status":
            chain = build_chain(
                conn,
                "default",
                profile=config.recommendation_default_profile,
                max_chain_length=config.fallback_max_chain_length,
            )
            if not chain.recommendations:
                print("No eligible providers.")
            for rank, rec in enumerate(chain.recommendations):
                label = "primary" if rank == 0 else f"fallback {rank}"
                print(
                    f"[{label}] {rec.provider_name} {rec.model_identifier}"
                    f" score={rec.final_score}"
                )
            recovered = check_recovery(conn, chain)
            if recovered is not None:
                print(f"Primary recovered: {recovered.provider_name}")
            else:
                print("Primary not recovered.")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def cmd_dashboard(args) -> None:
    conn = db_util.connect(_get_db(load_config()))
    try:
        if args.action == "status":
            print(dashboard_reports.report_overview(conn), end="")
        elif args.action == "report":
            report = dashboard_reports.REPORT_BUILDERS.get(args.report)
            if report is None:
                print(
                    f"Unknown report: {args.report!r}."
                    f" Choose from: {sorted(dashboard_reports.REPORT_BUILDERS)}",
                    file=sys.stderr,
                )
                sys.exit(1)
            print(report(conn), end="")
        elif args.action == "history":
            if args.availability:
                _print_availability_history(conn, args.provider)
            else:
                if args.model is None:
                    print("--model is required for score history.", file=sys.stderr)
                    sys.exit(1)
                _print_score_history(conn, args.model, args.dimension)
    finally:
        conn.close()


def cmd_discovery(args) -> None:
    config = load_config()
    conn = db_util.connect(_get_db(config))
    try:
        if args.action == "run":
            _discovery_run(config, conn, args)
        elif args.action == "import":
            _discovery_import(config, conn, args)
        elif args.action == "list":
            _discovery_list(conn, args.state)
        elif args.action == "approve":
            candidate = discovery.approve_candidate(conn, args.candidate_id, reason=args.reason)
            print(
                f"Candidate #{candidate['id']} {candidate['provider_name']} APPROVED"
                f" and materialized (provider #{candidate['materialized_provider_id']})."
            )
        elif args.action == "reject":
            candidate = discovery.reject_candidate(conn, args.candidate_id, reason=args.reason)
            print(
                f"Candidate #{candidate['id']} {candidate['provider_name']} REJECTED"
                f" (reason={args.reason!r}). Record retained in history."
            )
    except discovery.DiscoveryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def _discovery_run(config, conn, args) -> None:
    if not args.allow_network:
        raise discovery.DiscoveryError(
            "Network discovery requires the explicit --allow-network flag"
            " (user gate, Constitution Article 2)."
        )
    if not config.discovery_enabled:
        raise discovery.DiscoveryError(
            "Discovery is disabled (discovery.enabled = false). Set it to true"
            " to acquire candidates."
        )
    timeout = args.timeout or config.discovery_timeout_seconds
    summary = discovery.run_network(
        conn, config.discovery_allowlisted_urls, timeout, submitter="cli:discovery run"
    )
    print(
        f"Network discovery complete: fetched={len(summary['fetched'])}"
        f" added={len(summary['added'])} skipped={len(summary['skipped'])}"
        f" failed={len(summary['failed'])}"
    )
    for url in summary["fetched"]:
        print(f"  fetched {url}")
    for url in summary["failed"]:
        print(f"  failed {url}")


def _discovery_import(config, conn, args) -> None:
    if not config.discovery_enabled:
        raise discovery.DiscoveryError(
            "Discovery is disabled (discovery.enabled = false). Set it to true"
            " to acquire candidates."
        )
    path = Path(args.path or config.discovery_import_dir)
    if not path.exists():
        raise discovery.DiscoveryError(f"Import path not found: {path}")
    files = sorted(p for p in (path.glob("*.json") if path.is_dir() else [path]))
    if path.is_dir() and not files:
        print(f"No .json files found in {path}.")
        return
    added_total: list[int] = []
    skipped_total: list[str] = []
    failed = 0
    for file_path in files:
        try:
            result = discovery.import_file(conn, file_path, submitter="cli:discovery import")
            added_total.extend(result["added"])
            skipped_total.extend(result["skipped"])
            print(
                f"{file_path}: added={len(result['added'])} skipped={len(result['skipped'])}"
            )
        except discovery.DiscoveryError as exc:
            discovery.record_import_error(
                conn, str(file_path), "cli:discovery import", str(exc)
            )
            failed += 1
            print(f"Error importing {file_path}: {exc}", file=sys.stderr)
    print(
        f"Import complete: added={len(added_total)} skipped={len(skipped_total)}"
        f" failed={failed}"
    )


def _discovery_list(conn, state) -> None:
    rows = discovery.list_candidates(conn, state=state)
    if not rows:
        print("No discovery candidates.")
        return
    for row in rows:
        reason = f" reason={row['reason']!r}" if row["reason"] else ""
        print(
            f"#{row['id']} {row['provider_name']} state={row['state']}"
            f" source={row['source_type']} ref={row['source_ref'] or '-'}"
            f" imported_at={row['imported_at']}{reason}"
        )


def cmd_benchmark(args) -> None:
    config = load_config()
    conn = db_util.connect(_get_db(config))
    try:
        if args.action == "import":
            _benchmark_import(config, conn, args)
        elif args.action == "list":
            _benchmark_list(conn, args.run)
    except benchmark.BenchmarkError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def _benchmark_import(config, conn, args) -> None:
    path = Path(args.file or config.benchmark_import_dir)
    if not path.exists():
        raise benchmark.BenchmarkError(f"Import path not found: {path}")
    files = sorted(p for p in (path.glob("*.json") if path.is_dir() else [path]))
    if path.is_dir() and not files:
        print(f"No .json files found in {path}.")
        return
    imported = 0
    errors = 0
    for file_path in files:
        try:
            summary = benchmark.import_file(
                conn,
                file_path,
                submitter="cli:benchmark import",
                dry_run=args.dry_run,
                name=args.name,
            )
            mode = "DRY-RUN" if summary["dry_run"] else "IMPORTED"
            dup = (
                f" duplicate_of=#{summary['duplicate_of']}"
                if summary["duplicate_of"]
                else ""
            )
            print(
                f"{file_path}: {mode} run_id={summary['run_id']}"
                f" name={summary['name']} version={summary['version']}"
                f" results={summary['results']}"
                f" scored_dimensions={summary['scored_dimensions']}{dup}"
            )
            imported += 1
        except benchmark.BenchmarkError as exc:
            errors += 1
            print(f"Error importing {file_path}: {exc}", file=sys.stderr)
    mode = "Dry-run" if args.dry_run else "Import"
    print(f"{mode} complete: ok={imported} failed={errors}")


def cmd_model(args) -> None:
    conn = db_util.connect(_get_db(load_config()))
    try:
        if args.action == "list":
            rows = model_registry.list_models(conn, provider_id=args.provider)
            if not rows:
                print("No models found.")
                return
            for row in rows:
                print(
                    f"#{row['id']} {row['model_identifier']} provider={row['provider_name']}"
                    f" name={row['model_name']}"
                )
    except model_registry.ModelRegistryError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def cmd_trend(args) -> None:
    config = load_config()
    conn = db_util.connect(_get_db(config))
    window_days = config.trend_window_days if args.days is None else args.days
    try:
        if args.action == "scores":
            results = trend.score_trend(
                conn,
                args.model,
                dimension=args.dimension,
                window_days=window_days,
                min_points=config.trend_min_points,
            )
            _print_score_trends(conn, results)
        elif args.action == "availability":
            results = trend.availability_trend(
                conn,
                provider_id=args.provider,
                window_days=window_days,
                min_points=config.trend_min_points,
            )
            _print_availability_trends(results)
    except trend.TrendError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def _num(value) -> str:
    if value is None:
        return "-"
    return repr(float(value))


def _model_label(conn, model_id) -> str:
    row = conn.execute(
        "SELECT m.model_identifier, p.name AS provider_name"
        " FROM models m JOIN providers p ON p.id = m.provider_id"
        " WHERE m.id = ?",
        (model_id,),
    ).fetchone()
    if row is None or row["model_identifier"] is None:
        return str(model_id)
    return f"{row['model_identifier']} ({row['provider_name']})"


def _print_score_trends(conn, results) -> None:
    if not results:
        print("No score history.")
        return
    for r in results:
        meta = f"stdev={r['stdev']} window_days={r['window_days']}"
        if r["direction"] == trend.DIRECTION_INSUFFICIENT:
            meta = f"min_points={r['min_points']} " + meta
        print(
            f"model={_model_label(conn, r['model_id'])}"
            f" dimension={r['dimension']}"
            f" direction={r['direction']}"
            f" magnitude={_num(r['magnitude'])}"
            f" stability={_num(r['stability'])}"
            f" points={r['point_count']}/{r['series_count']}"
            f" ({meta})"
        )


def _print_availability_trends(results) -> None:
    if not results:
        print("No availability history.")
        return
    for r in results:
        meta = (
            f"domain={_num(r['domain'])} stdev={r['stdev']}"
            f" window_days={r['window_days']}"
        )
        if r["direction"] == trend.DIRECTION_INSUFFICIENT:
            meta = f"min_points={r['min_points']} " + meta
        print(
            f"provider={r['provider_id']}"
            f" direction={r['direction']}"
            f" magnitude={_num(r['magnitude'])}"
            f" stability={_num(r['stability'])}"
            f" points={r['point_count']}/{r['series_count']}"
            f" excluded_unknown={r['excluded_unknown']}"
            f" excluded_transitions={r['excluded_transitions']}"
            f" ({meta})"
        )


def _benchmark_list(conn, run) -> None:
    if run is not None:
        results = benchmark.list_run_results(conn, run)
        if not results:
            print("No benchmark results.")
            return
        headers = ("provider", "model_identifier", "metric", "raw_value", "norm_value")
        print("\t".join(headers))
        for rec in results:
            print(
                "\t".join(
                    str(rec[h])
                    for h in ("provider_name", "model_identifier", "metric", "raw_value", "norm_value")
                )
            )
        return
    rows = benchmark.list_runs(conn)
    if not rows:
        print("No benchmark runs.")
        return
    for row in rows:
        print(
            f"#{row['id']} {row['name']} v{row['version']}"
            f" origin={row['origin']} results={row['result_count']}"
            f" imported_at={row['imported_at']}"
        )


def _print_score_history(conn, model_id, dimension) -> None:
    series = dashboard_history.score_history(conn, model_id, dimension=dimension)
    if not series:
        print("No score history.")
        return
    headers = ("occurred_at", "dimension", "value", "confidence", "source")
    print("\t".join(headers))
    for rec in series:
        print(
            "\t".join(
                "" if rec[h] is None else str(rec[h]) for h in headers
            )
        )


def _print_availability_history(conn, provider_id) -> None:
    series = dashboard_history.availability_history(conn, provider_id=provider_id)
    if not series:
        print("No availability history.")
        return
    headers = ("occurred_at", "event_type", "entity_type", "entity_id")
    print("\t".join(headers))
    for rec in series:
        print(
            "\t".join(
                "" if rec[h] is None else str(rec[h]) for h in headers
            )
        )


def _ref(value: str):
    """Accept a numeric id or a literal name for provider/model filters."""
    stripped = value.strip()
    try:
        return int(stripped)
    except ValueError:
        return stripped


def cmd_route(args) -> None:
    config = load_config()
    conn = db_util.connect(_get_db(config))
    try:
        if args.action == "decide":
            envelope = build_decision_envelope(
                conn,
                args.task,
                profile=args.profile or config.recommendation_default_profile,
                min_context_window=args.min_context,
                required_capabilities=tuple(args.capability or ()),
                allowed_providers=[_ref(v) for v in (args.allow_provider or [])],
                denied_providers=[_ref(v) for v in (args.deny_provider or [])],
                allowed_models=[_ref(v) for v in (args.allow_model or [])],
                denied_models=[_ref(v) for v in (args.deny_model or [])],
                max_stale_days=args.max_stale_days,
                limit=args.limit,
                policy=DecisionPolicy.from_config(config),
            )
            if args.json:
                print(json.dumps(envelope, indent=2, sort_keys=True))
                return
            print(f"Status: {envelope['status']}")
            if envelope["selected"]:
                top = envelope["candidates"][0]
                flags = ", ".join(top["flags"])
                print(
                    f"Selected: {top['provider_name']} {top['model_identifier']}"
                    f" score={top['final_score']} confidence={top['confidence']}"
                    + (f" ({flags})" if flags else "")
                )
                for i, entry in enumerate(envelope["fallback_chain"], start=1):
                    cand = envelope["candidates"][entry["rank"]]
                    flags = ", ".join(cand["flags"])
                    print(
                        f"Fallback {i}: {cand['provider_name']}"
                        f" {cand['model_identifier']}"
                        + (f" ({flags})" if flags else "")
                    )
            if envelope["warnings"]:
                print("Warnings: " + "; ".join(envelope["warnings"]))
            print()
            print(envelope["rationale"])
        elif args.action == "record":
            raw = sys.stdin.read()
            try:
                envelope = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise DecisionError(f"stdin is not valid JSON: {exc}") from exc
            result = record_decision(conn, envelope)
            print(f"Recorded {result['count']} recommendation(s).")
            print(f"decision_id={result['decision_id']}")
            candidates = envelope["candidates"]
            for i, rec_id in enumerate(result["recorded_ids"]):
                cand = candidates[i]
                print(
                    f"id={rec_id} {cand['provider_name']}"
                    f" {cand['model_identifier']}"
                )
    except (DecisionError, ProfileError, RecommendationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-hub", description="AI-Hub Phase 1 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    db = sub.add_parser("init-db", help="Create the SQLite database and schema")
    db.set_defaults(func=cmd_init_db)

    cfg = sub.add_parser("config", help="Show or validate configuration")
    cfg_sub = cfg.add_subparsers(dest="action", required=True)
    cfg_show = cfg_sub.add_parser("show", help="Print effective configuration")
    cfg_show.set_defaults(func=cmd_config)
    cfg_val = cfg_sub.add_parser("validate", help="Validate configuration")
    cfg_val.add_argument("--path", help="Path to a config.toml file to validate")
    cfg_val.set_defaults(func=cmd_config)

    prov = sub.add_parser("provider", help="Manual provider registry")
    prov_sub = prov.add_subparsers(dest="action", required=True)

    add = prov_sub.add_parser("add", help="Add a provider")
    add.add_argument("name")
    add.add_argument("--company")
    add.add_argument("--api-type")
    add.add_argument("--base-url")
    add.add_argument("--doc-url", dest="documentation_url")
    add.add_argument("--status", choices=providers.VALID_STATUSES)
    add.add_argument("--reason")
    add.add_argument("--notes")
    add.set_defaults(func=cmd_provider)

    lst = prov_sub.add_parser("list", help="List providers")
    lst.add_argument("--status", choices=providers.VALID_STATUSES)
    lst.set_defaults(func=cmd_provider)

    upd = prov_sub.add_parser("update", help="Update a provider")
    upd.add_argument("provider_id", type=int)
    upd.add_argument("--name")
    upd.add_argument("--company")
    upd.add_argument("--api-type")
    upd.add_argument("--base-url")
    upd.add_argument("--doc-url", dest="documentation_url")
    upd.add_argument("--status", choices=providers.VALID_STATUSES)
    upd.add_argument("--reason")
    upd.add_argument("--notes")
    upd.set_defaults(func=cmd_provider)

    arc = prov_sub.add_parser("archive", help="Archive a provider")
    arc.add_argument("provider_id", type=int)
    arc.add_argument("--reason", required=True)
    arc.set_defaults(func=cmd_provider)

    mon = sub.add_parser("monitor", help="Monitoring engine (Phase 2)")
    mon_sub = mon.add_subparsers(dest="action", required=True)

    run = mon_sub.add_parser("run", help="Run health checks for all providers")
    run.add_argument("--provider", dest="provider_id", type=int, help="Check a single provider")
    run.set_defaults(func=cmd_monitor)

    status = mon_sub.add_parser("status", help="Show current availability state")
    status.set_defaults(func=cmd_monitor)

    val = mon_sub.add_parser("validate", help="Validate provider seed metadata")
    val.set_defaults(func=cmd_monitor)

    sc = sub.add_parser("score", help="Scoring engine (Phase 3)")
    sc_sub = sc.add_subparsers(dest="action", required=True)
    sc_list = sc_sub.add_parser("list", help="List stored scores")
    sc_list.add_argument("--model", type=int, help="Filter by model id")
    sc_list.set_defaults(func=cmd_score)
    sc_set = sc_sub.add_parser("set", help="Store a score for a model dimension")
    sc_set.add_argument("--model", type=int, required=True)
    sc_set.add_argument("--dimension", required=True)
    sc_set.add_argument("--value", type=float, required=True)
    sc_set.add_argument("--confidence", type=float)
    sc_set.add_argument(
        "--source",
        choices=score_ingest.ALLOWED_SOURCES,
        default="MANUAL",
    )
    sc_set.set_defaults(func=cmd_score)

    rec = sub.add_parser("recommend", help="Recommendation engine (Phase 3)")
    rec_sub = rec.add_subparsers(dest="action", required=True)
    rec_top = rec_sub.add_parser("top", help="Top recommendation (records provenance)")
    rec_top.add_argument("--task", required=True)
    rec_top.add_argument("--profile")
    rec_top.set_defaults(func=cmd_recommend)
    rec_chain = rec_sub.add_parser("chain", help="Show the full fallback chain")
    rec_chain.add_argument("--task", required=True)
    rec_chain.add_argument("--profile")
    rec_chain.add_argument("--max", type=int)
    rec_chain.set_defaults(func=cmd_recommend)

    fb = sub.add_parser("fallback", help="Fallback engine (Phase 3)")
    fb_sub = fb.add_subparsers(dest="action", required=True)
    fb_status = fb_sub.add_parser("status", help="Show current fallback chain")
    fb_status.set_defaults(func=cmd_fallback)

    dash = sub.add_parser("dashboard", help="Dashboard (Phase 4)")
    dash_sub = dash.add_subparsers(dest="action", required=True)

    dash_status = dash_sub.add_parser("status", help="Headline dashboard overview")
    dash_status.set_defaults(func=cmd_dashboard)

    dash_report = dash_sub.add_parser("report", help="Generate a report")
    dash_report.add_argument(
        "report",
        choices=sorted(dashboard_reports.REPORT_BUILDERS),
        help="Report to generate",
    )
    dash_report.set_defaults(func=cmd_dashboard)

    dash_history = dash_sub.add_parser("history", help="Reconstruct history from events")
    dash_history.add_argument("--model", type=int, help="Model id for score history")
    dash_history.add_argument("--dimension", help="Filter score history by dimension")
    dash_history.add_argument(
        "--availability", action="store_true", help="Show availability/health history"
    )
    dash_history.add_argument("--provider", type=int, help="Filter availability history by provider")
    dash_history.set_defaults(func=cmd_dashboard)

    disc = sub.add_parser("discovery", help="Ecosystem discovery (Phase 6)")
    disc_sub = disc.add_subparsers(dest="action", required=True)

    d_import = disc_sub.add_parser("import", help="Import curated candidate metadata (JSON file or directory)")
    d_import.add_argument(
        "path", nargs="?", help="JSON file or directory of *.json files (default: discovery.import_dir)"
    )
    d_import.set_defaults(func=cmd_discovery)

    d_run = disc_sub.add_parser("run", help="Fetch allowlisted public metadata endpoints into candidates")
    d_run.add_argument(
        "--allow-network", action="store_true",
        help="Explicit user gate: permit controlled network fetch (Article 2)",
    )
    d_run.add_argument("--timeout", type=int, help="Per-fetch timeout in seconds (default: discovery.timeout_seconds)")
    d_run.set_defaults(func=cmd_discovery)

    d_list = disc_sub.add_parser("list", help="List discovery candidates")
    d_list.add_argument("--state", choices=discovery.CANDIDATE_STATES, help="Filter by candidate state")
    d_list.set_defaults(func=cmd_discovery)

    d_approve = disc_sub.add_parser("approve", help="Approve a PENDING_REVIEW candidate")
    d_approve.add_argument("candidate_id", type=int, help="Candidate id to approve")
    d_approve.add_argument("--reason", help="Optional approval note")
    d_approve.set_defaults(func=cmd_discovery)

    d_reject = disc_sub.add_parser("reject", help="Reject a PENDING_REVIEW candidate (retained, never deleted)")
    d_reject.add_argument("candidate_id", type=int, help="Candidate id to reject")
    d_reject.add_argument("--reason", required=True, help="Rejection reason (required)")
    d_reject.set_defaults(func=cmd_discovery)

    bench = sub.add_parser("benchmark", help="Ecosystem benchmark ingestion (Phase 6)")
    bench_sub = bench.add_subparsers(dest="action", required=True)

    b_import = bench_sub.add_parser("import", help="Import curated benchmark results (JSON file or directory)")
    b_import.add_argument(
        "--file", help="JSON file or directory of *.json files (default: benchmark.import_dir)"
    )
    b_import.add_argument("--name", help="Benchmark name override (unused if file provides one)")
    b_import.add_argument(
        "--dry-run", action="store_true", help="Validate without mutation (no writes, no event)"
    )
    b_import.set_defaults(func=cmd_benchmark)

    b_list = bench_sub.add_parser("list", help="List benchmark runs (or the results of one run)")
    b_list.add_argument("--run", type=int, help="Show the results of a specific run id")
    b_list.set_defaults(func=cmd_benchmark)

    mod = sub.add_parser("model", help="Governed model registry (Phase 6 M3)")
    mod_sub = mod.add_subparsers(dest="action", required=True)
    m_list = mod_sub.add_parser("list", help="List models")
    m_list.add_argument("--provider", type=int, help="Filter by provider id")
    m_list.set_defaults(func=cmd_model)

    tr = sub.add_parser("trend", help="Trend analysis (Phase 6, read-only)")
    tr_sub = tr.add_subparsers(dest="action", required=True)

    tr_scores = tr_sub.add_parser(
        "scores", help="Per-dimension score trends for a model (read-only)"
    )
    tr_scores.add_argument("--model", type=int, required=True, help="Model id")
    tr_scores.add_argument(
        "--dimension", help="Restrict the analysis to one dimension"
    )
    tr_scores.add_argument(
        "--days",
        type=int,
        help="Analysis window in days anchored to the most recent point"
        " (default: trend.window_days)",
    )
    tr_scores.set_defaults(func=cmd_trend)

    tr_avail = tr_sub.add_parser(
        "availability", help="Availability success/failure trends per provider (read-only)"
    )
    tr_avail.add_argument(
        "--provider", type=int, help="Restrict the analysis to one provider"
    )
    tr_avail.add_argument(
        "--days",
        type=int,
        help="Analysis window in days anchored to the most recent point"
        " (default: trend.window_days)",
    )
    tr_avail.set_defaults(func=cmd_trend)

    route = sub.add_parser(
        "route", help="Routing decision plane (post-v1 contract)"
    )
    route_sub = route.add_subparsers(dest="action", required=True)

    r_decide = route_sub.add_parser(
        "decide", help="Compute a routing decision envelope (read-only)"
    )
    r_decide.add_argument("--task", required=True)
    r_decide.add_argument("--profile")
    r_decide.add_argument(
        "--min-context", type=int, dest="min_context",
        help="Minimum context window",
    )
    r_decide.add_argument(
        "--capability", action="append", choices=VALID_CAPABILITIES,
        help="Required capability (repeatable)",
    )
    r_decide.add_argument(
        "--allow-provider", action="append", dest="allow_provider",
        help="Only these providers, by id or name (repeatable)",
    )
    r_decide.add_argument(
        "--deny-provider", action="append", dest="deny_provider",
        help="Never these providers, by id or name (repeatable)",
    )
    r_decide.add_argument(
        "--allow-model", action="append", dest="allow_model",
        help="Only these models, by id or identifier (repeatable)",
    )
    r_decide.add_argument(
        "--deny-model", action="append", dest="deny_model",
        help="Never these models, by id or identifier (repeatable)",
    )
    r_decide.add_argument(
        "--max-stale-days", type=int, dest="max_stale_days",
        help="Exclude candidates whose newest stored evidence is older",
    )
    r_decide.add_argument("--limit", type=int, help="Truncate the candidate list")
    r_decide.add_argument(
        "--json", action="store_true", help="Print the raw decision envelope"
    )
    r_decide.set_defaults(func=cmd_route)

    r_record = route_sub.add_parser(
        "record", help="Persist a previously produced envelope (reads stdin JSON)"
    )
    r_record.set_defaults(func=cmd_route)

    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
