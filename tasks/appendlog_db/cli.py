"""Command line interface for the append log database exercise."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from appendlog_db import AppendLogDB


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="db",
        description="Minimal append-only key/value database.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("appendlog.db"),
        help="Path to the append log file (default: %(default)s).",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    set_parser = subparsers.add_parser("set", help="Store a value for a key.")
    set_parser.add_argument("key", help="Key to update.")
    set_parser.add_argument("value", help="Value to persist.")

    get_parser = subparsers.add_parser("get", help="Retrieve a value.")
    get_parser.add_argument("key", help="Key to look up.")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    db_path = args.path.expanduser().resolve()
    db = AppendLogDB(db_path)

    if args.command == "set":
        db.set(str(args.key), str(args.value))
        return 0

    if args.command == "get":
        value = db.get(str(args.key))
        if value is None:
            print("Key not found.", file=sys.stderr)
            return 1
        print(value)
        return 0

    raise RuntimeError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
