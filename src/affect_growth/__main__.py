from __future__ import annotations

import argparse
from pathlib import Path

from .evaluation import run_experiment, verify_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline synthetic functional-state pilot")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--verify-report", type=Path)
    args = parser.parse_args()
    if args.verify_report:
        if args.config or args.run_id:
            parser.error("Report verification cannot be combined with execution")
        verify_report(args.verify_report)
        print("REPORT VERIFIED")
    else:
        if not args.config or not args.run_id:
            parser.error("Execution requires --config and --run-id")
        result = run_experiment(args.config, args.run_id)
        print(f"EVIDENCE WRITTEN: {result}")


if __name__ == "__main__":
    main()
