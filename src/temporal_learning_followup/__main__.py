"""CLI for a separately named follow-up run or read-only verification."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .preflight import preflight
from .runner import run_full
from .verify import replay_artifact, verify_artifact, verify_audit


def main() -> int:
    parser = argparse.ArgumentParser(prog="temporal-learning-followup")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "preflight"):
        item = commands.add_parser(command); item.add_argument("--config", required=True)
        if command == "run": item.add_argument("--output", required=True)
    for command in ("verify", "replay"):
        item = commands.add_parser(command); item.add_argument("--output", required=True); item.add_argument("--with-audit", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "verify":
            return verify_audit(Path(args.output)) if args.with_audit else verify_artifact(Path(args.output))
        if args.command == "replay":
            if not args.with_audit: raise ValueError("followup replay requires --with-audit")
            return replay_artifact(Path(args.output))
        config, _ = load_config(args.config)
        if args.command == "preflight":
            print(json.dumps(preflight(config), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0
        return run_full(config, Path(args.output))
    except (OSError, ValueError) as error:
        print(f"temporal-learning-followup error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
