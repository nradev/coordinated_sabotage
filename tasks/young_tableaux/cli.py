"""Command line interface for counting Standard Young Tableaux."""

from __future__ import annotations

import argparse
import sys
from typing import Iterable

from tableaux import parse_shape
from count import count_standard_young_tableaux, generate_standard_young_tableaux


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="young-tableaux",
        description="Count and optionally list Standard Young Tableaux for a given shape.",
    )
    parser.add_argument(
        "shape",
        help="Comma separated row lengths describing the Young diagram (e.g. 3,2).",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print each tableau instead of only the final count.",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        shape = parse_shape(args.shape)
    except ValueError as exc:
        parser.error(str(exc))

    tableaux = list(generate_standard_young_tableaux(shape))
    if args.list:
        for tableau in tableaux:
            for row in tableau.as_matrix():
                print(" ".join(f"{value:2d}" for value in row))
            print("-" * 8)

    total = len(tableaux)
    plural = "tableau" if total == 1 else "tableaux"
    print(f"{total} standard Young {plural} of shape {shape}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
