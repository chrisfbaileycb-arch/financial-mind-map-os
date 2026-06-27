"""
Command-line entry point for Financial Mind-Map OS.

Usage::

    python -m src migrate     # create the database schema
    python -m src seed        # load sample data
    python -m src sync        # run a single heartbeat and print the report
    python -m src run         # start the scheduled heartbeat loop
    python -m src graph       # print the mind-map graph as JSON
    python -m src report      # show the latest action report
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from src import db
from src.db.seed import seed_database
from src.sync.engine import heartbeat, run
from src.visualization import build_map_from_db


def _cmd_migrate(_args: argparse.Namespace) -> None:
    db.migrate()
    print("Database migration complete. Schema initialized.")


def _cmd_seed(_args: argparse.Namespace) -> None:
    seed_database()


def _cmd_sync(_args: argparse.Namespace) -> None:
    summary = heartbeat(today=date.today())
    print(json.dumps(summary, indent=2))


def _cmd_run(_args: argparse.Namespace) -> None:
    run()


def _cmd_graph(_args: argparse.Namespace) -> None:
    conn = db.get_connection()
    try:
        graph = build_map_from_db(conn).to_graph_data()
    finally:
        conn.close()
    print(json.dumps(graph, indent=2))


def _cmd_report(_args: argparse.Namespace) -> None:
    conn = db.get_connection()
    try:
        rows = list(
            conn.execute("SELECT * FROM action_reports ORDER BY id DESC LIMIT 1")
        )
        if not rows:
            print("No action reports yet. Run `python -m src sync` first.")
            return
        report = rows[0]
        print(f"Action Report #{report['id']} ({report['report_type']})")
        print(f"  {report['summary']}")
        items = db.get_action_items(conn, report["id"])
        for item in items:
            print(
                f"  [{item['urgency']}] {item['item_type']}: {item['description']}"
            )
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="src", description="Financial Mind-Map OS")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate", help="create the database schema").set_defaults(
        func=_cmd_migrate
    )
    sub.add_parser("seed", help="load sample data").set_defaults(func=_cmd_seed)
    sub.add_parser("sync", help="run a single heartbeat").set_defaults(func=_cmd_sync)
    sub.add_parser("run", help="start the heartbeat scheduler").set_defaults(
        func=_cmd_run
    )
    sub.add_parser("graph", help="print the mind-map graph as JSON").set_defaults(
        func=_cmd_graph
    )
    sub.add_parser("report", help="show the latest action report").set_defaults(
        func=_cmd_report
    )

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
