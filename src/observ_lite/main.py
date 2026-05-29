"""CLI entrypoint for observ-lite."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from .collector import run_once
from .config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="observ-lite",
        description="Collect local Ubuntu hardware and OS observations into log files.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run-once", help="collect one snapshot and append logs")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = load_config()

    if args.command == "run-once":
        try:
            run_once(config)
        except OSError as exc:
            print(
                "observ-lite failed to write logs in {0}: {1}".format(config.log_dir, exc),
                file=sys.stderr,
            )
            return 1
        print("observ-lite wrote logs to {0}".format(config.log_dir))
        return 0

    parser.error("unknown command: {0}".format(args.command))
    return 2


if __name__ == "__main__":
    sys.exit(main())
