"""Collect, replay and verify DBC migration evidence."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

from .evidence import validate_evidence


def main() -> None:
    from .replay import build, verify, export
    from .collector import collect
    from .records import SCHEMA
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("collect")
    p.add_argument("directory", type=Path)
    p.add_argument("--seconds", type=int, default=1800)
    p.add_argument("--max-pools", type=int, default=4)
    p.add_argument("--max-events", type=int, default=20000)
    for name in ("replay", "verify", "export", "aggregate"):
        p = sub.add_parser(name)
        p.add_argument("path", type=Path)
        if name == "replay":
            p.add_argument("--source", choices=["mainnet_capture", "synthetic_test"], default="mainnet_capture")
        if name == "export":
            p.add_argument("destination", type=Path)
    sub.add_parser("schema")
    argv = sys.argv[1:]
    if argv and argv[0] not in sub.choices and not argv[0].startswith("-"):
        argv = ["aggregate"] + argv
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            result = asyncio.run(collect(args.directory, seconds=args.seconds, max_pools=args.max_pools, max_events=args.max_events))
        elif args.command == "replay":
            result = build(args.path, source=args.source)
        elif args.command == "verify":
            result = verify(args.path)
        elif args.command == "export":
            export(args.path, args.destination)
            result = {"exported": str(args.destination)}
        elif args.command == "schema":
            result = SCHEMA
        else:
            result = validate_evidence(json.loads(args.path.read_text(encoding="utf-8"))).as_dict()
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f"{type(exc).__name__}: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
