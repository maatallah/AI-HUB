"""AI-Hub command line interface (Phase 1).

Run from the repository root:

    python -m app.main init-db
    python -m app.main config show
    python -m app.main provider add Gemini --company Google
    python -m app.main provider list
    python -m app.main provider archive 1 --reason "Officially retired"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.config import ConfigError, effective_config_text, load_config
from core import providers
from database import database as db_util


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

    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
