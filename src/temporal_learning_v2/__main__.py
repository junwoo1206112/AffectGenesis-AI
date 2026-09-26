"""Small explicit CLI for isolated temporal-learning-v2 artifacts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .preflight import preflight
from .runner import run_full
from .verify import replay_full, verify_full, verify_full_audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="temporal-learning-v2")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--with-audit", action="store_true")
    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--config", required=True)
    for command in ("verify", "replay"):
        item = subparsers.add_parser(command)
        item.add_argument("--output", required=True)
        item.add_argument("--with-audit", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            config, _ = load_config(args.config)
            print(json.dumps(preflight(config), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0
        output = Path(args.output)
        if args.command == "run":
            config, _ = load_config(args.config)
            return run_full(config, output, with_restricted_audit=args.with_audit)
        if args.command == "verify":
            result = verify_full(output)
            return verify_full_audit(output) if args.with_audit else result
        if args.with_audit:
            verify_full_audit(output)
        return replay_full(output)
    except (OSError, ValueError) as error:
        print(f"temporal-learning-v2 error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
