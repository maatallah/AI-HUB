"""AI-Hub command line interface (Phases 1-3).

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
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config import ConfigError, effective_config_text, load_config
from core import providers
from database import database as db_util
from fallback import build_chain, check_recovery
from monitoring import availability, health, validation
from recommendation import RecommendationError, list_recommendations, recommend, record_recommendation
from scoring import ingest as score_ingest
from scoring import list_scores


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

    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
